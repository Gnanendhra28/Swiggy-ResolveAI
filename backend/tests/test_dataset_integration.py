import os
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from backend.app.models.restaurant import Restaurant
from backend.app.models.historical_order import HistoricalOrder
from backend.app.models.order import Order
from backend.app.services.ingestion.column_mapper import ColumnMapper
from backend.app.services.ingestion.dataset_validator import DatasetValidator
from backend.app.services.ingestion.quality_report import DataQualityReport
from backend.app.services.ingestion.restaurant_loader import RestaurantDatasetLoader
from backend.app.services.ingestion.order_history_loader import OrderHistoryDatasetLoader
from backend.app.core.exceptions import ValidationError


def test_column_mapper_normalization():
    raw_rest = {
        "Restaurant": "Empire",
        "Food type": "Biryani",
        "Avg ratings": "4.2",
        "Delivery time": "45",
    }
    mapped = ColumnMapper.map_restaurant_row(raw_rest)
    assert mapped["name"] == "Empire"
    assert mapped["cuisine"] == "Biryani"
    assert mapped["rating"] == "4.2"
    assert mapped["delivery_time_listing"] == "45"

    raw_order = {
        "order_id": "12345",
        "first_miledistance": "2.4",
        "reassigned_order": "1",
    }
    mapped_order = ColumnMapper.map_order_history_row(raw_order)
    assert mapped_order["order_id"] == "12345"
    assert mapped_order["first_mile_distance"] == "2.4"
    assert mapped_order["reassigned_order"] == "1"


def test_dataset_validator_required_columns():
    # Valid columns
    DatasetValidator.validate_required_columns(
        available_columns=["Restaurant", "City", "Area", "Price"],
        required_columns=["Restaurant", "City"],
        dataset_name="Test",
    )

    # Missing column should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        DatasetValidator.validate_required_columns(
            available_columns=["Restaurant", "Price"],
            required_columns=["Restaurant", "City"],
            dataset_name="Test",
        )
    assert "Missing required columns" in str(exc_info.value)


def test_dataset_validator_parsers():
    # Datetime
    dt = DatasetValidator.parse_datetime("2021-01-26 02:21:35")
    assert dt is not None
    assert dt.year == 2021
    assert dt.month == 1
    assert dt.day == 26
    assert DatasetValidator.parse_datetime("nan") is None

    # Float & Int
    assert DatasetValidator.parse_float("3.14") == 3.14
    assert DatasetValidator.parse_float("null") is None
    assert DatasetValidator.parse_int("42") == 42
    assert DatasetValidator.parse_int("-") is None

    # Bool
    assert DatasetValidator.parse_bool("1") is True
    assert DatasetValidator.parse_bool("true") is True
    assert DatasetValidator.parse_bool("0") is False
    assert DatasetValidator.parse_bool("nan") is False


def test_restaurant_dataset_loader_and_idempotency(db_session: Session):
    loader = RestaurantDatasetLoader(db_session)

    # Ingest 15 rows from local raw file
    report1 = loader.ingest(limit=15)
    assert report1.inserted_count == 15
    assert report1.provenance == "PUBLIC_HISTORICAL"

    # Verify fields in database
    rest = db_session.scalars(
        select(Restaurant).where(Restaurant.external_dataset_id.is_not(None))
    ).first()
    assert rest is not None
    assert rest.data_source == "PUBLIC_HISTORICAL"
    assert rest.latitude is None  # Coordinates not fabricated
    assert rest.longitude is None

    # Test Repeatable Ingestion (Idempotency)
    report2 = loader.ingest(limit=15)
    assert report2.inserted_count == 0
    assert report2.duplicate_rows == 15
    assert report2.skipped_count == 15


def test_order_history_dataset_loader(db_session: Session):
    loader = OrderHistoryDatasetLoader(db_session)

    # Ingest 25 rows from local Kaggle raw file
    report = loader.ingest(limit=25)
    assert report.inserted_count == 25
    assert report.provenance == "PUBLIC_HISTORICAL"

    # Verify historical order record
    hist_order = db_session.scalars(select(HistoricalOrder)).first()
    assert hist_order is not None
    assert hist_order.data_source == "PUBLIC_HISTORICAL"
    assert hist_order.order_id is not None
    assert hist_order.created_at is not None

    # Verify complete separation from synthetic live orders
    synthetic_orders = db_session.scalars(
        select(Order).where(Order.data_source == "SYNTHETIC")
    ).all()
    historical_orders = db_session.scalars(select(HistoricalOrder)).all()

    # Neither table shares rows or types
    assert len(historical_orders) == 25
    for ho in historical_orders:
        assert ho.data_source == "PUBLIC_HISTORICAL"


def test_missing_and_cancelled_values_handling(db_session: Session):
    """Verify quality report captures nulls and cancels accurately."""
    report = DataQualityReport(
        dataset_name="Test Quality Report",
        source_file_or_id="test.csv",
    )
    report.record_null("accept_time")
    report.record_null("pickup_time")
    report.record_null("accept_time")

    summary = report.summary()
    assert summary["missing_values"]["accept_time"] == 2
    assert summary["missing_values"]["pickup_time"] == 1
    assert summary["provenance"] == "PUBLIC_HISTORICAL"
