import csv
import io
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.core.logging import logger
from backend.app.core.exceptions import ValidationError
from backend.app.models.restaurant import Restaurant


class IngestionService:
    @staticmethod
    def parse_float(val: Any) -> Optional[float]:
        if val is None or val == "" or str(val).strip().lower() in ["none", "null", "nan", "-"]:
            return None
        try:
            return float(str(val).strip())
        except ValueError:
            return None

    @staticmethod
    def parse_int(val: Any) -> Optional[int]:
        if val is None or val == "" or str(val).strip().lower() in ["none", "null", "nan", "-"]:
            return None
        try:
            return int(float(str(val).strip()))
        except ValueError:
            return None

    @staticmethod
    def parse_bool(val: Any) -> bool:
        if val is None:
            return False
        s = str(val).strip().lower()
        return s in ["true", "1", "yes", "veg", "pure_veg", "t"]

    @classmethod
    def ingest_restaurants_csv(
        cls,
        db: Session,
        csv_content: str,
        filename: str = "dataset.csv",
    ) -> Dict[str, Any]:
        """
        Parses and ingests a restaurant dataset CSV preserving exact fields.
        Does not fabricate coordinates or historical records.
        """
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            raise ValidationError("CSV file is empty or missing headers")

        # Normalize column header keys
        header_map = {col.strip().lower().replace(" ", "_"): col for col in reader.fieldnames}

        # Check essential fields
        name_key = header_map.get("name") or header_map.get("restaurant_name")
        city_key = header_map.get("city")
        if not name_key:
            raise ValidationError("CSV must contain a 'name' or 'restaurant_name' column")

        imported_count = 0
        skipped_count = 0
        records: List[Restaurant] = []

        for row in reader:
            raw_name = row.get(name_key)
            if not raw_name or not raw_name.strip():
                skipped_count += 1
                continue

            name = raw_name.strip()
            city = (row.get(city_key) or "Unknown").strip() if city_key else "Unknown"
            area = (row.get(header_map.get("area", "")) or "Unknown").strip()
            cuisine = (row.get(header_map.get("cuisine", "")) or "Multi-Cuisine").strip()

            rating = cls.parse_float(row.get(header_map.get("rating", "")))
            rating_count = cls.parse_int(row.get(header_map.get("rating_count", "")))
            average_price = cls.parse_float(row.get(header_map.get("average_price", "")))
            number_of_offers = cls.parse_int(row.get(header_map.get("number_of_offers", ""))) or 0
            offer_name = row.get(header_map.get("offer_name", ""))
            pure_veg = cls.parse_bool(row.get(header_map.get("pure_veg", "")))
            location = row.get(header_map.get("location", ""))

            # Coordinates: DO NOT invent if absent
            latitude = cls.parse_float(row.get(header_map.get("latitude", "")))
            longitude = cls.parse_float(row.get(header_map.get("longitude", "")))

            restaurant = Restaurant(
                id=str(uuid.uuid4()),
                name=name,
                city=city,
                area=area,
                cuisine=cuisine,
                rating=rating,
                rating_count=rating_count,
                average_price=average_price,
                number_of_offers=number_of_offers,
                offer_name=offer_name.strip() if offer_name else None,
                pure_veg=pure_veg,
                location=location.strip() if location else None,
                latitude=latitude,
                longitude=longitude,
                created_at=datetime.now(timezone.utc),
            )
            records.append(restaurant)
            imported_count += 1

        if records:
            db.add_all(records)
            db.commit()

        logger.info(
            f"Ingested {imported_count} restaurant records from {filename} (skipped {skipped_count})"
        )

        return {
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "source_file": filename,
            "data_source": "HISTORICAL_DATASET",
        }
