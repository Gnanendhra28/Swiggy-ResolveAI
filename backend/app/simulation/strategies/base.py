from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from backend.app.simulation.advanced_engine import SimulatedOrderState, SimulationConfig


@dataclass
class StrategyExecutionResult:
    """Individual order outcome resulting from a specific recovery strategy."""
    order_id: str
    external_order_id: str
    strategy_name: str
    seed: int
    scenario_type: str

    # Delivery outcomes
    delivery_duration_min: float
    promised_duration_min: float
    is_on_time: bool
    is_cancelled: bool
    cancellation_reason: Optional[str] = None
    is_post_landmark_cancelled: bool = False

    # Operational metrics
    restaurant_prep_duration_min: float = 0.0
    courier_allotment_duration_min: float = 0.0
    first_mile_duration_min: float = 0.0
    last_mile_duration_min: float = 0.0
    courier_reassigned: bool = False

    # Interventions & Costs
    interventions_count: int = 0
    actions_triggered: List[Dict[str, Any]] = field(default_factory=list)
    total_intervention_cost_inr: float = 0.0
    time_to_first_intervention_min: Optional[float] = None
    time_to_recovery_min: Optional[float] = None
    recovery_successful: bool = False

    # ML & Agent metrics
    eta_p10_min: Optional[float] = None
    eta_p50_min: Optional[float] = None
    eta_p90_min: Optional[float] = None
    eta_interval_width_min: Optional[float] = None
    is_long_tail: bool = False
    task_c2_calibrated_prob: Optional[float] = None
    task_c2_alert_10k: bool = False

    # Agent Performance
    investigation_success: bool = True
    agent_failure: bool = False
    workflow_completed: bool = True
    investigation_latency_ms: float = 0.0
    recommendations_count: int = 0
    requires_approval: bool = False
    approval_status: str = "AUTO_APPROVED"
    rejection_reason: Optional[str] = None

    # Economic impact (Simulated Assumptions)
    cancellation_losses_avoided_inr: float = 0.0
    net_operational_benefit_inr: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "external_order_id": self.external_order_id,
            "strategy_name": self.strategy_name,
            "seed": self.seed,
            "scenario_type": self.scenario_type,
            "delivery_duration_min": round(self.delivery_duration_min, 2),
            "promised_duration_min": round(self.promised_duration_min, 2),
            "is_on_time": self.is_on_time,
            "is_cancelled": self.is_cancelled,
            "cancellation_reason": self.cancellation_reason,
            "is_post_landmark_cancelled": self.is_post_landmark_cancelled,
            "restaurant_prep_duration_min": round(self.restaurant_prep_duration_min, 2),
            "courier_allotment_duration_min": round(self.courier_allotment_duration_min, 2),
            "first_mile_duration_min": round(self.first_mile_duration_min, 2),
            "last_mile_duration_min": round(self.last_mile_duration_min, 2),
            "courier_reassigned": self.courier_reassigned,
            "interventions_count": self.interventions_count,
            "actions_triggered": self.actions_triggered,
            "total_intervention_cost_inr": round(self.total_intervention_cost_inr, 2),
            "time_to_first_intervention_min": self.time_to_first_intervention_min,
            "time_to_recovery_min": self.time_to_recovery_min,
            "recovery_successful": self.recovery_successful,
            "eta_p10_min": self.eta_p10_min,
            "eta_p50_min": self.eta_p50_min,
            "eta_p90_min": self.eta_p90_min,
            "eta_interval_width_min": self.eta_interval_width_min,
            "is_long_tail": self.is_long_tail,
            "task_c2_calibrated_prob": self.task_c2_calibrated_prob,
            "task_c2_alert_10k": self.task_c2_alert_10k,
            "investigation_success": self.investigation_success,
            "agent_failure": self.agent_failure,
            "workflow_completed": self.workflow_completed,
            "investigation_latency_ms": round(self.investigation_latency_ms, 2),
            "recommendations_count": self.recommendations_count,
            "requires_approval": self.requires_approval,
            "approval_status": self.approval_status,
            "rejection_reason": self.rejection_reason,
            "cancellation_losses_avoided_inr": round(self.cancellation_losses_avoided_inr, 2),
            "net_operational_benefit_inr": round(self.net_operational_benefit_inr, 2),
        }


class BaseRecoveryStrategy(ABC):
    """Abstract base class for comparative recovery strategies."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def evaluate_order(
        self, state: SimulatedOrderState, config: SimulationConfig
    ) -> StrategyExecutionResult:
        """Executes the strategy on the order state and produces an outcome result."""
        pass
