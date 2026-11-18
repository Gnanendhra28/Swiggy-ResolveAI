from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass(frozen=True)
class TrainingTaskConfig:
    task_name: str
    target_column: str
    task_type: str  # "REGRESSION" | "BINARY_CLASSIFICATION"
    dataset_dir: str
    feature_columns: List[str]
    categorical_columns: List[str]
    random_state: int = 42

    # Hyperparameters for baseline and candidate models
    ridge_alpha: float = 1.0
    logistic_c: float = 1.0
    lgb_n_estimators: int = 150
    lgb_learning_rate: float = 0.05
    lgb_num_leaves: int = 31
    lgb_min_child_samples: int = 20

    # Class weighting for imbalanced tasks
    scale_pos_weight: Optional[float] = None


def get_task_a_config() -> TrainingTaskConfig:
    """Task A: Pre-dispatch Delivery Duration Regression (ETA)."""
    return TrainingTaskConfig(
        task_name="delivery_duration",
        target_column="target_delivery_duration_min",
        task_type="REGRESSION",
        dataset_dir="data/processed/delivery_duration",
        feature_columns=[
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
        ],
        categorical_columns=["distance_bracket", "meal_period"],
        random_state=42,
    )


def get_task_b_config() -> TrainingTaskConfig:
    """Task B: Rider Allocation Delay Risk (>3 minutes)."""
    return TrainingTaskConfig(
        task_name="allocation_delay",
        target_column="target_is_allocation_delayed",
        task_type="BINARY_CLASSIFICATION",
        dataset_dir="data/processed/allocation_delay",
        feature_columns=[
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
        ],
        categorical_columns=["distance_bracket", "meal_period"],
        scale_pos_weight=15.3,  # ~93.9% / 6.1%
        random_state=42,
    )


def get_task_c1_config() -> TrainingTaskConfig:
    """Task C1: Upfront Cancellation Risk at Order Placement."""
    return TrainingTaskConfig(
        task_name="cancellation_upfront",
        target_column="target_is_cancelled",
        task_type="BINARY_CLASSIFICATION",
        dataset_dir="data/processed/cancellation",
        feature_columns=[
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
        ],
        categorical_columns=["distance_bracket", "meal_period"],
        scale_pos_weight=85.2,  # ~98.8% / 1.2%
        random_state=42,
    )


def get_task_c2_config() -> TrainingTaskConfig:
    """Task C2: Operational Landmark Cancellation Risk (at t_allot + 5m)."""
    return TrainingTaskConfig(
        task_name="cancellation_landmark",
        target_column="target_cancelled_post_landmark",
        task_type="BINARY_CLASSIFICATION",
        dataset_dir="data/processed/cancellation/operational_landmark",
        feature_columns=[
            # Order-time features
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
            # Landmark features
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
        ],
        categorical_columns=["distance_bracket", "meal_period"],
        scale_pos_weight=93.6,  # ~98.9% / 1.1%
        random_state=42,
    )
