import pandas as pd
import numpy as np


class SpatialFeatures:
    """
    Transforms geographic distance fields into non-linear, binned, and interaction features.
    """

    @staticmethod
    def extract_order_time_spatial(df: pd.DataFrame) -> pd.DataFrame:
        """Features available at order creation: last-mile delivery distance."""
        df = df.copy()

        # Non-linear quadratic term
        df["last_mile_distance_sq"] = df["last_mile_distance"] ** 2

        # Distance brackets
        bins = [-np.inf, 1.0, 2.5, 5.0, 8.0, np.inf]
        labels = ["ultra_short", "short", "medium", "long", "hyper_long"]
        df["distance_bracket"] = pd.cut(
            df["last_mile_distance"], bins=bins, labels=labels
        ).astype(str)

        return df

    @staticmethod
    def extract_allotment_spatial(df: pd.DataFrame) -> pd.DataFrame:
        """Features available at courier allotment: first-mile transit and spatial ratios."""
        df = df.copy()

        if "first_mile_distance" in df.columns and "last_mile_distance" in df.columns:
            # Ratio of courier-to-restaurant distance vs restaurant-to-customer distance
            df["first_to_last_mile_ratio"] = df["first_mile_distance"] / (
                df["last_mile_distance"] + 0.1
            )
            df["total_route_distance"] = (
                df["first_mile_distance"] + df["last_mile_distance"]
            )

        return df
