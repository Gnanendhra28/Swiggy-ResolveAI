from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class RiskTier(str, Enum):
    NOMINAL = "NOMINAL"
    MONITORED = "MONITORED"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


class InvestigationStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ActionType(str, Enum):
    MONITOR_ORDER = "MONITOR_ORDER"
    EXPEDITE_KITCHEN_PING = "EXPEDITE_KITCHEN_PING"
    PRIORITIZE_COURIER_DISPATCH = "PRIORITIZE_COURIER_DISPATCH"
    REASSIGN_COURIER = "REASSIGN_COURIER"
    PROACTIVE_CUSTOMER_NOTIFICATION = "PROACTIVE_CUSTOMER_NOTIFICATION"
    APOLOGY_CREDIT_VOUCHER = "APOLOGY_CREDIT_VOUCHER"


class SensitivityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ApprovalStatus(str, Enum):
    AUTO_APPROVED = "AUTO_APPROVED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RestaurantEvidence(BaseModel):
    acceptance_latency_min: float = 0.0
    is_delayed_acceptance: bool = False
    prep_elapsed_min: float = 0.0
    estimated_prep_total_min: float = 15.0
    prep_delay_min: float = 0.0
    kitchen_backlog_orders: int = 0
    kitchen_backlog_source: str = "SIMULATED_TELEMETRY"  # Clearly marked: not from historical telemetry
    merchant_active: bool = True
    operational_impact: str = "Nominal kitchen preparation"
    suspected_cause: str = "Normal preparation pace"
    confidence: str = "HIGH"


class DeliveryEvidence(BaseModel):
    courier_assigned: bool = True
    courier_id: Optional[str] = None
    courier_name: Optional[str] = None
    allotment_latency_min: float = 0.0
    is_allotment_delayed: bool = False
    first_mile_km: float = 1.85
    is_extreme_first_mile: bool = False
    courier_accepted: bool = True
    courier_acceptance_latency_min: float = 1.2
    transit_congestion_factor: float = 1.0
    reassignment_count: int = 0
    operational_impact: str = "Nominal courier dispatch"
    suspected_cause: str = "Courier on expected transit route"
    confidence: str = "HIGH"


class RecoveryActionRecommendation(BaseModel):
    id: str = Field(default_factory=lambda: "rec_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:17])
    action_type: ActionType
    title: str
    rationale: str
    sensitivity_level: SensitivityLevel
    estimated_impact: str
    requires_approval: bool
    approval_status: ApprovalStatus = ApprovalStatus.PENDING_APPROVAL
    rank: int = 1
    execution_payload: Dict[str, Any] = Field(default_factory=dict)


class CustomerResolutionSynthesis(BaseModel):
    root_cause_summary: str
    primary_bottleneck: str  # "RESTAURANT_KITCHEN", "COURIER_DISPATCH", "TRANSIT_TRAFFIC", "NOMINAL"
    customer_impact_severity: str  # "LOW", "MODERATE", "SEVERE"
    recommendations: List[RecoveryActionRecommendation] = Field(default_factory=list)
    operational_risk_summary: str
