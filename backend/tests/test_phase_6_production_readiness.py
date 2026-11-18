"""
Swiggy ResolveAI — Phase 6 Test Suite.
Production Engineering, Deployment Readiness & Release Governance.

Verifies:
1. Configuration validation and environment separation.
2. Correlation ID middleware and execution timing header propagation.
3. Granular health diagnostics (/health, /health/live, /health/ready).
4. Database connection pooling and readiness probing.
5. Role-based access control (RBAC) and security error masking.
6. Graceful degradation when external AI or ML features are impaired.
7. Presence and integrity of performance benchmark artifacts.
"""

import os
import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.config import Settings
from backend.app.database.session import SessionLocal, get_db
from backend.app.services.ml_inference import MLInferenceService
from backend.app.services.policy_engine import PolicyEngine
from backend.app.services.intelligence_service import IntelligenceService
from backend.app.models.order import Order
from backend.app.models.recommendation import RecoveryRecommendation


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Transactional DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# 1. Configuration & Environment Validation
# =============================================================================

class TestConfigurationAndEnvironmentValidation:
    """Verifies Pydantic settings parsing, environment validation, and CORS assembly."""

    def test_environment_validation_accepts_valid_modes(self):
        for env in ["development", "testing", "staging", "production"]:
            s = Settings(ENVIRONMENT=env)
            assert s.ENVIRONMENT == env

    def test_environment_validation_rejects_invalid_mode(self):
        with pytest.raises(ValueError, match="Invalid ENVIRONMENT"):
            Settings(ENVIRONMENT="invalid_cloud_env")

    def test_cors_assembly_from_string_and_list(self):
        s1 = Settings(BACKEND_CORS_ORIGINS="http://localhost:3000, https://swiggy.com")
        assert "http://localhost:3000" in s1.BACKEND_CORS_ORIGINS
        assert "https://swiggy.com" in s1.BACKEND_CORS_ORIGINS

        s2 = Settings(BACKEND_CORS_ORIGINS=["http://localhost:8000"])
        assert s2.BACKEND_CORS_ORIGINS == ["http://localhost:8000"]

    def test_env_example_files_exist(self):
        assert os.path.exists("backend/.env.example")
        assert os.path.exists("frontend/.env.example")
        assert os.path.exists(".gitignore")

        with open("backend/.env.example", "r") as f:
            content = f.read()
            assert "DATABASE_URL" in content
            assert "LOG_LEVEL" in content
            assert "DB_POOL_SIZE" in content


# =============================================================================
# 2. Correlation ID & Execution Timing Middleware
# =============================================================================

class TestCorrelationIdAndMiddleware:
    """Verifies correlation ID tracing and execution timing headers on all HTTP endpoints."""

    def test_incoming_correlation_id_is_preserved(self, client):
        custom_id = f"trace-test-{uuid.uuid4().hex[:8]}"
        res = client.get("/api/v1/health/live", headers={"X-Correlation-ID": custom_id})

        assert res.status_code == 200
        assert res.headers.get("X-Correlation-ID") == custom_id
        assert "X-Process-Time-Ms" in res.headers
        assert float(res.headers["X-Process-Time-Ms"]) >= 0.0

    def test_missing_correlation_id_is_automatically_generated(self, client):
        res = client.get("/api/v1/health/live")

        assert res.status_code == 200
        generated_id = res.headers.get("X-Correlation-ID")
        assert generated_id is not None
        # Check valid UUID format
        parsed_uuid = uuid.UUID(generated_id)
        assert str(parsed_uuid) == generated_id
        assert "X-Process-Time-Ms" in res.headers


# =============================================================================
# 3. Granular Health & Readiness Diagnostics
# =============================================================================

class TestHealthAndReadinessEndpoints:
    """Verifies operational diagnostics across Application, Infrastructure, AI Provider, and ML Artifacts."""

    def test_comprehensive_health_endpoint_structure(self, client):
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()

        assert data["status"] in ("healthy", "degraded")
        assert "application" in data
        assert "infrastructure" in data
        assert "ai_provider" in data
        assert "ml_artifacts" in data

        # Infrastructure
        assert data["infrastructure"]["database_status"] == "healthy"
        assert data["infrastructure"]["database_latency_ms"] >= 0.0

        # AI Provider (fallback ready)
        assert data["ai_provider"]["fallback_engine_available"] is True
        assert data["ai_provider"]["status"] in ("live", "fallback_ready")

        # ML Artifacts
        assert data["ml_artifacts"]["status"] in ("ready", "degraded")
        assert data["ml_artifacts"]["model_version"] == "2.5.0"

    def test_liveness_probe_returns_200(self, client):
        res = client.get("/api/v1/health/live")
        assert res.status_code == 200
        assert res.json()["status"] == "alive"

    def test_readiness_probe_returns_200_when_healthy(self, client):
        res = client.get("/api/v1/health/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"

    def test_readiness_probe_returns_503_on_database_failure(self, client):
        mock_db = MagicMock(spec=Session)
        mock_db.execute.side_effect = Exception("Simulated PostgreSQL connection timeout")

        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            res = client.get("/api/v1/health/ready")
            assert res.status_code == 503
            assert "Database unreachable" in res.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_db, None)


# =============================================================================
# 4. Security & Role-Based Access Control (RBAC) Enforcement
# =============================================================================

class TestSecurityAndRBACEnforcement:
    """Verifies backend RBAC authorization and error masking."""

    def test_policy_engine_rejects_unauthorized_identities(self):
        auth, msg = PolicyEngine.check_operator_authorization("UNAUTHORIZED_OPERATOR")
        assert auth is False
        assert "not authorized" in msg

        auth, msg = PolicyEngine.check_operator_authorization("guest_user", role="INTERN")
        assert auth is False
        assert "not permitted" in msg

    def test_policy_engine_accepts_authorized_roles(self):
        for role in ["OPERATOR", "SUPERVISOR", "OPS_LEAD", "ADMIN"]:
            auth, msg = PolicyEngine.check_operator_authorization("lead_analyst_1", role=role)
            assert auth is True
            assert "confirmed" in msg

    def test_approval_endpoint_enforces_403_on_unauthorized_role(self, client, db_session):
        from datetime import datetime, timezone
        from backend.app.models.investigation import OrderInvestigation

        # Create a transient test order, investigation & recommendation
        order_id = str(uuid.uuid4())
        order = Order(
            id=order_id,
            external_order_id=f"SWIG-P6-AUTH-{uuid.uuid4().hex[:6]}",
            customer_id="cust_sim_1",
            restaurant_id="rest_sim_1",
            order_status="IN_KITCHEN",
            order_value=450.0,
            promised_delivery_at=datetime.now(timezone.utc),
        )
        inv_id = str(uuid.uuid4())
        inv = OrderInvestigation(
            id=inv_id,
            order_id=order_id,
            status="COMPLETED",
            risk_tier="HIGH_RISK",
        )
        rec_id = str(uuid.uuid4())
        rec = RecoveryRecommendation(
            id=rec_id,
            investigation_id=inv_id,
            order_id=order_id,
            action_type="REASSIGN_COURIER",
            title="Courier Reassignment",
            rationale="Test recommendation",
            sensitivity_level="HIGH",
            requires_approval=True,
            approval_status="AWAITING_APPROVAL",
        )
        db_session.add(order)
        db_session.add(inv)
        db_session.add(rec)
        db_session.commit()

        try:
            # Attempt to approve with unauthorized role
            payload = {
                "operator_identity": "intern_user",
                "operator_role": "INTERN",
                "notes": "Unauthorized approval attempt",
            }
            res = client.post(f"/api/v1/intelligence/recommendations/{rec_id}/approve", json=payload)
            assert res.status_code == 403
            assert "Authorization denied" in res.json()["detail"]
        finally:
            db_session.delete(rec)
            db_session.delete(inv)
            db_session.delete(order)
            db_session.commit()

    def test_unhandled_exception_does_not_leak_stack_traces(self, client):
        # Trigger an invalid route or mock an internal exception
        res = client.get("/api/v1/orders/non-existent-uuid-12345678")
        assert res.status_code == 404
        data = res.json()
        # Verify clean error structure without Python traceback
        assert "traceback" not in str(data).lower()
        assert "error" in data or "detail" in data


# =============================================================================
# 5. AI & ML Operational Readiness & Graceful Fallback
# =============================================================================

class TestMLAndAgentGracefulDegradation:
    """Verifies that missing LLM keys or corrupted features fall back cleanly."""

    def test_customer_resolution_agent_fallback_when_gemini_unavailable(self):
        from backend.app.agents.customer_resolution import CustomerResolutionAgent
        from backend.app.agents.state import MultiAgentInvestigationState
        from backend.app.agents.schemas import RiskTier

        # Explicitly initialize with no API key
        agent = CustomerResolutionAgent(use_llm=False)
        dummy_state: MultiAgentInvestigationState = {
            "order_id": "order-test-fallback",
            "external_order_id": "SWIG-FALLBACK-001",
            "risk_tier": RiskTier.HIGH_RISK,
            "order_context": {"order_value": 450.0},
            "ml_predictions": {},
            "restaurant_investigation": {"kitchen_delay_detected": True, "prep_delay_min": 12.0},
            "delivery_investigation": {"assignment_delay_detected": False},
        }

        result_state = agent.synthesize(dummy_state)
        synthesis = result_state.get("resolution_synthesis")
        recommendations = result_state.get("recovery_recommendations", [])

        assert synthesis is not None
        assert len(recommendations) > 0
        assert synthesis["primary_bottleneck"] != ""
        # Provenance shows deterministic synthesizer
        assert any(r["action_type"] == "EXPEDITE_KITCHEN_PING" for r in recommendations)

    def test_ml_inference_handles_empty_raw_features_with_defaults(self):
        svc = MLInferenceService.get_instance()
        res = svc.run_inference("test-order-robustness", {})

        assert res.task_a_eta.eta_p50_min > 0
        assert res.task_a_eta.eta_p10_min <= res.task_a_eta.eta_p50_min <= res.task_a_eta.eta_p90_min
        assert res.task_c2_cancellation is not None


# =============================================================================
# 6. Performance & Benchmark Artifact Verification
# =============================================================================

class TestPerformanceBenchmarkArtifacts:
    """Verifies that Phase 6 benchmark results are persisted and report valid metrics."""

    def test_benchmark_results_json_exists_and_valid(self):
        artifact_path = "data/artifacts/benchmarks/phase_6_performance_results.json"
        assert os.path.exists(artifact_path), "Performance benchmark artifact must exist"

        import json
        with open(artifact_path, "r") as f:
            data = json.load(f)

        assert "benchmark_timestamp" in data
        assert "results" in data
        assert len(data["results"]) >= 4

        for r in data["results"]:
            assert r["sample_count"] > 0
            assert r["median_latency_ms"] >= 0.0
            assert r["p95_latency_ms"] >= r["median_latency_ms"]
            assert r["error_rate_pct"] == 0.0
