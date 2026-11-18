import os
import time
import uuid
import csv
from typing import Optional, List, Dict, Any, Generator
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.core.logging import logger
from backend.app.models.historical_order import HistoricalOrder
from backend.app.services.ingestion.column_mapper import ColumnMapper
from backend.app.services.ingestion.dataset_validator import DatasetValidator
from backend.app.services.ingestion.quality_report import DataQualityReport


class OrderHistoryDatasetLoader:
    """
    Ingests public Swiggy/Zomato historical order lifecycle telemetry dataset (Kaggle / local CSV).
    Maintains strict separation: records are stored in 'historical_orders' table, completely
    isolated from synthetic live demo orders.
    Preserves exact rider/order IDs without inventing fake customer or restaurant IDs.
    """
    DATASET_ID = "cbhavik/swiggyzomato-order-information"
    DEFAULT_LOCAL_PATH = "data/raw/orders/Rider-Info.csv"

    def __init__(self, db: Session):
        self.db = db

    def load_rows_from_source(
        self,
        filepath: Optional[str] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        target_path = filepath or self.DEFAULT_LOCAL_PATH
        if os.path.exists(target_path):
            logger.info(f"Reading historical order dataset from local file: {target_path}")
            with open(target_path, mode="r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield row
        else:
            logger.warning(
                f"Local order dataset file {target_path} not found. "
                f"To import Kaggle dataset, run: kagglehub.dataset_download('{self.DATASET_ID}') "
                f"and place Rider-Info.csv under data/raw/orders/."
            )
            return

    def ingest(
        self,
        filepath: Optional[str] = None,
        limit: Optional[int] = None,
        batch_size: int = 1000,
    ) -> DataQualityReport:
        start_time = time.time()
        report = DataQualityReport(
            dataset_name="Kaggle Swiggy/Zomato Order Information",
            source_file_or_id=filepath or self.DEFAULT_LOCAL_PATH,
            provenance="PUBLIC_HISTORICAL",
        )

        # Existing order_ids for idempotent safe re-ingestion
        existing_order_ids = set(
            self.db.scalars(
                select(HistoricalOrder.order_id)
            ).all()
        )

        batch: List[HistoricalOrder] = []
        validated_headers = False

        for raw_row in self.load_rows_from_source(filepath):
            report.total_rows_read += 1

            if not validated_headers:
                DatasetValidator.validate_required_columns(
                    available_columns=list(raw_row.keys()),
                    required_columns=["order_id", "order_time", "cancelled"],
                    dataset_name="Kaggle Order History",
                )
                validated_headers = True

            mapped = ColumnMapper.map_order_history_row(raw_row)

            raw_order_id = str(mapped.get("order_id") or "").strip()
            if not raw_order_id:
                report.record_null("order_id")
                report.skipped_count += 1
                continue

            if raw_order_id in existing_order_ids:
                report.duplicate_rows += 1
                report.skipped_count += 1
                continue

            # Parse timestamps safely
            order_time = DatasetValidator.parse_datetime(mapped.get("order_time"))
            if order_time is None:
                report.record_null("order_time")

            allot_time = DatasetValidator.parse_datetime(mapped.get("allot_time"))
            accept_time = DatasetValidator.parse_datetime(mapped.get("accept_time"))
            pickup_time = DatasetValidator.parse_datetime(mapped.get("pickup_time"))
            delivered_time = DatasetValidator.parse_datetime(mapped.get("delivered_time"))
            cancelled_time = DatasetValidator.parse_datetime(mapped.get("cancelled_time"))

            # Cancelled flag handling
            cancelled = DatasetValidator.parse_bool(mapped.get("cancelled"))
            if cancelled and delivered_time is not None:
                # Inconsistent row: both cancelled and delivered
                report.record_error(f"Order {raw_order_id} flagged cancelled but has delivered_time")

            rider_id = str(mapped.get("rider_id") or "").strip() or None
            if rider_id is None:
                report.record_null("rider_id")

            # Numeric operational metrics
            first_mile = DatasetValidator.parse_float(mapped.get("first_mile_distance"))
            last_mile = DatasetValidator.parse_float(mapped.get("last_mile_distance"))
            allotted_orders = DatasetValidator.parse_int(mapped.get("allotted_orders"))
            delivered_orders = DatasetValidator.parse_int(mapped.get("delivered_orders"))
            undelivered_orders = DatasetValidator.parse_int(mapped.get("undelivered_orders"))
            lifetime_orders = DatasetValidator.parse_int(mapped.get("lifetime_order_count"))
            session_time = DatasetValidator.parse_float(mapped.get("session_time"))

            # Reassignment
            reassigned = DatasetValidator.parse_bool(mapped.get("reassigned_order"))
            reassign_method = str(mapped.get("reassignment_method") or "").strip() or None
            reassign_reason = str(mapped.get("reassignment_reason") or "").strip() or None

            order_record = HistoricalOrder(
                id=str(uuid.uuid4()),
                order_id=raw_order_id,
                order_time=order_time,
                order_date=str(mapped.get("order_date") or "").strip() or None,
                allot_time=allot_time,
                accept_time=accept_time,
                pickup_time=pickup_time,
                delivered_time=delivered_time,
                cancelled_time=cancelled_time,
                cancelled=cancelled,
                rider_id=rider_id,
                first_mile_distance=first_mile,
                last_mile_distance=last_mile,
                allotted_orders=allotted_orders,
                delivered_orders=delivered_orders,
                undelivered_orders=undelivered_orders,
                lifetime_order_count=lifetime_orders,
                reassigned_order=reassigned,
                reassignment_method=reassign_method,
                reassignment_reason=reassign_reason,
                session_time=session_time,
                data_source="PUBLIC_HISTORICAL",
            )

            batch.append(order_record)
            existing_order_ids.add(raw_order_id)
            report.valid_rows += 1

            if len(batch) >= batch_size:
                self.db.add_all(batch)
                self.db.commit()
                report.inserted_count += len(batch)
                batch = []

            if limit and report.total_rows_read >= limit:
                break

        if batch:
            self.db.add_all(batch)
            self.db.commit()
            report.inserted_count += len(batch)

        report.duration_seconds = time.time() - start_time
        logger.info(
            f"Completed historical orders ingestion: {report.inserted_count} inserted, {report.skipped_count} skipped ({report.duration_seconds:.2f}s)"
        )
        return report
