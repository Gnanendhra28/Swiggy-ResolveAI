from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for data preprocessing and feature engineering pipelines."""

    raw_orders_path: str = "data/raw/orders/Rider-Info.csv"
    output_base_dir: str = "data/processed"

    # Chronological Split Boundaries (Phase 2.1 Specification)
    train_start_date: str = "2021-01-26 00:00:00"
    train_end_date: str = "2021-02-03 00:00:00"  # Exclusive (train: Jan 26 - Feb 02)
    val_end_date: str = "2021-02-05 00:00:00"    # Exclusive (val: Feb 03 - Feb 04)
    test_end_date: str = "2021-02-07 00:00:00"   # Exclusive (test: Feb 05 - Feb 06 10:03)

    # Operational Thresholds
    min_delivery_duration_min: float = 5.0
    max_delivery_duration_min: float = 180.0
    allocation_delay_threshold_min: float = 3.0
    landmark_offset_min: float = 5.0
    median_last_mile_impute: float = 2.67
    first_mile_outlier_km: float = 20.0

    # Rolling window intervals
    rolling_windows_min: List[int] = field(default_factory=lambda: [15, 60])
