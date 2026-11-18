from typing import Dict, Any, List, Optional
from typing_extensions import TypedDict
from backend.app.agents.schemas import (
    RiskTier,
    InvestigationStatus,
    RestaurantEvidence,
    DeliveryEvidence,
    RecoveryActionRecommendation,
    CustomerResolutionSynthesis,
)


class MultiAgentInvestigationState(TypedDict, total=False):
    # Core Order Context
    order_id: str
    external_order_id: str
    order_context: Dict[str, Any]
    order_events: List[Dict[str, Any]]

    # ML Inference Results (Task A & Task C2)
    ml_predictions: Optional[Dict[str, Any]]
    risk_tier: RiskTier

    # Agent Investigation Findings
    restaurant_investigation: Optional[Dict[str, Any]]
    delivery_investigation: Optional[Dict[str, Any]]
    evidence_and_provenance: Dict[str, Any]

    # Customer Resolution Synthesis & Recommendations
    resolution_synthesis: Optional[Dict[str, Any]]
    recovery_recommendations: List[Dict[str, Any]]

    # Deterministic Policy Engine & Approvals
    policy_validation: Dict[str, Any]
    human_approval_status: Dict[str, Any]

    # Execution & Audit Results
    execution_results: List[Dict[str, Any]]

    # Workflow Status & Telemetry
    workflow_status: InvestigationStatus
    errors: List[str]
