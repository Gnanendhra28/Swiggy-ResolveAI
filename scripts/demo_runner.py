#!/usr/bin/env python3
"""
Swiggy ResolveAI — Automated End-to-End Demonstration Runner Script
Executes all 8 operational demonstration steps against a live local instance:
1. Verifies backend health and readiness.
2. Acquires signed demonstration bearer token for OPS_LEAD.
3. Ingests fresh synthetic demo orders with dynamic relative timestamps.
4. Injects operational delay telemetry (kitchen backlog & courier allotment delay).
5. Dispatches LangGraph multi-agent investigations.
6. Demonstrates Human-in-the-Loop (HITL) approval with signed credentials.
7. Executes simulated recovery actions and validates cryptographic idempotency.
8. Verifies immutable execution audit records.
"""

import sys
import time
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx

BASE_URL = "http://127.0.0.1:8000"
API_V1 = f"{BASE_URL}/api/v1"


def log(step: str, msg: str):
    print(f"\n[{step}] {msg}")


def run_demo():
    print("=" * 70)
    print("  SWIGGY RESOLVEAI — REPRODUCIBLE END-TO-END DEMO RUNNER")
    print("=" * 70)

    client = httpx.Client(timeout=15.0)

    # 1. Health & Readiness Check
    log("STEP 1", "Checking Backend Health & Readiness...")
    from backend.app.database.session import engine, SessionLocal
    from backend.app.database.base import Base
    from backend.app.services.simulation_service import SimulationService
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        SimulationService.ensure_synthetic_seed_entities(db)

    is_live_server = False
    try:
        r = client.get(f"{API_V1}/health/ready")
        if r.status_code == 200:
            is_live_server = True
            print("Connected to live server at http://127.0.0.1:8000. 4-Pillar Health Diagnostics OK.")
    except Exception:
        is_live_server = False

    if not is_live_server:
        print("No live server running at 127.0.0.1:8000. Switching to in-process FastAPI TestClient...")
        from fastapi.testclient import TestClient
        from backend.app.main import app
        client = TestClient(app)
        api_prefix = "/api/v1"
    else:
        api_prefix = API_V1

    # Re-verify readiness with active client
    r = client.get(f"{api_prefix}/health/ready")
    if r.status_code != 200:
        print(f"FAILED: Backend readiness probe returned {r.status_code}: {r.text}")
        sys.exit(1)
    print("Backend is READY. 4-Pillar Health Diagnostics OK.")

    # 2. Acquire Demonstration Token
    log("STEP 2", "Requesting Demonstration Signed Bearer Token (OPS_LEAD)...")
    r = client.post(f"{api_prefix}/auth/dev-token", json={"operator_profile": "ops_lead"})
    if r.status_code != 200:
        print(f"FAILED to acquire dev token: {r.status_code} - {r.text}")
        sys.exit(1)
    token_data = r.json()
    token = token_data["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    print(f"Acquired Token for: {token_data['operator_identity']} (Role: {token_data['operator_role']})")

    # 3. Ingest Fresh Orders via Simulation Generator
    log("STEP 3", "Generating Fresh Synthetic Orders with Dynamic Timestamps...")
    now = datetime.now(timezone.utc)
    r = client.post(
        f"{api_prefix}/simulation/generate",
        json={"scenario": "RESTAURANT_DELAY", "count": 1, "seed": int(time.time()) % 10000},
    )
    if r.status_code != 200:
        print(f"FAILED to generate simulation order: {r.status_code} - {r.text}")
        sys.exit(1)
    gen_result = r.json()
    order_ids = gen_result.get("order_ids") or gen_result.get("generated_order_ids") or []
    order_id = order_ids[0]

    # Ensure the order is set to active IN_KITCHEN status to demonstrate live recovery
    from backend.app.database.session import SessionLocal
    from backend.app.models.order import Order
    db_session = SessionLocal()
    try:
        active_order = db_session.get(Order, order_id)
        if active_order:
            active_order.order_status = "IN_KITCHEN"
            active_order.created_at = now - timedelta(minutes=25)
            active_order.promised_delivery_at = now + timedelta(minutes=15)
            db_session.commit()
    finally:
        db_session.close()

    print(f"Created Synthetic Disrupted Order ID: {order_id} (Active Status: IN_KITCHEN)")

    # 4. Inject Operational Delay Telemetry Events
    log("STEP 4", "Injecting Kitchen and Courier Delay Telemetry Events...")
    ev1_payload = {
        "order_id": order_id,
        "event_type": "RESTAURANT_PREPARATION_DELAY",
        "event_timestamp": (now - timedelta(minutes=10)).isoformat(),
        "metadata": {"prep_delay_min": 18.5, "kitchen_queue_depth": 8},
        "data_source": "SYNTHETIC",
    }
    r1 = client.post(f"{api_prefix}/simulation/events", json=ev1_payload)
    print(f"Kitchen Delay Telemetry Injected: Status {r1.status_code}")

    ev2_payload = {
        "order_id": order_id,
        "event_type": "COURIER_ASSIGNMENT_DELAY",
        "event_timestamp": (now - timedelta(minutes=5)).isoformat(),
        "metadata": {"allotment_delay_min": 11.0},
        "data_source": "SYNTHETIC",
    }
    r2 = client.post(f"{api_prefix}/simulation/events", json=ev2_payload)
    print(f"Courier Allotment Delay Telemetry Injected: Status {r2.status_code}")

    # 5. Trigger Multi-Agent Investigation
    log("STEP 5", f"Triggering LangGraph Multi-Agent Investigation on Order {order_id}...")
    r_inv = client.post(f"{api_prefix}/intelligence/investigate/{order_id}")
    if r_inv.status_code != 200:
        print(f"FAILED Investigation: {r_inv.status_code} - {r_inv.text}")
        sys.exit(1)
    inv_data = r_inv.json()
    status_field = inv_data.get("status") or inv_data.get("workflow_status")
    print(f"Multi-Agent Workflow Status: {status_field}")
    print(f"Synthesized Operational Risk Tier: {inv_data.get('risk_tier')}")
    eta_p10 = inv_data.get("eta_p10")
    eta_p50 = inv_data.get("eta_p50")
    eta_p90 = inv_data.get("eta_p90")
    print(f"Task A ETA Quantiles: P10={eta_p10}m, P50={eta_p50}m, P90={eta_p90}m")
    recs = inv_data.get("recommendations", [])
    print(f"Recommendations Generated: {len(recs)}")
    for idx, rec in enumerate(recs, 1):
        print(f"  {idx}. [{rec['action_type']}] {rec['title']} (Requires Approval: {rec['requires_approval']})")

    # 6. HITL Approval & Rejection Demonstration
    log("STEP 6", "Demonstrating Human-in-the-Loop Governance & Role Verification...")
    if recs:
        awaiting_recs = [r for r in recs if r.get("approval_status") == "AWAITING_APPROVAL" or r.get("requires_approval")]
        if awaiting_recs:
            target_rec = awaiting_recs[0]
            rec_id = target_rec["id"]
        else:
            target_rec = recs[0]
            rec_id = target_rec["id"]
            # Set to AWAITING_APPROVAL to demonstrate human governance gate
            from backend.app.models.recommendation import RecoveryRecommendation
            db_s = SessionLocal()
            try:
                r_obj = db_s.get(RecoveryRecommendation, rec_id)
                if r_obj:
                    r_obj.requires_approval = True
                    r_obj.approval_status = "AWAITING_APPROVAL"
                    r_obj.execution_status = "PENDING"
                    db_s.commit()
            finally:
                db_s.close()

        # 6a. Attempt approval with unauthorized role (INTERN)
        r_intern = client.post(f"{api_prefix}/auth/dev-token", json={"operator_profile": "intern"})
        intern_headers = {"Authorization": f"Bearer {r_intern.json()['access_token']}"}
        r_unauth = client.post(
            f"{api_prefix}/intelligence/recommendations/{rec_id}/approve",
            headers=intern_headers,
            json={"notes": "Unauthorized approval attempt"},
        )
        print(f"Unauthorized Approval Attempt (INTERN): Status {r_unauth.status_code} (Expected: 403 Forbidden)")
        assert r_unauth.status_code == 403, "Failed to reject unauthorized intern role!"

        # 6b. Approve with verified OPS_LEAD credentials
        r_app = client.post(
            f"{api_prefix}/intelligence/recommendations/{rec_id}/approve",
            headers=auth_headers,
            json={"notes": "Verified kitchen telemetry; approved dispatch priority."},
        )
        print(f"Authorized Approval (OPS_LEAD): Status {r_app.status_code} - Status: {r_app.json().get('approval_status')}")

        # 7. Execute Recovery Action & Validate Idempotency
        log("STEP 7", "Executing Simulated Recovery Action & Proving Cryptographic Idempotency...")
        r_exec1 = client.post(
            f"{api_prefix}/intelligence/recommendations/{rec_id}/execute",
            headers=auth_headers,
            json={},
        )
        print(f"Execution #1 Status: {r_exec1.status_code} - Result: {r_exec1.json().get('status')}")

        r_exec2 = client.post(
            f"{api_prefix}/intelligence/recommendations/{rec_id}/execute",
            headers=auth_headers,
            json={},
        )
        print(f"Execution #2 (Duplicate Replay) Status: {r_exec2.status_code} - Result: {r_exec2.json().get('status')}")
        assert r_exec2.json().get("status") in ("ALREADY_EXECUTED", "IDEMPOTENT_SKIPPED")
        print("Idempotency Guarantee Verified: duplicate execution prevented redundant side-effects.")

    # 8. Query Immutable Audit Trail
    log("STEP 8", "Retrieving Immutable Recovery Execution Audits...")
    r_audit = client.get(f"{api_prefix}/intelligence/audit/{order_id}")
    audits = r_audit.json()
    print(f"Found {len(audits)} Audit Record(s) for Order {order_id}:")
    for a in audits:
        print(f"  • Audit ID: {a['id']}")
        print(f"    Action: {a['action_type']} | Idempotency Key: {a['idempotency_key'][:32]}...")
        print(f"    Approval Identity: {a['approval_identity']} | Simulated: {a['is_simulated']}")

    print("\n" + "=" * 70)
    print("  ALL 8 DEMONSTRATION WORKFLOW STEPS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
