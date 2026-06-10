"""Phase 2 — API Key system tests."""
import asyncio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import DEFAULT_ORG_ID
from app.services.api_key_service import create_api_key, verify_api_key, revoke_api_key, rotate_api_key


# ── helpers ──────────────────────────────────────────────────────────────────

def _admin_headers(client: TestClient) -> dict:
    """Get JWT headers for an admin user in the default org."""
    resp = client.post("/auth/token", json={
        "user_id": "USR-ADMIN", "organization_id": DEFAULT_ORG_ID, "role": "admin"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── unit: key generation & verification ──────────────────────────────────────

@pytest.mark.asyncio
async def test_create_and_verify_key(session_factory):
    async with session_factory() as db:
        key_orm, full_key = await create_api_key(db, DEFAULT_ORG_ID, "Test Key")
        assert full_key.startswith("relay_")
        assert key_orm.is_active is True

        found = await verify_api_key(db, full_key)
        assert found is not None
        assert found.id == key_orm.id


@pytest.mark.asyncio
async def test_invalid_key_returns_none(session_factory):
    async with session_factory() as db:
        result = await verify_api_key(db, "relay_badprefix_invalidsecret")
        assert result is None


@pytest.mark.asyncio
async def test_revoke_key(session_factory):
    async with session_factory() as db:
        key_orm, full_key = await create_api_key(db, DEFAULT_ORG_ID, "Revoke Me")
        await revoke_api_key(db, key_orm.id, DEFAULT_ORG_ID)
        result = await verify_api_key(db, full_key)
        assert result is None


@pytest.mark.asyncio
async def test_rotate_key(session_factory):
    async with session_factory() as db:
        old_orm, old_key = await create_api_key(db, DEFAULT_ORG_ID, "Rotate Me")
        result = await rotate_api_key(db, old_orm.id, DEFAULT_ORG_ID)
        assert result is not None
        new_orm, new_key = result

        # old key no longer works
        assert await verify_api_key(db, old_key) is None
        # new key works
        assert await verify_api_key(db, new_key) is not None
        assert new_orm.name == old_orm.name


# ── API endpoints ─────────────────────────────────────────────────────────────

def test_create_key_endpoint(client: TestClient):
    headers = _admin_headers(client)
    resp = client.post("/api-keys", json={"name": "Production"}, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "key" in data          # shown once
    assert data["key"].startswith("relay_")
    assert data["name"] == "Production"
    assert data["is_active"] is True


def test_list_keys_endpoint(client: TestClient):
    headers = _admin_headers(client)
    client.post("/api-keys", json={"name": "Key A"}, headers=headers)
    client.post("/api-keys", json={"name": "Key B"}, headers=headers)
    resp = client.get("/api-keys", headers=headers)
    assert resp.status_code == 200
    names = [k["name"] for k in resp.json()]
    assert "Key A" in names
    assert "Key B" in names


def test_revoke_key_endpoint(client: TestClient):
    headers = _admin_headers(client)
    create_resp = client.post("/api-keys", json={"name": "To Revoke"}, headers=headers)
    key_id = create_resp.json()["id"]
    resp = client.delete(f"/api-keys/{key_id}", headers=headers)
    assert resp.status_code == 204


def test_rotate_key_endpoint(client: TestClient):
    headers = _admin_headers(client)
    create_resp = client.post("/api-keys", json={"name": "To Rotate"}, headers=headers)
    key_id = create_resp.json()["id"]
    resp = client.post(f"/api-keys/{key_id}/rotate", headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "key" in data
    assert data["key"].startswith("relay_")


def test_agent_role_cannot_create_key(client: TestClient):
    resp = client.post("/auth/token", json={
        "user_id": "USR-AGENT", "organization_id": DEFAULT_ORG_ID, "role": "agent"
    })
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    resp = client.post("/api-keys", json={"name": "Forbidden"}, headers=headers)
    assert resp.status_code == 403


# ── external /v1/tickets endpoint ─────────────────────────────────────────────

def test_external_create_ticket_with_api_key(client: TestClient):
    # create a key via the admin endpoint first
    admin_headers = _admin_headers(client)
    key_resp = client.post("/api-keys", json={"name": "External"}, headers=admin_headers)
    full_key = key_resp.json()["key"]

    resp = client.post(
        "/v1/tickets",
        json={"title": "Charged twice", "message": "I was billed twice in June."},
        headers={"X-API-Key": full_key},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Charged twice"
    assert data["source"] == "api"
    assert data["organization_id"] == DEFAULT_ORG_ID


def test_external_get_ticket_with_api_key(client: TestClient):
    admin_headers = _admin_headers(client)
    key_resp = client.post("/api-keys", json={"name": "Read Key"}, headers=admin_headers)
    full_key = key_resp.json()["key"]

    create = client.post(
        "/v1/tickets",
        json={"title": "Test", "message": "Test message"},
        headers={"X-API-Key": full_key},
    )
    ticket_id = create.json()["id"]

    get = client.get(f"/v1/tickets/{ticket_id}", headers={"X-API-Key": full_key})
    assert get.status_code == 200
    assert get.json()["id"] == ticket_id


def test_external_invalid_key_rejected(client: TestClient):
    resp = client.post(
        "/v1/tickets",
        json={"title": "Test", "message": "Test"},
        headers={"X-API-Key": "relay_badkey_invalid"},
    )
    assert resp.status_code == 401


def test_external_no_key_rejected(client: TestClient):
    resp = client.post("/v1/tickets", json={"title": "Test", "message": "Test"})
    assert resp.status_code == 401
