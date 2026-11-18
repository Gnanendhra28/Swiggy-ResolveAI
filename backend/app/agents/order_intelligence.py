from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.app.core.logging import logger
from backend.app.agents.schemas import RiskTier, InvestigationStatus
from backend.app.agents.state import MultiAgentInvestigationState
from backend.app.services.ml_inference import MLInferenceService


class OrderIntelligenceAgent:
    """
    Order Intelligence Agent:
    - Evaluates order lifecycle eligibility.
    - Requests approved ML predictions (Task A ETA intervals, Task C2 landmark cancellation).
    - Applies deterministic operational risk tiering.
    - Sets initial investigation state.
    """

    def __init__(self, ml_service: Optional[MLInferenceService] = None):
        self.ml_service = ml_service or MLInferenceService.get_instance()

    def evaluate_order(self, state: MultiAgentInvestigationState) -> MultiAgentInvestigationState:
        order_ctx = state.get("order_context", {})
        events = state.get("order_events", [])
        order_status = order_ctx.get("order_status", "PLACED")
        external_order_id = state.get("external_order_id", "UNKNOWN")

        logger.info(f"OrderIntelligenceAgent evaluating order {external_order_id} (Status: {order_status})")

        # 1. Eligibility Check
        terminal_statuses = {"DELIVERED", "CANCELLED"}
        if order_status in terminal_statuses:
            return {
                **state,
                "workflow_status": InvestigationStatus.COMPLETED,
                "risk_tier": RiskTier.NOMINAL,
                "errors": [f"Order is already in terminal status: {order_status}"],
            }

        # 2. Invoke ML Inference Service
        # Build simple mock order wrapper to pass to ML service
        from types import SimpleNamespace
        created_at = order_ctx.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except Exception:
                created_at = datetime.now(timezone.utc)
        elif created_at is None:
            created_at = datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        order_obj = SimpleNamespace(
            id=state.get("order_id"),
            external_order_id=external_order_id,
            created_at=created_at,
            order_status=order_status,
        )

        event_objs = []
        for ev in events:
            ts = ev.get("event_timestamp")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except Exception:
                    ts = datetime.now(timezone.utc)
            elif ts is None:
                ts = datetime.now(timezone.utc)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            event_objs.append(
                SimpleNamespace(
                    event_type=ev.get("event_type", ""),
                    event_timestamp=ts,
                    event_metadata=ev.get("metadata", {}) or ev.get("event_metadata", {}) or {},
                )
            )

        ml_result = self.ml_service.run_inference(order_obj, event_objs)

        # 3. Deterministic Risk Tiering
        task_a = ml_result.task_a_eta
        task_c2 = ml_result.task_c2_cancellation

        # Check promised delivery time vs ETA quantiles
        promised_at = order_ctx.get("promised_delivery_at")
        eta_delay_min = 0.0
        p90_delay_min = 0.0
        if promised_at:
            if isinstance(promised_at, str):
                try:
                    promised_at = datetime.fromisoformat(promised_at)
                except Exception:
                    promised_at = None
            if promised_at:
                if promised_at.tzinfo is None:
                    promised_at = promised_at.replace(tzinfo=timezone.utc)
                projected_p50 = created_at + __import__("datetime").timedelta(minutes=task_a.eta_p50_min)
                projected_p90 = created_at + __import__("datetime").timedelta(minutes=task_a.eta_p90_min)
                eta_delay_min = (projected_p50 - promised_at).total_seconds() / 60.0
                p90_delay_min = (projected_p90 - promised_at).total_seconds() / 60.0

        # Check reassignments
        reassignment_count = 0
        for ev in events:
            if ev.get("event_type") in ("RIDER_REASSIGNED", "ORDER_REASSIGNED"):
                reassignment_count += 1

        # Apply deterministic rule hierarchy
        if task_c2.alert_budget_5_per_1000 or reassignment_count >= 2 or eta_delay_min > 20.0:
            risk_tier = RiskTier.CRITICAL
        elif task_c2.alert_budget_10_per_1000 or eta_delay_min > 10.0 or p90_delay_min > 15.0:
            risk_tier = RiskTier.HIGH_RISK
        elif eta_delay_min > 0.0 or p90_delay_min > 5.0 or task_a.is_long_tail or reassignment_count == 1:
            risk_tier = RiskTier.MONITORED
        else:
            risk_tier = RiskTier.NOMINAL

        ml_dict = {
            "task_a_eta": task_a.model_dump(),
            "task_c2_cancellation": task_c2.model_dump(),
            "research_models": {k: v.model_dump() for k, v in (ml_result.research_models or {}).items()},
            "feature_provenance": ml_result.feature_provenance,
            "model_version": ml_result.model_registry_version,
            "eta_delay_min": round(eta_delay_min, 1),
            "reassignment_count": reassignment_count,
        }

        return {
            **state,
            "ml_predictions": ml_dict,
            "risk_tier": risk_tier,
            "workflow_status": InvestigationStatus.IN_PROGRESS,
            "evidence_and_provenance": {
                "order_intelligence": {
                    "risk_tier": risk_tier.value,
                    "eta_delay_min": round(eta_delay_min, 1),
                    "reassignment_count": reassignment_count,
                    "evaluated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        }
