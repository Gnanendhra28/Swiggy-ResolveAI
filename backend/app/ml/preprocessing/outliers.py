import pandas as pd
from typing import Tuple, Dict, Any, Optional


class OutlierHandler:
    """
    Handles physical and operational outliers transparently.
    Imputes invalid sensor/GPS values using parameters fitted exclusively on the training partition.
    Logs every cohort exclusion without silent record deletion.
    """

    def __init__(
        self,
        min_duration_min: float = 5.0,
        max_duration_min: float = 180.0,
        median_last_mile: Optional[float] = None,
        max_first_mile: float = 20.0,
    ):
        self.min_duration_min = min_duration_min
        self.max_duration_min = max_duration_min
        self.median_last_mile = median_last_mile
        self.max_first_mile = max_first_mile
        self.fitted_median_last_mile: Optional[float] = median_last_mile

    def fit(self, train_df: pd.DataFrame) -> "OutlierHandler":
        """
        Fits imputation statistics strictly on the training partition.
        Guarantees that validation and test data cannot influence fitted values.
        """
        if "last_mile_distance" in train_df.columns:
            non_zero = train_df.loc[train_df["last_mile_distance"] > 0, "last_mile_distance"]
            if len(non_zero) > 0:
                self.fitted_median_last_mile = float(non_zero.median())
                self.median_last_mile = self.fitted_median_last_mile
        return self

    def handle_distances(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies distance imputation and boundary capping using fitted parameters.
        """
        if self.fitted_median_last_mile is None:
            raise ValueError(
                "OutlierHandler has not been fitted! Call fit(train_df) before handle_distances()."
            )

        df = df.copy()

        # Handle zero or negative last-mile distance (94 records in audit)
        if "last_mile_distance" in df.columns:
            df["is_zero_last_mile"] = (df["last_mile_distance"] <= 0.0).astype(int)
            df.loc[df["last_mile_distance"] <= 0.0, "last_mile_distance"] = self.fitted_median_last_mile

        # Handle extreme first-mile distance (1 record > 20 km)
        if "first_mile_distance" in df.columns:
            df["is_extreme_first_mile"] = (df["first_mile_distance"] > self.max_first_mile).astype(int)
            df.loc[df["first_mile_distance"] > self.max_first_mile, "first_mile_distance"] = self.max_first_mile

        return df

    def filter_delivery_duration_cohort(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Filters completed orders for Task A (Delivery Duration Regression).
        Requires completed orders with 5.0 <= delivery_duration_min <= 180.0.
        """
        df = df.copy()

        # Must be completed orders
        completed_mask = df["cancelled"] == 0
        non_null_duration_mask = df["delivery_duration_min"].notnull()

        valid_base = completed_mask & non_null_duration_mask

        under_min_mask = valid_base & (df["delivery_duration_min"] < self.min_duration_min)
        over_max_mask = valid_base & (df["delivery_duration_min"] > self.max_duration_min)
        eligible_mask = (
            valid_base
            & (df["delivery_duration_min"] >= self.min_duration_min)
            & (df["delivery_duration_min"] <= self.max_duration_min)
        )

        exclusions = {
            "initial_completed_orders": int(completed_mask.sum()),
            "under_min_duration_excluded": int(under_min_mask.sum()),
            "over_max_duration_excluded": int(over_max_mask.sum()),
            "eligible_cohort_rows": int(eligible_mask.sum()),
            "retention_rate_pct": round(float(eligible_mask.sum() / completed_mask.sum() * 100), 4),
        }

        eligible_df = df[eligible_mask].copy()
        return eligible_df, exclusions
