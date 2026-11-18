import pandas as pd
from typing import Tuple, Dict, Any, List
from backend.app.ml.schemas.metadata import FeatureMetadata, TargetMetadata


class TargetBuilder:
    """
    Constructs target labels with operational definitions and leakage control.
    """

    @staticmethod
    def build_delivery_duration_target(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["target_delivery_duration_min"] = df["delivery_duration_min"]
        return df

    @staticmethod
    def build_allocation_delay_target(
        df: pd.DataFrame, threshold_min: float = 3.0
    ) -> pd.DataFrame:
        df = df.copy()
        df["target_is_allocation_delayed"] = (
            df["allot_delay_min"] > threshold_min
        ).astype(int)
        df["aux_allot_delay_min"] = df["allot_delay_min"]
        return df

    @staticmethod
    def build_cancellation_target(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["target_is_cancelled"] = df["cancelled"].astype(int)
        return df

    @staticmethod
    def build_landmark_cancellation_target(
        df: pd.DataFrame, landmark_offset_min: float = 5.0
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        df = df.copy()

        # Landmark timestamp
        landmark_ts = df["allot_time"] + pd.Timedelta(minutes=landmark_offset_min)

        # Orders terminated prior to the landmark cannot be predicted at landmark
        cancelled_prior = (df["cancelled"] == 1) & (
            df["cancelled_time"] <= landmark_ts
        )
        delivered_prior = (df["cancelled"] == 0) & (
            df["delivered_time"] <= landmark_ts
        )

        active_at_landmark = (~cancelled_prior) & (~delivered_prior)

        cohort_df = df[active_at_landmark].copy()

        # Target: Did order cancel subsequently during the remaining lifecycle?
        cohort_df["target_cancelled_post_landmark"] = cohort_df["cancelled"].astype(int)

        exclusions = {
            "initial_rows": int(len(df)),
            "cancelled_prior_to_landmark": int(cancelled_prior.sum()),
            "delivered_prior_to_landmark": int(delivered_prior.sum()),
            "active_at_landmark_rows": int(active_at_landmark.sum()),
            "cancelled_post_landmark_count": int(
                (cohort_df["target_cancelled_post_landmark"] == 1).sum()
            ),
            "cancelled_post_landmark_rate_pct": round(
                float(
                    (cohort_df["target_cancelled_post_landmark"] == 1).sum()
                    / len(cohort_df)
                    * 100
                ),
                4,
            ),
        }

        return cohort_df, exclusions


class DatasetBuilder:
    """
    Constructs clean, leak-free feature and target matrices for the 3 ML tasks.
    """

    ORDER_TIME_FEATURE_COLUMNS: List[str] = [
        "last_mile_distance",
        "is_zero_last_mile",
        "last_mile_distance_sq",
        "distance_bracket",
        "order_hour",
        "hour_sin",
        "hour_cos",
        "order_dayofweek",
        "dow_sin",
        "dow_cos",
        "is_weekend",
        "meal_period",
        "is_peak_meal_window",
        "rolling_order_volume_15m",
        "rolling_order_volume_60m",
        "demand_acceleration",
    ]

    LANDMARK_FEATURE_COLUMNS: List[str] = [
        "first_mile_distance",
        "is_extreme_first_mile",
        "first_to_last_mile_ratio",
        "total_route_distance",
        "courier_session_time_min",
        "courier_fatigue_flag",
        "is_delayed_allotment",
        "allot_delay_min",
        "has_accepted_by_landmark",
        "accept_delay_at_landmark",
    ]

    @classmethod
    def get_order_time_feature_metadata(cls) -> List[FeatureMetadata]:
        return [
            FeatureMetadata("last_mile_distance", "float64", "t_order", "Restaurant-to-customer doorstep distance in km", "median=2.67km"),
            FeatureMetadata("is_zero_last_mile", "int32", "t_order", "Binary indicator for missing/zero last mile distance", "imputed with median"),
            FeatureMetadata("last_mile_distance_sq", "float64", "t_order", "Quadratic last-mile distance for non-linear travel latency"),
            FeatureMetadata("distance_bracket", "category", "t_order", "Binned distance tier (ultra_short, short, medium, long, hyper_long)"),
            FeatureMetadata("order_hour", "int32", "t_order", "Order placement hour of day (0-23)"),
            FeatureMetadata("hour_sin", "float64", "t_order", "Cyclic sine transform of hour of day"),
            FeatureMetadata("hour_cos", "float64", "t_order", "Cyclic cosine transform of hour of day"),
            FeatureMetadata("order_dayofweek", "int32", "t_order", "Order placement day of week (0=Mon, 6=Sun)"),
            FeatureMetadata("dow_sin", "float64", "t_order", "Cyclic sine transform of day of week"),
            FeatureMetadata("dow_cos", "float64", "t_order", "Cyclic cosine transform of day of week"),
            FeatureMetadata("is_weekend", "int32", "t_order", "Binary indicator for Saturday/Sunday demand"),
            FeatureMetadata("meal_period", "category", "t_order", "Operational meal window (BREAKFAST, LUNCH_PEAK, etc.)"),
            FeatureMetadata("is_peak_meal_window", "int32", "t_order", "Binary flag for lunch or dinner peak dispatch window"),
            FeatureMetadata("rolling_order_volume_15m", "float64", "t_order", "Backward-looking order placement volume in preceding 15m"),
            FeatureMetadata("rolling_order_volume_60m", "float64", "t_order", "Backward-looking order placement volume in preceding 60m"),
            FeatureMetadata("demand_acceleration", "float64", "t_order", "Ratio of recent 15m surge intensity to hourly average"),
        ]

    @classmethod
    def get_landmark_feature_metadata(cls) -> List[FeatureMetadata]:
        return [
            FeatureMetadata("first_mile_distance", "float64", "t_landmark", "Courier-to-restaurant transit distance in km", "capped at 20km"),
            FeatureMetadata("is_extreme_first_mile", "int32", "t_landmark", "Binary flag for courier transit distance > 20km"),
            FeatureMetadata("first_to_last_mile_ratio", "float64", "t_landmark", "Ratio of courier pickup distance to customer dropoff distance"),
            FeatureMetadata("total_route_distance", "float64", "t_landmark", "Sum of first-mile and last-mile distances"),
            FeatureMetadata("courier_session_time_min", "float64", "t_landmark", "Courier active shift duration in minutes at assignment", "median=175.5min"),
            FeatureMetadata("courier_fatigue_flag", "int32", "t_landmark", "Binary indicator for courier shift duration > 8 hours"),
            FeatureMetadata("is_delayed_allotment", "int32", "t_landmark", "Binary flag if allotment delay exceeded 3 minutes"),
            FeatureMetadata("allot_delay_min", "float64", "t_landmark", "Continuous minutes between order placement and courier assignment"),
            FeatureMetadata("has_accepted_by_landmark", "int32", "t_landmark", "Binary indicator if courier accepted assignment within 5 minutes"),
            FeatureMetadata("accept_delay_at_landmark", "float64", "t_landmark", "Observed courier acceptance delay capped at 5 minutes"),
        ]

    def build_delivery_duration_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = ["order_id", "order_time"] + self.ORDER_TIME_FEATURE_COLUMNS + ["target_delivery_duration_min"]
        return df[cols].copy()

    def build_allocation_delay_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = ["order_id", "order_time"] + self.ORDER_TIME_FEATURE_COLUMNS + ["target_is_allocation_delayed", "aux_allot_delay_min"]
        return df[cols].copy()

    def build_cancellation_order_time_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = ["order_id", "order_time"] + self.ORDER_TIME_FEATURE_COLUMNS + ["target_is_cancelled"]
        return df[cols].copy()

    def build_cancellation_landmark_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = (
            ["order_id", "order_time", "allot_time"]
            + self.ORDER_TIME_FEATURE_COLUMNS
            + self.LANDMARK_FEATURE_COLUMNS
            + ["target_cancelled_post_landmark"]
        )
        return df[cols].copy()
