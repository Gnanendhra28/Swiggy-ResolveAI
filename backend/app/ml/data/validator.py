from dataclasses import dataclass, field
from typing import Dict, Any, List, Set
import pandas as pd


@dataclass
class ValidationReport:
    total_raw_rows: int = 0
    unique_orders: int = 0
    duplicate_rows_dropped: int = 0
    duplicate_order_ids: List[int] = field(default_factory=list)
    negative_accept_delay_count: int = 0
    negative_pickup_delay_count: int = 0
    zero_last_mile_count: int = 0
    extreme_first_mile_count: int = 0
    duration_under_5min_count: int = 0
    duration_over_180min_count: int = 0
    cancelled_count: int = 0
    cancelled_pre_acceptance_count: int = 0
    cancelled_pre_pickup_count: int = 0
    cancelled_in_transit_count: int = 0
    missing_values: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_raw_rows": self.total_raw_rows,
            "unique_orders": self.unique_orders,
            "duplicate_rows_dropped": self.duplicate_rows_dropped,
            "duplicate_order_ids": self.duplicate_order_ids,
            "negative_accept_delay_count": self.negative_accept_delay_count,
            "negative_pickup_delay_count": self.negative_pickup_delay_count,
            "zero_last_mile_count": self.zero_last_mile_count,
            "extreme_first_mile_count": self.extreme_first_mile_count,
            "duration_under_5min_count": self.duration_under_5min_count,
            "duration_over_180min_count": self.duration_over_180min_count,
            "cancelled_count": self.cancelled_count,
            "cancelled_pre_acceptance_count": self.cancelled_pre_acceptance_count,
            "cancelled_pre_pickup_count": self.cancelled_pre_pickup_count,
            "cancelled_in_transit_count": self.cancelled_in_transit_count,
            "missing_values": self.missing_values,
        }


class DataValidator:
    """
    Validates data integrity, identifies anomalies without silent drops,
    and handles exact duplicates according to the Phase 2.1 audit findings.
    """

    REQUIRED_COLUMNS: Set[str] = {
        "order_id",
        "order_time",
        "order_date",
        "allot_time",
        "accept_time",
        "pickup_time",
        "delivered_time",
        "cancelled",
        "rider_id",
        "first_mile_distance",
        "last_mile_distance",
    }

    def validate_and_deduplicate(self, df: pd.DataFrame) -> (pd.DataFrame, ValidationReport):
        report = ValidationReport()
        report.total_raw_rows = len(df)

        # 1. Column existence
        missing_cols = self.REQUIRED_COLUMNS - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns in dataset: {missing_cols}")

        # 2. Missing values profile
        for col in df.columns:
            nulls = int(df[col].isnull().sum())
            if nulls > 0:
                report.missing_values[col] = nulls

        # 3. Duplicate order_id detection
        report.unique_orders = int(df["order_id"].nunique())
        dup_series = df["order_id"].value_counts()
        dup_ids = dup_series[dup_series > 1].index.tolist()
        report.duplicate_order_ids = [int(i) for i in dup_ids]

        # De-duplicate exact rows (Phase 2.1 audit identified 1 exact duplicate: order_id 181402)
        initial_len = len(df)
        df_clean = df.drop_duplicates(subset=["order_id"], keep="first").copy()
        report.duplicate_rows_dropped = initial_len - len(df_clean)

        # 4. Invalid distance checks
        if "last_mile_distance" in df_clean.columns:
            report.zero_last_mile_count = int((df_clean["last_mile_distance"] <= 0.0).sum())
        if "first_mile_distance" in df_clean.columns:
            report.extreme_first_mile_count = int((df_clean["first_mile_distance"] > 20.0).sum())

        # 5. Negative duration checks (if intervals already computed or computable)
        if "accept_delay_min" in df_clean.columns:
            report.negative_accept_delay_count = int((df_clean["accept_delay_min"] < 0).sum())
        if "pickup_delay_min" in df_clean.columns:
            report.negative_pickup_delay_count = int((df_clean["pickup_delay_min"] < 0).sum())

        # 6. Outlier duration checks for completed orders
        if "delivery_duration_min" in df_clean.columns:
            completed_mask = df_clean["cancelled"] == 0
            durations = df_clean.loc[completed_mask, "delivery_duration_min"]
            report.duration_under_5min_count = int((durations < 5.0).sum())
            report.duration_over_180min_count = int((durations > 180.0).sum())

        # 7. Cancellation breakdown
        if "cancelled" in df_clean.columns:
            report.cancelled_count = int((df_clean["cancelled"] == 1).sum())
            if "accept_time" in df_clean.columns:
                report.cancelled_pre_acceptance_count = int(
                    ((df_clean["cancelled"] == 1) & (df_clean["accept_time"].isnull())).sum()
                )
            if "pickup_time" in df_clean.columns:
                report.cancelled_pre_pickup_count = int(
                    (
                        (df_clean["cancelled"] == 1)
                        & (df_clean["accept_time"].notnull())
                        & (df_clean["pickup_time"].isnull())
                    ).sum()
                )
                report.cancelled_in_transit_count = int(
                    ((df_clean["cancelled"] == 1) & (df_clean["pickup_time"].notnull())).sum()
                )

        return df_clean, report
