import os
import time
import uuid
import csv
from typing import Optional, List, Dict, Any, Generator
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.core.logging import logger
from backend.app.models.restaurant import Restaurant
from backend.app.services.ingestion.column_mapper import ColumnMapper
from backend.app.services.ingestion.dataset_validator import DatasetValidator
from backend.app.services.ingestion.quality_report import DataQualityReport


class RestaurantDatasetLoader:
    """
    Ingests public Swiggy restaurant listings dataset (Hugging Face / local CSV).
    Preserves exact source values and provenance (PUBLIC_HISTORICAL).
    Does not invent latitude/longitude coordinates.
    """
    DATASET_ID = "jason1966/abhijitdahatonde_swiggy-restuarant-dataset"
    DEFAULT_LOCAL_PATH = "data/raw/restaurants/swiggy_restaurants.csv"

    def __init__(self, db: Session):
        self.db = db

    def load_rows_from_source(
        self,
        filepath: Optional[str] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        target_path = filepath or self.DEFAULT_LOCAL_PATH
        if os.path.exists(target_path):
            logger.info(f"Reading restaurant dataset from local file: {target_path}")
            with open(target_path, mode="r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield row
        else:
            logger.info(f"Local file {target_path} not found. Attempting Hugging Face load: {self.DATASET_ID}")
            from datasets import load_dataset
            ds = load_dataset(self.DATASET_ID)
            train_split = ds["train"]
            for row in train_split:
                yield dict(row)

    def ingest(
        self,
        filepath: Optional[str] = None,
        limit: Optional[int] = None,
        batch_size: int = 500,
    ) -> DataQualityReport:
        start_time = time.time()
        report = DataQualityReport(
            dataset_name="Swiggy Restaurant Dataset",
            source_file_or_id=filepath or self.DEFAULT_LOCAL_PATH,
            provenance="PUBLIC_HISTORICAL",
        )

        # Existing external_dataset_ids to guarantee idempotent ingestion
        existing_ids = set(
            self.db.scalars(
                select(Restaurant.external_dataset_id).where(
                    Restaurant.external_dataset_id.is_not(None)
                )
            ).all()
        )

        batch: List[Restaurant] = []
        validated_headers = False

        for raw_row in self.load_rows_from_source(filepath):
            report.total_rows_read += 1
            if limit and report.total_rows_read > limit:
                break

            if not validated_headers:
                DatasetValidator.validate_restaurant_columns(
                    available_columns=list(raw_row.keys()),
                    dataset_name="Restaurant Dataset",
                )
                validated_headers = True

            mapped = ColumnMapper.map_restaurant_row(raw_row)

            # Extract fields
            name = str(mapped.get("name") or "").strip()
            city = str(mapped.get("city") or "").strip()
            area = str(mapped.get("area") or "").strip()
            ext_id = str(mapped.get("external_dataset_id") or "").strip() or None

            if not name:
                report.record_null("Restaurant")
                report.skipped_count += 1
                continue
            if not city:
                report.record_null("City")
            if not area:
                report.record_null("Area")

            # Check duplicate
            if ext_id and ext_id in existing_ids:
                report.duplicate_rows += 1
                report.skipped_count += 1
                continue

            rating = DatasetValidator.parse_float(mapped.get("rating"))
            if rating is None:
                report.record_null("rating")

            rating_count = DatasetValidator.parse_int(mapped.get("rating_count"))
            if rating_count is None:
                report.record_null("rating_count")

            price = DatasetValidator.parse_float(mapped.get("average_price"))
            if price is None:
                report.record_null("average_price")

            # Delivery time listing: string/int representation preserved without claiming prep time
            delivery_time_raw = mapped.get("delivery_time_listing")
            delivery_time_str = f"{delivery_time_raw} mins" if delivery_time_raw is not None else None

            # Coordinates: DO NOT invent
            lat = DatasetValidator.parse_float(mapped.get("latitude"))
            lon = DatasetValidator.parse_float(mapped.get("longitude"))

            restaurant = Restaurant(
                id=str(uuid.uuid4()),
                external_dataset_id=ext_id,
                name=name,
                city=city or "Unknown",
                area=area or "Unknown",
                cuisine=str(mapped.get("cuisine") or "Multi-Cuisine").strip(),
                rating=rating,
                rating_count=rating_count,
                average_price=price,
                number_of_offers=DatasetValidator.parse_int(mapped.get("number_of_offers")) or 0,
                offer_name=str(mapped.get("offer_name") or "").strip() or None,
                pure_veg=DatasetValidator.parse_bool(mapped.get("pure_veg")),
                location=str(mapped.get("location") or "").strip() or None,
                latitude=lat,
                longitude=lon,
                delivery_time_listing=delivery_time_str,
                data_source="PUBLIC_HISTORICAL",
            )

            batch.append(restaurant)
            if ext_id:
                existing_ids.add(ext_id)
            report.valid_rows += 1

            if len(batch) >= batch_size:
                self.db.add_all(batch)
                self.db.commit()
                report.inserted_count += len(batch)
                batch = []

        if batch:
            self.db.add_all(batch)
            self.db.commit()
            report.inserted_count += len(batch)

        report.duration_seconds = time.time() - start_time
        logger.info(
            f"Completed restaurant ingestion: {report.inserted_count} inserted, {report.skipped_count} skipped ({report.duration_seconds:.2f}s)"
        )
        return report
