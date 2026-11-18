from typing import Dict, Any, Optional


class ColumnMapper:
    """Standardizes heterogeneous source column names to canonical internal fields."""

    RESTAURANT_MAPPING: Dict[str, str] = {
        "id": "external_dataset_id",
        "restaurant": "name",
        "name": "name",
        "restaurant_name": "name",
        "area": "area",
        "city": "city",
        "food_type": "cuisine",
        "cuisine": "cuisine",
        "avg_ratings": "rating",
        "rating": "rating",
        "total_ratings": "rating_count",
        "rating_count": "rating_count",
        "price": "average_price",
        "average_price": "average_price",
        "address": "location",
        "location": "location",
        "delivery_time": "delivery_time_listing",
        "delivery_time_listing": "delivery_time_listing",
        "pure_veg": "pure_veg",
        "offer_name": "offer_name",
        "number_of_offers": "number_of_offers",
        "latitude": "latitude",
        "longitude": "longitude",
    }

    ORDER_HISTORY_MAPPING: Dict[str, str] = {
        "order_id": "order_id",
        "order_time": "order_time",
        "order_date": "order_date",
        "allot_time": "allot_time",
        "accept_time": "accept_time",
        "pickup_time": "pickup_time",
        "delivered_time": "delivered_time",
        "cancelled_time": "cancelled_time",
        "cancelled": "cancelled",
        "rider_id": "rider_id",
        "first_miledistance": "first_mile_distance",
        "first_mile_distance": "first_mile_distance",
        "last_miledistance": "last_mile_distance",
        "last_mile_distance": "last_mile_distance",
        "allotted_orders": "allotted_orders",
        "delivered_orders": "delivered_orders",
        "undelivered_orders": "undelivered_orders",
        "lifetime_ordercount": "lifetime_order_count",
        "lifetime_order_count": "lifetime_order_count",
        "reassigned_order": "reassigned_order",
        "reassignment_method": "reassignment_method",
        "reassignment_reason": "reassignment_reason",
        "session_time": "session_time",
    }

    @classmethod
    def normalize_key(cls, key: str) -> str:
        return key.strip().lower().replace(" ", "_").replace("-", "_")

    @classmethod
    def map_restaurant_row(cls, raw_row: Dict[str, Any]) -> Dict[str, Any]:
        mapped = {}
        for k, v in raw_row.items():
            norm_k = cls.normalize_key(str(k))
            target_field = cls.RESTAURANT_MAPPING.get(norm_k)
            if target_field:
                mapped[target_field] = v
        return mapped

    @classmethod
    def map_order_history_row(cls, raw_row: Dict[str, Any]) -> Dict[str, Any]:
        mapped = {}
        for k, v in raw_row.items():
            norm_k = cls.normalize_key(str(k))
            target_field = cls.ORDER_HISTORY_MAPPING.get(norm_k)
            if target_field:
                mapped[target_field] = v
        return mapped
