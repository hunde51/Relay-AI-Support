"""Phase 8 — Email integration tests (mocked Gmail/Outlook APIs)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select


# ── Encryption ────────────────────────────────────────────────────────────────


def test_encrypt_decrypt_roundtrip():
    from app.core.encrypt import encrypt_token, decrypt_token
    plain = "my-secret-access-token-12345"
    cipher = encrypt_token(plain)
    assert cipher != plain
    assert decrypt_token(cipher) == plain


def test_encrypt_deterministic_different():
    from app.core.encrypt import encrypt_token
    t1 = encrypt_token("hello")
    t2 = encrypt_token("hello")
    # Fernet is non-deterministic (different IV each time)
    assert t1 != t2


def test_encrypt_decrypt_empty_string():
    from app.core.encrypt import encrypt_token, decrypt_token
    cipher = encrypt_token("")
    assert decrypt_token(cipher) == ""


# ── OAuth URL builders ────────────────────────────────────────────────────────


def test_build_gmail_auth_url():
    from app.services.email_service import build_gmail_auth_url
    url = build_gmail_auth_url(state="ORG-123")
    assert "accounts.google.com" in url
    assert "client_id=" in url
    assert "state=ORG-123" in url
    assert "gmail.modify" in url


def test_build_outlook_auth_url():
    from app.services.email_service import build_outlook_auth_url
    url = build_outlook_auth_url(state="ORG-456")
    assert "login.microsoftonline.com" in url
    assert "client_id=" in url
    assert "state=ORG-456" in url
    assert "Mail.ReadWrite" in url


# ── Token exchange (mocked) ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_exchange_gmail_code_success():
    from app.services.email_service import exchange_gmail_code
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "access_token": "ya29.mock-access",
        "refresh_token": "1//mock-refresh",
        "expires_in": 3600,
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.post.return_value = mock_resp
        MockClient.return_value.__aenter__.return_value = client_instance

        result = await exchange_gmail_code("mock-code")
        assert result["access_token"] == "ya29.mock-access"
        assert result["refresh_token"] == "1//mock-refresh"


@pytest.mark.asyncio
async def test_exchange_outlook_code_success():
    from app.services.email_service import exchange_outlook_code
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "access_token": "outlook-mock-access",
        "refresh_token": "outlook-mock-refresh",
        "expires_in": 3600,
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.post.return_value = mock_resp
        MockClient.return_value.__aenter__.return_value = client_instance

        result = await exchange_outlook_code("mock-code")
        assert result["access_token"] == "outlook-mock-access"


# ── Store integration (DB test) ───────────────────────────────────────────────


def test_store_integration(client, session_factory):
    """Storing an integration should encrypt tokens and persist."""
    resp = client.post("/organizations", json={
        "org_name": "EmailTest",
        "admin_email": "email@test.com",
        "admin_name": "Email Tester",
        "password": "Pass123!",
    })
    assert resp.status_code == 201
    org_id = resp.json()["organization_id"]

    async def _check():
        async with session_factory() as db:
            from app.services.email_service import store_integration
            token_data = {
                "access_token": "plain-access-token-123",
                "refresh_token": "plain-refresh-token-456",
                "expires_in": 3600,
            }
            integration = await store_integration(db, org_id, "gmail", "test@gmail.com", token_data)
            assert integration.provider == "gmail"
            assert integration.email_address == "test@gmail.com"
            assert integration.is_active is True
            assert integration.access_token_encrypted != "plain-access-token-123"
            assert integration.refresh_token_encrypted != "plain-refresh-token-456"
            assert "plain-access" not in integration.access_token_encrypted

            from app.core.encrypt import decrypt_token
            assert decrypt_token(integration.access_token_encrypted) == "plain-access-token-123"
            assert decrypt_token(integration.refresh_token_encrypted) == "plain-refresh-token-456"

    asyncio.run(_check())


# ── Polling creates tickets (mocked Gmail) ────────────────────────────────────


def test_poll_gmail_creates_ticket(client, session_factory):
    """Polling Gmail with a mock message should create a ticket."""
    resp = client.post("/organizations", json={
        "org_name": "PollGmail",
        "admin_email": "pollgmail@test.com",
        "admin_name": "Poll",
        "password": "Pass123!",
    })
    assert resp.status_code == 201
    org_id = resp.json()["organization_id"]

    async def _create_integration():
        async with session_factory() as db:
            from app.services.email_service import store_integration
            token_data = {"access_token": "mock-access", "refresh_token": "mock-refresh", "expires_in": 36000}
            return await store_integration(db, org_id, "gmail", "support@relayai.com", token_data)

    integration = asyncio.run(_create_integration())

    # Mock Gmail API responses
    mock_list_resp = MagicMock()
    mock_list_resp.json.return_value = {"messages": [{"id": "msg-001"}]}
    mock_list_resp.raise_for_status = MagicMock()

    mock_get_resp = MagicMock()
    mock_get_resp.json.return_value = {
        "id": "msg-001",
        "threadId": "thread-001",
        "labelIds": ["UNREAD", "INBOX"],
        "payload": {
            "headers": [
                {"name": "From", "value": "Customer <customer@example.com>"},
                {"name": "Subject", "value": "Help needed"},
            ],
            "mimeType": "text/plain",
            "body": {"data": "SGVscCBtZSBwbGVhc2U="},  # "Help me please" in base64
        },
        "snippet": "Help me please",
    }
    mock_get_resp.raise_for_status = MagicMock()

    mock_modify_resp = MagicMock()
    mock_modify_resp.raise_for_status = MagicMock()

    async def _run_poll():
        async with session_factory() as db:
            with patch("httpx.AsyncClient") as MockClient:
                client_instance = AsyncMock()
                # First call (list), second call (get), third call (modify)
                client_instance.get.side_effect = [mock_list_resp, mock_get_resp]
                client_instance.post.return_value = mock_modify_resp
                MockClient.return_value.__aenter__.return_value = client_instance

                from app.services.email_service import poll_gmail
                from app.db.models import EmailIntegrationORM
                fresh = await db.get(EmailIntegrationORM, integration.id)
                return await poll_gmail(db, fresh)

    count = asyncio.run(_run_poll())
    assert count >= 1

    # Verify ticket was created
    async def _verify():
        async with session_factory() as db:
            from app.db.models import TicketORM, EmailMessageORM
            tickets = (await db.execute(select(TicketORM).where(TicketORM.organization_id == org_id))).scalars().all()
            assert len(tickets) >= 1
            assert tickets[0].source == "email_gmail"
            assert "Help" in tickets[0].title

            msgs = (await db.execute(select(EmailMessageORM).where(EmailMessageORM.provider_message_id == "msg-001"))).scalars().all()
            assert len(msgs) >= 1
            assert msgs[0].direction == "inbound"

    asyncio.run(_verify())


def test_poll_duplicate_email_not_reingested(client, session_factory):
    """The same email message should not create a second ticket."""
    from app.core.encrypt import encrypt_token

    resp = client.post("/organizations", json={
        "org_name": "DedupTest",
        "admin_email": "dedup@test.com",
        "admin_name": "Dedup",
        "password": "Pass123!",
    })
    assert resp.status_code == 201
    org_id = resp.json()["organization_id"]

    async def _setup():
        async with session_factory() as db:
            from app.db.models import EmailIntegrationORM, EmailMessageORM
            from app.models.base import make_id
            encrypted = encrypt_token("dummy-access-token")
            integration = EmailIntegrationORM(
                id=make_id("EMI"),
                organization_id=org_id,
                provider="gmail",
                email_address="support@relayai.com",
                access_token_encrypted=encrypted,
                refresh_token_encrypted=encrypt_token("dummy-refresh"),
                token_expires_at=None,
                is_active=True,
            )
            db.add(integration)
            await db.flush()
            # Pre-insert the email message so it looks already processed
            db.add(EmailMessageORM(
                id=make_id("EMM"),
                email_integration_id=integration.id,
                ticket_id=None,
                provider_message_id="msg-dup-001",
                provider_thread_id="thread-dup",
                from_address="customer@example.com",
                to_address="support@relayai.com",
                subject="Duplicate",
                body_text="Already processed",
                direction="inbound",
            ))
            await db.commit()
            return integration.id

    integration_id = asyncio.run(_setup())

    mock_list_resp = MagicMock()
    mock_list_resp.json.return_value = {"messages": [{"id": "msg-dup-001"}]}
    mock_list_resp.raise_for_status = MagicMock()

    async def _run_poll():
        async with session_factory() as db:
            from app.db.models import EmailIntegrationORM
            fresh = await db.get(EmailIntegrationORM, integration_id)
            with patch("httpx.AsyncClient") as MockClient:
                client_instance = AsyncMock()
                client_instance.get.return_value = mock_list_resp
                MockClient.return_value.__aenter__.return_value = client_instance
                from app.services.email_service import poll_gmail
                return await poll_gmail(db, fresh)

    count = asyncio.run(_run_poll())
    assert count == 0  # No new tickets created


def test_disconnect_removes_integration(client, session_factory):
    """Disconnecting an integration should delete it."""
    resp = client.post("/organizations", json={
        "org_name": "DisconnectTest",
        "admin_email": "disc@test.com",
        "admin_name": "Disc",
        "password": "Pass123!",
    })
    assert resp.status_code == 201
    org_id = resp.json()["organization_id"]

    async def _setup():
        async with session_factory() as db:
            from app.services.email_service import store_integration
            token_data = {"access_token": "a", "refresh_token": "r", "expires_in": 3600}
            integration = await store_integration(db, org_id, "outlook", "out@test.com", token_data)
            return integration.id

    integration_id = asyncio.run(_setup())

    resp_data = resp.json()
    resp = client.delete(
        f"/settings/email/integrations/{integration_id}",
        headers={"Authorization": f"Bearer {resp_data['access_token']}"},
    )
    assert resp.status_code == 204

    async def _verify():
        async with session_factory() as db:
            from app.db.models import EmailIntegrationORM
            r = await db.execute(select(EmailIntegrationORM).where(EmailIntegrationORM.id == integration_id))
            assert r.scalar_one_or_none() is None

    asyncio.run(_verify())


def test_org_scoping_enforced(client, session_factory):
    """Org A should not see or disconnect org B's email integration."""
    # Create two orgs
    resp_a = client.post("/organizations", json={
        "org_name": "OrgA",
        "admin_email": "orga@test.com",
        "admin_name": "A",
        "password": "Pass123!",
    })
    assert resp_a.status_code == 201
    org_a_id = resp_a.json()["organization_id"]
    token_a = resp_a.json()["access_token"]

    resp_b = client.post("/organizations", json={
        "org_name": "OrgB",
        "admin_email": "orgb@test.com",
        "admin_name": "B",
        "password": "Pass123!",
    })
    assert resp_b.status_code == 201
    org_b_id = resp_b.json()["organization_id"]
    token_b = resp_b.json()["access_token"]

    async def _create_for_org(org_id: str):
        async with session_factory() as db:
            from app.services.email_service import store_integration
            token_data = {"access_token": "a", "refresh_token": "r", "expires_in": 3600}
            return await store_integration(db, org_id, "gmail", f"{org_id}@test.com", token_data)

    int_a = asyncio.run(_create_for_org(org_a_id))
    asyncio.run(_create_for_org(org_b_id))

    # Org A lists — should see only A's integration
    resp = client.get("/settings/email/integrations", headers={"Authorization": f"Bearer {token_a}"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == int_a.id

    # Org A cannot delete Org B's integration
    resp_b_list = client.get("/settings/email/integrations", headers={"Authorization": f"Bearer {token_b}"})
    org_b_int_id = resp_b_list.json()[0]["id"]
    resp = client.delete(f"/settings/email/integrations/{org_b_int_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 404  # Not found for org A's scope


def test_last_error_updates_on_poll_failure(client, session_factory):
    """When polling fails, last_error should be updated."""
    resp = client.post("/organizations", json={
        "org_name": "ErrorTest",
        "admin_email": "error@test.com",
        "admin_name": "Error",
        "password": "Pass123!",
    })
    assert resp.status_code == 201
    org_id = resp.json()["organization_id"]

    async def _setup():
        async with session_factory() as db:
            from app.services.email_service import store_integration
            token_data = {"access_token": "a", "refresh_token": "r", "expires_in": 3600}
            return await store_integration(db, org_id, "gmail", "err@test.com", token_data)

    integration = asyncio.run(_setup())

    async def _run_poll():
        async with session_factory() as db:
            from app.db.models import EmailIntegrationORM
            fresh = await db.get(EmailIntegrationORM, integration.id)
            with patch("httpx.AsyncClient") as MockClient:
                client_instance = AsyncMock()
                client_instance.get.side_effect = Exception("Connection refused")
                MockClient.return_value.__aenter__.return_value = client_instance
                from app.services.email_service import poll_gmail
                try:
                    await poll_gmail(db, fresh)
                except Exception:
                    pass

    asyncio.run(_run_poll())

    async def _verify():
        async with session_factory() as db:
            fresh = await db.get(type(integration), integration.id)
            assert fresh.last_error is not None

    asyncio.run(_verify())


# ── send_reply tests ──────────────────────────────────────────────────────────


def test_send_reply_gmail(client, session_factory):
    """send_reply should send a reply via Gmail API and store outbound EmailMessageORM."""
    from app.core.encrypt import encrypt_token

    resp = client.post("/organizations", json={
        "org_name": "ReplyGmail",
        "admin_email": "replygmail@test.com",
        "admin_name": "Reply",
        "password": "Pass123!",
    })
    assert resp.status_code == 201
    org_id = resp.json()["organization_id"]

    async def _seed():
        async with session_factory() as db:
            from app.db.models import EmailIntegrationORM, EmailMessageORM, TicketORM
            from app.models.base import make_id
            encrypted = encrypt_token("mock-access")
            integration = EmailIntegrationORM(
                id=make_id("EMI"),
                organization_id=org_id,
                provider="gmail",
                email_address="support@relayai.com",
                access_token_encrypted=encrypted,
                refresh_token_encrypted=encrypt_token("mock-refresh"),
                token_expires_at=None,
                is_active=True,
            )
            db.add(integration)
            await db.flush()
            ticket = TicketORM(
                id="TKT-SENDREPLY",
                organization_id=org_id,
                title="Test reply",
                message="Original",
                source="email_gmail",
            )
            db.add(ticket)
            await db.flush()
            db.add(EmailMessageORM(
                id=make_id("EMM"),
                email_integration_id=integration.id,
                ticket_id=ticket.id,
                provider_message_id="orig-msg-id",
                provider_thread_id="orig-thread-id",
                from_address="customer@example.com",
                to_address="support@relayai.com",
                subject="Original",
                body_text="Original",
                direction="inbound",
            ))
            await db.commit()
            return ticket.id, integration.id
    ticket_id, integration_id = asyncio.run(_seed())

    # Mock Gmail send API
    mock_send_resp = MagicMock()
    mock_send_resp.raise_for_status = MagicMock()

    async def _run():
        async with session_factory() as db:
            with patch("httpx.AsyncClient") as MockClient:
                client_instance = AsyncMock()
                client_instance.post.return_value = mock_send_resp
                MockClient.return_value.__aenter__.return_value = client_instance
                from app.services.email_service import send_reply
                result = await send_reply(db, ticket_id, "This is my reply")
                return result

    result = asyncio.run(_run())
    assert result is True

    # Verify outbound email message was stored
    async def _verify():
        async with session_factory() as db:
            from app.db.models import EmailMessageORM
            msgs = (await db.execute(
                select(EmailMessageORM).where(
                    EmailMessageORM.ticket_id == ticket_id,
                    EmailMessageORM.direction == "outbound",
                )
            )).scalars().all()
            assert len(msgs) == 1
            assert msgs[0].body_text == "This is my reply"
            assert msgs[0].from_address == "support@relayai.com"
            assert msgs[0].to_address == "customer@example.com"

    asyncio.run(_verify())


def test_send_reply_outlook(client, session_factory):
    """send_reply should work for Outlook-sourced tickets as well."""
    from app.core.encrypt import encrypt_token

    resp = client.post("/organizations", json={
        "org_name": "ReplyOutlook",
        "admin_email": "replyoutlook@test.com",
        "admin_name": "Reply",
        "password": "Pass123!",
    })
    assert resp.status_code == 201
    org_id = resp.json()["organization_id"]

    async def _seed():
        async with session_factory() as db:
            from app.db.models import EmailIntegrationORM, EmailMessageORM, TicketORM
            from app.models.base import make_id
            integration = EmailIntegrationORM(
                id=make_id("EMI"),
                organization_id=org_id,
                provider="outlook",
                email_address="support@relayai.com",
                access_token_encrypted=encrypt_token("mock-access"),
                refresh_token_encrypted=encrypt_token("mock-refresh"),
                token_expires_at=None,
                is_active=True,
            )
            db.add(integration)
            await db.flush()
            ticket = TicketORM(
                id="TKT-REPLY-OUTLOOK",
                organization_id=org_id,
                title="Test reply outlook",
                message="Original outlook",
                source="email_outlook",
            )
            db.add(ticket)
            await db.flush()
            db.add(EmailMessageORM(
                id=make_id("EMM"),
                email_integration_id=integration.id,
                ticket_id=ticket.id,
                provider_message_id="orig-msg-outlook",
                provider_thread_id="orig-thread-outlook",
                from_address="customer@example.com",
                to_address="support@relayai.com",
                subject="Original",
                body_text="Original",
                direction="inbound",
            ))
            await db.commit()
            return ticket.id
    ticket_id = asyncio.run(_seed())

    mock_send_resp = MagicMock()
    mock_send_resp.raise_for_status = MagicMock()

    async def _run():
        async with session_factory() as db:
            with patch("httpx.AsyncClient") as MockClient:
                client_instance = AsyncMock()
                client_instance.post.return_value = mock_send_resp
                MockClient.return_value.__aenter__.return_value = client_instance
                from app.services.email_service import send_reply
                return await send_reply(db, ticket_id, "Outlook reply body")

    assert asyncio.run(_run()) is True


def test_send_reply_non_email_ticket_returns_false(client, session_factory):
    """send_reply should return False for non-email-sourced tickets."""
    resp = client.post("/organizations", json={
        "org_name": "NonEmail",
        "admin_email": "nonemail@test.com",
        "admin_name": "Non",
        "password": "Pass123!",
    })
    assert resp.status_code == 201
    org_id = resp.json()["organization_id"]

    async def _seed():
        async with session_factory() as db:
            from app.db.models import TicketORM
            ticket = TicketORM(
                id="TKT-NONEMAIL",
                organization_id=org_id,
                title="API ticket",
                message="From API",
                source="api",
            )
            db.add(ticket)
            await db.commit()
            return ticket.id
    ticket_id = asyncio.run(_seed())

    async def _run():
        async with session_factory() as db:
            from app.services.email_service import send_reply
            return await send_reply(db, ticket_id, "Should not send")

    assert asyncio.run(_run()) is False


# ── Token refresh tests ───────────────────────────────────────────────────────


def test_get_valid_access_token_refreshes_expired(client, session_factory):
    """get_valid_access_token should refresh an expired token."""
    resp = client.post("/organizations", json={
        "org_name": "TokenTest",
        "admin_email": "token@test.com",
        "admin_name": "Token",
        "password": "Pass123!",
    })
    assert resp.status_code == 201
    org_id = resp.json()["organization_id"]

    async def _seed():
        async with session_factory() as db:
            from app.services.email_service import store_integration
            token_data = {"access_token": "old-access", "refresh_token": "old-refresh", "expires_in": -3600}
            return await store_integration(db, org_id, "gmail", "test@test.com", token_data)

    integration = asyncio.run(_seed())

    mock_refresh_resp = MagicMock()
    mock_refresh_resp.json.return_value = {
        "access_token": "new-access-token",
        "expires_in": 3600,
    }
    mock_refresh_resp.raise_for_status = MagicMock()

    async def _refresh():
        async with session_factory() as db:
            from app.db.models import EmailIntegrationORM
            from app.services.email_service import get_valid_access_token
            fresh = await db.get(EmailIntegrationORM, integration.id)
            with patch("httpx.AsyncClient") as MockClient:
                client_instance = AsyncMock()
                client_instance.post.return_value = mock_refresh_resp
                MockClient.return_value.__aenter__.return_value = client_instance
                token = await get_valid_access_token(db, fresh)
                return token

    token = asyncio.run(_refresh())
    assert token == "new-access-token"


# ── List integrations API test ────────────────────────────────────────────────


def test_list_integrations_api(client, session_factory):
    """GET /settings/email/integrations should list integrations for the org."""
    resp = client.post("/organizations", json={
        "org_name": "ListTest",
        "admin_email": "list@test.com",
        "admin_name": "List",
        "password": "Pass123!",
    })
    assert resp.status_code == 201
    org_id = resp.json()["organization_id"]
    token = resp.json()["access_token"]

    # No integrations yet — should return empty list
    resp = client.get("/settings/email/integrations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []

    # Add one integration directly
    async def _seed():
        async with session_factory() as db:
            from app.services.email_service import store_integration
            token_data = {"access_token": "a", "refresh_token": "r", "expires_in": 3600}
            return await store_integration(db, org_id, "gmail", "list@test.com", token_data)
    asyncio.run(_seed())

    resp = client.get("/settings/email/integrations", headers={"Authorization": f"Bearer {token}"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["provider"] == "gmail"
    assert data[0]["email_address"] == "list@test.com"


# ── Get single integration API test ───────────────────────────────────────────


def test_get_integration_by_id_api(client, session_factory):
    """GET /settings/email/integrations/{id} should return the integration."""
    resp = client.post("/organizations", json={
        "org_name": "GetOneTest",
        "admin_email": "getone@test.com",
        "admin_name": "GetOne",
        "password": "Pass123!",
    })
    assert resp.status_code == 201
    org_id = resp.json()["organization_id"]
    token = resp.json()["access_token"]

    async def _seed():
        async with session_factory() as db:
            from app.services.email_service import store_integration
            return await store_integration(db, org_id, "outlook", "getone@test.com", {"access_token": "a", "refresh_token": "r", "expires_in": 3600})
    integration = asyncio.run(_seed())

    resp = client.get(f"/settings/email/integrations/{integration.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["provider"] == "outlook"
    assert resp.json()["email_address"] == "getone@test.com"

    # Wrong org should get 404
    resp_bad = client.get(f"/settings/email/integrations/{integration.id}")
    assert resp_bad.status_code == 404


# ── PATCH integration API test ────────────────────────────────────────────────


def test_patch_integration_toggle_active(client, session_factory):
    """PATCH /settings/email/integrations/{id} should update is_active."""
    resp = client.post("/organizations", json={
        "org_name": "PatchTest",
        "admin_email": "patch@test.com",
        "admin_name": "Patch",
        "password": "Pass123!",
    })
    assert resp.status_code == 201
    org_id = resp.json()["organization_id"]
    token = resp.json()["access_token"]

    async def _seed():
        async with session_factory() as db:
            from app.services.email_service import store_integration
            return await store_integration(db, org_id, "gmail", "patch@test.com", {"access_token": "a", "refresh_token": "r", "expires_in": 3600})
    integration = asyncio.run(_seed())
    assert integration.is_active is True

    resp = client.patch(
        f"/settings/email/integrations/{integration.id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


# ── Poll endpoint API test ────────────────────────────────────────────────────


def test_poll_endpoint_api(client, session_factory):
    """POST /settings/email/integrations/{id}/poll should trigger a poll."""
    resp = client.post("/organizations", json={
        "org_name": "PollAPI",
        "admin_email": "pollapi@test.com",
        "admin_name": "Poll",
        "password": "Pass123!",
    })
    assert resp.status_code == 201
    org_id = resp.json()["organization_id"]
    token = resp.json()["access_token"]

    async def _seed():
        async with session_factory() as db:
            from app.services.email_service import store_integration
            return await store_integration(db, org_id, "outlook", "pollapi@test.com", {"access_token": "a", "refresh_token": "r", "expires_in": 3600})
    integration = asyncio.run(_seed())

    mock_list_resp = MagicMock()
    mock_list_resp.json.return_value = {"value": []}
    mock_list_resp.raise_for_status = MagicMock()

    with patch("app.services.email_service.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_list_resp
        MockClient.return_value.__aenter__.return_value = client_instance
        resp = client.post(
            f"/settings/email/integrations/{integration.id}/poll",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["new_messages"] == 0
