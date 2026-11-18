import numpy as np
import pandas as pd


class TemporalFeatures:
    """
    Transforms calendar and clock timestamps into continuous cyclic trigonometric
    representations and domain-specific food delivery meal periods.
    """

    @staticmethod
    def extract_temporal(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # 24-Hour Cyclic Transform
        hour = df["order_hour"].astype(float)
        df["hour_sin"] = np.sin(2.0 * np.pi * hour / 24.0)
        df["hour_cos"] = np.cos(2.0 * np.pi * hour / 24.0)

        # 7-Day Cyclic Transform
        dow = df["order_dayofweek"].astype(float)
        df["dow_sin"] = np.sin(2.0 * np.pi * dow / 7.0)
        df["dow_cos"] = np.cos(2.0 * np.pi * dow / 7.0)

        # Food Delivery Meal Period Mapping
        def assign_meal_period(h: int) -> str:
            if 7 <= h <= 10:
                return "BREAKFAST"
            elif 11 <= h <= 14:
                return "LUNCH_PEAK"
            elif 15 <= h <= 18:
                return "AFTERNOON_SLACK"
            elif 19 <= h <= 22:
                return "DINNER_PEAK"
            else:
                return "LATE_NIGHT"

        df["meal_period"] = df["order_hour"].apply(assign_meal_period).astype(str)

        # Peak Meal Period Flag (High Dispatch Pressure Window)
        df["is_peak_meal_window"] = df["meal_period"].isin(
            ["LUNCH_PEAK", "DINNER_PEAK"]
        ).astype(int)

        return df
