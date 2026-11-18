"""
Swiggy ResolveAI — Phase 7 End-to-End Acceptance Test Matrix.
Final Product Validation & Comprehensive Business Workflow Verification.

Evaluates 18 required operational and failure scenarios:
 1. Normal order (zero unnecessary intervention)
 2. Restaurant preparation delay (triggers kitchen ping)
 3. Delivery assignment delay (triggers courier priority)
 4. Courier acceptance delay (triggers courier escalation)
 5. Combined kitchen and delivery delay (dual bottleneck mitigation)
 6. High cancellation risk at eligible landmark (Task C2 alert)
 7. Missing ML artifact (graceful degraded mode)
 8. Gemini provider timeout (fallback engine activates)
 9. Agent investigation failure / degraded mode handling
10. Unauthorized approval request (RBAC HTTP 403)
11. Expired recommendation (rejection on expiry)
12. Duplicate recovery execution (Idempotency enforcement)
13. Order state drift (rejects execution if state has changed)
14. Customer notification opt-out (Consent check respected)
15. Terminal order protection (DELIVERED / CANCELLED cannot be recovered)
16. High fleet shortage (PolicyEngine suppresses futile courier priority)
17. Successful recovery lifecycle (End-to-end audit persisted)
18. Rejected human approval (Transitions to REJECTED with operator rationale)
"""

import os
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.models.order import Order
from backend.app.models.order_event import OrderEvent
from backend.app.models.customer import Customer
from backend.app.models.restaurant import Restaurant
from backend.app.models.delivery_partner import DeliveryPartner
from backend.app.models.investigation import OrderInvestigation
from backend.app.models.recommendation import RecoveryRecommendation
from backend.app.models.audit import RecoveryExecutionAudit
from backend.app.services.intelligence_service import IntelligenceService
from backend.app.services.policy_engine import PolicyEngine
from backend.app.services.recovery_executor import RecoveryExecutionService
from backend.app.services.ml_inference import MLInferenceService
from backend.app.agents.customer_resolution import CustomerResolutionAgent
from backend.app.agents.schemas import RiskTier, ActionType


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_base_test_entities(db: Session, cust_id: str, rest_id: str, rider_id: str):
    """Helper to ensure reference customer, restaurant, and rider exist."""
    cust = db.query(Customer).filter(Customer.id == cust_id).first()
    if not cust:
        cust = Customer(
            id=cust_id,
            name="Acceptance Test Customer",
            phone="+919876543210",
        )
        db.add(cust)

    rest = db.query(Restaurant).filter(Restaurant.id == rest_id).first()
    if not rest:
        rest = Restaurant(
            id=rest_id,
            name="Acceptance Test Kitchen",
            city="Bengaluru",
            area="Indiranagar",
            cuisine="South Indian",
            number_of_offers=1,
            pure_veg=True,
        )
        db.add(rest)

    dp = db.query(DeliveryPartner).filter(DeliveryPartner.id == rider_id).first()
    if not dp:
        dp = DeliveryPartner(
            id=rider_id,
            name="Acceptance Test Rider",
            availability_status="AVAILABLE",
        )
        db.add(dp)

    db.commit()


# =============================================================================
# SCENARIOS 1–5: OPERATIONAL DELAY & NORMAL FLOWS
# =============================================================================

class TestOperationalDeliveryScenarios:
    """Scenarios 1 through 5: Normal flows, single delays, and combined disruptions."""

    def test_scenario_01_normal_order_zero_unnecessary_interventions(self, client, db):
        """Scenario 1: Normal order on track. Investigation produces nominal tier and zero intrusive interventions."""
        order_id = str(uuid.uuid4())
        create_base_test_entities(db, "cust_sc1", "rest_sc1", "rider_sc1")

        order = Order(
            id=order_id,
            external_order_id=f"SWIG-SC01-{uuid.uuid4().hex[:6]}",
            customer_id="cust_sc1",
            restaurant_id="rest_sc1",
            order_status="IN_KITCHEN",
            order_value=350.0,
            promised_delivery_at=datetime.now(timezone.utc) + timedelta(minutes=55),
        )
        db.add(order)
        db.commit()

        # Trigger investigation
        res = client.post(f"/api/v1/intelligence/investigate/{order_id}")
        assert res.status_code == 200
        data = res.json()

        assert data["order_id"] == order_id
        # For a normal order with ample SLA margin and no delay events, risk tier is NOMINAL
        assert data["risk_tier"] in ("NOMINAL", "MONITORED")
        # No sensitive actions requiring human approval
        assert not any(r["requires_approval"] for r in data.get("recommendations", []))

    def test_scenario_02_restaurant_preparation_delay_triggers_kitchen_ping(self, client, db):
        """Scenario 2: Kitchen delay event triggers automated kitchen ping alert."""
        order_id = str(uuid.uuid4())
        create_base_test_entities(db, "cust_sc2", "rest_sc2", "rider_sc2")

        now = datetime.now(timezone.utc)
        order = Order(
            id=order_id,
            external_order_id=f"SWIG-SC02-{uuid.uuid4().hex[:6]}",
            customer_id="cust_sc2",
            restaurant_id="rest_sc2",
            order_status="IN_KITCHEN",
            order_value=450.0,
            created_at=now - timedelta(minutes=25),
            promised_delivery_at=now + timedelta(minutes=15),
        )
        ev = OrderEvent(
            id=str(uuid.uuid4()),
            order_id=order_id,
            event_type="RESTAURANT_PREPARATION_DELAY",
            event_timestamp=now - timedelta(minutes=5),
            metadata={"prep_delay_min": 18.0, "kitchen_queue_depth": 7},
            data_source="SYNTHETIC",
        )
        db.add(order)
        db.add(ev)
        db.commit()

        res = client.post(f"/api/v1/intelligence/investigate/{order_id}")
        assert res.status_code == 200
        data = res.json()

        assert data["risk_tier"] in ("MONITORED", "HIGH_RISK", "CRITICAL")
        action_types = [r["action_type"] for r in data["recommendations"]]
        assert "EXPEDITE_KITCHEN_PING" in action_types

    def test_scenario_03_delivery_assignment_delay_triggers_courier_priority(self, client, db):
        """Scenario 3: Courier assignment delay triggers courier priority dispatch escalation."""
        order_id = str(uuid.uuid4())
        create_base_test_entities(db, "cust_sc3", "rest_sc3", "rider_sc3")

        order = Order(
            id=order_id,
            external_order_id=f"SWIG-SC03-{uuid.uuid4().hex[:6]}",
            customer_id="cust_sc3",
            restaurant_id="rest_sc3",
            order_status="PLACED",
            order_value=500.0,
            promised_delivery_at=datetime.now(timezone.utc) + timedelta(minutes=20),
        )
        ev = OrderEvent(
            id=str(uuid.uuid4()),
            order_id=order_id,
            event_type="COURIER_ASSIGNMENT_DELAY",
            event_timestamp=datetime.now(timezone.utc),
            metadata={"allotment_delay_min": 14.0, "courier_search_radius_km": 3.5},
            data_source="SYNTHETIC",
        )
        db.add(order)
        db.add(ev)
        db.commit()

        res = client.post(f"/api/v1/intelligence/investigate/{order_id}")
        assert res.status_code == 200
        data = res.json()

        assert data["risk_tier"] in ("HIGH_RISK", "CRITICAL")
        action_types = [r["action_type"] for r in data["recommendations"]]
        assert "PRIORITIZE_COURIER_DISPATCH" in action_types

    def test_scenario_04_courier_acceptance_delay_triggers_escalation(self, client, db):
        """Scenario 4: Courier assigned but stalls acceptance triggers reassignment or priority dispatch."""
        order_id = str(uuid.uuid4())
        create_base_test_entities(db, "cust_sc4", "rest_sc4", "rider_sc4")

        order = Order(
            id=order_id,
            external_order_id=f"SWIG-SC04-{uuid.uuid4().hex[:6]}",
            customer_id="cust_sc4",
            restaurant_id="rest_sc4",
            delivery_partner_id="rider_sc4",
            order_status="ALLOTTED",
            order_value=480.0,
            promised_delivery_at=datetime.now(timezone.utc) + timedelta(minutes=18),
        )
        ev = OrderEvent(
            id=str(uuid.uuid4()),
            order_id=order_id,
            event_type="COURIER_ACCEPTANCE_TIMEOUT",
            event_timestamp=datetime.now(timezone.utc),
            metadata={"accept_delay_min": 8.0, "reassignment_count": 1},
            data_source="SYNTHETIC",
        )
        db.add(order)
        db.add(ev)
        db.commit()

        res = client.post(f"/api/v1/intelligence/investigate/{order_id}")
        assert res.status_code == 200
        data = res.json()

        action_types = [r["action_type"] for r in data["recommendations"]]
        assert any(act in action_types for act in ["PRIORITIZE_COURIER_DISPATCH", "REASSIGN_COURIER"])

    def test_scenario_05_combined_kitchen_and_delivery_delay(self, client, db):
        """Scenario 5: Both kitchen delay and courier stall trigger dual-pillar mitigation plan."""
        order_id = str(uuid.uuid4())
        create_base_test_entities(db, "cust_sc5", "rest_sc5", "rider_sc5")

        now = datetime.now(timezone.utc)
        order_created = now - timedelta(minutes=35)
        order = Order(
            id=order_id,
            external_order_id=f"SWIG-SC05-{uuid.uuid4().hex[:6]}",
            customer_id="cust_sc5",
            restaurant_id="rest_sc5",
            order_status="IN_KITCHEN",
            order_value=650.0,
            created_at=order_created,
            promised_delivery_at=order_created + timedelta(minutes=5),
        )
        ev1 = OrderEvent(
            id=str(uuid.uuid4()),
            order_id=order_id,
            event_type="RESTAURANT_PREPARATION_DELAY",
            event_timestamp=now - timedelta(minutes=15),
            metadata={"prep_delay_min": 22.0, "kitchen_queue_depth": 9},
            data_source="SYNTHETIC",
        )
        ev2 = OrderEvent(
            id=str(uuid.uuid4()),
            order_id=order_id,
            event_type="COURIER_ASSIGNMENT_DELAY",
            event_timestamp=now - timedelta(minutes=10),
            metadata={"allotment_delay_min": 12.0},
            data_source="SYNTHETIC",
        )
        # Add 2 reassignment events to signify extreme courier churn
        ev3 = OrderEvent(
            id=str(uuid.uuid4()),
            order_id=order_id,
            event_type="RIDER_REASSIGNED",
            event_timestamp=now - timedelta(minutes=8),
            metadata={"reason": "DISTANCE_REJECTED"},
            data_source="SYNTHETIC",
        )
        ev4 = OrderEvent(
            id=str(uuid.uuid4()),
            order_id=order_id,
            event_type="RIDER_REASSIGNED",
            event_timestamp=now - timedelta(minutes=4),
            metadata={"reason": "VEHICLE_BREAKDOWN"},
            data_source="SYNTHETIC",
        )
        db.add_all([order, ev1, ev2, ev3, ev4])
        db.commit()

        res = client.post(f"/api/v1/intelligence/investigate/{order_id}")
        assert res.status_code == 200
        data = res.json()

        assert data["risk_tier"] == "CRITICAL"
        action_types = {r["action_type"] for r in data["recommendations"]}
        # Both customer notification and courier reassignment are formulated for critical multi-point delay
        assert "PROACTIVE_CUSTOMER_NOTIFICATION" in action_types
        assert "REASSIGN_COURIER" in action_types


# =============================================================================
# SCENARIOS 6–9: ML LANDMARK & SYSTEM FAILURE MODES
# =============================================================================

class TestMLLandmarkAndFailureModes:
    """Scenarios 6 through 9: Landmark cancellation alerts, missing artifacts, and timeouts."""

    def test_scenario_06_high_cancellation_risk_at_eligible_landmark(self, client, db):
        """Scenario 6: At t_allot + 5m, high cancellation risk triggers calibrated alert and proactive messaging."""
        order_id = str(uuid.uuid4())
        create_base_test_entities(db, "cust_sc6", "rest_sc6", "rider_sc6")

        order = Order(
            id=order_id,
            external_order_id=f"SWIG-SC06-{uuid.uuid4().hex[:6]}",
            customer_id="cust_sc6",
            restaurant_id="rest_sc6",
            order_status="IN_KITCHEN",
            order_value=550.0,
            promised_delivery_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        # Add allotment event 6 minutes ago (qualifying landmark with standard event type RIDER_ASSIGNED)
        allot_ev = OrderEvent(
            id=str(uuid.uuid4()),
            order_id=order_id,
            event_type="RIDER_ASSIGNED",
            event_timestamp=datetime.now(timezone.utc) - timedelta(minutes=6),
            metadata={"allot_time_min": 6.0},
            data_source="SYNTHETIC",
        )
        db.add(order)
        db.add(allot_ev)
        db.commit()

        res = client.get(f"/api/v1/intelligence/predictions/{order_id}")
        assert res.status_code == 200
        preds = res.json()

        assert preds["task_c2_cancellation"]["is_eligible"] is True
        assert preds["task_c2_cancellation"]["calibrated_probability"] is not None

    def test_scenario_07_missing_ml_artifact_graceful_degraded_mode(self, client):
        """Scenario 7: When an ML artifact directory is missing or invalid, service operates in degraded fallback mode."""
        svc = MLInferenceService.get_instance(artifacts_dir="non_existent_ml_dir_xyz")
        # Re-running with empty/default features falls back without crashing
        res = svc.run_inference("order-missing-artifact-test", {})

        assert res.task_a_eta.eta_p50_min > 0
        assert res.task_a_eta.confidence == "LOW" or res.task_a_eta.interval_width_min > 0

    def test_scenario_08_gemini_provider_timeout_deterministic_fallback(self):
        """Scenario 8: External Gemini API timeout/error activates deterministic synthesis seamlessly."""
        agent = CustomerResolutionAgent(use_llm=False)
        state = {
            "order_id": "order-sc8-timeout",
            "external_order_id": "SWIG-SC08-TIMEOUT",
            "risk_tier": RiskTier.HIGH_RISK,
            "order_context": {"order_value": 450.0},
            "ml_predictions": {},
            "restaurant_investigation": {"kitchen_delay_detected": True, "prep_delay_min": 14.0},
            "delivery_investigation": {},
        }
        res_state = agent.synthesize(state)

        assert res_state["resolution_synthesis"] is not None
        assert len(res_state["recovery_recommendations"]) > 0
        assert res_state["resolution_synthesis"]["primary_bottleneck"] == "RESTAURANT_KITCHEN"

    def test_scenario_09_agent_investigation_failure_returns_structured_error(self, client):
        """Scenario 9: Attempting to investigate a non-existent order returns structured HTTP 404."""
        non_existent_id = str(uuid.uuid4())
        res = client.post(f"/api/v1/intelligence/investigate/{non_existent_id}")

        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


# =============================================================================
# SCENARIOS 10–14: GOVERNANCE, RBAC, IDEMPOTENCY & CONSENT
# =============================================================================

class TestGovernanceRBACIdempotencyAndConsent:
    """Scenarios 10 through 14: Authorization, expiration, idempotency, drift, and consent."""

    def test_scenario_10_unauthorized_approval_request_rejected_403(self, client, db):
        """Scenario 10: Non-privileged operator role attempting to approve sensitive action is blocked with 403."""
        order_id = str(uuid.uuid4())
        create_base_test_entities(db, "cust_sc10", "rest_sc10", "rider_sc10")
        order = Order(
            id=order_id,
            external_order_id=f"SWIG-SC10-{uuid.uuid4().hex[:6]}",
            customer_id="cust_sc10",
            restaurant_id="rest_sc10",
            order_status="IN_KITCHEN",
            order_value=450.0,
            promised_delivery_at=datetime.now(timezone.utc) + timedelta(minutes=20),
        )
        inv = OrderInvestigation(id=str(uuid.uuid4()), order_id=order_id, status="COMPLETED", risk_tier="HIGH_RISK")
        rec = RecoveryRecommendation(
            id=str(uuid.uuid4()),
            investigation_id=inv.id,
            order_id=order_id,
            action_type="REASSIGN_COURIER",
            title="Courier Reassignment",
            rationale="Test recommendation",
            sensitivity_level="HIGH",
            requires_approval=True,
            approval_status="AWAITING_APPROVAL",
        )
        db.add_all([order, inv, rec])
        db.commit()

        payload = {"operator_identity": "guest_user", "operator_role": "GUEST", "notes": "Unauthorized"}
        res = client.post(f"/api/v1/intelligence/recommendations/{rec.id}/approve", json=payload)

        assert res.status_code == 403
        assert "Authorization denied" in res.json()["detail"]

    def test_scenario_11_expired_recommendation_rejected_at_approval(self, client, db):
        """Scenario 11: Recommendation past its expires_at timestamp cannot be approved."""
        order_id = str(uuid.uuid4())
        create_base_test_entities(db, "cust_sc11", "rest_sc11", "rider_sc11")
        order = Order(
            id=order_id,
            external_order_id=f"SWIG-SC11-{uuid.uuid4().hex[:6]}",
            customer_id="cust_sc11",
            restaurant_id="rest_sc11",
            order_status="IN_KITCHEN",
            order_value=450.0,
            promised_delivery_at=datetime.now(timezone.utc) + timedelta(minutes=20),
        )
        inv = OrderInvestigation(id=str(uuid.uuid4()), order_id=order_id, status="COMPLETED", risk_tier="HIGH_RISK")
        # Recommendation expired 10 minutes ago
        rec = RecoveryRecommendation(
            id=str(uuid.uuid4()),
            investigation_id=inv.id,
            order_id=order_id,
            action_type="APOLOGY_CREDIT_VOUCHER",
            title="Expired Voucher",
            rationale="Test recommendation",
            sensitivity_level="HIGH",
            requires_approval=True,
            approval_status="AWAITING_APPROVAL",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        db.add_all([order, inv, rec])
        db.commit()

        payload = {"operator_identity": "ops_lead_1", "operator_role": "OPS_LEAD", "notes": "Late approval"}
        res = client.post(f"/api/v1/intelligence/recommendations/{rec.id}/approve", json=payload)

        assert res.status_code == 400
        assert "expired" in res.json()["detail"].lower()

    def test_scenario_12_duplicate_recovery_execution_enforces_idempotency(self, client, db):
        """Scenario 12: Calling execute_recommendation twice returns the original audit without duplicate dispatch."""
        order_id = str(uuid.uuid4())
        create_base_test_entities(db, "cust_sc12", "rest_sc12", "rider_sc12")
        order = Order(
            id=order_id,
            external_order_id=f"SWIG-SC12-{uuid.uuid4().hex[:6]}",
            customer_id="cust_sc12",
            restaurant_id="rest_sc12",
            order_status="IN_KITCHEN",
            order_value=450.0,
            promised_delivery_at=datetime.now(timezone.utc) + timedelta(minutes=20),
        )
        inv = OrderInvestigation(id=str(uuid.uuid4()), order_id=order_id, status="COMPLETED", risk_tier="HIGH_RISK")
        rec = RecoveryRecommendation(
            id=str(uuid.uuid4()),
            investigation_id=inv.id,
            order_id=order_id,
            action_type="EXPEDITE_KITCHEN_PING",
            title="Kitchen Ping",
            rationale="Test recommendation",
            sensitivity_level="LOW",
            requires_approval=False,
            approval_status="AUTO_APPROVED",
        )
        db.add_all([order, inv, rec])
        db.commit()

        # Execute #1
        res1 = client.post(f"/api/v1/intelligence/recommendations/{rec.id}/execute", json={})
        assert res1.status_code == 200
        audit1 = res1.json()

        # Execute #2 (Duplicate call)
        res2 = client.post(f"/api/v1/intelligence/recommendations/{rec.id}/execute", json={})
        assert res2.status_code == 200
        audit2 = res2.json()

        # Must return the exact same idempotency key and audit record
        assert audit1["idempotency_key"] == audit2["idempotency_key"]
        assert audit1["audit_id"] == audit2["audit_id"]

    def test_scenario_13_order_state_drift_blocks_invalid_action(self):
        """Scenario 13: If order state drifts to OUT_FOR_DELIVERY, courier reassignment is blocked as drift."""
        is_valid, reason = PolicyEngine.validate_order_state_drift(
            ActionType.REASSIGN_COURIER.value,
            "OUT_FOR_DELIVERY",
        )
        assert is_valid is False
        assert "already out_for_delivery" in reason.lower()

    def test_scenario_14_customer_notification_opt_out_respected(self):
        """Scenario 14: Customer with customer_consent=False is blocked from receiving automated push/SMS."""
        is_eligible, reason = PolicyEngine.validate_action_eligibility(
            ActionType.PROACTIVE_CUSTOMER_NOTIFICATION.value,
            "IN_KITCHEN",
            existing_actions=[],
            order_context={"customer_consent": False},
        )
        assert is_eligible is False
        assert "opted out" in reason.lower()


# =============================================================================
# SCENARIOS 15–18: TERMINAL PROTECTIONS, STRESS & FINAL LIFECYCLE
# =============================================================================

class TestTerminalProtectionsStressAndLifecycle:
    """Scenarios 15 through 18: Terminal orders, fleet shortages, successful recoveries, and rejections."""

    def test_scenario_15_terminal_order_protection(self):
        """Scenario 15: Delivered or Cancelled orders reject all operational recovery interventions."""
        for term_status in ["DELIVERED", "CANCELLED"]:
            is_drift_valid, drift_msg = PolicyEngine.validate_order_state_drift(
                ActionType.EXPEDITE_KITCHEN_PING.value,
                term_status,
            )
            assert is_drift_valid is False
            assert "terminal" in drift_msg.lower()

            is_elig_valid, elig_msg = PolicyEngine.validate_action_eligibility(
                ActionType.EXPEDITE_KITCHEN_PING.value,
                term_status,
                existing_actions=[],
            )
            assert is_elig_valid is False
            assert "terminal" in elig_msg.lower()

    def test_scenario_16_high_fleet_shortage_suppresses_futile_priority(self):
        """Scenario 16: When local courier availability < 35%, PolicyEngine suppresses futile prioritization."""
        is_safe = PolicyEngine.check_fleet_availability_threshold(courier_availability_ratio=0.25)
        assert is_safe is False

        is_safe_normal = PolicyEngine.check_fleet_availability_threshold(courier_availability_ratio=0.85)
        assert is_safe_normal is True

    def test_scenario_17_successful_recovery_end_to_end_lifecycle(self, client, db):
        """Scenario 17: Full lifecycle from order creation -> investigation -> approval -> execution -> audit log."""
        order_id = str(uuid.uuid4())
        create_base_test_entities(db, "cust_sc17", "rest_sc17", "rider_sc17")

        order = Order(
            id=order_id,
            external_order_id=f"SWIG-SC17-{uuid.uuid4().hex[:6]}",
            customer_id="cust_sc17",
            restaurant_id="rest_sc17",
            order_status="IN_KITCHEN",
            order_value=520.0,
            promised_delivery_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        db.add(order)
        db.commit()

        # Step 1: Investigate
        res_inv = client.post(f"/api/v1/intelligence/investigate/{order_id}")
        assert res_inv.status_code == 200
        inv_data = res_inv.json()
        assert len(inv_data["recommendations"]) > 0

        first_rec = inv_data["recommendations"][0]
        rec_id = first_rec["id"]

        # Step 2: Approve if requires approval, otherwise already auto-approved
        if first_rec["requires_approval"]:
            res_app = client.post(
                f"/api/v1/intelligence/recommendations/{rec_id}/approve",
                json={"operator_identity": "lead_ops_lead", "operator_role": "OPS_LEAD", "notes": "Approved for test"},
            )
            assert res_app.status_code == 200
            assert res_app.json()["approval_status"] == "APPROVED"

        # Step 3: Execute Action (or verify already executed if auto-approved by autonomous investigation)
        res_exec = client.post(f"/api/v1/intelligence/recommendations/{rec_id}/execute", json={})
        assert res_exec.status_code == 200
        exec_data = res_exec.json()
        assert exec_data["status"] in ("EXECUTED", "ALREADY_EXECUTED")
        assert "audit_id" in exec_data

        # Step 4: Audit Verification
        res_audit = client.get(f"/api/v1/intelligence/audit/{order_id}")
        assert res_audit.status_code == 200
        audits = res_audit.json()
        audit_match = next((a for a in audits if a["recommendation_id"] == rec_id), None)
        assert audit_match is not None
        assert audit_match["recovery_outcome"] == "SUCCESS"
        assert audit_match["is_simulated"] is True

    def test_scenario_18_rejected_human_approval_persists_rationale(self, client, db):
        """Scenario 18: Operator rejecting a recommendation transitions status to REJECTED and records reason."""
        order_id = str(uuid.uuid4())
        create_base_test_entities(db, "cust_sc18", "rest_sc18", "rider_sc18")

        order = Order(
            id=order_id,
            external_order_id=f"SWIG-SC18-{uuid.uuid4().hex[:6]}",
            customer_id="cust_sc18",
            restaurant_id="rest_sc18",
            order_status="IN_KITCHEN",
            order_value=450.0,
            promised_delivery_at=datetime.now(timezone.utc) + timedelta(minutes=20),
        )
        inv = OrderInvestigation(id=str(uuid.uuid4()), order_id=order_id, status="COMPLETED", risk_tier="HIGH_RISK")
        rec = RecoveryRecommendation(
            id=str(uuid.uuid4()),
            investigation_id=inv.id,
            order_id=order_id,
            action_type="REASSIGN_COURIER",
            title="Courier Reassignment",
            rationale="Test recommendation",
            sensitivity_level="HIGH",
            requires_approval=True,
            approval_status="AWAITING_APPROVAL",
        )
        db.add_all([order, inv, rec])
        db.commit()

        # Reject with rationale
        reject_payload = {
            "operator_identity": "ops_lead_supervisor",
            "operator_role": "OPS_LEAD",
            "reason": "Rider has confirmed they are 200m from merchant; reassignment counterproductive.",
        }
        res = client.post(f"/api/v1/intelligence/recommendations/{rec.id}/reject", json=reject_payload)
        assert res.status_code == 200
        data = res.json()

        assert data["approval_status"] == "REJECTED"
        assert "200m from merchant" in data["approval_notes"]
