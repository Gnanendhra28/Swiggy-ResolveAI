import pytest
from fastapi.testclient import TestClient


SCENARIOS = [
    ("NORMAL_ORDER", "DELIVERED"),
    ("RESTAURANT_DELAY", "DELIVERED"),
    ("DELIVERY_DELAY", "DELIVERED"),
    ("ASSIGNMENT_DELAY", "DELIVERED"),
    ("FAILED_RECOVERY", "ESCALATED"),
    ("SUCCESSFUL_RECOVERY", "RECOVERED"),
]


@pytest.mark.parametrize("scenario,expected_status", SCENARIOS)
def test_all_simulation_scenarios(client: TestClient, scenario: str, expected_status: str):
    response = client.post(
        "/api/v1/simulation/generate",
        json={"scenario": scenario, "count": 1, "seed": 42},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["generated_count"] == 1
    assert data["scenario"] == scenario
    order = data["orders"][0]
    assert order["order_status"] == expected_status
    assert order["data_source"] == "SYNTHETIC"

    # Fetch order events and verify chronology and event types
    order_id = order["id"]
    events_resp = client.get(f"/api/v1/orders/{order_id}/events")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) >= 3

    # Check chronological ordering
    for i in range(len(events) - 1):
        assert events[i]["event_timestamp"] <= events[i + 1]["event_timestamp"]

    # Verify scenario-specific event occurrences
    event_types = [e["event_type"] for e in events]
    if scenario == "RESTAURANT_DELAY":
        assert "KITCHEN_DELAY_DETECTED" in event_types
    elif scenario == "DELIVERY_DELAY":
        assert "TRAFFIC_CONGESTION_DETECTED" in event_types or "DELIVERY_DELAY_PREDICTED" in event_types
    elif scenario == "ASSIGNMENT_DELAY":
        assert "RIDER_SEARCH_TIMEOUT" in event_types
    elif scenario == "FAILED_RECOVERY":
        assert "RECOVERY_FAILED" in event_types or "ORDER_ESCALATED" in event_types
    elif scenario == "SUCCESSFUL_RECOVERY":
        assert "RECOVERY_TRIGGERED" in event_types and "RECOVERY_SUCCESSFUL" in event_types


def test_simulation_seed_reproducibility(client: TestClient):
    """Verify that same seed generates deterministic values and chronology."""
    res1 = client.post(
        "/api/v1/simulation/generate",
        json={"scenario": "NORMAL_ORDER", "count": 1, "seed": 999},
    ).json()

    res2 = client.post(
        "/api/v1/simulation/generate",
        json={"scenario": "NORMAL_ORDER", "count": 1, "seed": 999},
    ).json()

    order1 = res1["orders"][0]
    order2 = res2["orders"][0]
    assert order1["order_value"] == order2["order_value"]
    assert order1["order_status"] == order2["order_status"]


def test_inject_event_api(client: TestClient):
    """Test dynamic event injection into existing simulated order."""
    gen = client.post(
        "/api/v1/simulation/generate",
        json={"scenario": "NORMAL_ORDER", "count": 1, "seed": 123},
    ).json()
    order_id = gen["order_ids"][0]

    inject_resp = client.post(
        "/api/v1/simulation/events",
        json={
            "order_id": order_id,
            "event_type": "CUSTOMER_SUPPORT_INQUIRY",
            "metadata": {"channel": "IN_APP_CHAT", "query": "Is my food still hot?"},
            "data_source": "SYNTHETIC",
        },
    )
    assert inject_resp.status_code == 200
    injected = inject_resp.json()
    assert injected["event_type"] == "CUSTOMER_SUPPORT_INQUIRY"
    assert injected["data_source"] == "SYNTHETIC"

    # Confirm it appears in order event timeline
    events = client.get(f"/api/v1/orders/{order_id}/events").json()
    assert any(e["event_type"] == "CUSTOMER_SUPPORT_INQUIRY" for e in events)


def test_list_simulation_scenarios(client: TestClient):
    resp = client.get("/api/v1/simulation/scenarios")
    assert resp.status_code == 200
    scenarios = resp.json()["scenarios"]
    assert len(scenarios) == 6
