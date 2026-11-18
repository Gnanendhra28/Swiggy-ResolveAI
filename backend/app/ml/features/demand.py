import pandas as pd
import numpy as np


class DemandPressureFeatures:
    """
    Computes backward-looking rolling demand pressure features without lookahead leakage.
    Ensures that for any order at t_order, only orders with t < t_order are observed.

    IMPORTANT PROVENANCE & GEOGRAPHIC SCOPE NOTE:
    The Kaggle dataset (`Rider-Info.csv`) does not capture city, zone, or restaurant identifiers.
    Therefore, rolling order counts represent a GLOBAL SYSTEM-WIDE DEMAND VELOCITY across the
    entire dataset, rather than a localized neighborhood or restaurant kitchen queue.
    """

    @staticmethod
    def extract_rolling_demand(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Preserve original row ordering index
        orig_index = df.index

        # Sort temporarily by order_time to ensure strict chronological windowing
        df_sorted = df.sort_values("order_time").copy()

        # Construct time-indexed series
        ts_series = pd.Series(1, index=df_sorted["order_time"])

        # Rolling counts strictly backward-looking (closed='left' excludes the current order)
        # Any simultaneous orders placed at the exact same second are also excluded from each other
        rolling_15m = (
            ts_series.rolling("15min", closed="left")
            .count()
            .fillna(0.0)
            .values
        )
        rolling_60m = (
            ts_series.rolling("60min", closed="left")
            .count()
            .fillna(0.0)
            .values
        )

        df_sorted["rolling_order_volume_15m"] = rolling_15m
        df_sorted["rolling_order_volume_60m"] = rolling_60m

        # Demand acceleration metric: surge intensity in recent 15m vs hourly average rate
        # Denominator is strictly safe against division-by-zero:
        # Since rolling_60m >= 0, (rolling_60m + 1.0) >= 1.0 > 0 at all times.
        safe_denominator = np.maximum(rolling_60m, 0.0) + 1.0
        df_sorted["demand_acceleration"] = (rolling_15m * 4.0) / safe_denominator

        # Restore original DataFrame order
        df_restored = df_sorted.loc[orig_index]
        return df_restored
