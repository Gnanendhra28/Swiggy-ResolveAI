from fastapi.testclient import TestClient


def test_order_lifecycle_and_api(client: TestClient):
    # 1. Generate an order via simulation
    gen_resp = client.post(
        "/api/v1/simulation/generate",
        json={"scenario": "NORMAL_ORDER", "count": 2, "seed": 101},
    )
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["generated_count"] == 2
    order_id = gen_data["order_ids"][0]

    # 2. Get order details
    detail_resp = client.get(f"/api/v1/orders/{order_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == order_id
    assert detail["order_status"] == "DELIVERED"
    assert "customer" in detail
    assert "restaurant" in detail
    assert len(detail["events"]) > 0

    # 3. Verify event chronology: each event timestamp >= previous event timestamp
    events = detail["events"]
    for i in range(len(events) - 1):
        assert events[i]["event_timestamp"] <= events[i + 1]["event_timestamp"]

    # 4. Get order events endpoint
    events_resp = client.get(f"/api/v1/orders/{order_id}/events")
    assert events_resp.status_code == 200
    assert len(events_resp.json()) == len(events)

    # 5. List orders with pagination
    list_resp = client.get("/api/v1/orders?page=1&limit=10")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["page"] == 1
    assert list_data["total"] >= 2
    assert len(list_data["items"]) >= 2

    # 6. Filter by status
    filter_resp = client.get("/api/v1/orders?status=DELIVERED")
    assert filter_resp.status_code == 200
    for item in filter_resp.json()["items"]:
        assert item["order_status"] == "DELIVERED"

    # 7. Non-existent order returns 404
    missing_resp = client.get("/api/v1/orders/non-existent-order-id-999")
    assert missing_resp.status_code == 404
    assert missing_resp.json()["error"]["code"] == "NOT_FOUND"

    # 8. Dashboard metrics endpoint
    metrics_resp = client.get("/api/v1/orders/metrics")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert "total_orders" in metrics
    assert "active_orders" in metrics
    assert "delivered_orders" in metrics
    assert "delayed_orders" in metrics
    assert "status_distribution" in metrics
    assert "recent_activity" in metrics
