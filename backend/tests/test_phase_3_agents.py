import os
import json
import pytest
from datetime import datetime, timezone, timedelta
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
from backend.app.services.ml_inference import MLInferenceService, TaskAPrediction, TaskC2Prediction
from backend.app.agents.schemas import RiskTier, ActionType, ApprovalStatus, SensitivityLevel, InvestigationStatus
from backend.app.agents.state import MultiAgentInvestigationState
from backend.app.agents.workflow import intelligence_workflow
from backend.app.services.policy_engine import PolicyEngine
from backend.app.services.intelligence_service import IntelligenceService
from backend.app.services.recovery_executor import RecoveryExecutionService


@pytest.fixture(scope="module")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_test_order(test_db):
    """Creates a sample test order in DB with realistic events."""
    now = datetime.now(timezone.utc)
    # Ensure restaurant, customer, delivery partner exist
    rest = test_db.query(Restaurant).first()
    if not rest:
        rest = Restaurant(
            id="rest_test_1",
            name="Meghana Foods Indiranagar",
            city="Bengaluru",
            area="Indiranagar",
            cuisine="Biryani",
            rating=4.5,
            delivery_time_listing="30-35 mins",
            data_source="SYNTHETIC",
        )
        test_db.add(rest)

    cust = test_db.query(Customer).first()
    if not cust:
        cust = Customer(
            id="cust_test_1",
            name="Rahul Sharma",
            email="rahul@example.com",
            phone="+919876543210",
            address="100 Feet Road, Indiranagar",
            data_source="SYNTHETIC",
        )
        test_db.add(cust)

    dp = test_db.query(DeliveryPartner).first()
    if not dp:
        dp = DeliveryPartner(
            id="dp_test_1",
            name="Sunil Gowda",
            availability_status="AVAILABLE",
        )
        test_db.add(dp)

    test_db.commit()

    order = Order(
        external_order_id=f"SWIG-TEST-{datetime.now().strftime('%H%M%S%f')[:10]}",
        customer_id=cust.id,
        restaurant_id=rest.id,
        delivery_partner_id=dp.id,
        order_status="PREPARING",
        order_value=450.0,
        promised_delivery_at=now + timedelta(minutes=15),
        created_at=now - timedelta(minutes=25),
        data_source="SYNTHETIC",
    )
    test_db.add(order)
    test_db.commit()

    # Add Events
    ev1 = OrderEvent(
        order_id=order.id,
        event_type="ORDER_PLACED",
        event_timestamp=order.created_at,
        event_metadata={"last_mile_distance": 3.8, "items_count": 2},
        data_source="SYNTHETIC",
    )
    ev2 = OrderEvent(
        order_id=order.id,
        event_type="ORDER_ACCEPTED",
        event_timestamp=order.created_at + timedelta(minutes=2),
        event_metadata={"kitchen_queue_depth": 5},
        data_source="SYNTHETIC",
    )
    ev3 = OrderEvent(
        order_id=order.id,
        event_type="RIDER_ASSIGNED",
        event_timestamp=order.created_at + timedelta(minutes=10),
        event_metadata={"first_mile_distance": 2.1},
        data_source="SYNTHETIC",
    )
    ev4 = OrderEvent(
        order_id=order.id,
        event_type="RIDER_ACCEPTED",
        event_timestamp=order.created_at + timedelta(minutes=11),
        event_metadata={},
        data_source="SYNTHETIC",
    )
    test_db.add_all([ev1, ev2, ev3, ev4])
    test_db.commit()
    test_db.refresh(order)
    return order


class TestPhase3MLInferenceService:
    """Verifies ML artifact loading, feature schemas, monotonic ordering, and landmark checks."""

    def test_artifacts_loaded_correctly(self):
        service = MLInferenceService.get_instance()
        assert service.model_task_a_p10 is not None
        assert service.model_task_a_p50 is not None
        assert service.model_task_a_p90 is not None
        assert service.model_task_c2 is not None
        assert service.calibrator_task_c2 is not None
        assert len(service.task_a_cfg.feature_columns) == 16
        assert len(service.task_c2_cfg.feature_columns) == 26

    def test_task_a_quantile_monotonic_ordering(self):
        service = MLInferenceService.get_instance()
        features = {
            "last_mile_distance": 4.2,
            "is_zero_last_mile": 0,
            "last_mile_distance_sq": 17.64,
            "distance_bracket": "medium",
            "order_hour": 19,
            "hour_sin": -0.965,
            "hour_cos": 0.258,
            "order_dayofweek": 4,
            "dow_sin": -0.433,
            "dow_cos": -0.900,
            "is_weekend": 0,
            "meal_period": "dinner",
            "is_peak_meal_window": 1,
            "rolling_order_volume_15m": 35.0,
            "rolling_order_volume_60m": 120.0,
            "demand_acceleration": 1.16,
        }
        pred = service.predict_task_a(features)
        assert pred.eta_p10_min <= pred.eta_p50_min <= pred.eta_p90_min
        assert pred.interval_width_min == round(pred.eta_p90_min - pred.eta_p10_min, 2)
        assert pred.model_version == "2.5.0"
        assert pred.governance_status == "APPROVED_FOR_SIMULATION"

    def test_task_a_long_tail_interval_flagging(self):
        service = MLInferenceService.get_instance()
        # Mock high distance long tail features
        features = {
            "last_mile_distance": 18.5,
            "is_zero_last_mile": 0,
            "last_mile_distance_sq": 342.25,
            "distance_bracket": "very_long",
            "order_hour": 21,
            "hour_sin": -0.707,
            "hour_cos": 0.707,
            "order_dayofweek": 5,
            "dow_sin": -0.974,
            "dow_cos": -0.222,
            "is_weekend": 1,
            "meal_period": "dinner",
            "is_peak_meal_window": 1,
            "rolling_order_volume_15m": 65.0,
            "rolling_order_volume_60m": 220.0,
            "demand_acceleration": 1.18,
        }
        pred = service.predict_task_a(features)
        assert pred.eta_p10_min <= pred.eta_p50_min <= pred.eta_p90_min
        assert "not a guaranteed delivery time" in pred.disclaimer.lower()

    def test_landmark_ineligible_when_before_5_minutes(self):
        service = MLInferenceService.get_instance()
        from types import SimpleNamespace
        order = SimpleNamespace(
            id="ord_inel",
            external_order_id="SWIG-INEL-1",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=4),
            order_status="PREPARING",
        )
        events = [
            SimpleNamespace(
                event_type="RIDER_ASSIGNED",
                event_timestamp=datetime.now(timezone.utc) - timedelta(minutes=2),
                event_metadata={},
            )
        ]
        is_elig, reason, _, _ = service.check_landmark_eligibility(order, events)
        assert is_elig is False
        assert "5.0m post-allotment" in reason

        res = service.run_inference(order, events)
        assert res.task_c2_cancellation.is_eligible is False
        assert res.task_c2_cancellation.calibrated_probability is None

    def test_landmark_eligible_post_5_minutes(self):
        service = MLInferenceService.get_instance()
        from types import SimpleNamespace
        order = SimpleNamespace(
            id="ord_elig",
            external_order_id="SWIG-ELIG-1",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=20),
            order_status="PREPARING",
        )
        events = [
            SimpleNamespace(
                event_type="RIDER_ASSIGNED",
                event_timestamp=datetime.now(timezone.utc) - timedelta(minutes=10),
                event_metadata={"first_mile_distance": 1.8},
            ),
            SimpleNamespace(
                event_type="RIDER_ACCEPTED",
                event_timestamp=datetime.now(timezone.utc) - timedelta(minutes=8),
                event_metadata={},
            ),
        ]
        is_elig, reason, allot_time, elapsed = service.check_landmark_eligibility(order, events)
        assert is_elig is True
        assert elapsed >= 5.0

        res = service.run_inference(order, events)
        assert res.task_c2_cancellation.is_eligible is True
        assert res.task_c2_cancellation.calibrated_probability is not None
        assert 0.0 <= res.task_c2_cancellation.calibrated_probability <= 1.0
        assert res.task_c2_cancellation.target_semantics.startswith("Eventual post-landmark cancellation")

    def test_research_models_flagged_not_approved(self):
        service = MLInferenceService.get_instance()
        from types import SimpleNamespace
        order = SimpleNamespace(
            id="ord_res",
            external_order_id="SWIG-RES-1",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            order_status="PREPARING",
        )
        res = service.run_inference(order, [], include_research_models=True)
        assert res.research_models is not None
        if "task_b_allocation_delay" in res.research_models:
            assert res.research_models["task_b_allocation_delay"].governance_status == "NOT_APPROVED"
            assert res.research_models["task_b_allocation_delay"].is_operational_trigger is False
        if "task_c1_upfront_cancellation" in res.research_models:
            assert res.research_models["task_c1_upfront_cancellation"].governance_status == "RESEARCH_ONLY"
            assert res.research_models["task_c1_upfront_cancellation"].is_operational_trigger is False


class TestPhase3LangGraphWorkflow:
    """Verifies LangGraph orchestration across Order, Restaurant, Delivery, and Resolution agents."""

    def test_langgraph_workflow_nominal_order(self):
        now = datetime.now(timezone.utc)
        initial_state: MultiAgentInvestigationState = {
            "order_id": "ord_nom",
            "external_order_id": "SWIG-NOM-101",
            "order_context": {
                "order_status": "PREPARING",
                "created_at": (now - timedelta(minutes=10)).isoformat(),
                "promised_delivery_at": (now + timedelta(minutes=25)).isoformat(),
                "restaurant": {"name": "Leon's Burgers", "is_active": True},
                "delivery_partner": {"id": "dp_nom", "name": "Vikas K"},
            },
            "order_events": [
                {"event_type": "ORDER_PLACED", "event_timestamp": (now - timedelta(minutes=10)).isoformat(), "metadata": {"last_mile_distance": 2.5}},
                {"event_type": "ORDER_ACCEPTED", "event_timestamp": (now - timedelta(minutes=8)).isoformat()},
                {"event_type": "RIDER_ASSIGNED", "event_timestamp": (now - timedelta(minutes=6)).isoformat(), "metadata": {"first_mile_distance": 1.2}},
                {"event_type": "RIDER_ACCEPTED", "event_timestamp": (now - timedelta(minutes=5)).isoformat()},
            ],
            "workflow_status": InvestigationStatus.PENDING,
            "errors": [],
        }

        final_state = intelligence_workflow.invoke(initial_state)
        assert final_state["workflow_status"] == InvestigationStatus.COMPLETED
        assert final_state["risk_tier"] in (RiskTier.NOMINAL, RiskTier.MONITORED)
        assert final_state["restaurant_investigation"]["kitchen_backlog_source"] == "SIMULATED_TELEMETRY"
        assert final_state["delivery_investigation"]["courier_assigned"] is True
        assert len(final_state["recovery_recommendations"]) > 0

    def test_langgraph_workflow_critical_delayed_order(self):
        now = datetime.now(timezone.utc)
        initial_state: MultiAgentInvestigationState = {
            "order_id": "ord_crit",
            "external_order_id": "SWIG-CRIT-999",
            "order_context": {
                "order_status": "PREPARING",
                "created_at": (now - timedelta(minutes=45)).isoformat(),
                "promised_delivery_at": (now - timedelta(minutes=10)).isoformat(),
                "restaurant": {"name": "Spice Garden", "is_active": True},
                "delivery_partner": {"id": "dp_crit", "name": "Deepak R"},
            },
            "order_events": [
                {"event_type": "ORDER_PLACED", "event_timestamp": (now - timedelta(minutes=45)).isoformat(), "metadata": {"last_mile_distance": 5.0}},
                {"event_type": "ORDER_ACCEPTED", "event_timestamp": (now - timedelta(minutes=40)).isoformat(), "metadata": {"kitchen_queue_depth": 8}},
                {"event_type": "RIDER_ASSIGNED", "event_timestamp": (now - timedelta(minutes=30)).isoformat(), "metadata": {"first_mile_distance": 4.2}},
                {"event_type": "RIDER_REASSIGNED", "event_timestamp": (now - timedelta(minutes=20)).isoformat()},
                {"event_type": "RIDER_REASSIGNED", "event_timestamp": (now - timedelta(minutes=8)).isoformat()},
            ],
            "workflow_status": InvestigationStatus.PENDING,
            "errors": [],
        }

        final_state = intelligence_workflow.invoke(initial_state)
        assert final_state["risk_tier"] == RiskTier.CRITICAL
        recs = final_state["recovery_recommendations"]
        assert len(recs) >= 2

        # Verify sensitive actions are gated by human approval
        action_types = [r["action_type"] for r in recs]
        assert ActionType.REASSIGN_COURIER.value in action_types or ActionType.APOLOGY_CREDIT_VOUCHER.value in action_types
        for r in recs:
            if r["action_type"] in (ActionType.REASSIGN_COURIER.value, ActionType.APOLOGY_CREDIT_VOUCHER.value):
                assert r["requires_approval"] is True
                assert r["approval_status"] == ApprovalStatus.PENDING_APPROVAL.value


class TestPhase3PolicyEngine:
    """Verifies deterministic policy rules, cooldown suppression, and idempotency."""

    def test_policy_blocks_action_on_terminal_order(self):
        is_elig, reason = PolicyEngine.validate_action_eligibility(
            action_type=ActionType.REASSIGN_COURIER.value,
            order_status="DELIVERED",
            existing_actions=[],
        )
        assert is_elig is False
        assert "terminal" in reason.lower()

    def test_policy_blocks_kitchen_ping_after_pickup(self):
        is_elig, reason = PolicyEngine.validate_action_eligibility(
            action_type=ActionType.EXPEDITE_KITCHEN_PING.value,
            order_status="OUT_FOR_DELIVERY",
            existing_actions=[],
        )
        assert is_elig is False
        assert "already" in reason.lower()

    def test_duplicate_notification_cooldown(self):
        now = datetime.now(timezone.utc)
        recent_actions = [
            {
                "action_type": ActionType.PROACTIVE_CUSTOMER_NOTIFICATION.value,
                "created_at": (now - timedelta(minutes=5)).isoformat(),
            }
        ]
        is_elig, reason = PolicyEngine.validate_action_eligibility(
            action_type=ActionType.PROACTIVE_CUSTOMER_NOTIFICATION.value,
            order_status="PREPARING",
            existing_actions=recent_actions,
            now=now,
        )
        assert is_elig is False
        assert "cooldown window" in reason

    def test_duplicate_voucher_suppression(self):
        recent_actions = [
            {
                "action_type": ActionType.APOLOGY_CREDIT_VOUCHER.value,
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            }
        ]
        is_elig, reason = PolicyEngine.validate_action_eligibility(
            action_type=ActionType.APOLOGY_CREDIT_VOUCHER.value,
            order_status="PREPARING",
            existing_actions=recent_actions,
        )
        assert is_elig is False
        assert "already issued" in reason


class TestPhase3FastAPIEndpoints:
    """Verifies end-to-end FastAPI integration, approval lifecycle, and audit logs."""

    def test_investigate_order_api(self, client, sample_test_order):
        resp = client.post(f"/api/v1/intelligence/investigate/{sample_test_order.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_id"] == sample_test_order.id
        assert data["status"] == "COMPLETED"
        assert "risk_tier" in data
        assert "eta_p10" in data
        assert "eta_p50" in data
        assert "eta_p90" in data
        assert len(data["recommendations"]) > 0

    def test_get_predictions_api(self, client, sample_test_order):
        resp = client.get(f"/api/v1/intelligence/predictions/{sample_test_order.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "task_a_eta" in data
        assert "task_c2_cancellation" in data
        assert data["task_a_eta"]["model_version"] == "2.5.0"

    def test_approval_and_execution_lifecycle(self, client, test_db, sample_test_order):
        # 1. Trigger investigation
        inv_resp = client.post(f"/api/v1/intelligence/investigate/{sample_test_order.id}")
        assert inv_resp.status_code == 200
        inv_data = inv_resp.json()
        recs = inv_data["recommendations"]

        # Find or create a recommendation requiring approval
        sensitive_rec = next((r for r in recs if r["requires_approval"]), None)
        if not sensitive_rec:
            # Create a mock pending recommendation for explicit test
            sensitive_rec_obj = RecoveryRecommendation(
                investigation_id=inv_data["id"],
                order_id=sample_test_order.id,
                action_type=ActionType.REASSIGN_COURIER.value,
                title="Express Courier Reassignment",
                rationale="Test manual courier reassignment approval",
                sensitivity_level=SensitivityLevel.HIGH.value,
                requires_approval=True,
                approval_status=ApprovalStatus.PENDING_APPROVAL.value,
                execution_status="PENDING",
                execution_payload={"target_radius_km": 2.0},
            )
            test_db.add(sensitive_rec_obj)
            test_db.commit()
            test_db.refresh(sensitive_rec_obj)
            rec_id = sensitive_rec_obj.id
        else:
            rec_id = sensitive_rec["id"]

        # 2. Reject first to verify rejection endpoint
        rej_resp = client.post(
            f"/api/v1/intelligence/recommendations/{rec_id}/reject",
            json={"operator_identity": "lead_ops_officer", "reason": "Courier is already near restaurant"},
        )
        assert rej_resp.status_code == 200
        assert rej_resp.json()["approval_status"] == ApprovalStatus.REJECTED.value

        # 3. Approve
        app_resp = client.post(
            f"/api/v1/intelligence/recommendations/{rec_id}/approve",
            json={"operator_identity": "lead_ops_officer", "notes": "Approved reassignment after customer call"},
        )
        assert app_resp.status_code == 200
        assert app_resp.json()["approval_status"] == ApprovalStatus.APPROVED.value

        # 4. Execute approved action
        exec_resp = client.post(
            f"/api/v1/intelligence/recommendations/{rec_id}/execute",
            json={"operator_identity": "lead_ops_officer"},
        )
        assert exec_resp.status_code == 200
        exec_data = exec_resp.json()
        assert exec_data["status"] == "EXECUTED"
        assert "audit_id" in exec_data

        # 5. Idempotent re-execution
        re_exec_resp = client.post(
            f"/api/v1/intelligence/recommendations/{rec_id}/execute",
            json={"operator_identity": "lead_ops_officer"},
        )
        assert re_exec_resp.status_code == 200
        assert re_exec_resp.json()["status"] in ("ALREADY_EXECUTED", "IDEMPOTENT_SKIPPED")

        # 6. Verify Audit Trail
        audit_resp = client.get(f"/api/v1/intelligence/audit/{sample_test_order.id}")
        assert audit_resp.status_code == 200
        audits = audit_resp.json()
        assert len(audits) >= 1
        assert audits[0]["is_simulated"] is True
        assert audits[0]["ml_model_version"] == "2.5.0"
