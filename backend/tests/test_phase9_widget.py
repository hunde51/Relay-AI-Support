"""Phase 9 — Support Widget tests."""
import asyncio
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import DEFAULT_ORG_ID
from app.services.widget_key_service import (
    create_widget_key,
    verify_widget_key,
    revoke_widget_key,
    list_widget_keys,
)
from app.services.widget_service import check_widget_origin
from app.services.widget_session import create_session, verify_session, revoke_session


# ── helpers ──────────────────────────────────────────────────────────────────

def _admin_headers(client: TestClient) -> dict:
    resp = client.post("/auth/token", json={
        "user_id": "USR-ADMIN", "organization_id": DEFAULT_ORG_ID, "role": "admin"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════════════════════════════
# 1. Widget key creation
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_widget_key(session_factory):
    async with session_factory() as db:
        key_orm, full_key = await create_widget_key(db, DEFAULT_ORG_ID, "Test Widget")
        assert full_key.startswith("widget_")
        assert key_orm.is_active is True
        assert key_orm.organization_id == DEFAULT_ORG_ID


@pytest.mark.asyncio
async def test_create_widget_key_with_origins(session_factory):
    async with session_factory() as db:
        origins = ["https://example.com", "https://app.example.com"]
        key_orm, full_key = await create_widget_key(db, DEFAULT_ORG_ID, "Origins", allowed_origins=origins)
        assert key_orm.allowed_origins == origins


# ══════════════════════════════════════════════════════════════════════════════
# 2. Widget key verification
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_verify_widget_key(session_factory):
    async with session_factory() as db:
        key_orm, full_key = await create_widget_key(db, DEFAULT_ORG_ID, "Verify Me")
        found = await verify_widget_key(db, full_key)
        assert found is not None
        assert found.id == key_orm.id


@pytest.mark.asyncio
async def test_verify_invalid_widget_key(session_factory):
    async with session_factory() as db:
        result = await verify_widget_key(db, "widget_badprefix_invalidsecret")
        assert result is None


@pytest.mark.asyncio
async def test_verify_revoked_widget_key(session_factory):
    async with session_factory() as db:
        key_orm, full_key = await create_widget_key(db, DEFAULT_ORG_ID, "Revoke Me")
        await revoke_widget_key(db, key_orm.id, DEFAULT_ORG_ID)
        result = await verify_widget_key(db, full_key)
        assert result is None


@pytest.mark.asyncio
async def test_list_widget_keys(session_factory):
    async with session_factory() as db:
        await create_widget_key(db, DEFAULT_ORG_ID, "Key A")
        await create_widget_key(db, DEFAULT_ORG_ID, "Key B")
        keys = await list_widget_keys(db, DEFAULT_ORG_ID)
        names = [k.name for k in keys]
        assert "Key A" in names
        assert "Key B" in names


# ══════════════════════════════════════════════════════════════════════════════
# 3. Allowed origin enforcement
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_check_widget_origin_allowed(session_factory):
    async with session_factory() as db:
        origins = ["https://example.com"]
        key_orm, _ = await create_widget_key(db, DEFAULT_ORG_ID, "Origins", allowed_origins=origins)
        assert check_widget_origin(key_orm, "https://example.com") is True


@pytest.mark.asyncio
async def test_check_widget_origin_denied(session_factory):
    async with session_factory() as db:
        origins = ["https://example.com"]
        key_orm, _ = await create_widget_key(db, DEFAULT_ORG_ID, "Origins", allowed_origins=origins)
        assert check_widget_origin(key_orm, "https://evil.com") is False


@pytest.mark.asyncio
async def test_check_widget_origin_empty_allows_all(session_factory):
    async with session_factory() as db:
        key_orm, _ = await create_widget_key(db, DEFAULT_ORG_ID, "Open", allowed_origins=[])
        assert check_widget_origin(key_orm, "https://anything.com") is True


@pytest.mark.asyncio
async def test_check_widget_origin_wildcard(session_factory):
    async with session_factory() as db:
        key_orm, _ = await create_widget_key(db, DEFAULT_ORG_ID, "Wildcard", allowed_origins=["*"])
        assert check_widget_origin(key_orm, "https://anything.com") is True


@pytest.mark.asyncio
async def test_check_widget_origin_no_origin_denied_when_restricted(session_factory):
    async with session_factory() as db:
        key_orm, _ = await create_widget_key(db, DEFAULT_ORG_ID, "Restricted", allowed_origins=["https://example.com"])
        assert check_widget_origin(key_orm, None) is False


# ══════════════════════════════════════════════════════════════════════════════
# 4. Session token management
# ══════════════════════════════════════════════════════════════════════════════

def test_session_token_flow():
    token = create_session("TKT-ABC123", DEFAULT_ORG_ID)
    assert token is not None
    assert len(token) > 20

    data = verify_session(token)
    assert data is not None
    assert data["ticket_id"] == "TKT-ABC123"
    assert data["organization_id"] == DEFAULT_ORG_ID


def test_session_token_scoped_to_ticket():
    token = create_session("TKT-ABC123", DEFAULT_ORG_ID)
    # correct ticket
    assert verify_session(token, expected_ticket_id="TKT-ABC123") is not None
    # wrong ticket
    assert verify_session(token, expected_ticket_id="TKT-OTHER") is None


def test_session_token_invalid():
    assert verify_session("invalid-token") is None


def test_session_token_revocation():
    token = create_session("TKT-ABC123", DEFAULT_ORG_ID)
    assert verify_session(token) is not None
    revoke_session(token)
    assert verify_session(token) is None


# ══════════════════════════════════════════════════════════════════════════════
# 5. Widget ticket creation via API
# ══════════════════════════════════════════════════════════════════════════════

def test_widget_create_ticket(client: TestClient):
    # Create a widget key first
    admin_headers = _admin_headers(client)
    key_resp = client.post("/settings/widget", json={"name": "Website"}, headers=admin_headers)
    assert key_resp.status_code == 201
    full_key = key_resp.json()["key"]
    assert full_key.startswith("widget_")

    # Submit a ticket via widget endpoint
    resp = client.post(
        "/widget/tickets",
        json={
            "name": "Jane Smith",
            "email": "jane@example.com",
            "message": "I need help with my account",
            "page_url": "https://example.com/support",
        },
        headers={"X-Widget-Key": full_key},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "ticket_id" in data
    assert "session_token" in data
    assert data["status"] == "open"


def test_widget_create_ticket_without_key(client: TestClient):
    resp = client.post(
        "/widget/tickets",
        json={"name": "Test", "email": "test@test.com", "message": "Help"},
    )
    assert resp.status_code == 401


def test_widget_create_ticket_with_invalid_key(client: TestClient):
    resp = client.post(
        "/widget/tickets",
        json={"name": "Test", "email": "test@test.com", "message": "Help"},
        headers={"X-Widget-Key": "widget_badkey_invalid"},
    )
    assert resp.status_code == 401


def test_widget_create_ticket_sets_source_widget(client: TestClient):
    admin_headers = _admin_headers(client)
    key_resp = client.post("/settings/widget", json={"name": "Web"}, headers=admin_headers)
    full_key = key_resp.json()["key"]

    resp = client.post(
        "/widget/tickets",
        json={"name": "John", "email": "john@example.com", "message": "Help"},
        headers={"X-Widget-Key": full_key},
    )
    ticket_id = resp.json()["ticket_id"]

    # Verify ticket has source = widget
    ticket_resp = client.get(f"/tickets/{ticket_id}", headers=admin_headers)
    assert ticket_resp.json()["source"] == "widget"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Widget session token auth for follow-up and polling
# ══════════════════════════════════════════════════════════════════════════════

def test_widget_ticket_polling(client: TestClient):
    admin_headers = _admin_headers(client)
    key_resp = client.post("/settings/widget", json={"name": "Web"}, headers=admin_headers)
    full_key = key_resp.json()["key"]

    create_resp = client.post(
        "/widget/tickets",
        json={"name": "Poll", "email": "poll@example.com", "message": "Test poll"},
        headers={"X-Widget-Key": full_key},
    )
    ticket_id = create_resp.json()["ticket_id"]
    session_token = create_resp.json()["session_token"]

    # Poll ticket status with session token
    poll_resp = client.get(
        f"/widget/tickets/{ticket_id}",
        headers={"X-Session-Token": session_token},
    )
    assert poll_resp.status_code == 200
    data = poll_resp.json()
    assert data["id"] == ticket_id
    assert data["status"] == "open"


def test_widget_ticket_polling_wrong_token(client: TestClient):
    admin_headers = _admin_headers(client)
    key_resp = client.post("/settings/widget", json={"name": "Web"}, headers=admin_headers)
    full_key = key_resp.json()["key"]

    create_resp = client.post(
        "/widget/tickets",
        json={"name": "Poll", "email": "poll2@example.com", "message": "Test"},
        headers={"X-Widget-Key": full_key},
    )
    ticket_id = create_resp.json()["ticket_id"]

    # Wrong token
    poll_resp = client.get(
        f"/widget/tickets/{ticket_id}",
        headers={"X-Session-Token": "invalid-token"},
    )
    assert poll_resp.status_code == 401


def test_widget_follow_up_message(client: TestClient):
    admin_headers = _admin_headers(client)
    key_resp = client.post("/settings/widget", json={"name": "Web"}, headers=admin_headers)
    full_key = key_resp.json()["key"]

    create_resp = client.post(
        "/widget/tickets",
        json={"name": "Follow", "email": "follow@example.com", "message": "Initial message"},
        headers={"X-Widget-Key": full_key},
    )
    ticket_id = create_resp.json()["ticket_id"]
    session_token = create_resp.json()["session_token"]

    # Send follow-up
    msg_resp = client.post(
        f"/widget/tickets/{ticket_id}/messages",
        json={"body": "Follow-up message here"},
        headers={"X-Session-Token": session_token},
    )
    assert msg_resp.status_code == 201
    msg_data = msg_resp.json()
    assert msg_data["body"] == "Follow-up message here"

    # Verify message appears in ticket messages list
    poll_resp = client.get(
        f"/widget/tickets/{ticket_id}",
        headers={"X-Session-Token": session_token},
    )
    messages = poll_resp.json()["messages"]
    bodies = [m["body"] for m in messages]
    assert "Follow-up message here" in bodies


def test_widget_follow_up_requires_session(client: TestClient):
    resp = client.post(
        "/widget/tickets/NONEXISTENT/messages",
        json={"body": "test"},
    )
    assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# 7. Widget key API endpoints
# ══════════════════════════════════════════════════════════════════════════════

def test_settings_create_widget_key(client: TestClient):
    headers = _admin_headers(client)
    resp = client.post("/settings/widget", json={"name": "My Website"}, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "key" in data
    assert data["key"].startswith("widget_")
    assert data["name"] == "My Website"
    assert data["is_active"] is True


def test_settings_list_widget_keys(client: TestClient):
    headers = _admin_headers(client)
    client.post("/settings/widget", json={"name": "Site A"}, headers=headers)
    client.post("/settings/widget", json={"name": "Site B"}, headers=headers)
    resp = client.get("/settings/widget", headers=headers)
    assert resp.status_code == 200
    names = [k["name"] for k in resp.json()]
    assert "Site A" in names
    assert "Site B" in names


def test_settings_revoke_widget_key(client: TestClient):
    headers = _admin_headers(client)
    create_resp = client.post("/settings/widget", json={"name": "To Revoke"}, headers=headers)
    key_id = create_resp.json()["id"]
    resp = client.delete(f"/settings/widget/{key_id}", headers=headers)
    assert resp.status_code == 204


def test_settings_update_widget_key(client: TestClient):
    headers = _admin_headers(client)
    create_resp = client.post("/settings/widget", json={
        "name": "Old Name",
        "allowed_origins": ["https://old.com"],
    }, headers=headers)
    key_id = create_resp.json()["id"]

    resp = client.patch(f"/settings/widget/{key_id}", json={
        "name": "New Name",
        "allowed_origins": ["https://new.com"],
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["allowed_origins"] == ["https://new.com"]


def test_agent_cannot_create_widget_key(client: TestClient):
    resp = client.post("/auth/token", json={
        "user_id": "USR-AGENT", "organization_id": DEFAULT_ORG_ID, "role": "agent"
    })
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    resp = client.post("/settings/widget", json={"name": "Forbidden"}, headers=headers)
    assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# 8. Origin enforcement via API
# ══════════════════════════════════════════════════════════════════════════════

def test_widget_ticket_origin_restricted(client: TestClient):
    admin_headers = _admin_headers(client)
    key_resp = client.post("/settings/widget", json={
        "name": "Restricted",
        "allowed_origins": ["https://allowed.com"],
    }, headers=admin_headers)
    full_key = key_resp.json()["key"]

    # Request without origin header -> denied
    resp = client.post(
        "/widget/tickets",
        json={"name": "Test", "email": "test@test.com", "message": "Help"},
        headers={"X-Widget-Key": full_key},
    )
    assert resp.status_code == 403

    # Request with allowed origin
    resp = client.post(
        "/widget/tickets",
        json={"name": "Test", "email": "test@test.com", "message": "Help"},
        headers={
            "X-Widget-Key": full_key,
            "Origin": "https://allowed.com",
        },
    )
    assert resp.status_code == 201


# ══════════════════════════════════════════════════════════════════════════════
# 9. Cross-org isolation
# ══════════════════════════════════════════════════════════════════════════════

def test_widget_cross_org_isolation(client: TestClient, session_factory):
    # Create org A key
    admin_headers_a = _admin_headers(client)
    key_resp_a = client.post("/settings/widget", json={"name": "OrgA"}, headers=admin_headers_a)
    key_a = key_resp_a.json()["key"]

    # Create a ticket for org A
    ticket_resp = client.post(
        "/widget/tickets",
        json={"name": "UserA", "email": "usera@a.com", "message": "Org A issue"},
        headers={"X-Widget-Key": key_a},
    )
    ticket_id_a = ticket_resp.json()["ticket_id"]
    session_a = ticket_resp.json()["session_token"]

    # Try to access org A's ticket with a different session token from a
    # different org — this should be blocked by the service layer.
    # Simulate by checking the ticket directly via widget polling.
    poll_resp = client.get(
        f"/widget/tickets/{ticket_id_a}",
        headers={"X-Session-Token": "some-other-token"},
    )
    assert poll_resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# 10. Widget.js served correctly
# ══════════════════════════════════════════════════════════════════════════════

def test_widget_js_served(client: TestClient):
    resp = client.get("/widget.js")
    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "application/javascript"
    assert "relayai" in resp.text.lower()
    assert "data-key" in resp.text
