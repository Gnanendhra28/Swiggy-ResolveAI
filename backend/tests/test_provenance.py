from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.models.order import Order
from backend.app.models.restaurant import Restaurant


def test_synthetic_data_provenance(client: TestClient, db_session: Session):
    """Verify that all generated simulation records are explicitly tagged as SYNTHETIC."""
    gen = client.post(
        "/api/v1/simulation/generate",
        json={"scenario": "NORMAL_ORDER", "count": 2, "seed": 77},
    ).json()

    for order_id in gen["order_ids"]:
        order = db_session.get(Order, order_id)
        assert order.data_source == "SYNTHETIC"
        for ev in order.events:
            assert ev.data_source == "SYNTHETIC"


def test_historical_dataset_ingestion_provenance(client: TestClient, db_session: Session):
    """Verify CSV ingestion marks source as HISTORICAL_DATASET and does not fabricate coordinates."""
    sample_csv = (
        "name,city,area,cuisine,rating,rating_count,average_price,pure_veg,latitude,longitude\n"
        "Vidyarthi Bhavan,Bengaluru,Gandhi Bazaar,South Indian,4.6,50000,180.0,true,,\n"
        "Punjab Grill,Mumbai,Bandra West,North Indian,4.3,3200,850.0,false,19.0607,72.8362\n"
    )

    response = client.post(
        "/api/v1/ingest/restaurants",
        files={"file": ("swiggy_sample.csv", sample_csv, "text/csv")},
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["data_quality_report"]["inserted_count"] == 2

    # Check Vidyarthi Bhavan has no invented coordinates
    vb = db_session.query(Restaurant).filter(Restaurant.name == "Vidyarthi Bhavan").first()
    assert vb is not None
    assert vb.pure_veg is True
    assert vb.latitude is None  # Preserved null, not fabricated
    assert vb.longitude is None

    # Check Punjab Grill has preserved coordinates
    pg = db_session.query(Restaurant).filter(Restaurant.name == "Punjab Grill").first()
    assert pg is not None
    assert pg.latitude == 19.0607
    assert pg.longitude == 72.8362


def test_invalid_request_handling(client: TestClient):
    """Verify consistent error response format on 422 validation errors."""
    resp = client.post(
        "/api/v1/simulation/generate",
        json={"scenario": "INVALID_SCENARIO", "count": 999},  # exceeds count max 50
    )
    assert resp.status_code == 422
    err_body = resp.json()
    assert err_body["success"] is False
    assert err_body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    assert "details" in err_body["error"]
