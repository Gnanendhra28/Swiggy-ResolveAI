import pandas as pd
from typing import List


class TimestampProcessor:
    """
    Parses and standardizes lifecycle timestamps to UTC datetime64[ns].
    Computes operational milestone durations handling midnight and date boundaries.
    """

    TIMESTAMP_COLUMNS: List[str] = [
        "order_time",
        "allot_time",
        "accept_time",
        "pickup_time",
        "delivered_time",
        "cancelled_time",
    ]

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Parse all timestamp columns to UTC datetime64[ns]
        for col in self.TIMESTAMP_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # Parse order_date
        if "order_date" in df.columns:
            df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
        else:
            df["order_date"] = df["order_time"].dt.floor("D")

        # Derived temporal components
        df["order_hour"] = df["order_time"].dt.hour
        df["order_dayofweek"] = df["order_time"].dt.dayofweek
        df["is_weekend"] = df["order_dayofweek"].isin([5, 6]).astype(int)

        # Operational milestone durations (in minutes)
        # Using full datetime differences automatically handles midnight and cross-day rollovers
        df["allot_delay_min"] = (
            df["allot_time"] - df["order_time"]
        ).dt.total_seconds() / 60.0

        # Nullable milestone durations
        if "accept_time" in df.columns:
            df["accept_delay_min"] = (
                df["accept_time"] - df["allot_time"]
            ).dt.total_seconds() / 60.0

        if "pickup_time" in df.columns:
            df["pickup_delay_min"] = (
                df["pickup_time"] - df["accept_time"]
            ).dt.total_seconds() / 60.0

        if "delivered_time" in df.columns:
            df["transit_duration_min"] = (
                df["delivered_time"] - df["pickup_time"]
            ).dt.total_seconds() / 60.0

            df["delivery_duration_min"] = (
                df["delivered_time"] - df["order_time"]
            ).dt.total_seconds() / 60.0

        return df
