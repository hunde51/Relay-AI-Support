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
    assert [item["id"] for item in list_response.json()] == [ticket["id"]]

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
