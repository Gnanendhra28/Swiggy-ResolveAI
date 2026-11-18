import pandas as pd
from typing import Tuple, Dict, Any
from backend.app.ml.schemas.config import PipelineConfig


class ChronologicalSplitter:
    """
    Splits order datasets strictly chronologically into Train, Validation, and Test sets.
    Prohibits random cross-validation to prevent temporal lookahead leakage.
    """

    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()

    def split(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        df = df.copy()

        # Timestamp boundary masks
        t = df["order_time"]

        train_mask = (t >= self.config.train_start_date) & (
            t < self.config.train_end_date
        )
        val_mask = (t >= self.config.train_end_date) & (
            t < self.config.val_end_date
        )
        test_mask = (t >= self.config.val_end_date) & (
            t < self.config.test_end_date
        )

        train_df = df[train_mask].copy()
        val_df = df[val_mask].copy()
        test_df = df[test_mask].copy()

        total_split_rows = len(train_df) + len(val_df) + len(test_df)
        if total_split_rows != len(df):
            unassigned_count = len(df) - total_split_rows
            raise ValueError(
                f"Chronological split failed: {unassigned_count} rows out of temporal boundaries!"
            )

        # Integrity verification: zero overlap of order_id between partitions
        train_orders = set(train_df["order_id"])
        val_orders = set(val_df["order_id"])
        test_orders = set(test_df["order_id"])

        train_val_overlap = len(train_orders.intersection(val_orders))
        val_test_overlap = len(val_orders.intersection(test_orders))
        train_test_overlap = len(train_orders.intersection(test_orders))

        if (
            train_val_overlap > 0
            or val_test_overlap > 0
            or train_test_overlap > 0
        ):
            raise ValueError(
                f"Order leakage detected across partitions! Overlaps: Train-Val={train_val_overlap}, Val-Test={val_test_overlap}, Train-Test={train_test_overlap}"
            )

        split_stats = {
            "total_rows": len(df),
            "train_rows": len(train_df),
            "train_pct": round(len(train_df) / len(df) * 100, 2),
            "val_rows": len(val_df),
            "val_pct": round(len(val_df) / len(df) * 100, 2),
            "test_rows": len(test_df),
            "test_pct": round(len(test_df) / len(df) * 100, 2),
            "train_date_range": [
                str(train_df["order_time"].min()),
                str(train_df["order_time"].max()),
            ],
            "val_date_range": [
                str(val_df["order_time"].min()),
                str(val_df["order_time"].max()),
            ],
            "test_date_range": [
                str(test_df["order_time"].min()),
                str(test_df["order_time"].max()),
            ],
        }

        return train_df, val_df, test_df, split_stats
