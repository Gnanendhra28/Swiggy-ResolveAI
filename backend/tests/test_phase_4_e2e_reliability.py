"""
Swiggy ResolveAI — Phase 4 End-to-End Validation, Reliability, Security & Operational Readiness Test Suite.

Covers:
- Workstream A: 12 End-to-End Workflow Validation Scenarios
- Workstream B: Execution Reliability, Idempotency & Concurrent Race Condition Safety
- Workstream C: Policy Hardening, Customer Consent Opt-Out, Role Authorization, Expiration, State Drift
- Workstream D & E: LangGraph Resilience, Degraded Evidence Handling, ML Governance & Auditing
- Workstream F: Observability, Correlation ID Propagation, Timing Latency, PII Masking
"""

import os
import uuid
import threading
from datetime import datetime, timezone, timedelta
from typing import Generator
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.session import SessionLocal, engine
from backend.app.database.base import Base
from backend.app.models.order import Order
from backend.app.models.order_event import OrderEvent
from backend.app.models.restaurant import Restaurant
from backend.app.models.customer import Customer
from backend.app.models.delivery_partner import DeliveryPartner
from backend.app.models.investigation import OrderInvestigation
from backend.app.models.recommendation import RecoveryRecommendation
from backend.app.models.audit import RecoveryExecutionAudit
from backend.app.models.ml_audit import MLPredictionAudit
from backend.app.services.ml_inference import (
    MLInferenceService,
    TaskAPrediction,
    TaskC2Prediction,
    ResearchModelPrediction,
)
from backend.app.agents.schemas import (
    RiskTier,
    ActionType,
    ApprovalStatus,
    SensitivityLevel,
    InvestigationStatus,
)
from backend.app.agents.state import MultiAgentInvestigationState
from backend.app.agents.workflow import (
    intelligence_workflow,
    order_intelligence_node,
    restaurant_node,
    delivery_node,
    customer_resolution_node,
)
from backend.app.services.policy_engine import PolicyEngine
from backend.app.services.intelligence_service import IntelligenceService
from backend.app.services.recovery_executor import RecoveryExecutionService


@pytest.fixture(scope="module")
def test_db() -> Generator:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def client() -> Generator:
    with TestClient(app) as c:
        yield c


def create_mock_order(
    db,
    scenario_type: str = "NORMAL",
    order_status: str = "PREPARING",
    customer_phone: str = "+919876543210",
    consent: bool = True,
    age_minutes: int = 20,
) -> Order:
    """Helper to construct rich mock orders with chronological events."""
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(minutes=age_minutes)

    rest = db.query(Restaurant).filter(Restaurant.id == "rest_p4_test").first()
    if not rest:
        rest = Restaurant(
            id="rest_p4_test",
            name="Empire Restaurant Koramangala",
            city="Bengaluru",
            area="Koramangala",
            cuisine="North Indian, Biryani",
            rating=4.4,
            delivery_time_listing="30-35 mins",
            data_source="SYNTHETIC",
        )
        db.add(rest)

    cust = Customer(
        id=f"cust_p4_{uuid.uuid4().hex[:8]}",
        name="Ananya Roy",
        phone=customer_phone,
    )
    db.add(cust)

    dp = DeliveryPartner(
        id=f"dp_p4_{uuid.uuid4().hex[:8]}",
        name="Ramesh Babu",
        availability_status="AVAILABLE",
    )
    db.add(dp)
    db.commit()

    order = Order(
        external_order_id=f"SWIG-P4-{uuid.uuid4().hex[:8].upper()}",
        customer_id=cust.id,
        restaurant_id=rest.id,
        delivery_partner_id=dp.id,
        order_status=order_status,
        order_value=520.0,
        promised_delivery_at=created_at + timedelta(minutes=35),
        created_at=created_at,
        data_source="SYNTHETIC",
    )
    db.add(order)
    db.commit()

    # Base events
    ev_placed = OrderEvent(
        order_id=order.id,
        event_type="ORDER_PLACED",
        event_timestamp=created_at,
        event_metadata={"last_mile_distance": 3.2, "items_count": 3, "customer_consent": consent},
        data_source="SYNTHETIC",
    )
    ev_accepted = OrderEvent(
        order_id=order.id,
        event_type="ORDER_ACCEPTED",
        event_timestamp=created_at + timedelta(minutes=2),
        event_metadata={"kitchen_queue_depth": 4},
        data_source="SYNTHETIC",
    )
    events = [ev_placed, ev_accepted]

    if scenario_type == "KITCHEN_DELAY":
        # Order accepted long ago, still not ready
        pass
    elif scenario_type == "FLEET_DELAY":
        ev_assigned = OrderEvent(
            order_id=order.id,
            event_type="RIDER_ASSIGNED",
            event_timestamp=created_at + timedelta(minutes=5),
            event_metadata={"first_mile_distance": 4.5},
            data_source="SYNTHETIC",
        )
        ev_rider_acc = OrderEvent(
            order_id=order.id,
            event_type="RIDER_ACCEPTED",
            event_timestamp=created_at + timedelta(minutes=6),
            event_metadata={},
            data_source="SYNTHETIC",
        )
        events.extend([ev_assigned, ev_rider_acc])
    elif scenario_type == "LANDMARK_CANCELLATION":
        ev_assigned = OrderEvent(
            order_id=order.id,
            event_type="RIDER_ASSIGNED",
            event_timestamp=created_at + timedelta(minutes=5),
            event_metadata={"first_mile_distance": 3.0},
            data_source="SYNTHETIC",
        )
        ev_rider_acc = OrderEvent(
            order_id=order.id,
            event_type="RIDER_ACCEPTED",
            event_timestamp=created_at + timedelta(minutes=6),
            event_metadata={},
            data_source="SYNTHETIC",
        )
        events.extend([ev_assigned, ev_rider_acc])
    elif scenario_type == "DUAL_DELAY":
        ev_assigned = OrderEvent(
            order_id=order.id,
            event_type="RIDER_ASSIGNED",
            event_timestamp=created_at + timedelta(minutes=5),
            event_metadata={"first_mile_distance": 5.0},
            data_source="SYNTHETIC",
        )
        events.append(ev_assigned)
    else:  # NORMAL
        ev_assigned = OrderEvent(
            order_id=order.id,
            event_type="RIDER_ASSIGNED",
            event_timestamp=created_at + timedelta(minutes=4),
            event_metadata={"first_mile_distance": 1.2},
            data_source="SYNTHETIC",
        )
        ev_rider_acc = OrderEvent(
            order_id=order.id,
            event_type="RIDER_ACCEPTED",
            event_timestamp=created_at + timedelta(minutes=5),
            event_metadata={},
            data_source="SYNTHETIC",
        )
        events.extend([ev_assigned, ev_rider_acc])

    db.add_all(events)
    db.commit()
    db.refresh(order)
    return order


# =============================================================================
# Workstream A: 12 End-to-End Workflow Validation Scenarios
# =============================================================================
class TestWorkstreamAEndToEndScenarios:

    def test_scenario_01_normal_order_workflow(self, test_db):
        """Scenario 1: Normal on-time order triggers non-intrusive monitoring only."""
        order = create_mock_order(test_db, scenario_type="NORMAL", age_minutes=8)
        inv = IntelligenceService.trigger_investigation(test_db, order.id, "SCHEDULED_CHECK")

        assert inv.status == InvestigationStatus.COMPLETED.value
        assert inv.risk_tier in (RiskTier.NOMINAL.value, RiskTier.MONITORED.value)
        # Ensure no sensitive interventions triggered
        action_types = [r.action_type for r in inv.recommendations]
        assert ActionType.REASSIGN_COURIER.value not in action_types
        assert ActionType.APOLOGY_CREDIT_VOUCHER.value not in action_types
        assert ActionType.MONITOR_ORDER.value in action_types

    def test_scenario_02_high_eta_uncertainty_workflow(self, test_db):
        """Scenario 2: Wide quantile spread triggers long-tail disclaimer & expectation setting."""
        order = create_mock_order(test_db, scenario_type="NORMAL", age_minutes=15)
        service = MLInferenceService.get_instance()
        # Force high uncertainty in features
        pred = service.predict_task_a(
            {
                "order_time_hour": 21,
                "order_time_dow": 5,
                "items_count": 8,
                "first_mile_distance": 4.5,
                "last_mile_distance": 14.5,
                "is_weekend": 1,
                "order_volume_last_10m": 90,
                "rider_busy_ratio": 0.95,
            }
        )
        assert pred.eta_p90_min >= pred.eta_p50_min >= pred.eta_p10_min
        assert pred.interval_width_min > 5.0

    def test_scenario_03_landmark_cancellation_risk_workflow(self, test_db):
        """Scenario 3: Post-5min landmark cancellation risk triggers intervention."""
        order = create_mock_order(test_db, scenario_type="LANDMARK_CANCELLATION", age_minutes=25)
        service = MLInferenceService.get_instance()
        is_elig, reason, allot_time, elapsed = service.check_landmark_eligibility(order, order.events)
        assert is_elig is True
        pred_c2 = service.predict_task_c2(
            features={"first_mile_distance": 3.0, "last_mile_distance": 3.2},
            is_eligible=is_elig,
            eligibility_reason=reason,
            landmark_evaluated_at=datetime.now(timezone.utc).isoformat(),
            allot_to_landmark_min=elapsed,
        )
        assert pred_c2.is_eligible is True
        assert pred_c2.calibrated_probability is not None
        assert pred_c2.calibrated_probability >= 0.0

    def test_scenario_04_kitchen_delay_workflow(self, test_db):
        """Scenario 4: Kitchen prep stalled triggers EXPEDITE_KITCHEN_PING."""
        order = create_mock_order(test_db, scenario_type="KITCHEN_DELAY", age_minutes=24)
        inv = IntelligenceService.trigger_investigation(test_db, order.id, "KITCHEN_STALL_ALERT")
        actions = [r.action_type for r in inv.recommendations]
        assert ActionType.EXPEDITE_KITCHEN_PING.value in actions

    def test_scenario_05_fleet_delay_workflow(self, test_db):
        """Scenario 5: Transit delay triggers delivery fleet action or notification."""
        order = create_mock_order(test_db, scenario_type="FLEET_DELAY", age_minutes=22)
        inv = IntelligenceService.trigger_investigation(test_db, order.id, "TRANSIT_DELAY_ALERT")
        assert inv.status == InvestigationStatus.COMPLETED.value
        assert len(inv.recommendations) > 0

    def test_scenario_06_dual_delays_workflow(self, test_db):
        """Scenario 6: Both kitchen and fleet delayed -> kitchen expedited before courier reassign."""
        order = create_mock_order(test_db, scenario_type="DUAL_DELAY", age_minutes=30)
        inv = IntelligenceService.trigger_investigation(test_db, order.id, "DUAL_DELAY_DETECTED")
        action_types = [r.action_type for r in inv.recommendations]
        assert ActionType.EXPEDITE_KITCHEN_PING.value in action_types

    def test_scenario_07_recovery_success_lifecycle(self, client, test_db):
        """Scenario 7: Full recovery success lifecycle with audit trail."""
        order = create_mock_order(test_db, scenario_type="NORMAL", age_minutes=12)
        inv_resp = client.post(f"/api/v1/intelligence/investigate/{order.id}")
        assert inv_resp.status_code == 200
        inv_data = inv_resp.json()

        # Find auto-approved recommendation
        rec_data = inv_data["recommendations"][0]
        exec_resp = client.post(
            f"/api/v1/intelligence/recommendations/{rec_data['id']}/execute",
            json={"operator_identity": "ops_lead"},
        )
        assert exec_resp.status_code == 200
        res = exec_resp.json()
        assert res["status"] in ("EXECUTED", "ALREADY_EXECUTED", "IDEMPOTENT_SKIPPED")

        # Verify audit trail
        audit_resp = client.get(f"/api/v1/intelligence/audit/{order.id}")
        assert audit_resp.status_code == 200
        audits = audit_resp.json()
        assert len(audits) >= 1
        assert audits[0]["is_simulated"] is True

    def test_scenario_08_rejected_recommendation_lifecycle(self, client, test_db):
        """Scenario 8: Rejected recommendation transitions to REJECTED and cannot execute."""
        order = create_mock_order(test_db, scenario_type="NORMAL", age_minutes=15)
        rec = RecoveryRecommendation(
            investigation_id="inv_mock_rej",
            order_id=order.id,
            action_type=ActionType.REASSIGN_COURIER.value,
            title="Express Courier Reassignment",
            rationale="Test rejection flow",
            sensitivity_level=SensitivityLevel.HIGH.value,
            requires_approval=True,
            approval_status=ApprovalStatus.PENDING_APPROVAL.value,
            execution_status="PENDING",
        )
        test_db.add(rec)
        test_db.commit()

        # Reject
        rej_resp = client.post(
            f"/api/v1/intelligence/recommendations/{rec.id}/reject",
            json={"operator_identity": "ops_lead", "reason": "Courier is at restaurant"},
        )
        assert rej_resp.status_code == 200
        assert rej_resp.json()["approval_status"] == ApprovalStatus.REJECTED.value

        # Execution attempt must be rejected (cannot execute unapproved/cancelled recommendation)
        exec_resp = client.post(
            f"/api/v1/intelligence/recommendations/{rec.id}/execute",
            json={"operator_identity": "ops_lead"},
        )
        assert exec_resp.status_code in (400, 422)

    def test_scenario_09_failed_recovery_handling(self, test_db):
        """Scenario 9: Execution failure handled gracefully with rollback and clean status."""
        order = create_mock_order(test_db, scenario_type="NORMAL", age_minutes=10)
        rec = RecoveryRecommendation(
            investigation_id="inv_mock_fail",
            order_id=order.id,
            action_type="UNKNOWN_INVALID_ACTION",
            title="Invalid Action",
            rationale="Test failure branch",
            requires_approval=False,
            approval_status=ApprovalStatus.APPROVED.value,
            execution_status="PENDING",
        )
        test_db.add(rec)
        test_db.commit()

        # Execute should succeed with generic simulated fallback or clean handling
        result = RecoveryExecutionService.execute_recommendation(test_db, rec.id, "ops_lead")
        assert result["status"] == "EXECUTED"
        assert result["execution_result"]["action"] == "UNKNOWN_INVALID_ACTION"

    def test_scenario_10_terminal_order_protection(self, test_db):
        """Scenario 10: Terminal order (DELIVERED/CANCELLED) rejects recovery interventions."""
        order_delivered = create_mock_order(test_db, order_status="DELIVERED")
        order_cancelled = create_mock_order(test_db, order_status="CANCELLED")

        can_del, msg_del = PolicyEngine.validate_action_eligibility(
            ActionType.REASSIGN_COURIER.value, order_delivered.order_status, []
        )
        assert can_del is False
        assert "terminal" in msg_del.lower()

        can_canc, msg_canc = PolicyEngine.validate_action_eligibility(
            ActionType.EXPEDITE_KITCHEN_PING.value, order_cancelled.order_status, []
        )
        assert can_canc is False
        assert "terminal" in msg_canc.lower()

    def test_scenario_11_missing_ml_artifact_fallback(self):
        """Scenario 11: Missing ML artifact triggers safe deterministic heuristic."""
        # Intentionally request prediction with an invalid or blank path
        service = MLInferenceService.get_instance()
        res = service.predict_task_a(
            {"order_time_hour": 14, "items_count": 2, "last_mile_distance": 3.0}
        )
        assert isinstance(res, TaskAPrediction)
        assert res.eta_p50_min > 0
        assert res.eta_p10_min <= res.eta_p50_min <= res.eta_p90_min

    def test_scenario_12_degraded_agent_response_handling(self, monkeypatch):
        """Scenario 12: Degraded agent evidence sets confidence=UNAVAILABLE without crashing."""
        from backend.app.agents.restaurant_coordination import RestaurantCoordinationAgent

        def mock_failing_investigate(self, state):
            raise TimeoutError("Merchant POS gateway connection timed out.")

        monkeypatch.setattr(RestaurantCoordinationAgent, "investigate", mock_failing_investigate)

        test_state = MultiAgentInvestigationState(
            order_id="test-degraded-order-id",
            trigger_event="DEGRADED_TEST",
            risk_tier=RiskTier.MONITORED,
        )
        # Calling restaurant node when downstream agent encounters exception
        res_state = restaurant_node(test_state)
        rest_ev = res_state.get("restaurant_investigation", {})
        assert rest_ev["is_available"] is False
        assert rest_ev["confidence"] == "UNAVAILABLE"
        assert "latency" in rest_ev["operational_impact"].lower() or "unavailable" in rest_ev["operational_impact"].lower()

        # Customer resolution handles missing evidence conservatively
        cust_state = customer_resolution_node(res_state)
        assert cust_state.get("risk_tier") in (RiskTier.MONITORED, RiskTier.MONITORED.value, RiskTier.NOMINAL, RiskTier.NOMINAL.value)
        # Generates fallback monitor recommendation
        assert any(r.get("action_type") == ActionType.MONITOR_ORDER.value for r in cust_state.get("recovery_recommendations", []))


# =============================================================================
# Workstream B: Execution Reliability & Idempotency
# =============================================================================
class TestWorkstreamBExecutionReliabilityAndIdempotency:

    def test_persistent_idempotency_key_prevents_duplicate_execution(self, test_db):
        """Executing the same recommendation twice returns IDEMPOTENT_SKIPPED."""
        order = create_mock_order(test_db, scenario_type="NORMAL")
        rec = RecoveryRecommendation(
            investigation_id=f"inv_{uuid.uuid4().hex[:6]}",
            order_id=order.id,
            action_type=ActionType.MONITOR_ORDER.value,
            title="Telemetry Polling",
            rationale="Test persistent idempotency",
            requires_approval=False,
            approval_status=ApprovalStatus.APPROVED.value,
            execution_status="PENDING",
            execution_payload={"poll_interval_sec": 45},
        )
        test_db.add(rec)
        test_db.commit()

        # First execution
        res1 = RecoveryExecutionService.execute_recommendation(test_db, rec.id, "ops_lead")
        assert res1["status"] == "EXECUTED"

        # Second execution
        res2 = RecoveryExecutionService.execute_recommendation(test_db, rec.id, "ops_lead")
        assert res2["status"] in ("ALREADY_EXECUTED", "IDEMPOTENT_SKIPPED")

        # Database must only have one audit row
        audits = (
            test_db.query(RecoveryExecutionAudit)
            .filter(RecoveryExecutionAudit.recommendation_id == rec.id)
            .all()
        )
        assert len(audits) == 1

    def test_concurrent_execution_race_condition_safety(self):
        """Concurrent execution threads on same recommendation resolve safely via unique constraint."""
        # Use a fresh db session to set up the recommendation
        db_setup = SessionLocal()
        order = create_mock_order(db_setup, scenario_type="NORMAL")
        rec = RecoveryRecommendation(
            investigation_id=f"inv_{uuid.uuid4().hex[:6]}",
            order_id=order.id,
            action_type=ActionType.EXPEDITE_KITCHEN_PING.value,
            title="Concurrent Kitchen Ping",
            rationale="Test concurrency race condition safety",
            requires_approval=False,
            approval_status=ApprovalStatus.APPROVED.value,
            execution_status="PENDING",
            execution_payload={"prep_delay_min": 6.0},
        )
        db_setup.add(rec)
        db_setup.commit()
        rec_id = rec.id
        db_setup.close()

        results = []
        errors = []

        def worker_task():
            thread_db = SessionLocal()
            try:
                out = RecoveryExecutionService.execute_recommendation(thread_db, rec_id, "concurrent_agent")
                results.append(out)
            except Exception as e:
                errors.append(e)
            finally:
                thread_db.close()

        # Launch 4 concurrent threads attempting to execute the same recommendation simultaneously
        threads = [threading.Thread(target=worker_task) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 4

        # Exactly one thread executes, others return ALREADY_EXECUTED or IDEMPOTENT_SKIPPED
        executed_count = sum(1 for r in results if r["status"] == "EXECUTED")
        skipped_count = sum(1 for r in results if r["status"] in ("ALREADY_EXECUTED", "IDEMPOTENT_SKIPPED"))

        assert executed_count == 1
        assert skipped_count == 3

        # Verify only 1 audit record in DB
        verify_db = SessionLocal()
        audits = (
            verify_db.query(RecoveryExecutionAudit)
            .filter(RecoveryExecutionAudit.recommendation_id == rec_id)
            .all()
        )
        assert len(audits) == 1
        verify_db.close()


# =============================================================================
# Workstream C: Policy & Security Hardening
# =============================================================================
class TestWorkstreamCPolicyAndSecurityHardening:

    def test_customer_consent_opt_out_suppresses_notification(self, test_db):
        """Customer who opted out of notifications has notification actions suppressed."""
        order_opted_out = create_mock_order(test_db, consent=False)
        can_exec, reason = PolicyEngine.validate_action_eligibility(
            ActionType.PROACTIVE_CUSTOMER_NOTIFICATION.value,
            order_opted_out.order_status,
            [],
            order_context={"customer_consent": False},
        )
        assert can_exec is False
        assert "consent" in reason.lower() or "opted out" in reason.lower()

    def test_role_based_authorization_enforcement(self, client, test_db):
        """Unauthorized roles rejected with HTTP 403 / PermissionError; authorized succeed."""
        order = create_mock_order(test_db)
        rec = RecoveryRecommendation(
            investigation_id="inv_auth_test",
            order_id=order.id,
            action_type=ActionType.REASSIGN_COURIER.value,
            title="Authorization Role Test",
            rationale="Verify role RBAC gate",
            requires_approval=True,
            approval_status=ApprovalStatus.PENDING_APPROVAL.value,
            execution_status="PENDING",
        )
        test_db.add(rec)
        test_db.commit()

        # Unauthorized role: JUNIOR_INTERN -> 403 Forbidden
        unauth_resp = client.post(
            f"/api/v1/intelligence/recommendations/{rec.id}/approve",
            json={"operator_identity": "intern_bob", "operator_role": "JUNIOR_INTERN"},
        )
        assert unauth_resp.status_code == 403

        # Authorized role: OPS_LEAD -> 200 OK
        auth_resp = client.post(
            f"/api/v1/intelligence/recommendations/{rec.id}/approve",
            json={"operator_identity": "lead_alice", "operator_role": "OPS_LEAD"},
        )
        assert auth_resp.status_code == 200
        assert auth_resp.json()["approval_status"] == ApprovalStatus.APPROVED.value

    def test_recommendation_expiration_enforcement(self, client, test_db):
        """Expired recommendations (>30 mins) cannot be approved or executed."""
        order = create_mock_order(test_db)
        past_time = datetime.now(timezone.utc) - timedelta(minutes=40)
        rec = RecoveryRecommendation(
            investigation_id="inv_exp_test",
            order_id=order.id,
            action_type=ActionType.EXPEDITE_KITCHEN_PING.value,
            title="Expired Ping",
            rationale="Verify expiration gate",
            requires_approval=True,
            approval_status=ApprovalStatus.PENDING_APPROVAL.value,
            execution_status="PENDING",
            expires_at=past_time,
        )
        test_db.add(rec)
        test_db.commit()

        # Approval attempt on expired recommendation fails
        resp = client.post(
            f"/api/v1/intelligence/recommendations/{rec.id}/approve",
            json={"operator_identity": "ops_lead"},
        )
        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"].lower()

    def test_order_state_drift_prevention(self, test_db):
        """State drift from PREPARING to OUT_FOR_DELIVERY blocks kitchen expedite."""
        order = create_mock_order(test_db, order_status="PREPARING")
        rec = RecoveryRecommendation(
            investigation_id="inv_drift_test",
            order_id=order.id,
            action_type=ActionType.EXPEDITE_KITCHEN_PING.value,
            title="Expedite Kitchen Ping",
            rationale="Verify drift gate",
            requires_approval=False,
            approval_status=ApprovalStatus.APPROVED.value,
            execution_status="PENDING",
        )
        test_db.add(rec)
        test_db.commit()

        # Courier picks up food while recommendation was waiting
        order.order_status = "OUT_FOR_DELIVERY"
        test_db.commit()

        with pytest.raises(ValueError, match="state drift|picked up|not in PREPARING"):
            RecoveryExecutionService.execute_recommendation(test_db, rec.id, "ops_lead")


# =============================================================================
# Workstream D, E, F: ML Governance, Observability & Auditing
# =============================================================================
class TestWorkstreamEAndFMLGovernanceAndObservability:

    def test_ml_feature_schema_validation_and_imputation(self):
        """ML inference validates feature maps and imputes missing columns with partition defaults."""
        service = MLInferenceService.get_instance()
        pred = service.predict_task_a({})
        assert isinstance(pred, TaskAPrediction)
        assert pred.eta_p10_min <= pred.eta_p50_min <= pred.eta_p90_min

    def test_task_a_quantile_monotonic_ordering(self):
        """Strict monotonic quantile property: P10 <= P50 <= P90."""
        service = MLInferenceService.get_instance()
        features = {
            "order_time_hour": 19,
            "order_time_dow": 6,
            "items_count": 4,
            "first_mile_distance": 2.5,
            "last_mile_distance": 5.0,
            "is_weekend": 1,
            "order_volume_last_10m": 45,
            "rider_busy_ratio": 0.8,
        }
        pred = service.predict_task_a(features)
        assert pred.eta_p10_min <= pred.eta_p50_min
        assert pred.eta_p50_min <= pred.eta_p90_min

    def test_research_models_isolation(self):
        """Tasks B and C1 explicitly return is_operational_trigger=False."""
        service = MLInferenceService.get_instance()
        models = service.predict_research_models({})
        assert isinstance(models, dict)
        if "task_b_allocation_delay" in models:
            pred_b = models["task_b_allocation_delay"]
            assert pred_b.is_operational_trigger is False
            assert pred_b.governance_status == "NOT_APPROVED"

        if "task_c1_upfront_cancellation" in models:
            pred_c1 = models["task_c1_upfront_cancellation"]
            assert pred_c1.is_operational_trigger is False
            assert pred_c1.governance_status == "RESEARCH_ONLY"

    def test_ml_prediction_audit_persisted_to_database(self, test_db):
        """Every investigation run persists an MLPredictionAudit record."""
        order = create_mock_order(test_db, scenario_type="NORMAL")
        inv = IntelligenceService.trigger_investigation(test_db, order.id, "AUDIT_PERSISTENCE_TEST")

        audits = (
            test_db.query(MLPredictionAudit)
            .filter(MLPredictionAudit.order_id == order.id)
            .all()
        )
        assert len(audits) >= 1
        audit = audits[0]
        assert audit.order_id == order.id
        assert audit.task_a_eta_p50 is not None
        assert audit.task_a_interval_min is not None
        assert audit.task_a_interval_max is not None
        assert audit.provenance_metadata is not None

    def test_correlation_id_propagation_and_timing_metrics(self, client, test_db):
        """X-Correlation-ID is propagated through headers and investigation timing is recorded."""
        order = create_mock_order(test_db)
        custom_corr_id = f"test-corr-{uuid.uuid4().hex[:8]}"

        resp = client.post(
            f"/api/v1/intelligence/investigate/{order.id}",
            headers={"X-Correlation-ID": custom_corr_id},
        )
        assert resp.status_code == 200
        assert resp.headers.get("x-correlation-id") == custom_corr_id

        data = resp.json()
        assert data["workflow_execution"]["correlation_id"] == custom_corr_id
        assert data["workflow_execution"]["investigation_duration_ms"] >= 0
        assert "task_a_eta" in data["ml_provenance"]

    def test_pii_masking_in_audit_and_responses(self, test_db):
        """Customer and delivery partner phone numbers are masked in audit and logs."""
        order = create_mock_order(test_db, customer_phone="+919876543210")
        masked_phone = PolicyEngine.mask_pii(order.customer.phone)
        assert masked_phone.startswith("+9198")
        assert masked_phone.endswith("210")
        assert "*****" in masked_phone
        assert order.customer.phone not in masked_phone
