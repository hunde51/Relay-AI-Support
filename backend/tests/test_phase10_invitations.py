"""Phase 10 — Organization Invitations tests."""
import asyncio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import DEFAULT_ORG_ID
from app.services import invitation_service
from app.services.email_sender import send_invitation_email


# ── helpers ──────────────────────────────────────────────────────────────────

def _admin_headers(client: TestClient) -> dict:
    resp = client.post("/auth/token", json={
        "user_id": "USR-ADMIN", "organization_id": DEFAULT_ORG_ID, "role": "admin"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _manager_headers(client: TestClient) -> dict:
    resp = client.post("/auth/token", json={
        "user_id": "USR-MGR", "organization_id": DEFAULT_ORG_ID, "role": "manager"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _agent_headers(client: TestClient) -> dict:
    resp = client.post("/auth/token", json={
        "user_id": "USR-AGT", "organization_id": DEFAULT_ORG_ID, "role": "agent"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════════════════════════════
# 1. Invitation service — token generation & hashing
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_invitation(session_factory):
    async with session_factory() as db:
        inv, plain = await invitation_service.create_invitation(
            db, DEFAULT_ORG_ID, "test@example.com", "agent", "USR-ADMIN"
        )
        assert inv.status == "pending"
        assert inv.email == "test@example.com"
        assert inv.role == "agent"
        assert inv.organization_id == DEFAULT_ORG_ID
        assert len(plain) > 20
        assert inv.expires_at is not None


@pytest.mark.asyncio
async def test_create_invitation_duplicate_email_rejected(session_factory):
    async with session_factory() as db:
        await invitation_service.create_invitation(
            db, DEFAULT_ORG_ID, "dup@example.com", "agent", "USR-ADMIN"
        )
        with pytest.raises(ValueError, match="pending invitation already exists"):
            await invitation_service.create_invitation(
                db, DEFAULT_ORG_ID, "dup@example.com", "manager", "USR-ADMIN"
            )


@pytest.mark.asyncio
async def test_create_invitation_invalid_role(session_factory):
    async with session_factory() as db:
        with pytest.raises(ValueError, match="Invalid role"):
            await invitation_service.create_invitation(
                db, DEFAULT_ORG_ID, "bad@example.com", "superadmin", "USR-ADMIN"
            )


# ══════════════════════════════════════════════════════════════════════════════
# 2. Invitation token validation
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_validate_invitation_token(session_factory):
    async with session_factory() as db:
        inv, plain = await invitation_service.create_invitation(
            db, DEFAULT_ORG_ID, "validate@example.com", "agent", "USR-ADMIN"
        )
        found = await invitation_service.validate_invitation_token(db, plain)
        assert found is not None
        assert found.id == inv.id


@pytest.mark.asyncio
async def test_validate_invitation_token_invalid(session_factory):
    async with session_factory() as db:
        result = await invitation_service.validate_invitation_token(db, "invalidtoken123")
        assert result is None


@pytest.mark.asyncio
async def test_validate_revoked_invitation(session_factory):
    async with session_factory() as db:
        inv, plain = await invitation_service.create_invitation(
            db, DEFAULT_ORG_ID, "revoked@example.com", "agent", "USR-ADMIN"
        )
        await invitation_service.revoke_invitation(db, inv.id, DEFAULT_ORG_ID)
        result = await invitation_service.validate_invitation_token(db, plain)
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# 3. Invitation revocation
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_revoke_invitation(session_factory):
    async with session_factory() as db:
        inv, plain = await invitation_service.create_invitation(
            db, DEFAULT_ORG_ID, "revokeme@example.com", "admin", "USR-ADMIN"
        )
        ok = await invitation_service.revoke_invitation(db, inv.id, DEFAULT_ORG_ID)
        assert ok is True
        # Verify it's not valid anymore
        result = await invitation_service.validate_invitation_token(db, plain)
        assert result is None


@pytest.mark.asyncio
async def test_revoke_invitation_wrong_org(session_factory):
    async with session_factory() as db:
        inv, _ = await invitation_service.create_invitation(
            db, DEFAULT_ORG_ID, "wrongorg@example.com", "agent", "USR-ADMIN"
        )
        ok = await invitation_service.revoke_invitation(db, inv.id, "ORG-OTHER000000")
        assert ok is False


@pytest.mark.asyncio
async def test_revoke_already_accepted_invitation(session_factory):
    async with session_factory() as db:
        inv, plain = await invitation_service.create_invitation(
            db, DEFAULT_ORG_ID, "accepted@example.com", "agent", "USR-ADMIN"
        )
        inv.status = "accepted"
        await db.commit()
        ok = await invitation_service.revoke_invitation(db, inv.id, DEFAULT_ORG_ID)
        assert ok is False


# ══════════════════════════════════════════════════════════════════════════════
# 4. Invitation acceptance
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_accept_invitation(session_factory):
    async with session_factory() as db:
        inv, plain = await invitation_service.create_invitation(
            db, DEFAULT_ORG_ID, "acceptme@example.com", "manager", "USR-ADMIN"
        )
        password_hash = "fake_hashed_password"
        result = await invitation_service.accept_invitation(db, plain, "Jane Smith", password_hash)
        assert result is not None
        user, org_id = result
        assert user.email == "acceptme@example.com"
        assert user.name == "Jane Smith"
        assert user.role == "manager"
        assert user.organization_id == DEFAULT_ORG_ID
        assert user.password_hash == password_hash
        assert org_id == DEFAULT_ORG_ID

        # Verify invitation is marked accepted
        assert inv.status == "accepted"
        assert inv.accepted_at is not None


@pytest.mark.asyncio
async def test_accept_invitation_twice_fails(session_factory):
    async with session_factory() as db:
        inv, plain = await invitation_service.create_invitation(
            db, DEFAULT_ORG_ID, "double@example.com", "agent", "USR-ADMIN"
        )
        password_hash = "fake_hashed_password"
        result1 = await invitation_service.accept_invitation(db, plain, "Jane", password_hash)
        assert result1 is not None

        result2 = await invitation_service.accept_invitation(db, plain, "Jane Again", password_hash)
        assert result2 is None


@pytest.mark.asyncio
async def test_accept_invitation_expired(session_factory):
    async with session_factory() as db:
        inv, plain = await invitation_service.create_invitation(
            db, DEFAULT_ORG_ID, "expired@example.com", "agent", "USR-ADMIN"
        )
        # Manually expire the invitation
        from app.models.base import utc_now
        from datetime import timedelta
        inv.expires_at = utc_now() - timedelta(days=1)
        await db.commit()

        result = await invitation_service.accept_invitation(db, plain, "Late User", "hash")
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# 5. API endpoint tests
# ══════════════════════════════════════════════════════════════════════════════

def test_create_invitation_via_api(client: TestClient):
    headers = _admin_headers(client)
    resp = client.post("/invitations", json={
        "email": "api-invite@example.com",
        "role": "agent",
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "api-invite@example.com"
    assert data["role"] == "agent"
    assert data["status"] == "pending"
    assert "expires_at" in data
    assert "id" in data


def test_create_invitation_duplicate_via_api(client: TestClient):
    headers = _admin_headers(client)
    client.post("/invitations", json={
        "email": "dup-api@example.com",
        "role": "agent",
    }, headers=headers)
    resp = client.post("/invitations", json={
        "email": "dup-api@example.com",
        "role": "manager",
    }, headers=headers)
    assert resp.status_code == 409


def test_create_invitation_unauthorized_for_agent(client: TestClient):
    headers = _agent_headers(client)
    resp = client.post("/invitations", json={
        "email": "agentcant@example.com",
        "role": "agent",
    }, headers=headers)
    assert resp.status_code == 403


def test_create_invitation_allowed_for_manager(client: TestClient):
    headers = _manager_headers(client)
    resp = client.post("/invitations", json={
        "email": "managercan@example.com",
        "role": "agent",
    }, headers=headers)
    assert resp.status_code == 201


def test_list_invitations(client: TestClient):
    headers = _admin_headers(client)
    # Create a couple
    client.post("/invitations", json={"email": "list1@example.com", "role": "agent"}, headers=headers)
    client.post("/invitations", json={"email": "list2@example.com", "role": "manager"}, headers=headers)
    resp = client.get("/invitations", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    emails = [i["email"] for i in data]
    assert "list1@example.com" in emails
    assert "list2@example.com" in emails


def test_revoke_invitation_via_api(client: TestClient):
    headers = _admin_headers(client)
    create = client.post("/invitations", json={
        "email": "revoke-api@example.com",
        "role": "agent",
    }, headers=headers)
    inv_id = create.json()["id"]

    resp = client.delete(f"/invitations/{inv_id}", headers=headers)
    assert resp.status_code == 204

    # Verify listed as revoked
    list_resp = client.get("/invitations", headers=headers)
    invs = [i for i in list_resp.json() if i["id"] == inv_id]
    assert len(invs) == 1
    assert invs[0]["status"] == "revoked"


def test_revoke_invitation_requires_admin(client: TestClient):
    manager_headers = _manager_headers(client)
    admin_headers = _admin_headers(client)
    create = client.post("/invitations", json={
        "email": "revoke-auth@example.com",
        "role": "agent",
    }, headers=admin_headers)
    inv_id = create.json()["id"]

    resp = client.delete(f"/invitations/{inv_id}", headers=manager_headers)
    assert resp.status_code == 403


def test_validate_invitation_token_via_api(client: TestClient):
    # We need the plain token, which we can get by calling the service directly
    # Use the API to create, but we can't get the token back. Instead test
    # the validate endpoint accepts tokens from the email flow.
    # For this test, create via service and call the API validate endpoint.
    import hashlib
    headers = _admin_headers(client)
    resp = client.post("/invitations", json={
        "email": "validate-api@example.com",
        "role": "admin",
    }, headers=headers)
    assert resp.status_code == 201

    # We can't get the plain token from API response — the validate endpoint
    # needs a real token. Let's test with an invalid token.
    bad_resp = client.get("/invitations/validate/invalidtoken123")
    assert bad_resp.status_code == 200
    assert bad_resp.json()["valid"] is False


def test_accept_invitation_via_api(client: TestClient, session_factory):
    # Create an invitation via the service to get the plain token
    import asyncio

    async def _setup():
        async with session_factory() as db:
            inv, plain = await invitation_service.create_invitation(
                db, DEFAULT_ORG_ID, "accept-full@example.com", "agent", "USR-ADMIN"
            )
            return plain

    plain_token = asyncio.new_event_loop().run_until_complete(_setup())

    resp = client.post("/invitations/accept", json={
        "token": plain_token,
        "name": "Jane Smith",
        "password": "securepass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user_id"] is not None
    assert data["organization_id"] == DEFAULT_ORG_ID
    assert data["role"] == "agent"

    # Verify the user can login
    login_resp = client.post("/auth/login", json={
        "email": "accept-full@example.com",
        "password": "securepass123",
    })
    assert login_resp.status_code == 200


def test_accept_invitation_invalid_token(client: TestClient):
    resp = client.post("/invitations/accept", json={
        "token": "invalidtoken123",
        "name": "Jane",
        "password": "securepass123",
    })
    assert resp.status_code == 400


def test_accept_invitation_short_password(client: TestClient):
    resp = client.post("/invitations/accept", json={
        "token": "sometoken",
        "name": "Jane",
        "password": "12345",
    })
    assert resp.status_code == 422


def test_list_members(client: TestClient):
    headers = _admin_headers(client)
    resp = client.get("/invitations/members", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_list_members_unauthorized_for_agent(client: TestClient):
    headers = _agent_headers(client)
    resp = client.get("/invitations/members", headers=headers)
    assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# 6. Email sending
# ══════════════════════════════════════════════════════════════════════════════

def test_send_invitation_email():
    result = send_invitation_email(
        to="test@example.com",
        org_name="TestOrg",
        inviter_name="Admin",
        role="agent",
        plain_token="test_token_123",
    )
    assert result is True  # In dev mode, email is logged, not sent


# ══════════════════════════════════════════════════════════════════════════════
# 7. Cross-org isolation
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cross_org_invitation_isolation(session_factory):
    async with session_factory() as db:
        org_a = DEFAULT_ORG_ID
        org_b = "ORG-OTHER000001"

        # Create invitations in both orgs for same email
        inv_a, plain_a = await invitation_service.create_invitation(
            db, org_a, "cross@example.com", "agent", "USR-ADMIN"
        )
        inv_b, plain_b = await invitation_service.create_invitation(
            db, org_b, "cross@example.com", "manager", "USR-ADMIN"
        )

        # Org A can't see Org B's invitation
        result = await invitation_service.get_invitation_by_id(db, inv_b.id, org_a)
        assert result is None

        # Org A can't revoke Org B's invitation
        ok = await invitation_service.revoke_invitation(db, inv_b.id, org_a)
        assert ok is False

        # Accepting Org A's token creates user in Org A
        password_hash = "hash"
        user, org_id = await invitation_service.accept_invitation(db, plain_a, "Cross User", password_hash)
        assert org_id == org_a
        assert user.organization_id == org_a
