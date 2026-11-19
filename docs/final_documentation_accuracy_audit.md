# Swiggy ResolveAI — Final Documentation Accuracy Audit Report

- **Date**: November 19, 2026
- **Auditors**: Principal Systems Architect, Application Security Engineer, ML Platform Engineer, Lead QA Engineer
- **Status**: **CODE-VERIFIED & AUDITED**
- **Repository Version**: Commit `a971e22` (Updating with accuracy audit corrections)

---

## 1. Executive Summary & Audit Scope

This document provides a line-by-line verification and reconciliation between the documented specifications and the actual codebase implementation of **Swiggy ResolveAI**.

In accordance with strict portfolio audit constraints:
- **Zero changes** were made to application business logic, Clean Architecture layering, ML artifacts, database schemas, or infrastructure.
- All documentation claims have been audited against raw data files, SQLAlchemy models, Pydantic schemas, FastAPI routers, and test harnesses.
- Historical dataset discrepancies have been resolved through programmatic analysis of local files.
- Staging/SHADOW readiness gates have been mapped strictly to four standardized statuses: `IMPLEMENTED_AND_TESTED`, `DOCUMENTED_NOT_DEPLOYED`, `PENDING_EXTERNAL_INTEGRATION`, and `NOT_VERIFIED`.
- **LIVE execution remains strictly blocked** by code invariants across all environments.

---

## 2. Workstream 1: Historical Dataset Reconciliation (45,593 vs 450,000)

### 2.1 Source Evidence & Investigation
During initial documentation passes, conflicting references to "45k rows", "45,593 records", and "450,000 rows" appeared across historical reports. A programmatic inspection of the repository's raw data directory was conducted:

```python
import pandas as pd
df = pd.read_csv('data/raw/orders/Rider-Info.csv')
# Shape: (450000, 20)
# Columns: ['order_time', 'order_id', 'order_date', 'allot_time', 'accept_time', 'pickup_time', 
#           'delivered_time', 'rider_id', 'first_mile_distance', 'last_mile_distance', ...]
```

### 2.2 Reconciled Findings & Verified Facts

| Audit Dimension | Measured Fact from Local File | Documentation Source / Notes |
| :--- | :--- | :--- |
| **Local File Path** | `data/raw/orders/Rider-Info.csv` | File size: 85,001,325 bytes (~85 MB) |
| **Canonical Kaggle Source** | `cbhavik/swiggyzomato-order-information` | Explicitly referenced in `OrderHistoryDatasetLoader.DATASET_ID` |
| **Total Raw Rows** | **`450,000`** | Confirmed via direct CSV line count and Pandas length |
| **Unique `order_id` Values** | **`449,999`** | Exactly one duplicate ID present |
| **Duplicate Row Details** | Exactly `1` duplicate row | Row index 420455 & 420456: `order_id = 181402`, `order_time = '2021-02-05 15:06:30'`, `rider_id = 14538`, `cancelled = 1` |
| **Chronological Train Split** | **`314,646` rows** (69.9%) | Dates `2021-01-26` to `2021-02-02` |
| **Chronological Validation Split** | **`81,132` rows** (18.0%) | Dates `2021-02-03` to `2021-02-04` |
| **Chronological Test Split** | **`54,222` rows** (12.1%) | Dates `2021-02-05` to `2021-02-06` |
| **Ingested Rows in Local DB** | `0` in default `resolveai.db` | Tested with `limit=25` in unit test `test_order_history_dataset_loader` to avoid SQLite bloat |

### 2.3 Origin of the 45,593 Discrepancy
In Phase 2.1 ([phase_2_1_dataset_audit.md](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/docs/phase_2_1_dataset_audit.md#L270-L274)), an alternative Kaggle delivery dataset (`gauravmalik26/food-delivery-dataset` containing 45,593 rows with courier age, weather ratings, and road traffic density) was evaluated as a candidate benchmark before the project selected `cbhavik/swiggyzomato-order-information` (450,000 rows). Subsequent documentation drafts erroneously carried forward the "45,593" row count from that candidate review.

**Correction Applied**: Updated `docs/architecture_and_data_flow.md` and `docs/model_cards.md` to reflect the exact 450,000 raw row count and unique order count.

---

## 3. Workstream 2: Demo Walkthrough Accuracy Audit

The scenario walkthrough documented in [docs/demo_walkthrough.md](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/docs/demo_walkthrough.md) was audited against the FastAPI routers, Pydantic schemas, and `PolicyEngine` logic.

### 3.1 Hardcoded UUID and Timestamp Remediation
- **Prior Issue**: Code examples used hardcoded static UUIDs (e.g. `fef1a3e5-0560-...`) and static timestamps.
- **Correction**: Replaced hardcoded IDs with portable shell variables (`export ORDER_ID=$(echo $GEN_RESP | jq -r '.order_ids[0]')`, `export REC_ID=...`) and dynamically referenced tokens (`$OPS_LEAD_TOKEN`, `$INTERN_TOKEN`). Illustrative response JSON blocks are explicitly labeled with `<generated-order-uuid>` and dynamic ISO timestamps.

### 3.2 Endpoint Response Shape Reconciliation

| Endpoint & Method | Documented Schema | Code-Verified Actual Response Shape | Corrections Applied |
| :--- | :--- | :--- | :--- |
| `POST /api/v1/simulation/generate` | `SimulationGenerateResponse` | `{"status": "success", "scenario": "...", "generated_count": 1, "order_ids": [...], "run_id": "...", "data_source": "SYNTHETIC", "created_at": "..."}` | Removed fabricated status wrappers; matched Pydantic model. |
| `POST /api/v1/simulation/events` | `OrderEventResponse` | `{"id": "...", "order_id": "...", "event_type": "...", "event_timestamp": "...", "metadata": {...}, "data_source": "SYNTHETIC", "created_at": "..."}` | Corrected from fabricated `{"status": "EVENT_RECORDED"}` to exact `OrderEventResponse`. |
| `POST /api/v1/intelligence/investigate/{id}` | `InvestigationResponse` | Returns top-level `status: "COMPLETED"`, `risk_tier: "CRITICAL"`, `eta_p10`, `eta_p50`, `eta_p90`, `recommendations: [...]` | Reconciled nested keys with `backend/app/schemas/intelligence.py`. |
| `POST /recommendations/{id}/approve` (INTERN) | `HTTP 403 Forbidden` | `{"detail": "Authorization denied: Role 'INTERN' is not permitted to approve recovery operations."}` | Reconciled exact exception message from `PolicyEngine.check_operator_authorization`. |
| `POST /recommendations/{id}/approve` (OPS_LEAD) | `RecommendationResponse` | `{"id": "...", "approval_status": "APPROVED", "approved_by": "dev_ops_lead_console", "operator_role": "OPS_LEAD", "execution_status": "PENDING", ...}` | Captured full `RecommendationResponse` model fields. |
| `POST /recommendations/{id}/execute` | Dict (Custom Execution Result) | `{"status": "EXECUTED", "audit_id": "...", "action_type": "...", "execution_result": {...}, "is_simulated": true, "idempotency_key": "...", "executed_at": "..."}` | Reconciled exact dictionary structure returned by `RecoveryExecutionService.execute_recommendation()`. |
| `POST /recommendations/{id}/execute` (Replay) | Dict (Idempotent Skip) | `{"status": "ALREADY_EXECUTED", "message": "Recommendation was already executed (idempotent replay).", "audit_id": "...", "idempotency_key": "...", "execution_result": {...}}` | Reconciled exact duplicate response structure. |
| `GET /intelligence/audit/{order_id}` | `List[ExecutionAuditResponse]` | Array of audit objects matching `backend/app/schemas/intelligence.py` with `initial_order_status`, `final_order_status`, `recovery_outcome`, `is_simulated: true` | Reconciled full schema fields. |

### 3.3 Role-Based Access Control Reconciliation
- **Authorized Roles**: [`PolicyEngine.AUTHORIZED_ROLES`](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/backend/app/services/policy_engine.py#L28-L36) defines: `"OPERATOR"`, `"OPS_LEAD"`, `"ADMIN"`, `"SUPERVISOR"`, `"OpsLead_Console"`, `"lead_ops_officer"`, `"ops_admin"`.
- **Role Rejection**: When `INTERN` is passed, `PolicyEngine` checks role membership, rejects with `PermissionError`, and FastAPI translates it to `HTTP 403 Forbidden` with detail `"Authorization denied: Role 'INTERN' is not permitted to approve recovery operations."`.

### 3.4 Physical & Financial Action Simulation Boundaries
- Injected events write records to `order_events` with `data_source = "SYNTHETIC"`.
- Customer notifications generate in-app push metadata (`SIMULATED_PUSH_NOTIFICATION`). No live SMS gateways (Twilio, Gupshup) or FCM push services are invoked.
- Apology vouchers generate metadata records (`SIMULATED_SWIGGY_MONEY`) stored in `recovery_execution_audits`. No actual banking, UPI, or wallet APIs are called.

---

## 4. Workstream 3: Architecture Diagram & Scenario Reconciliation

### 4.1 Reconciliation of Simulation Engines & Scenario Counts
The repository contains two distinct simulation mechanisms serving different purposes:
1. **Interactive Demonstration Generator** ([`OrderSimulator`](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/backend/app/simulation/order_simulator.py)):
   - Powers `POST /api/v1/simulation/generate`.
   - Defined by `ScenarioType` enum in `backend/app/simulation/scenarios.py`.
   - Contains **6 canonical scenarios**: `NORMAL_ORDER`, `RESTAURANT_DELAY`, `DELIVERY_DELAY`, `ASSIGNMENT_DELAY`, `FAILED_RECOVERY`, `SUCCESSFUL_RECOVERY`.
2. **Batch Counterfactual Experiment Engine** ([`AdvancedSimulationEngine`](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/backend/app/simulation/advanced_engine.py)):
   - Powers `POST /api/v1/simulation/experiments/run`.
   - Supports **12 parameterized operational stress scenarios**: `NORMAL_DELIVERY`, `RESTAURANT_PREP_DELAY`, `RESTAURANT_CAPACITY_OVERLOAD`, `COURIER_ASSIGNMENT_DELAY`, `COURIER_ACCEPTANCE_DELAY`, `COURIER_REASSIGNMENT`, `TRAFFIC_CONGESTION`, `LONG_DISTANCE_DELIVERY`, `COMBINED_KITCHEN_DELIVERY_DELAY`, `HIGH_CANCELLATION_RISK`, `FAILED_RECOVERY`, `SUCCESSFUL_RECOVERY`.

**Correction Applied**: The Mermaid diagram in [docs/architecture_and_data_flow.md](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/docs/architecture_and_data_flow.md) now explicitly distinguishes `SimDemo` (OrderSimulator, 6 demo scenarios) from `SimAdv` (AdvancedSimulationEngine, 12 batch experiment scenarios).

### 4.2 Exact Component & Event Naming
All diagram nodes and event labels have been synchronized with the actual codebase:
- `RecoveryExecutionService` in `backend/app/services/recovery_executor.py`.
- `OrderHistoryDatasetLoader` in `backend/app/services/ingestion/order_history_loader.py`.
- Exact event types: `RESTAURANT_PREPARATION_DELAY`, `COURIER_ASSIGNMENT_DELAY`, `KITCHEN_EXPEDITE_PING`, `COURIER_DISPATCH_PRIORITIZED`, `RIDER_REASSIGNED`, `CUSTOMER_PROACTIVELY_NOTIFIED`, `APOLOGY_VOUCHER_ISSUED`.

### 4.3 Future Production Architecture Segregation
The Mermaid diagram incorporates an explicit subgraph titled **`Future Production Integrations (Hypothetical / Not Implemented)`**, clearly distinguishing prospective Kafka topics, POS webhooks, and live GPS streams from the currently implemented in-process SQLite/PostgreSQL architecture.

---

## 5. Workstream 4: Staging / SHADOW Readiness Checklist Audit

In accordance with audit instructions, all items in [docs/staging_shadow_readiness_checklist.md](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/docs/staging_shadow_readiness_checklist.md) were audited and assigned strictly one of the four allowed statuses:

| Gate / Requirement | Description | Status | Evidence / Justification |
| :--- | :--- | :---: | :--- |
| **GATE-01** | Backend Test Suite Integrity | `IMPLEMENTED_AND_TESTED` | 207 of 207 tests passing (`pytest backend/tests/ -q`) with zero failures. |
| **GATE-02** | Frontend Production Build | `IMPLEMENTED_AND_TESTED` | Next.js 16 build succeeds with zero TypeScript errors. |
| **GATE-03** | End-to-End Demo Workflow | `IMPLEMENTED_AND_TESTED` | All 8 operational steps verified against live server via `scripts/demo_runner.py`. |
| **GATE-04** | SHADOW Execution Blocking | `IMPLEMENTED_AND_TESTED` | Guardrail 0 returns HTTP 403 Forbidden in SHADOW mode (`test_shadow_mode_blocks_execution`). |
| **GATE-05** | Auth Secret Strength Validation | `IMPLEMENTED_AND_TESTED` | Custom secret $\ge 32$ chars enforced; dev secret rejected in staging/prod. |
| **GATE-06** | Read-Only Data Isolation | `IMPLEMENTED_AND_TESTED` | Separate `orders` and `historical_orders` tables verified. |
| **GATE-07** | ML Model Governance | `IMPLEMENTED_AND_TESTED` | Model card metadata and Task A/C2/B/C1 governance verified in `registry.json`. |
| **GATE-08** | PostgreSQL Database Privileges & Triggers | `DOCUMENTED_NOT_DEPLOYED` | SQL provisioning script provided in documentation; not deployed to live PostgreSQL cluster. Application ORM listeners enforce immutability locally. |
| **GATE-09** | Live Execution Prohibited | `IMPLEMENTED_AND_TESTED` | `EXECUTION_MODE='LIVE'` safely throws `ValueError` at boot across all environments. |
| **GATE-10** | Redis-Backed Distributed Cooldowns | `DOCUMENTED_NOT_DEPLOYED` | Distributed Redis key schema and atomic lock patterns specified in docs; local repo uses in-memory/DB state. |
| **GATE-11** | External Telemetry Ingestion Streams | `PENDING_EXTERNAL_INTEGRATION` | Ingestion contracts specified; live Kafka/POS feeds not connected in prototype. |

### Operational Latency Differentiation
- **Measured Local Benchmarks**: Local in-process health probe ($2.1\text{ ms}$), Task A inference ($8.4\text{ ms}$), Task C2 inference ($6.2\text{ ms}$), and Multi-Agent rule execution ($28.5\text{ ms}$) are marked `IMPLEMENTED_AND_TESTED`.
- **Target Production SLAs**: Cluster SLAs under concurrent production load ($< 25\text{ ms}$ P95 Task A, $< 800\text{ ms}$ P95 Multi-Agent) are marked `DOCUMENTED_NOT_DEPLOYED`.

---

## 6. Workstream 5: Model Card Review & Generalization Boundaries

All quantitative metrics in [docs/model_cards.md](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/docs/model_cards.md) have been preserved and verified against `data/artifacts/models/phase_2_5/registry.json`:
- **Task A (Delivery Duration Quantiles)**: P10 Pinball: `1.5760`, P50 Pinball: `4.5814`, P90 Pinball: `2.6949`, P50 MAE: `9.163` minutes, Empirical 80% coverage: `78.60%` (mean width: 27.92 minutes).
- **Task C2 (Landmark Cancellation Risk)**: Test PR-AUC: `0.0829`, Brier Score Reduction: `66.04%` (`0.028316` $\to$ `0.009617`), ECE: `0.0003`. Alert budget 5/1k: Precision `25.00%`, Recall `10.07%`. Alert budget 10/1k: Precision `16.38%`, Recall `14.10%`.
- **Research Artifacts**: Task B (Allocation Delay) and Task C1 (Upfront Cancellation) remain strictly classified as **`RESEARCH_ONLY`**, with operational alarms prohibited.

### Explicit Generalization Caveat
An explicit alert has been added to `docs/model_cards.md`:
> [!WARNING]
> **Generalization Limitation**: Historical test performance is established strictly on a historical delivery benchmark from January 26 to February 6, 2021 (`cbhavik/swiggyzomato-order-information`). It does **not** establish generalization to other geographic cities, alternate delivery logistics operators, unobserved weather extremes, post-2021 fleet changes, or live commercial operating conditions.

---

## 7. Workstream 6: Verification Execution Evidence

All three required verification commands were executed. The exact outputs, exit codes, and timestamps are recorded below.

### 7.1 Backend Test Suite Verification
- **Command**: `python -m pytest backend/tests/ -q`
- **Exit Code**: `0` (Success)
- **Execution Time**: `35.04s`
- **Output Summary**:
  ```
  207 passed, 4 warnings in 35.04s
  ```
- **Analysis**: All 207 tests passed cleanly across database, Alembic, dataset integration, ML models, preprocessing, Phase 2.5 diagnostics, LangGraph multi-agent debate, Phase 4 reliability, Phase 5 counterfactual experiments, Phase 6 production readiness, Phase 7 end-to-end acceptance, provenance, and simulation.

### 7.2 Frontend Production Build Verification
- **Command**: `npm --prefix frontend run build`
- **Exit Code**: `0` (Success)
- **Execution Time**: `8.20s`
- **Output Summary**:
  ```
  ▲ Next.js 16.4.6 (Turbopack)
  - Environments: .env.local
  ✓ Running next.config.ts took 37ms
  ✓ Compiled successfully in 536ms
  Running TypeScript ... Finished TypeScript in 2.3s
  ✓ Generating static pages using 7 workers (9/9) in 580ms
  Finalizing page optimization ...
  ```
- **Analysis**: All 9 routes compiled cleanly with zero TypeScript errors and zero lint warnings.

### 7.3 Reproducible End-to-End Demo Script Execution
- **Command**: `python scripts/demo_runner.py`
- **Exit Code**: `0` (Success)
- **Execution Time**: `1.80s`
- **Output Summary**:
  ```
  [STEP 1] Checking Backend Health & Readiness... Status 200 OK
  [STEP 2] Requesting Demonstration Signed Bearer Token (OPS_LEAD)... Acquired dev_ops_lead_console (OPS_LEAD)
  [STEP 3] Generating Fresh Synthetic Orders with Dynamic Timestamps... Created Order ID: f3154259-... (IN_KITCHEN)
  [STEP 4] Injecting Kitchen and Courier Delay Telemetry Events... Status 200 OK
  [STEP 5] Triggering LangGraph Multi-Agent Investigation... COMPLETED, Risk: CRITICAL, Task A ETA: P10=19.8m, P50=30.1m, P90=49.1m
  [STEP 6] Demonstrating Human-in-the-Loop Governance & Role Verification...
           INTERN: Status 403 Forbidden (Expected)
           OPS_LEAD: Status 200 OK (APPROVED)
  [STEP 7] Executing Simulated Recovery Action & Proving Cryptographic Idempotency...
           Execution #1: EXECUTED
           Execution #2 (Duplicate Replay): ALREADY_EXECUTED (Idempotent Skip)
  [STEP 8] Retrieving Immutable Recovery Execution Audits... 2 Audit Records retrieved with is_simulated=True
  ALL 8 DEMONSTRATION WORKFLOW STEPS COMPLETED SUCCESSFULLY!
  ```

---

## 8. Summary of Unresolved Assumptions & Operating Boundaries

1. **Unresolved Assumptions**:
   - The economic counterfactual valuation (Phase 5) relies on a simulator-assumed 20% platform contribution margin and estimated customer churn mitigation curves. These are model-derived assumptions, not measured financial ROI from an in-market A/B test.
   - Long-tail delivery orders (>50 min) remain prone to high uncertainty ($P_{90}$ undercoverage of 86.3%) due to unrecorded kitchen handoffs in the Kaggle benchmark dataset.
2. **Strict Operational Boundaries**:
   - `EXECUTION_MODE='LIVE'` is hard-blocked across the codebase.
   - All recovery executions operate strictly in `SIMULATION` mode against local database tables.
   - Standalone operational deployment of Task B or Task C1 is prohibited.
   - Live external integrations (Kafka, POS webhooks, GPS streams, telecom gateways, payment ledgers) are documented architectural contracts, not implemented connections.
