# Swiggy ResolveAI — Final Independent Remediation Audit
## Workstream 0: Comprehensive Repository Gap Analysis & Defect Catalog

- **Date**: November 18, 2026
- **Auditors**: Principal AI Platform Architect, Senior Backend Engineer, ML Platform Engineer, Application Security Engineer, QA Lead
- **Scope**: Complete audit of Phases 1–7 implementation against uploaded documentation, system code, models, tests, and operational requirements.

---

## 1. Executive Summary of Audit Findings

An exhaustive independent audit of the completed Phase 1–7 repository was conducted prior to any remediation modifications. The platform demonstrates sound modular architecture, functional ML inference pipelines (Task A Quantiles and Task C2 Calibrated Cancellation), robust LangGraph multi-agent orchestration, and comprehensive test coverage (177 tests passing).

However, rigorous verification against production-grade criteria revealed **11 specific technical and architectural findings** across security, API consistency, ML point-in-time validity, simulation economics, and audit immutability:

| Finding ID | Area | Title | Severity | Classification |
|---|---|---|---|---|
| **GAP-01** | Security / Auth | Client-Controlled `operator_identity` & `operator_role` in Approval Requests | **CRITICAL** | Partially Implemented |
| **GAP-02** | Governance / Safety | Missing Backend-Enforced Execution Modes (`SIMULATION`, `SHADOW`, `LIVE`) | **HIGH** | Missing |
| **GAP-03** | API Parity | API Documentation Route Divergence vs Registered FastAPI Schema | **HIGH** | Documentation Defect |
| **GAP-04** | ML Validity | Task A Static Order-Time Prediction vs Lifecycle Stage Dynamic Remaining ETA | **MEDIUM** | Implemented with Documented Limitation |
| **GAP-05** | ML Platform | Missing Runtime Feature Schema Parity & Drift Rejection Guard | **HIGH** | Partially Implemented |
| **GAP-06** | Agent / Recovery | Conflation of Simulated Execution Success with Business Recovery Outcome | **HIGH** | Partially Implemented |
| **GAP-07** | Simulation | Economic Net-Benefit Calculation Equates Gross Order Value to Net Profit | **HIGH** | Partially Implemented |
| **GAP-08** | Observability | Audit Table Lacks Explicit ORM-Level Immutability Enforcement | **MEDIUM** | Partially Implemented |
| **GAP-09** | Configuration | Environment Variable Inventory & Driver-Specific Pooling Divergence | **MEDIUM** | Partially Implemented |
| **GAP-10** | Runbook | Demo Runbook Contains Hardcoded Stale Timestamps and Path Mismatches | **MEDIUM** | Documentation Defect |
| **GAP-11** | Simulation | Absence of Parametric Sensitivity Analysis Across Conservative/Optimistic ROI | **MEDIUM** | Partially Implemented |

---

## 2. Detailed Findings Catalog

---

### GAP-01: Client-Controlled Operator Identity & Role in Sensitive Endpoints
- **Requirement**: Sensitive operational actions (approving high-sensitivity recommendations, executing recovery dispatches, resetting simulations) must derive operator identity and role strictly from cryptographically verified credentials (signed bearer tokens). Callers must never obtain elevated privileges (`OPS_LEAD`, `ADMIN`) simply by submitting a string in the JSON payload.
- **Reported Implementation**: Phase 4 and Phase 7 reports claimed strict Role-Based Access Control (RBAC) enforced by `PolicyEngine.check_operator_authorization`.
- **Actual Code Evidence**:
  In `backend/app/schemas/intelligence.py`:
  ```python
  class ApprovalRequest(BaseModel):
      operator_identity: str = Field(default="ops_admin")
      operator_role: Optional[str] = Field(default="OPS_LEAD")
  ```
  In `backend/app/api/routes/intelligence.py` (`approve_recommendation` and `execute_recommendation`), the endpoint accepted `operator_identity` and `operator_role` directly from `payload.operator_identity` and `payload.operator_role`. Any unauthenticated caller could bypass RBAC by supplying `"operator_role": "ADMIN"`.
- **Relevant Files**: `backend/app/api/routes/intelligence.py`, `backend/app/schemas/intelligence.py`, `backend/app/services/policy_engine.py`
- **Severity**: **CRITICAL**
- **Classification**: **Partially Implemented**
- **Required Correction**:
  1. Implement a signed bearer token verification module (`backend/app/core/auth.py`) using HMAC-SHA256 JWT format with signature, expiration, issuer, and audience validation.
  2. Implement FastAPI security dependency `require_roles(["OPS_LEAD", "ADMIN"])`.
  3. Resolve operator identity and role strictly from verified token claims.
  4. In `ENVIRONMENT=development`, provide an explicit, gated development token generation endpoint (`/api/v1/auth/dev-token`) with automated tests proving it is strictly disabled in `staging` and `production`.
- **Verification Test**: `test_unauthenticated_approval_rejected`, `test_client_cannot_spoof_ops_lead_via_body`, `test_dev_token_disabled_in_staging`.

---

### GAP-02: Missing Backend-Enforced Execution Modes (`SIMULATION`, `SHADOW`, `LIVE`)
- **Requirement**: The system must enforce explicit execution modes:
  - `SIMULATION`: Default mode for demonstrations and synthetic evaluation.
  - `SHADOW`: Ingests and investigates real/production telemetry passively; produces recommendations and audits in read-only mode; strictly blocks any recovery execution requests.
  - `LIVE`: Customer-facing dispatch; must remain disabled and reject any execution attempt.
- **Reported Implementation**: Phase 6 and Phase 7 reports stated the platform operates in simulated recovery mode without live Swiggy dispatches.
- **Actual Code Evidence**:
  `Settings` in `backend/app/core/config.py` does not define `EXECUTION_MODE`. `RecoveryExecutionService` does not check execution mode prior to action execution.
- **Relevant Files**: `backend/app/core/config.py`, `backend/app/services/recovery_executor.py`
- **Severity**: **HIGH**
- **Classification**: **Missing**
- **Required Correction**:
  1. Add `EXECUTION_MODE: str = "SIMULATION"` in `Settings` with strict validator (`{"SIMULATION", "SHADOW", "LIVE"}`).
  2. In `RecoveryExecutionService.execute_recommendation`, enforce mode checks: reject execution in `SHADOW` mode (`403 Forbidden` / `PermissionError`), raise fatal configuration error if `LIVE` is attempted.
  3. Add regression tests validating execution mode safety.
- **Verification Test**: `test_shadow_mode_rejects_execution`, `test_live_mode_remains_disabled`, `test_invalid_execution_mode_rejected`.

---

### GAP-03: API Documentation Route Divergence vs Registered FastAPI Schema
- **Requirement**: `docs/api_reference.md` must accurately reflect 100% of registered FastAPI endpoints, exact HTTP methods, URL paths, and schemas without documenting phantom routes or omitting public endpoints.
- **Reported Implementation**: Documented 33 endpoints including `/health`, `/api/v1/ingestion/events`, `/simulation/reset`, `/simulation/bootstrap/evaluate`, and `/models/status`.
- **Actual Code Evidence**:
  Actual routes registered on `FastAPI.routes`:
  - Registered health routes are `/api/v1/health`, `/api/v1/health/live`, `/api/v1/health/ready`.
  - Registered event ingestion route is `/api/v1/simulation/events`.
  - Routes `/simulation/reset`, `/simulation/bootstrap/evaluate`, and `/models/status` were not registered on the router.
  - Omitted registered routes included `GET /api/v1/ingest/status`, `POST /api/v1/ingest/orders/history`, `POST /api/v1/ingest/restaurants`, `GET /api/v1/orders/metrics`, `GET /api/v1/orders/{id}/events`, `GET /api/v1/intelligence/orders/{id}/latest`, `GET /api/v1/intelligence/ml-audits/{id}`, `POST /api/v1/simulation/generate`, `GET /api/v1/simulation/experiments/actions/effectiveness`, `POST /api/v1/simulation/experiments/stress-test`.
- **Relevant Files**: `backend/app/api/router.py`, `backend/app/main.py`, `docs/api_reference.md`
- **Severity**: **HIGH**
- **Classification**: **Documentation Defect**
- **Required Correction**:
  1. Author an automated test (`backend/tests/test_api_contract_reconciliation.py`) comparing the OpenAPI registered route catalog directly against documentation.
  2. Mount health router at both `/health` and `/api/v1/health` for standard container probe interoperability.
  3. Rewrite `docs/api_reference.md` to reflect the exact 33 registered endpoints with their schemas.
- **Verification Test**: `test_openapi_catalog_matches_registered_routes`.

---

### GAP-04: Task A Static Order-Time Prediction vs Lifecycle Stage Dynamic Remaining ETA
- **Requirement**: Clarify whether Task A provides dynamic stage-specific remaining delivery duration (recalculated at allotment, pickup, transit) or static order-time delivery duration.
- **Reported Implementation**: Phase 2.1 problem definition discussed multiple prediction stages ($t_0$, $t_{\text{allot}}$, $t_{\text{pickup}}$), while Phase 2.5 trained an order-time quantile regression model.
- **Actual Code Evidence**:
  In `backend/app/services/ml_inference.py`, `predict_task_a` takes 16 order-time features (`last_mile_distance`, `order_hour`, `rolling_order_volume_15m`, etc.) and predicts total delivery duration from placement.
  The underlying Kaggle historical dataset (`Rider-Info.csv`) lacks intermediate telematics timestamps (granular pickup confirmations are missing in 40%+ rows; live GPS transit points do not exist). Training intermediate remaining-time models on this dataset without telemetry leads to severe target leakage and synthetic distortions.
- **Relevant Files**: `backend/app/services/ml_inference.py`, `backend/app/agents/order_intelligence.py`, `docs/ml_point_in_time_and_dynamic_eta_review.md`
- **Severity**: **MEDIUM**
- **Classification**: **Implemented with Documented Limitation**
- **Required Correction**:
  1. Formally retain the approved order-time quantile regression model.
  2. Document the exact missing historical data required for intermediate stage modeling in `docs/ml_point_in_time_and_dynamic_eta_review.md`.
  3. Ensure no model output is deceptively presented as a dynamic remaining-time prediction.
- **Verification Test**: `test_task_a_order_time_prediction_integrity`.

---

### GAP-05: Missing Runtime Feature Schema Parity & Drift Rejection Guard
- **Requirement**: `MLInferenceService` must enforce strict feature schema parity, ensuring that input feature names, types, order, and imputation statistics match the fitted training schema. Incompatible feature sets must be explicitly rejected rather than silently executing corrupted predictions.
- **Reported Implementation**: Phase 2.2.1 and Phase 2.5 reported fitted training parameters (e.g. median imputation of 2.67 km for `last_mile_distance`).
- **Actual Code Evidence**:
  `MLInferenceService` relied on hardcoded `DEFAULT_ORDER_FEATURES` dictionary lookups without verifying metadata schema consistency or rejecting malformed input feature DataFrames.
- **Relevant Files**: `backend/app/services/ml_inference.py`, `data/artifacts/models/phase_2_5/registry.json`
- **Severity**: **HIGH**
- **Classification**: **Partially Implemented**
- **Required Correction**:
  1. Add strict feature schema verification in `MLInferenceService` comparing extracted features against `task_a_cfg.feature_columns` and `task_c2_cfg.feature_columns`.
  2. Reject inference with descriptive error if required features are missing or corrupted.
  3. Add regression tests validating feature order and schema drift rejection.
- **Verification Test**: `test_feature_schema_parity_and_ordering`, `test_incompatible_feature_schema_rejected`.

---

### GAP-06: Conflation of Simulated Execution Success with Delivery Recovery Outcome
- **Requirement**: An execution audit record marking `recovery_outcome: "SUCCESS"` indicates that the simulated executor dispatched the action successfully. It must NOT imply that the order was actually recovered or delivered on time.
- **Reported Implementation**: Phase 4 and Phase 6 logged `RecoveryExecutionAudit` with `recovery_outcome = "SUCCESS"`.
- **Actual Code Evidence**:
  In `RecoveryExecutionService.execute_recommendation`:
  ```python
  audit = RecoveryExecutionAudit(
      ...
      recovery_outcome="SUCCESS",
      ...
  )
  ```
  The field `recovery_outcome` defaults to `"SUCCESS"` upon executor completion, conflating simulated execution dispatch status with actual observed delivery recovery.
- **Relevant Files**: `backend/app/models/audit.py`, `backend/app/services/recovery_executor.py`
- **Severity**: **HIGH**
- **Classification**: **Partially Implemented**
- **Required Correction**:
  1. Clarify audit schema semantics: `execution_status = "EXECUTED_SIMULATED"`, `recovery_outcome = "ACTION_DISPATCHED"`.
  2. Document in `docs/system_architecture.md` and `docs/api_reference.md` that dispatch success is distinct from observed delivery delay recovery.
- **Verification Test**: `test_execution_status_distinct_from_business_recovery`.

---

### GAP-07: Economic Net-Benefit Calculation Equates Gross Order Value to Net Profit
- **Requirement**: Economic ROI in Phase 5 simulation must model Swiggy platform economics realistically by applying a contribution margin (e.g., 20% commission on Gross Order Value) and factoring in intervention costs, rather than equating 100% of Gross Order Value to lost platform profit upon cancellation.
- **Reported Implementation**: Phase 5 report claimed net economic benefit calculation.
- **Actual Code Evidence**:
  In `backend/app/simulation/kpi_calculator.py`:
  ```python
  losses_avoided = cancellations_prevented * config.gross_order_value_inr
  net_benefit = losses_avoided - total_cost
  ```
  If an order has GOV ₹450, Swiggy's revenue is ~₹90 (20% take rate). Equating ₹450 directly to platform profit overstates baseline financial losses by ~5x.
- **Relevant Files**: `backend/app/simulation/advanced_engine.py`, `backend/app/simulation/kpi_calculator.py`
- **Severity**: **HIGH**
- **Classification**: **Partially Implemented**
- **Required Correction**:
  1. Add `contribution_margin_ratio: float = 0.20` in `SimulationConfig`.
  2. Update `KPICalculator.calculate_strategy_kpis` to compute:
     - `recovered_contribution_inr = cancellations_prevented * config.gross_order_value_inr * config.contribution_margin_ratio`
     - `net_simulated_operational_benefit_inr = recovered_contribution_inr - total_cost`
  3. Include parametric sensitivity analysis (conservative 15%, base 20%, optimistic 25% margin) in `docs/simulation_methodology_and_roi_audit.md`.
- **Verification Test**: `test_economic_kpi_contribution_margin_accounting`.

---

### GAP-08: Audit Table Lacks Explicit ORM-Level Immutability Enforcement
- **Requirement**: `RecoveryExecutionAudit` records must be strictly append-only. Application code must be prevented from updating or deleting historical audit records.
- **Reported Implementation**: Phase 4 and Phase 6 described recovery audits as immutable.
- **Actual Code Evidence**:
  In `backend/app/models/audit.py`, `RecoveryExecutionAudit` has a unique constraint on `idempotency_key`, but lacks ORM-level event interceptors blocking `UPDATE` and `DELETE` operations.
- **Relevant Files**: `backend/app/models/audit.py`
- **Severity**: **MEDIUM**
- **Classification**: **Partially Implemented**
- **Required Correction**:
  Attach SQLAlchemy `before_update` and `before_delete` event listeners to `RecoveryExecutionAudit` raising `PermissionError("RecoveryExecutionAudit records are immutable and cannot be modified or deleted.")`.
- **Verification Test**: `test_audit_records_cannot_be_updated_or_deleted`.

---

### GAP-09: Environment Variable Inventory & Driver-Specific Pooling Divergence
- **Requirement**: All environment variables used across backend, frontend, and Docker Compose must be documented, reconciled, and validated in Pydantic settings.
- **Reported Implementation**: Phase 6 reported a 20-variable inventory in `docs/environment_configuration_guide.md`.
- **Actual Code Evidence**:
  `EXECUTION_MODE` and authentication secrets (`AUTH_SECRET_KEY`) were missing from `backend/.env.example` and `config.py`.
- **Relevant Files**: `backend/.env.example`, `backend/app/core/config.py`, `docs/environment_configuration_guide.md`
- **Severity**: **MEDIUM**
- **Classification**: **Partially Implemented**
- **Required Correction**:
  Reconcile `Settings` class with `backend/.env.example`, add `EXECUTION_MODE`, `AUTH_SECRET_KEY`, `AUTH_TOKEN_EXPIRE_MINUTES`.
- **Verification Test**: `test_environment_settings_reconciliation`.

---

### GAP-10: Demo Runbook Contains Hardcoded Stale Timestamps and Path Mismatches
- **Requirement**: `docs/demo_runbook.md` must provide working, reproducible demonstration instructions with live relative timestamps, actual registered endpoint paths, and valid schemas.
- **Reported Implementation**: Phase 7 demo runbook was drafted.
- **Actual Code Evidence**:
  The runbook contained fixed ISO timestamps from past dates and referenced `/api/v1/ingestion/events` instead of `/api/v1/simulation/events`.
- **Relevant Files**: `docs/demo_runbook.md`
- **Severity**: **MEDIUM**
- **Classification**: **Documentation Defect**
- **Required Correction**:
  1. Author a standalone automated demo runner script (`scripts/demo_runner.py`).
  2. Update `docs/demo_runbook.md` with correct paths, dynamic timestamps, and authentication headers.
- **Verification Test**: `test_demo_runbook_commands_execute_cleanly`.

---

### GAP-11: Absence of Parametric Sensitivity Analysis Across Conservative/Optimistic ROI
- **Requirement**: Business ROI claims must be accompanied by sensitivity analysis testing varying merchant compliance (kitchen time saved), courier acceptance rates, and contribution margins.
- **Reported Implementation**: Phase 5 provided single point-estimate simulation results.
- **Actual Code Evidence**:
  `advanced_engine.py` evaluated a single default configuration without exposing a multi-scenario sensitivity sweep.
- **Relevant Files**: `backend/app/simulation/advanced_engine.py`, `docs/simulation_methodology_and_roi_audit.md`
- **Severity**: **MEDIUM**
- **Classification**: **Partially Implemented**
- **Required Correction**:
  Implement sensitivity analysis in `docs/simulation_methodology_and_roi_audit.md` comparing conservative, base, and optimistic scenarios.
- **Verification Test**: `test_simulation_sensitivity_sweep`.

---

## 3. Remediation Roadmap & Workstream Sequencing

Following the prompt's mandated execution order:
1. **Workstream 1 (P0)**: Fix GAP-01 (Authentication & RBAC trust boundary) and GAP-02 (Backend execution modes `SIMULATION`, `SHADOW`, `LIVE`).
2. **Workstream 2 (P1)**: Fix GAP-03 (API catalog reconciliation), GAP-09 (Environment settings), and GAP-10 (Demo runbook & script).
3. **Workstream 3 (P1)**: Fix GAP-04 (ML dynamic ETA clarification) and GAP-05 (Runtime feature schema parity & drift rejection).
4. **Workstream 4 (P2)**: Fix GAP-06 (Separate execution dispatch from business recovery outcome) and GAP-08 (Audit immutability ORM listeners).
5. **Workstream 5 (P2)**: Fix GAP-07 (Contribution margin economic modeling) and GAP-11 (Simulation sensitivity analysis).
6. **Workstream 6 & 7 (P3)**: Final end-to-end regression and documentation deliverables.
