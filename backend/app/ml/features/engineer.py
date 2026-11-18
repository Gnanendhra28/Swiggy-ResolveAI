import pandas as pd
from typing import Optional
from backend.app.ml.features.spatial import SpatialFeatures
from backend.app.ml.features.temporal import TemporalFeatures
from backend.app.ml.features.demand import DemandPressureFeatures


class FeatureEngineer:
    """
    Coordinates point-in-time feature engineering across operational stages.
    Strictly separates order-creation features from downstream landmark features.
    Learned parameters (e.g. median courier shift session) are fitted exclusively on the training partition.
    """

    def __init__(self, median_session_time: Optional[float] = None):
        self.median_session_time = median_session_time
        self.fitted_median_session_time: Optional[float] = median_session_time

    def fit(self, train_df: pd.DataFrame) -> "FeatureEngineer":
        """
        Fits feature imputation statistics strictly on the training partition.
        """
        if "session_time" in train_df.columns:
            valid_sessions = train_df["session_time"].dropna()
            if len(valid_sessions) > 0:
                self.fitted_median_session_time = float(valid_sessions.median())
                self.median_session_time = self.fitted_median_session_time
        return self

    def generate_order_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generates only features genuinely available at order creation (t_order).
        No courier, allotment, or milestone information.
        """
        df = df.copy()
        df = SpatialFeatures.extract_order_time_spatial(df)
        df = TemporalFeatures.extract_temporal(df)
        df = DemandPressureFeatures.extract_rolling_demand(df)
        return df

    def generate_landmark_features(
        self, df: pd.DataFrame, landmark_offset_min: float = 5.0
    ) -> pd.DataFrame:
        """
        Generates operational features available at the dispatch landmark (t_allot + 5 min).
        Includes courier transit, session duration, and acceptance latency.
        Uses training-fitted median session time for imputation.
        """
        df = df.copy()

        # Spatial features for assigned courier
        df = SpatialFeatures.extract_allotment_spatial(df)

        # Courier shift telemetry (valid at allotment, imputed with training median)
        impute_session = (
            self.fitted_median_session_time
            if self.fitted_median_session_time is not None
            else 178.15
        )

        if "session_time" in df.columns:
            df["courier_session_time_min"] = df["session_time"].fillna(impute_session)
            df["courier_fatigue_flag"] = (
                df["courier_session_time_min"] > 480.0
            ).astype(int)

        # Allotment latency observed prior to landmark
        df["is_delayed_allotment"] = (df["allot_delay_min"] > 3.0).astype(int)

        # Courier acceptance status at the 5-minute landmark
        landmark_ts = df["allot_time"] + pd.Timedelta(minutes=landmark_offset_min)
        has_accepted = (
            df["accept_time"].notnull() & (df["accept_time"] <= landmark_ts)
        ).astype(int)
        df["has_accepted_by_landmark"] = has_accepted

        # Acceptance delay observed at landmark
        accept_delay = df["accept_delay_min"].fillna(landmark_offset_min)
        # Cap observed acceptance delay at the landmark window
        df["accept_delay_at_landmark"] = accept_delay.clip(
            lower=0.0, upper=landmark_offset_min
        )

        return df
