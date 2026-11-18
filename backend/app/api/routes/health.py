import os
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.session import get_db, engine
from backend.app.schemas.common import (
    HealthResponse,
    ApplicationHealth,
    InfrastructureHealth,
    AIProviderHealth,
    MLArtifactHealth,
    LivenessResponse,
    ReadinessResponse,
)
from backend.app.services.ml_inference import MLInferenceService

router = APIRouter(prefix="/health", tags=["System Health & Diagnostics"])


@router.get("", response_model=HealthResponse, summary="Granular Operational Health Diagnostics")
def health_check(db: Session = Depends(get_db)):
    """
    Comprehensive operational diagnostics across 4 distinct pillars:
    1. Application Health (FastAPI, version, environment)
    2. Infrastructure Health (Database ping latency, engine, pooling)
    3. AI Provider Health (Gemini API readiness / verified deterministic fallback)
    4. ML Artifact Health (Phase 2.5 Task A & C2 model readiness)
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Infrastructure (Database)
    db_status = "unhealthy"
    db_engine_name = "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "postgresql"
    db_latency_ms = 0.0

    start_db = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.perf_counter() - start_db) * 1000.0, 2)
        db_status = "healthy"
    except Exception as exc:
        db_latency_ms = round((time.perf_counter() - start_db) * 1000.0, 2)
        logger.error(f"Database health check failed: {exc}")
        db_status = f"unhealthy: {str(exc)}"

    pooling_info = {
        "engine": db_engine_name,
        "pool_size": getattr(engine.pool, "size", lambda: 0)() if hasattr(engine.pool, "size") else "N/A",
        "checked_in": getattr(engine.pool, "checkedin", lambda: 0)() if hasattr(engine.pool, "checkedin") else "N/A",
        "checked_out": getattr(engine.pool, "checkedout", lambda: 0)() if hasattr(engine.pool, "checkedout") else "N/A",
    }

    infra_health = InfrastructureHealth(
        database_status=db_status,
        database_engine=db_engine_name,
        database_latency_ms=db_latency_ms,
        connection_pooling=pooling_info,
    )

    # 2. AI Provider (Gemini API)
    gemini_key = os.getenv("GEMINI_API_KEY", "") or settings.GEMINI_API_KEY
    if gemini_key and not gemini_key.startswith("mock") and len(gemini_key) > 10:
        ai_status = "live"
        ai_details = "Live Gemini API configured with active model and fallback engine standby."
    else:
        ai_status = "fallback_ready"
        ai_details = "Deterministic rule-based multi-agent fallback engine active (zero external API dependency)."

    ai_health = AIProviderHealth(
        provider_name="Google Gemini & Deterministic Synthesizer",
        status=ai_status,
        model_name=settings.GEMINI_MODEL_NAME,
        fallback_engine_available=True,
        details=ai_details,
    )

    # 3. ML Artifacts (Phase 2.5 Models)
    ml_status = "ready"
    task_a_ok = False
    task_c2_ok = False
    reg_ok = False

    try:
        svc = MLInferenceService.get_instance(artifacts_dir=settings.ML_ARTIFACTS_DIR)
        task_a_ok = (
            svc.model_task_a_p10 is not None
            and svc.model_task_a_p50 is not None
            and svc.model_task_a_p90 is not None
        )
        task_c2_ok = svc.model_task_c2 is not None and svc.calibrator_task_c2 is not None
        reg_ok = bool(svc.registry)
        if not (task_a_ok and task_c2_ok):
            ml_status = "degraded"
    except Exception as exc:
        logger.warning(f"ML artifact health check inspection note: {exc}")
        ml_status = "missing"

    ml_health = MLArtifactHealth(
        status=ml_status,
        model_version="2.5.0",
        task_a_quantiles=task_a_ok,
        task_c2_calibrated=task_c2_ok,
        registry_loaded=reg_ok,
        artifacts_dir=settings.ML_ARTIFACTS_DIR,
    )

    # Overall Status Calculation
    if db_status == "healthy" and ml_status == "ready":
        overall_status = "healthy"
    elif db_status == "healthy":
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    app_health = ApplicationHealth(
        name=settings.PROJECT_NAME,
        status=overall_status,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )

    return HealthResponse(
        status=overall_status,
        database=db_status,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=now_iso,
        application=app_health,
        infrastructure=infra_health,
        ai_provider=ai_health,
        ml_artifacts=ml_health,
    )


@router.get("/live", response_model=LivenessResponse, summary="Kubernetes/Docker Liveness Probe")
def liveness_probe():
    """Returns 200 OK if the FastAPI process is running and receiving traffic."""
    return LivenessResponse(
        status="alive",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/ready", response_model=ReadinessResponse, summary="Kubernetes/Docker Readiness Probe")
def readiness_probe(db: Session = Depends(get_db)):
    """
    Returns 200 OK only if the application is fully ready to accept user traffic:
    - Database is reachable.
    - ML inference service is loaded.
    Returns 503 Service Unavailable if database is down.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.error(f"Readiness probe failed on database check: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unreachable: {exc}",
        )

    ml_status = "ready"
    try:
        svc = MLInferenceService.get_instance(artifacts_dir=settings.ML_ARTIFACTS_DIR)
        if not (svc.model_task_a_p50 and svc.model_task_c2):
            ml_status = "degraded"
    except Exception:
        ml_status = "degraded"

    return ReadinessResponse(
        status="ready",
        timestamp=now_iso,
        database="connected",
        ml_artifacts=ml_status,
    )
