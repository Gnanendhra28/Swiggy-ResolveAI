from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.app.core.exceptions import ValidationError


class DatasetValidator:
    """Validates raw dataset structures, required columns, and data consistency."""

    REQUIRED_RESTAURANT_COLUMNS = ["Restaurant", "City", "Area"]
    REQUIRED_ORDER_COLUMNS = ["order_id", "order_time", "cancelled"]

    @classmethod
    def normalize_key(cls, key: str) -> str:
        return key.strip().lower().replace(" ", "_").replace("-", "_")

    @classmethod
    def validate_restaurant_columns(cls, available_columns: List[str], dataset_name: str) -> None:
        norm = {cls.normalize_key(c) for c in available_columns}
        has_name = "restaurant" in norm or "name" in norm or "restaurant_name" in norm
        has_city = "city" in norm
        has_area = "area" in norm
        if not (has_name and has_city and has_area):
            missing = []
            if not has_name:
                missing.append("Restaurant/Name")
            if not has_city:
                missing.append("City")
            if not has_area:
                missing.append("Area")
            raise ValidationError(f"Missing required columns in {dataset_name}: {missing}")

    @classmethod
    def validate_required_columns(
        cls,
        available_columns: List[str],
        required_columns: List[str],
        dataset_name: str,
    ) -> None:
        normalized_available = {
            cls.normalize_key(col)
            for col in available_columns
        }
        missing = []
        for req in required_columns:
            norm_req = cls.normalize_key(req)
            if norm_req not in normalized_available:
                missing.append(req)

        if missing:
            raise ValidationError(
                f"Missing required columns in {dataset_name} dataset: {missing}. Available: {available_columns[:10]}"
            )

    @classmethod
    def parse_datetime(cls, val: Any) -> Optional[datetime]:
        if val is None or str(val).strip().lower() in ["", "none", "null", "nan", "nat", "-"]:
            return None
        s = str(val).strip()
        # Common formats: '2021-01-26 02:21:35', '2021-01-26T02:21:35', '2021-01-26'
        for fmt in [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d",
            "%d-%m-%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
        ]:
            try:
                dt = datetime.strptime(s, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    @classmethod
    def parse_float(cls, val: Any) -> Optional[float]:
        if val is None or str(val).strip().lower() in ["", "none", "null", "nan", "-"]:
            return None
        try:
            return float(str(val).strip())
        except (ValueError, TypeError):
            return None

    @classmethod
    def parse_int(cls, val: Any) -> Optional[int]:
        if val is None or str(val).strip().lower() in ["", "none", "null", "nan", "-"]:
            return None
        try:
            return int(float(str(val).strip()))
        except (ValueError, TypeError):
            return None

    @classmethod
    def parse_bool(cls, val: Any) -> bool:
        if val is None or str(val).strip().lower() in ["", "none", "null", "nan", "0", "false", "f", "no"]:
            return False
        s = str(val).strip().lower()
        return s in ["1", "true", "t", "yes", "y", "veg", "pure_veg"]
