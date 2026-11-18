from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class TriggerInvestigationRequest(BaseModel):
    trigger_event: Optional[str] = "MANUAL_OPERATOR_TRIGGER"


class ApprovalRequest(BaseModel):
    operator_identity: str = Field(default="ops_admin", description="Operator ID or username approving the action")
    operator_role: Optional[str] = Field(default="OPS_LEAD", description="Role of the operator approving the action")
    notes: Optional[str] = Field(default=None, description="Optional operator rationale or instructions")


class RejectionRequest(BaseModel):
    operator_identity: str = Field(default="ops_admin", description="Operator ID or username rejecting the action")
    operator_role: Optional[str] = Field(default="OPS_LEAD", description="Role of the operator rejecting the action")
    reason: str = Field(..., description="Operational reason for rejection")


class ExecuteActionRequest(BaseModel):
    operator_identity: str = Field(default="ops_admin", description="Operator ID or trigger identity")
    operator_role: Optional[str] = Field(default="OPS_LEAD", description="Role of the executing operator")


class RecommendationResponse(BaseModel):
    id: str
    investigation_id: str
    order_id: str
    action_type: str
    title: str
    rationale: str
    sensitivity_level: str
    estimated_impact: Optional[str] = None
    requires_approval: bool
    approval_status: str
    approved_by: Optional[str] = None
    operator_role: Optional[str] = None
    approval_notes: Optional[str] = None
    approval_timestamp: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    execution_status: str
    execution_payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvestigationResponse(BaseModel):
    id: str
    order_id: str
    status: str
    risk_tier: str
    trigger_event: Optional[str] = None
    eta_p10: Optional[float] = None
    eta_p50: Optional[float] = None
    eta_p90: Optional[float] = None
    eta_interval_width: Optional[float] = None
    is_long_tail: bool = False
    cancellation_probability: Optional[float] = None
    cancellation_alert_budget_10k: bool = False
    ml_provenance: Dict[str, Any] = Field(default_factory=dict)
    restaurant_evidence: Dict[str, Any] = Field(default_factory=dict)
    delivery_evidence: Dict[str, Any] = Field(default_factory=dict)
    agent_reasoning: Dict[str, Any] = Field(default_factory=dict)
    workflow_execution: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[RecommendationResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExecutionAuditResponse(BaseModel):
    id: str
    recommendation_id: str
    order_id: str
    action_type: str
    initial_order_status: str
    final_order_status: str
    idempotency_key: str
    trigger_reason: str
    ml_model_version: str
    approval_identity: Optional[str] = None
    approval_timestamp: Optional[datetime] = None
    execution_result: Dict[str, Any] = Field(default_factory=dict)
    recovery_outcome: str
    is_simulated: bool
    executed_at: datetime

    class Config:
        from_attributes = True


class MLPredictionAuditResponse(BaseModel):
    id: str
    order_id: str
    model_version: str
    feature_schema_version: str
    task_a_eta_p50: Optional[float] = None
    task_a_interval_min: Optional[float] = None
    task_a_interval_max: Optional[float] = None
    task_a_is_long_tail: bool = False
    task_c2_is_eligible: bool = False
    task_c2_calibrated_prob: Optional[float] = None
    task_c2_alert_5k: bool = False
    task_c2_alert_10k: bool = False
    task_b_score: Optional[float] = None
    task_c1_score: Optional[float] = None
    provenance_metadata: Dict[str, Any] = Field(default_factory=dict)
    prediction_timestamp: datetime

    class Config:
        from_attributes = True
