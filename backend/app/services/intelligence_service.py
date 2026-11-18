import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.models.order import Order
from backend.app.models.investigation import OrderInvestigation
from backend.app.models.recommendation import RecoveryRecommendation
from backend.app.models.audit import RecoveryExecutionAudit
from backend.app.models.ml_audit import MLPredictionAudit
from backend.app.agents.workflow import intelligence_workflow
from backend.app.agents.schemas import InvestigationStatus, ApprovalStatus
from backend.app.services.policy_engine import PolicyEngine
from backend.app.services.recovery_executor import RecoveryExecutionService
from backend.app.services.ml_inference import MLInferenceService


class IntelligenceService:
    """
    Hardened central application service managing multi-agent investigations,
    persisting results, ML audits, role-based operator approvals, and simulated recoveries.
    """

    @classmethod
    def trigger_investigation(
        cls,
        db: Session,
        order_id: str,
        trigger_event: Optional[str] = "MANUAL_OPERATOR_TRIGGER",
        correlation_id: Optional[str] = None,
    ) -> OrderInvestigation:
        """
        Executes an end-to-end multi-agent investigation workflow for the given order,
        persisting the investigation record, ML prediction audits, and recommendations.
        """
        start_perf = time.perf_counter()
        order = db.query(Order).filter(
            (Order.id == order_id) | (Order.external_order_id == order_id)
        ).first()
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        logger.info(
            f"Triggering multi-agent investigation for order {order.external_order_id} "
            f"({trigger_event}) [CorrID: {correlation_id or 'NONE'}]"
        )

        # 1. Prepare LangGraph state
        order_events_data = []
        for ev in order.events:
            order_events_data.append({
                "event_type": ev.event_type,
                "event_timestamp": ev.event_timestamp.isoformat() if ev.event_timestamp else None,
                "metadata": ev.event_metadata or {},
                "data_source": ev.data_source,
            })

        order_context = {
            "order_id": order.id,
            "external_order_id": order.external_order_id,
            "order_status": order.order_status,
            "order_value": order.order_value,
            "promised_delivery_at": order.promised_delivery_at.isoformat() if order.promised_delivery_at else None,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "restaurant": {
                "id": order.restaurant.id if order.restaurant else None,
                "name": order.restaurant.name if order.restaurant else "Unknown Restaurant",
                "cuisine": order.restaurant.cuisine if order.restaurant else "Indian",
                "city": order.restaurant.city if order.restaurant else "Bengaluru",
                "is_active": getattr(order.restaurant, "is_active", True),
            },
            "delivery_partner": {
                "id": order.delivery_partner.id if order.delivery_partner else None,
                "name": order.delivery_partner.name if order.delivery_partner else "Unassigned",
                "phone": getattr(order.delivery_partner, "phone", None),
            } if order.delivery_partner else None,
        }

        initial_state = {
            "order_id": order.id,
            "external_order_id": order.external_order_id,
            "order_context": order_context,
            "order_events": order_events_data,
            "workflow_status": InvestigationStatus.PENDING,
            "errors": [],
        }

        # 2. Execute LangGraph Workflow
        final_state = intelligence_workflow.invoke(initial_state)

        # 3. Extract and parse results
        ml_preds = final_state.get("ml_predictions", {}) or {}
        task_a = ml_preds.get("task_a_eta", {})
        task_c2 = ml_preds.get("task_c2_cancellation", {})
        risk_tier_val = final_state.get("risk_tier")
        risk_tier_str = risk_tier_val.value if hasattr(risk_tier_val, "value") else str(risk_tier_val)

        now = datetime.now(timezone.utc)
        inv_duration_ms = round((time.perf_counter() - start_perf) * 1000.0, 2)

        investigation = OrderInvestigation(
            order_id=order.id,
            status=final_state.get("workflow_status", InvestigationStatus.COMPLETED).value
            if hasattr(final_state.get("workflow_status"), "value")
            else str(final_state.get("workflow_status")),
            risk_tier=risk_tier_str,
            trigger_event=trigger_event,
            eta_p10=task_a.get("eta_p10_min"),
            eta_p50=task_a.get("eta_p50_min"),
            eta_p90=task_a.get("eta_p90_min"),
            eta_interval_width=task_a.get("interval_width_min"),
            is_long_tail=task_a.get("is_long_tail", False),
            cancellation_probability=task_c2.get("calibrated_probability"),
            cancellation_alert_budget_10k=task_c2.get("alert_budget_10_per_1000", False),
            ml_provenance=ml_preds,
            restaurant_evidence=final_state.get("restaurant_investigation", {}) or {},
            delivery_evidence=final_state.get("delivery_investigation", {}) or {},
            agent_reasoning=final_state.get("resolution_synthesis", {}) or {},
            workflow_execution={
                "policy_summary": final_state.get("policy_validation", {}),
                "graph_status": final_state.get("workflow_status", InvestigationStatus.COMPLETED).value
                if hasattr(final_state.get("workflow_status"), "value")
                else str(final_state.get("workflow_status")),
                "investigation_duration_ms": inv_duration_ms,
                "completed_at": now.isoformat(),
                "correlation_id": correlation_id,
            },
            created_at=now,
            updated_at=now,
        )
        db.add(investigation)
        db.flush()

        # 4. Persist Independent ML Prediction Audit
        ml_audit = MLPredictionAudit(
            order_id=order.id,
            model_version=ml_preds.get("model_version", "2.5.0"),
            feature_schema_version="1.0.0",
            task_a_eta_p50=task_a.get("eta_p50_min"),
            task_a_interval_min=task_a.get("eta_p10_min"),
            task_a_interval_max=task_a.get("eta_p90_min"),
            task_a_is_long_tail=task_a.get("is_long_tail", False),
            task_c2_is_eligible=task_c2.get("is_eligible", False),
            task_c2_calibrated_prob=task_c2.get("calibrated_probability"),
            task_c2_alert_5k=task_c2.get("alert_budget_5_per_1000", False),
            task_c2_alert_10k=task_c2.get("alert_budget_10_per_1000", False),
            task_b_score=ml_preds.get("research_models", {}).get("task_b_allocation_delay", {}).get("score"),
            task_c1_score=ml_preds.get("research_models", {}).get("task_c1_upfront_cancellation", {}).get("score"),
            provenance_metadata=ml_preds.get("feature_provenance", {}),
            prediction_timestamp=now,
        )
        db.add(ml_audit)

        # 5. Persist Recommendations with Expiry Window (30 min)
        recs_data = final_state.get("recovery_recommendations", [])
        persisted_recs = []
        expires_at = now + timedelta(minutes=30)

        for r in recs_data:
            action_type_val = r.get("action_type")
            action_type_str = action_type_val.value if hasattr(action_type_val, "value") else str(action_type_val)
            approval_status_val = r.get("approval_status")
            approval_status_str = approval_status_val.value if hasattr(approval_status_val, "value") else str(approval_status_val)
            sensitivity_val = r.get("sensitivity_level")
            sensitivity_str = sensitivity_val.value if hasattr(sensitivity_val, "value") else str(sensitivity_val)

            rec_obj = RecoveryRecommendation(
                investigation_id=investigation.id,
                order_id=order.id,
                action_type=action_type_str,
                title=r.get("title", action_type_str),
                rationale=r.get("rationale", "Grounded multi-agent recommendation."),
                sensitivity_level=sensitivity_str,
                estimated_impact=r.get("estimated_impact"),
                requires_approval=r.get("requires_approval", False),
                approval_status=approval_status_str,
                approval_notes=r.get("approval_notes"),
                expires_at=expires_at,
                execution_status="PENDING",
                execution_payload=r.get("execution_payload", {}),
                created_at=now,
                updated_at=now,
            )
            db.add(rec_obj)
            persisted_recs.append(rec_obj)

        db.commit()
        db.refresh(investigation)

        # 6. Automatically execute auto-approved, non-intrusive actions
        for rec in persisted_recs:
            if not rec.requires_approval and rec.approval_status == ApprovalStatus.AUTO_APPROVED.value:
                try:
                    RecoveryExecutionService.execute_recommendation(
                        db=db, recommendation_id=rec.id, operator_identity="AUTONOMOUS_POLICY_ENGINE"
                    )
                except Exception as exc:
                    logger.warning(f"Error auto-executing recommendation {rec.id}: {exc}")

        db.refresh(investigation)
        return investigation

    @classmethod
    def get_investigation(cls, db: Session, investigation_id: str) -> Optional[OrderInvestigation]:
        return db.query(OrderInvestigation).filter(OrderInvestigation.id == investigation_id).first()

    @classmethod
    def get_latest_investigation(cls, db: Session, order_id: str) -> Optional[OrderInvestigation]:
        order = db.query(Order).filter(
            (Order.id == order_id) | (Order.external_order_id == order_id)
        ).first()
        if not order:
            return None
        return (
            db.query(OrderInvestigation)
            .filter(OrderInvestigation.order_id == order.id)
            .order_by(OrderInvestigation.created_at.desc())
            .first()
        )

    @classmethod
    def get_predictions(cls, db: Session, order_id: str) -> Dict[str, Any]:
        order = db.query(Order).filter(
            (Order.id == order_id) | (Order.external_order_id == order_id)
        ).first()
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        ml_service = MLInferenceService.get_instance()
        res = ml_service.run_inference(order, order.events)
        return res.model_dump()

    @classmethod
    def list_recommendations(
        cls,
        db: Session,
        order_id: Optional[str] = None,
        pending_only: bool = False,
        limit: int = 50,
    ) -> List[RecoveryRecommendation]:
        query = db.query(RecoveryRecommendation)
        if order_id:
            order = db.query(Order).filter(
                (Order.id == order_id) | (Order.external_order_id == order_id)
            ).first()
            if order:
                query = query.filter(RecoveryRecommendation.order_id == order.id)
        if pending_only:
            query = query.filter(
                RecoveryRecommendation.approval_status == ApprovalStatus.PENDING_APPROVAL.value
            )
        return query.order_by(RecoveryRecommendation.created_at.desc()).limit(limit).all()

    @classmethod
    def approve_recommendation(
        cls,
        db: Session,
        recommendation_id: str,
        operator_identity: str,
        operator_role: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> RecoveryRecommendation:
        rec = db.query(RecoveryRecommendation).filter(RecoveryRecommendation.id == recommendation_id).first()
        if not rec:
            raise ValueError(f"Recommendation not found: {recommendation_id}")

        # Guardrail 1: Role-based authorization
        is_auth, auth_msg = PolicyEngine.check_operator_authorization(
            operator_identity=operator_identity, role=operator_role
        )
        if not is_auth:
            raise PermissionError(f"Authorization denied: {auth_msg}")

        # Guardrail 2: Expiration check
        is_expired, exp_msg = PolicyEngine.check_recommendation_expiry(rec.expires_at)
        if is_expired:
            rec.execution_status = "EXPIRED"
            db.commit()
            raise ValueError(f"Cannot approve expired recommendation: {exp_msg}")

        # Guardrail 3: State checks
        if rec.approval_status == ApprovalStatus.APPROVED.value:
            return rec  # Idempotent re-approval
        if rec.execution_status == "EXECUTED":
            raise ValueError("Cannot approve an already executed recommendation.")

        rec.approval_status = ApprovalStatus.APPROVED.value
        rec.execution_status = "PENDING"
        rec.approved_by = operator_identity
        rec.operator_role = operator_role or "OPS_LEAD"
        rec.approval_notes = notes or "Approved by operator."
        rec.approval_timestamp = datetime.now(timezone.utc)
        rec.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(rec)
        logger.info(f"Operator '{operator_identity}' approved recommendation {rec.id} ({rec.action_type})")
        return rec

    @classmethod
    def reject_recommendation(
        cls,
        db: Session,
        recommendation_id: str,
        operator_identity: str,
        rejection_reason: str,
        operator_role: Optional[str] = None,
    ) -> RecoveryRecommendation:
        rec = db.query(RecoveryRecommendation).filter(RecoveryRecommendation.id == recommendation_id).first()
        if not rec:
            raise ValueError(f"Recommendation not found: {recommendation_id}")

        is_auth, auth_msg = PolicyEngine.check_operator_authorization(
            operator_identity=operator_identity, role=operator_role
        )
        if not is_auth:
            raise PermissionError(f"Authorization denied: {auth_msg}")

        if rec.execution_status == "EXECUTED":
            raise ValueError("Cannot reject an already executed recommendation.")

        rec.approval_status = ApprovalStatus.REJECTED.value
        rec.approved_by = operator_identity
        rec.operator_role = operator_role or "OPS_LEAD"
        rec.approval_notes = f"Rejected: {rejection_reason}"
        rec.approval_timestamp = datetime.now(timezone.utc)
        rec.execution_status = "CANCELLED"
        rec.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(rec)
        logger.info(f"Operator '{operator_identity}' rejected recommendation {rec.id} ({rec.action_type})")
        return rec

    @classmethod
    def execute_recommendation(
        cls,
        db: Session,
        recommendation_id: str,
        operator_identity: str,
        operator_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        return RecoveryExecutionService.execute_recommendation(
            db=db,
            recommendation_id=recommendation_id,
            operator_identity=operator_identity,
            operator_role=operator_role,
        )

    @classmethod
    def get_audit_history(cls, db: Session, order_id: str) -> List[RecoveryExecutionAudit]:
        order = db.query(Order).filter(
            (Order.id == order_id) | (Order.external_order_id == order_id)
        ).first()
        if not order:
            return []
        return (
            db.query(RecoveryExecutionAudit)
            .filter(RecoveryExecutionAudit.order_id == order.id)
            .order_by(RecoveryExecutionAudit.executed_at.desc())
            .all()
        )

    @classmethod
    def get_prediction_audits(cls, db: Session, order_id: str) -> List[MLPredictionAudit]:
        order = db.query(Order).filter(
            (Order.id == order_id) | (Order.external_order_id == order_id)
        ).first()
        if not order:
            return []
        return (
            db.query(MLPredictionAudit)
            .filter(MLPredictionAudit.order_id == order.id)
            .order_by(MLPredictionAudit.prediction_timestamp.desc())
            .all()
        )
