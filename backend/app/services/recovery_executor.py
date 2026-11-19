from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.core.logging import logger
from backend.app.models.order import Order
from backend.app.models.order_event import OrderEvent
from backend.app.models.recommendation import RecoveryRecommendation
from backend.app.models.audit import RecoveryExecutionAudit
from backend.app.models.delivery_partner import DeliveryPartner
from backend.app.agents.schemas import ActionType, ApprovalStatus
from backend.app.services.policy_engine import PolicyEngine


class RecoveryExecutionService:
    """
    Hardened Simulated Autonomous Recovery Execution Service.
    - Strictly simulated: NO real money, SMS, calls, or external partner mutations.
    - Idempotent and transactionally logged via RecoveryExecutionAudit.
    - Protected against race conditions, replay attacks, stale approvals, and state drift.
    """

    @classmethod
    def execute_recommendation(
        cls,
        db: Session,
        recommendation_id: str,
        operator_identity: Optional[str] = "SYSTEM_AUTONOMOUS",
        operator_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes an approved or auto-approved recommendation with full reliability guardrails.
        """
        now = datetime.now(timezone.utc)

        # Guardrail 0: Execution Mode & Environment Enforcement (SIMULATION, SHADOW, LIVE)
        from backend.app.core.config import settings
        exec_mode = getattr(settings, "EXECUTION_MODE", "SIMULATION").upper().strip()
        env = getattr(settings, "ENVIRONMENT", "development").lower().strip()

        if env == "production":
            raise PermissionError(
                "Recovery execution is strictly prohibited in production environment. "
                "No live operational recovery or automated side effects are permitted."
            )

        if exec_mode == "SHADOW":
            raise PermissionError(
                "Recovery execution rejected: system is running in read-only SHADOW mode. "
                "Simulated actions, physical mutations, and partner dispatches are disabled."
            )
        elif exec_mode == "LIVE":
            raise RuntimeError(
                "Recovery execution rejected: LIVE execution mode is disabled by safety governance policy."
            )
        elif exec_mode != "SIMULATION":
            raise ValueError(f"Unknown or unsupported execution mode: '{exec_mode}'")

        rec = db.query(RecoveryRecommendation).filter(RecoveryRecommendation.id == recommendation_id).first()
        if not rec:
            raise ValueError(f"Recommendation not found: {recommendation_id}")

        order = db.query(Order).filter(Order.id == rec.order_id).first()
        if not order:
            raise ValueError(f"Order not found: {rec.order_id}")

        # Guardrail 1: Rejected recommendations can NEVER execute
        if rec.approval_status == ApprovalStatus.REJECTED.value:
            raise ValueError(f"Cannot execute rejected recommendation {recommendation_id} (Reason: {rec.approval_notes})")

        # Guardrail 2: Human-in-the-loop approval requirement
        if rec.requires_approval and rec.approval_status != ApprovalStatus.APPROVED.value:
            raise ValueError(
                f"Action {rec.action_type} requires operator approval before execution (Current: {rec.approval_status})"
            )

        # Guardrail 3: Operator role-based authorization check
        is_auth, auth_msg = PolicyEngine.check_operator_authorization(
            operator_identity=operator_identity or "SYSTEM_AUTONOMOUS", role=operator_role
        )
        if not is_auth:
            raise PermissionError(f"Authorization denied: {auth_msg}")

        # Guardrail 4: Expiration check (30-minute validity window)
        is_expired, exp_msg = PolicyEngine.check_recommendation_expiry(rec.expires_at, now=now)
        if is_expired:
            rec.execution_status = "EXPIRED"
            db.commit()
            raise ValueError(f"Recommendation execution rejected: {exp_msg}")

        # Guardrail 5: Order state drift check
        is_state_valid, drift_msg = PolicyEngine.validate_order_state_drift(
            action_type=rec.action_type, current_status=order.order_status
        )
        if not is_state_valid:
            rec.execution_status = "CANCELLED"
            db.commit()
            raise ValueError(f"Order state drift detected: {drift_msg}")

        # Guardrail 6: Already executed check (in-memory / status)
        if rec.execution_status == "EXECUTED":
            existing_audit = (
                db.query(RecoveryExecutionAudit)
                .filter(RecoveryExecutionAudit.recommendation_id == recommendation_id)
                .first()
            )
            return {
                "status": "ALREADY_EXECUTED",
                "message": "Recommendation was already executed (idempotent replay).",
                "audit_id": existing_audit.id if existing_audit else None,
                "idempotency_key": existing_audit.idempotency_key if existing_audit else None,
                "execution_result": existing_audit.execution_result if existing_audit else {},
            }

        # Guardrail 7: Idempotency Key check in database
        idempotency_key = PolicyEngine.generate_idempotency_key(
            order_id=order.id, action_type=rec.action_type, disambiguator=rec.id
        )
        existing_key_audit = (
            db.query(RecoveryExecutionAudit)
            .filter(RecoveryExecutionAudit.idempotency_key == idempotency_key)
            .first()
        )
        if existing_key_audit:
            rec.execution_status = "EXECUTED"
            db.commit()
            return {
                "status": "IDEMPOTENT_SKIPPED",
                "message": "Action with identical idempotency key was previously executed.",
                "audit_id": existing_key_audit.id,
                "idempotency_key": existing_key_audit.idempotency_key,
                "execution_result": existing_key_audit.execution_result,
            }

        initial_status = order.order_status
        payload = rec.execution_payload or {}
        action_result: Dict[str, Any] = {}
        outcome = "SUCCESS"

        try:
            # -----------------------------------------------------------------
            # Simulated Action Execution Branches
            # -----------------------------------------------------------------
            if rec.action_type == ActionType.MONITOR_ORDER.value:
                action_result = {
                    "action": "MONITOR_ORDER",
                    "telemetry_interval_sec": payload.get("poll_interval_sec", 30),
                    "message": "Autonomous telemetry monitoring registered for order lifecycle.",
                }

            elif rec.action_type == ActionType.EXPEDITE_KITCHEN_PING.value:
                event = OrderEvent(
                    order_id=order.id,
                    event_type="KITCHEN_EXPEDITE_PING",
                    event_timestamp=now,
                    event_metadata={
                        "prep_delay_min": payload.get("prep_delay_min", 5.0),
                        "channel": "SIMULATED_MERCHANT_POS_API",
                        "note": "Prompted merchant KDS terminal to expedite packaging.",
                    },
                    data_source="SYNTHETIC",
                )
                db.add(event)
                action_result = {
                    "action": "EXPEDITE_KITCHEN_PING",
                    "ping_delivered": True,
                    "merchant_device_ack": "ACK_200",
                    "reassurance_delay_min_recovered": 3.5,
                }

            elif rec.action_type == ActionType.PRIORITIZE_COURIER_DISPATCH.value:
                event = OrderEvent(
                    order_id=order.id,
                    event_type="COURIER_DISPATCH_PRIORITIZED",
                    event_timestamp=now,
                    event_metadata={
                        "priority_boost": True,
                        "target_pool": "NEARBY_AVAILABLE_COURIERS",
                        "allotment_boost_score": 1.5,
                    },
                    data_source="SYNTHETIC",
                )
                db.add(event)
                action_result = {
                    "action": "PRIORITIZE_COURIER_DISPATCH",
                    "queue_rank_promoted": 1,
                    "dispatch_reallotment_target_sec": 45,
                }

            elif rec.action_type == ActionType.REASSIGN_COURIER.value:
                alt_courier = (
                    db.query(DeliveryPartner)
                    .filter(DeliveryPartner.id != order.delivery_partner_id)
                    .first()
                )
                old_courier_id = order.delivery_partner_id
                new_courier_id = alt_courier.id if alt_courier else f"dp_sim_{now.strftime('%H%M%S')}"
                new_courier_name = alt_courier.name if alt_courier else "Kiran Kumar (Express)"

                order.delivery_partner_id = new_courier_id
                event = OrderEvent(
                    order_id=order.id,
                    event_type="RIDER_REASSIGNED",
                    event_timestamp=now,
                    event_metadata={
                        "previous_rider_id": old_courier_id,
                        "new_rider_id": new_courier_id,
                        "new_rider_name": new_courier_name,
                        "reassignment_reason": "AUTONOMOUS_OPERATIONAL_RECOVERY",
                        "expected_pickup_saving_min": 10.0,
                    },
                    data_source="SYNTHETIC",
                )
                db.add(event)
                action_result = {
                    "action": "REASSIGN_COURIER",
                    "previous_courier_id": old_courier_id,
                    "reassigned_courier_id": new_courier_id,
                    "reassigned_courier_name": new_courier_name,
                    "estimated_transit_gain_min": 9.5,
                }

            elif rec.action_type == ActionType.PROACTIVE_CUSTOMER_NOTIFICATION.value:
                event = OrderEvent(
                    order_id=order.id,
                    event_type="CUSTOMER_PROACTIVELY_NOTIFIED",
                    event_timestamp=now,
                    event_metadata={
                        "channel": "SIMULATED_PUSH_NOTIFICATION",
                        "headline": "We're closely tracking your order",
                        "content": "Your meal is being prepared with extra care. Our driver is on standby.",
                        "revised_eta_p50": payload.get("revised_eta_p50"),
                    },
                    data_source="SYNTHETIC",
                )
                db.add(event)
                action_result = {
                    "action": "PROACTIVE_CUSTOMER_NOTIFICATION",
                    "channel": "SIMULATED_IN_APP_PUSH",
                    "delivery_success": True,
                    "wismo_deflection_probability": 0.88,
                }

            elif rec.action_type == ActionType.APOLOGY_CREDIT_VOUCHER.value:
                credit_amount = payload.get("credit_amount_inr", 50.0)
                event = OrderEvent(
                    order_id=order.id,
                    event_type="APOLOGY_VOUCHER_ISSUED",
                    event_timestamp=now,
                    event_metadata={
                        "credit_amount_inr": credit_amount,
                        "wallet_type": "SIMULATED_SWIGGY_MONEY",
                        "voucher_code": f"RECOVERY-{order.external_order_id[-6:]}",
                        "reason": "PROACTIVE_HIGH_RISK_APPEASEMENT",
                    },
                    data_source="SYNTHETIC",
                )
                db.add(event)
                action_result = {
                    "action": "APOLOGY_CREDIT_VOUCHER",
                    "amount_inr": credit_amount,
                    "wallet_credited": True,
                    "churn_mitigation_score": 0.94,
                }

            else:
                action_result = {"action": rec.action_type, "note": "Generic simulated recovery action."}

            final_status = order.order_status
            rec.execution_status = "EXECUTED"
            rec.updated_at = now

            audit = RecoveryExecutionAudit(
                recommendation_id=rec.id,
                order_id=order.id,
                action_type=rec.action_type,
                initial_order_status=initial_status,
                final_order_status=final_status,
                idempotency_key=idempotency_key,
                trigger_reason=rec.rationale[:250],
                ml_model_version="2.5.0",
                approval_identity=operator_identity,
                approval_timestamp=rec.approval_timestamp or now,
                execution_result=action_result,
                recovery_outcome=outcome,
                is_simulated=True,
                executed_at=now,
            )
            db.add(audit)
            db.commit()

            logger.info(
                f"Successfully executed simulated action {rec.action_type} for order {order.external_order_id} (Audit: {audit.id})"
            )

            return {
                "status": "EXECUTED",
                "audit_id": audit.id,
                "action_type": rec.action_type,
                "idempotency_key": idempotency_key,
                "execution_result": action_result,
                "executed_at": now.isoformat(),
            }

        except IntegrityError as iexc:
            # Concurrent race condition caught by database unique constraint on idempotency_key
            db.rollback()
            logger.warning(
                f"Concurrency conflict on idempotency key '{idempotency_key}': {iexc}. Returning existing execution audit."
            )
            existing_audit = (
                db.query(RecoveryExecutionAudit)
                .filter(RecoveryExecutionAudit.idempotency_key == idempotency_key)
                .first()
            )
            return {
                "status": "ALREADY_EXECUTED",
                "message": "Concurrent execution conflict resolved via database unique constraint (idempotent response).",
                "audit_id": existing_audit.id if existing_audit else None,
                "execution_result": existing_audit.execution_result if existing_audit else {},
            }
        except Exception as exc:
            db.rollback()
            rec.execution_status = "FAILED"
            rec.updated_at = now
            try:
                db.commit()
            except Exception:
                pass
            logger.error(f"Execution failed for recommendation {recommendation_id}: {exc}")
            raise
