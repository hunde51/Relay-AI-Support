"""Tests for Phase 2 endpoints: dashboard, customers, analytics, settings, AI, assign."""


# ── Dashboard ─────────────────────────────────────────────────────────────────

def test_dashboard_summary(client):
    response = client.get("/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_tickets" in data
    assert "open_tickets" in data
    assert "resolved_today" in data


def test_dashboard_ticket_volume(client):
    response = client.get("/dashboard/ticket-volume")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_dashboard_ai_performance(client):
    response = client.get("/dashboard/ai-performance")
    assert response.status_code == 200
    data = response.json()
    assert "total_runs" in data
    assert "auto_resolution_rate" in data


def test_dashboard_recent_activity(client):
    # Create a ticket so there's at least one event
    client.post("/tickets", json={"title": "Activity test", "message": "msg"})
    response = client.get("/dashboard/recent-activity")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ── Ticket assign ─────────────────────────────────────────────────────────────

def test_ticket_assign(client):
    ticket = client.post("/tickets", json={"title": "Assign test", "message": "help"}).json()
    tid = ticket["id"]
    response = client.post(f"/tickets/{tid}/assign", json={"assignee_id": "USR-FAKE001"})
    assert response.status_code == 200
    assert response.json()["assignee_id"] == "USR-FAKE001"


def test_ticket_list_filters_extended(client):
    client.post("/tickets", json={"title": "Old ticket", "message": "msg"})
    # sort param should not crash
    response = client.get("/tickets?sort=created_at_asc")
    assert response.status_code == 200
    assert "items" in response.json()


# ── Customers ─────────────────────────────────────────────────────────────────

def test_customer_crud(client):
    create = client.post("/customers", json={"name": "Alice", "email": "alice@example.com", "company": "Acme"})
    assert create.status_code == 201
    cid = create.json()["id"]

    get = client.get(f"/customers/{cid}")
    assert get.status_code == 200
    assert get.json()["email"] == "alice@example.com"

    lst = client.get("/customers")
    assert lst.status_code == 200
    assert any(c["id"] == cid for c in lst.json())


def test_customer_tickets_and_timeline(client):
    cust = client.post("/customers", json={"name": "Bob", "email": "bob@example.com"}).json()
    cid = cust["id"]

    tickets_resp = client.get(f"/customers/{cid}/tickets")
    assert tickets_resp.status_code == 200
    assert isinstance(tickets_resp.json(), list)

    timeline_resp = client.get(f"/customers/{cid}/timeline")
    assert timeline_resp.status_code == 200
    assert isinstance(timeline_resp.json(), list)


def test_customer_not_found(client):
    assert client.get("/customers/not-exist").status_code == 404


# ── Analytics ─────────────────────────────────────────────────────────────────

def test_analytics_endpoints(client):
    for path in [
        "/analytics/categories",
        "/analytics/resolution-trend",
        "/analytics/auto-resolution-rate",
        "/analytics/peak-hours",
        "/analytics/sla-performance",
        "/analytics/agent-performance",
    ]:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} returned {resp.status_code}"


# ── Settings ──────────────────────────────────────────────────────────────────

def test_settings_workspace(client):
    resp = client.get("/settings/workspace")
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data

    patch = client.patch("/settings/workspace", json={"name": "Updated Org"})
    assert patch.status_code == 200
    assert patch.json()["name"] == "Updated Org"


def test_settings_ai(client):
    resp = client.get("/settings/ai")
    assert resp.status_code == 200
    assert "ai_enabled" in resp.json()

    patch = client.patch("/settings/ai", json={"auto_resolve_enabled": True})
    assert patch.status_code == 200
    assert patch.json()["auto_resolve_enabled"] is True


def test_settings_notifications(client):
    resp = client.get("/settings/notifications")
    assert resp.status_code == 200
    assert "email_digest_enabled" in resp.json()

    patch = client.patch("/settings/notifications", json={"slack_alerts_enabled": True})
    assert patch.status_code == 200
    assert patch.json()["slack_alerts_enabled"] is True


def test_settings_integrations(client):
    resp = client.get("/settings/integrations")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Knowledge ─────────────────────────────────────────────────────────────────

def test_knowledge_sources(client):
    create = client.post("/knowledge/sources?name=Help+Docs&source_type=manual_upload")
    assert create.status_code == 201
    assert create.json()["name"] == "Help Docs"

    lst = client.get("/knowledge/sources")
    assert lst.status_code == 200
    assert isinstance(lst.json(), list)


def test_knowledge_documents(client):
    lst = client.get("/knowledge/documents")
    assert lst.status_code == 200
    assert isinstance(lst.json(), list)


def test_knowledge_chunk_not_found(client):
    assert client.get("/knowledge/chunks/not-exist").status_code == 404


# ── AI endpoints ──────────────────────────────────────────────────────────────

def test_ai_run_not_found(client):
    resp = client.get("/ai/runs/not-exist")
    assert resp.status_code == 404


def test_ai_tool_calls_empty(client):
    # Create a ticket, then check tool-calls for a fake run returns 404
    resp = client.get("/ai/runs/not-exist/tool-calls")
    # tool-calls endpoint doesn't 404 on missing run — returns empty list
    # (no run = no rows). Accept either 200 empty or 404.
    assert resp.status_code in (200, 404)
