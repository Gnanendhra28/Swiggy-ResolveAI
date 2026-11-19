"""
Comprehensive Database Reliability & Health Endpoint Verification against Neon PostgreSQL.
"""
import sys
import uuid
from datetime import datetime, timezone
sys.path.insert(0, ".")

from sqlalchemy import create_engine, text
from backend.app.core.config import settings
from backend.app.database.session import SessionLocal, engine
from backend.app.models.customer import Customer

def test_reliability():
    print("=== 1. URL NORMALIZATION & POOL CONFIGURATION ===")
    print(f"Configured DATABASE_URL dialect: {engine.dialect.name}")
    assert engine.dialect.name == "postgresql", "Dialect must be postgresql"
    print(f"Driver in use: {engine.driver}")
    assert engine.driver == "psycopg2", "Driver must be psycopg2"
    print(f"Pool size: {engine.pool.size()}")
    print(f"Pool max overflow: {engine.pool._max_overflow}")
    print(f"Pool recycle seconds: {engine.pool._recycle}")
    print(f"Pool pre-ping enabled: {engine.pool._pre_ping}")
    assert engine.pool.size() == 10
    assert engine.pool._max_overflow == 20
    assert engine.pool._recycle == 1800
    assert engine.pool._pre_ping is True
    print("Pool sizing & lifecycle settings verified: OK")

    print("\n=== 2. TRANSACTION COMMIT & PERSISTENCE TEST ===")
    db = SessionLocal()
    test_id = f"test_audit_{uuid.uuid4().hex[:8]}"
    test_customer = Customer(
        id=test_id,
        name="Reliability Audit Customer",
        phone="+919999999999",
        created_at=datetime.now(timezone.utc)
    )
    db.add(test_customer)
    db.commit()
    db.close()

    # Verify persistence on a fresh connection
    db2 = SessionLocal()
    persisted = db2.query(Customer).filter_by(id=test_id).first()
    assert persisted is not None, "Failed to persist customer in Neon"
    assert persisted.name == "Reliability Audit Customer"
    print(f"Persisted record verified in Neon: ID={persisted.id}")

    print("\n=== 3. TRANSACTION ROLLBACK INTEGRITY TEST ===")
    rollback_id = f"rollback_{uuid.uuid4().hex[:8]}"
    rollback_customer = Customer(
        id=rollback_id,
        name="Should Rollback Customer",
        phone="+910000000000",
        created_at=datetime.now(timezone.utc)
    )
    db2.add(rollback_customer)
    db2.flush()
    # Explicitly trigger rollback
    db2.rollback()
    
    # Verify record was NOT persisted
    rolled_back = db2.query(Customer).filter_by(id=rollback_id).first()
    assert rolled_back is None, "Rollback failed: record was unexpectedly found!"
    print("Transaction rollback verified: record was successfully discarded.")

    # Clean up test customer
    db2.delete(persisted)
    db2.commit()
    print(f"Cleaned up test customer ID={test_id}")
    db2.close()

    print("\n=== 4. HEALTH ENDPOINTS DIFFERENTIATION AUDIT ===")
    import httpx
    # 4a. Live probe (fast liveness)
    r_live = httpx.get("http://127.0.0.1:8000/api/v1/health/live")
    print(f"GET /api/v1/health/live -> Status {r_live.status_code}, Body: {r_live.json()}")
    assert r_live.status_code == 200
    assert r_live.json()["status"] == "alive"

    # 4b. Ready probe (readiness check)
    r_ready = httpx.get("http://127.0.0.1:8000/api/v1/health/ready")
    print(f"GET /api/v1/health/ready -> Status {r_ready.status_code}, Body: {r_ready.json()}")
    assert r_ready.status_code == 200
    assert r_ready.json()["status"] == "ready"
    assert r_ready.json()["database"] == "connected"

    # 4c. Detailed diagnostics
    r_diag = httpx.get("http://127.0.0.1:8000/api/v1/health")
    print(f"GET /api/v1/health -> Status {r_diag.status_code}, DB Latency: {r_diag.json()['infrastructure']['database_latency_ms']}ms")
    assert r_diag.status_code == 200
    assert r_diag.json()["infrastructure"]["database_status"] == "healthy"
    assert r_diag.json()["infrastructure"]["database_engine"] == "postgresql"

    print("\nDATABASE RELIABILITY & HEALTH PROBES: 100% VERIFIED!")

if __name__ == "__main__":
    test_reliability()
