from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


@dataclass
class FeatureMetadata:
    name: str
    dtype: str
    prediction_point: str
    description: str
    imputation: Optional[str] = None


@dataclass
class TargetMetadata:
    name: str
    task_type: str  # "REGRESSION" | "BINARY_CLASSIFICATION"
    description: str
    stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetMetadata:
    task_name: str
    prediction_point: str
    eligible_cohort_description: str
    total_rows: int
    train_rows: int
    val_rows: int
    test_rows: int
    features: List[Dict[str, Any]]
    target: Dict[str, Any]
    exclusions_log: Dict[str, Any]
    leakage_exclusions: List[str]
    fitted_parameters: Dict[str, Any] = field(default_factory=dict)
    data_provenance: str = "cbhavik/swiggyzomato-order-information (Kaggle)"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
