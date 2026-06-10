"""Phase 3 — Webhooks + Login tests."""
import pytest
from fastapi.testclient import TestClient
from app.db.seed import DEFAULT_ORG_ID


def _admin_headers(client: TestClient) -> dict:
    resp = client.post("/auth/token", json={
        "user_id": "USR-ADMIN", "organization_id": DEFAULT_ORG_ID, "role": "admin"
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── Organization signup ───────────────────────────────────────────────────────

def test_signup_creates_org_and_admin(client: TestClient):
    resp = client.post("/organizations", json={
        "org_name": "Acme Corp",
        "admin_email": "admin@acme.com",
        "admin_name": "Alice",
        "password": "secret123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "organization_id" in data
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_signup_duplicate_email_returns_409(client: TestClient):
    payload = {
        "org_name": "Dup Corp", "admin_email": "dup@test.com",
        "admin_name": "Bob", "password": "pass123",
    }
    client.post("/organizations", json=payload)
    resp = client.post("/organizations", json=payload)
    assert resp.status_code == 409


# ── Real login ────────────────────────────────────────────────────────────────

def test_login_with_correct_password(client: TestClient):
    client.post("/organizations", json={
        "org_name": "Login Corp", "admin_email": "login@test.com",
        "admin_name": "Carol", "password": "mypassword",
    })
    resp = client.post("/auth/login", json={"email": "login@test.com", "password": "mypassword"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password_returns_401(client: TestClient):
    client.post("/organizations", json={
        "org_name": "Wrong Corp", "admin_email": "wrong@test.com",
        "admin_name": "Dave", "password": "correct",
    })
    resp = client.post("/auth/login", json={"email": "wrong@test.com", "password": "incorrect"})
    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client: TestClient):
    resp = client.post("/auth/login", json={"email": "nobody@test.com", "password": "x"})
    assert resp.status_code == 401


# ── Webhook endpoints CRUD ────────────────────────────────────────────────────

def test_create_webhook_endpoint(client: TestClient):
    headers = _admin_headers(client)
    resp = client.post("/webhooks/endpoints", json={
        "url": "https://example.com/hook",
        "events": ["ticket.created", "ticket.resolved"],
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"] == "https://example.com/hook"
    assert "secret" in data   # shown once on creation
    assert "ticket.created" in data["events"]


def test_list_webhook_endpoints(client: TestClient):
    headers = _admin_headers(client)
    client.post("/webhooks/endpoints", json={"url": "https://a.com/h", "events": ["ticket.created"]}, headers=headers)
    resp = client.get("/webhooks/endpoints", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_delete_webhook_endpoint(client: TestClient):
    headers = _admin_headers(client)
    create = client.post("/webhooks/endpoints", json={"url": "https://del.com/h", "events": []}, headers=headers)
    ep_id = create.json()["id"]
    resp = client.delete(f"/webhooks/endpoints/{ep_id}", headers=headers)
    assert resp.status_code == 204


def test_non_admin_cannot_manage_webhooks(client: TestClient):
    resp = client.post("/auth/token", json={
        "user_id": "USR-AGENT", "organization_id": DEFAULT_ORG_ID, "role": "agent"
    })
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    resp = client.post("/webhooks/endpoints", json={"url": "https://x.com", "events": []}, headers=headers)
    assert resp.status_code == 403


# ── Webhook deliveries list ───────────────────────────────────────────────────

def test_list_deliveries_empty(client: TestClient):
    headers = _admin_headers(client)
    resp = client.get("/webhooks/deliveries", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Webhook triggered on ticket events ───────────────────────────────────────

def test_ticket_create_queues_webhook_delivery(client: TestClient):
    headers = _admin_headers(client)
    # register endpoint
    client.post("/webhooks/endpoints", json={
        "url": "https://hook.example.com/receive",
        "events": ["ticket.created"],
    }, headers=headers)

    # create ticket — should trigger webhook delivery record
    client.post("/tickets", json={"title": "Hook test", "message": "test"}, headers=headers)

    deliveries = client.get("/webhooks/deliveries", headers=headers).json()
    assert any(d["event_type"] == "ticket.created" for d in deliveries)
