def test_create_list_get_and_update_ticket(client):
    create_response = client.post(
        "/tickets",
        json={
            "title": "Payment failed",
            "message": "The payment failed but the card was charged.",
            "priority": "high",
            "category": "billing",
        },
    )

    assert create_response.status_code == 201
    ticket = create_response.json()
    assert ticket["id"].startswith("TKT-")
    assert ticket["status"] == "open"
    assert ticket["priority"] == "high"
    assert ticket["category"] == "billing"

    list_response = client.get("/tickets")
    assert list_response.status_code == 200
    data = list_response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == ticket["id"]

    get_response = client.get(f"/tickets/{ticket['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Payment failed"

    update_response = client.patch(
        f"/tickets/{ticket['id']}",
        json={"status": "in_progress", "priority": "critical"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "in_progress"
    assert update_response.json()["priority"] == "critical"


def test_get_missing_ticket_returns_404(client):
    response = client.get("/tickets/not-found")
    assert response.status_code == 404


def test_ticket_messages(client):
    ticket = client.post("/tickets", json={"title": "Test", "message": "Help"}).json()
    tid = ticket["id"]

    msg_response = client.post(f"/tickets/{tid}/messages", json={"body": "We are looking into this."})
    assert msg_response.status_code == 201
    assert msg_response.json()["body"] == "We are looking into this."

    msgs = client.get(f"/tickets/{tid}/messages").json()
    assert len(msgs) == 1


def test_ticket_timeline(client):
    ticket = client.post("/tickets", json={"title": "Test", "message": "Help"}).json()
    tid = ticket["id"]

    client.patch(f"/tickets/{tid}", json={"status": "in_progress"})
    timeline = client.get(f"/tickets/{tid}/timeline").json()
    event_types = [e["event_type"] for e in timeline]
    assert "ticket_created" in event_types
    assert "status_changed" in event_types


def test_resolve_and_escalate(client):
    ticket = client.post("/tickets", json={"title": "Test", "message": "Help"}).json()
    tid = ticket["id"]

    resolved = client.post(f"/tickets/{tid}/resolve").json()
    assert resolved["status"] == "resolved"
    assert resolved["resolved_at"] is not None

    ticket2 = client.post("/tickets", json={"title": "Urgent", "message": "Help now"}).json()
    escalated = client.post(f"/tickets/{ticket2['id']}/escalate").json()
    assert escalated["status"] == "in_progress"


def test_list_filters(client):
    client.post("/tickets", json={"title": "Billing issue", "message": "Charge", "category": "billing"})
    client.post("/tickets", json={"title": "Login broken", "message": "Cannot login", "category": "technical"})

    billing = client.get("/tickets?category=billing").json()
    assert all(t["category"] == "billing" for t in billing["items"])

    search = client.get("/tickets?search=login").json()
    assert any("login" in t["title"].lower() for t in search["items"])
