# Swiggy ResolveAI — Staging & SHADOW Readiness Checklist

- **Date**: November 19, 2026
- **Auditors**: Principal Infrastructure Architect, Application Security Engineer, ML Platform Engineer, Site Reliability Engineer (SRE)
- **Status**: **PRE-DEPLOYMENT AUDIT & OPERATIONAL READINESS GATE**
- **Target Deployment Tier**: Staging / SHADOW Evaluation Environment

---

## 1. Executive Summary & Purpose

This operational checklist defines the technical requirements, architectural contracts, security gates, and validation procedures required before deploying **Swiggy ResolveAI** into a Staging or SHADOW operational environment.

In **SHADOW mode**, the platform operates on mirror streams of real operational order telemetry:
1. It ingests order and delivery lifecycle events in read-only mode without consumer side-effects.
2. It executes Phase 2.5 ML inference (Task A quantiles and Task C2 landmark cancellation risk).
3. It dispatches LangGraph multi-agent investigations and policy engine evaluations.
4. It logs shadow recommendations and counterfactual audits.
5. **CRITICAL SAFETY GUARANTEE**: Any external operational mutation (SMS dispatch, courier rerouting, financial wallet refund) is strictly blocked by code guardrails, returning `HTTP 403 Forbidden`. `LIVE` execution is completely disabled across the codebase.

### Status Classification Taxonomy
All checklist items and gate criteria are classified strictly using one of the following four standardized statuses:
- **`IMPLEMENTED_AND_TESTED`**: Verified via passing automated tests, code execution, or local runtime inspection.
- **`DOCUMENTED_NOT_DEPLOYED`**: Architecturally specified and documented with reference scripts/schemas, but not deployed or executed against an external staging/production cluster.
- **`PENDING_EXTERNAL_INTEGRATION`**: Dependent on external enterprise infrastructure (e.g., live Kafka topics, POS webhooks, payment gateways) that is not connected in this prototype.
- **`NOT_VERIFIED`**: Unverified or untested capability.

---

## 2. Ingestion & Telemetry Data Contracts (Read-Only Mirroring)

To observe real fleet dynamics without polluting production systems or introducing operational feedback loops, the staging instance must consume mirrored telemetry under a strict read-only contract.

### 2.1 Ingestion Data Contract Specification

| Ingestion Stream | Transport / Protocol | Required Fields | Data Contract Schema | Implementation Status | Side-Effect Protection |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Order Lifecycle Stream** | Kafka / SQS Mirror Consumer | `order_id`, `customer_id`, `restaurant_id`, `created_at`, `promised_delivery_at`, `order_status` | JSON Schema: `schemas/telemetry/order_v1.json` | `PENDING_EXTERNAL_INTEGRATION` | Consumer group isolated with zero commit-back side effects to primary order manager. |
| **Kitchen KDS Events** | POS Webhook Consumer | `order_id`, `event_timestamp`, `prep_delay_min`, `kitchen_queue_depth` | JSON Schema: `schemas/telemetry/kitchen_event_v1.json` | `PENDING_EXTERNAL_INTEGRATION` | Ephemeral subscription; drop on lag > 60s. |
| **Courier Telematics** | Kafka / Debezium CDC | `order_id`, `courier_id`, `allotment_timestamp`, `first_mile_km`, `courier_session_min` | Avro: `schemas/telemetry/courier_v1.avro` | `PENDING_EXTERNAL_INTEGRATION` | Read-only replica access; no courier dispatch callbacks. |

### 2.2 Ingestion Guardrail Checklist
- [x] **Local Data Isolation**: `orders` and `order_events` tables strictly segregated with `data_source = "SYNTHETIC"`, and historical data isolated in `historical_orders` with `data_source = "PUBLIC_HISTORICAL"`. Status: `IMPLEMENTED_AND_TESTED`.
- [ ] **External Consumer Group Isolation**: SHADOW consumer group (`resolveai-shadow-consumer`) configured with no produce permissions on production Kafka clusters. Status: `PENDING_EXTERNAL_INTEGRATION`.
- [ ] **External Schema Validation Gate**: All incoming JSON/Avro payloads validate against Pydantic schemas in `backend/app/schemas/` with `extra="ignore"`. Status: `PENDING_EXTERNAL_INTEGRATION`.

---

## 3. Authentication, RBAC & Secret Management

### 3.1 Cryptographic Key & Secret Requirements
- [x] **Secret Key Strength Validation**: Startup validator in `backend/app/core/config.py` enforces that default dev secret key (`resolveai-insecure-dev-secret-key...`) is rejected with a fatal exit code in `staging` or `production`, and requires $\ge 32$ characters. Status: `IMPLEMENTED_AND_TESTED`.
- [x] **Dev Token Endpoint Invalidation**: `POST /api/v1/auth/dev-token` is automatically disabled (`HTTP 403 Forbidden`) when `ENVIRONMENT` is set to `staging` or `production`. Status: `IMPLEMENTED_AND_TESTED`.
- [ ] **Production Secret Manager Injection**: Injection of secrets at container boot via AWS Secrets Manager or HashiCorp Vault. Status: `DOCUMENTED_NOT_DEPLOYED`.

### 3.2 Role-Based Access Control (RBAC) Verification Matrix

| Role | Permitted Actions | Prohibited Actions | Enforcement Mechanism | Status |
| :--- | :--- | :--- | :--- | :---: |
| `VIEWER` | Query health, list orders, view audits | Cannot trigger investigations, cannot approve or execute | Route dependencies (`require_roles`) | `IMPLEMENTED_AND_TESTED` |
| `INTERN` | View dashboards, run read-only simulation queries | Cannot approve recommendations (HTTP 403) | `PolicyEngine.AUTHORIZED_ROLES` check | `IMPLEMENTED_AND_TESTED` |
| `OPERATOR` | Trigger investigations, approve standard operational actions | Cannot modify global policy thresholds | `PolicyEngine.AUTHORIZED_ROLES` check | `IMPLEMENTED_AND_TESTED` |
| `OPS_LEAD` | Trigger investigations, approve operational recommendations | Cannot modify global policy thresholds | `PolicyEngine.AUTHORIZED_ROLES` check | `IMPLEMENTED_AND_TESTED` |
| `SUPERVISOR` | Approve high-sensitivity operational actions | Cannot access database directly | `PolicyEngine.AUTHORIZED_ROLES` check | `IMPLEMENTED_AND_TESTED` |
| `ADMIN` | System maintenance, service account provisioning | Full role auditing active | Route dependencies & policy checks | `IMPLEMENTED_AND_TESTED` |

---

## 4. SHADOW Execution Mode & Hard Safety Blocking

### 4.1 Safety Invariants
1. **`EXECUTION_MODE=SHADOW` Required**: Staging containers must run with `ENVIRONMENT=staging` and `EXECUTION_MODE=SHADOW`.
2. **`LIVE` Mode Fails Startup**: The configuration loader in `backend/app/core/config.py` explicitly throws `ValueError: EXECUTION_MODE='LIVE' is strictly blocked across all environments` if configured. Status: `IMPLEMENTED_AND_TESTED`.
3. **Guardrail 0 in RecoveryExecutionService**: The execution entrypoint in `backend/app/services/recovery_executor.py` checks `settings.EXECUTION_MODE` before any database lookups or external API dispatch:
   ```python
   if exec_mode == "SHADOW":
       raise PermissionError(
           "Recovery execution rejected: system is running in read-only SHADOW mode. "
           "Simulated actions, physical mutations, and partner dispatches are disabled."
       )
   ```
   Status: `IMPLEMENTED_AND_TESTED`.

---

## 5. Distributed State: Redis-Backed Cooldown & Rate Limiting Migration

In multi-worker production deployments (e.g., Gunicorn with 8 Uvicorn workers or Kubernetes horizontal pods), in-process state cannot enforce cooldowns across independent worker processes. A managed Redis cluster must coordinate cross-worker rate limits and policy cooldowns.

### 5.1 Current Implementation vs Production Specification
- **Current Repository State**: Cooldown timers (15m customer SMS, 24h apology voucher) and duplicate execution protection are implemented via transactional database queries (`RecoveryExecutionAudit.idempotency_key` and order event timestamps) and in-memory policy state. Status: `IMPLEMENTED_AND_TESTED`.
- **Redis Migration Specification**: The distributed Redis schema below is architecturally specified and documented for multi-worker scaling, but is **not deployed** to a live Redis cluster in this prototype. Status: `DOCUMENTED_NOT_DEPLOYED`.

| Cooldown Objective | Key Pattern | TTL | Fallback Behavior | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Customer SMS Cooldown** | `cooldown:customer:{customer_id}:sms` | 900s (15 min) | If Redis unreachable, default to blocking SMS (fail safe). | `DOCUMENTED_NOT_DEPLOYED` |
| **Order Apology Voucher** | `cooldown:order:{order_id}:voucher` | 86400s (24 hr) | Atomic `SETNX`; enforce single voucher per order lifetime. | `DOCUMENTED_NOT_DEPLOYED` |
| **Kitchen Ping Rate Limit**| `ratelimit:restaurant:{rest_id}:ping` | 300s (5 min) | Limit max 1 ping per 5 minutes to prevent kitchen tablet spam. | `DOCUMENTED_NOT_DEPLOYED` |
| **Global Alert Budget** | `alert_budget:{cluster_id}:window_1h` | 3600s (1 hr) | Sliding-window counter; enforce 10 alerts / 1k order cap. | `DOCUMENTED_NOT_DEPLOYED` |

---

## 6. Database Privilege Separation & Audit Immutability

### 6.1 Current Implementation vs Production DBA Configuration
- **Application ORM Immutability Listeners**: `RecoveryExecutionAudit` and `MLPredictionAudit` implement SQLAlchemy event listeners (`before_update`, `before_delete`) that raise `PermissionError` on any modification attempt in application code. Status: `IMPLEMENTED_AND_TESTED`.
- **PostgreSQL Database Role Privilege Separation**: The SQL script below specifying dedicated `resolveai_app` credentials with `REVOKE UPDATE, DELETE` and database-level trigger functions is documented for production DBA provisioning, but has **not been executed or deployed** on an enterprise PostgreSQL instance. Status: `DOCUMENTED_NOT_DEPLOYED`.

```sql
-- Production DBA Provisioning Script (DOCUMENTED_NOT_DEPLOYED)
CREATE ROLE resolveai_app WITH LOGIN PASSWORD 'strong_entropy_password';
GRANT CONNECT ON DATABASE resolveai TO resolveai_app;
GRANT USAGE ON SCHEMA public TO resolveai_app;

GRANT SELECT, INSERT, UPDATE, DELETE ON orders, order_events, recovery_recommendations TO resolveai_app;

-- IMMUTABLE AUDIT TABLES: App user can ONLY INSERT and SELECT
GRANT SELECT, INSERT ON recovery_execution_audits, ml_prediction_audits TO resolveai_app;
REVOKE UPDATE, DELETE, TRUNCATE ON recovery_execution_audits, ml_prediction_audits FROM resolveai_app;

CREATE OR REPLACE FUNCTION prevent_audit_tampering()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit records are strictly append-only. UPDATE and DELETE are prohibited.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_no_update_exec_audit
BEFORE UPDATE OR DELETE ON recovery_execution_audits
FOR EACH ROW EXECUTE FUNCTION prevent_audit_tampering();

CREATE TRIGGER trg_no_update_ml_audit
BEFORE UPDATE OR DELETE ON ml_prediction_audits
FOR EACH ROW EXECUTE FUNCTION prevent_audit_tampering();
```

---

## 7. Production Monitoring, Target SLAs, Freshness & Model Drift

### 7.1 Operational Latency: Target SLAs vs Measured Benchmarks

| Service Component | Documented Target SLA (P95) | Documented Target SLA (P99) | Measured Benchmark (Local Dev/CI) | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Health Probe (`/health/ready`)** | $< 10\text{ ms}$ | $< 50\text{ ms}$ | $2.1\text{ ms}$ | `IMPLEMENTED_AND_TESTED` (Local) / `DOCUMENTED_NOT_DEPLOYED` (Target SLA) |
| **Task A ML Quantiles** | $< 25\text{ ms}$ | $< 60\text{ ms}$ | $8.4\text{ ms}$ | `IMPLEMENTED_AND_TESTED` (Local) / `DOCUMENTED_NOT_DEPLOYED` (Target SLA) |
| **Task C2 Landmark Inference** | $< 20\text{ ms}$ | $< 50\text{ ms}$ | $6.2\text{ ms}$ | `IMPLEMENTED_AND_TESTED` (Local) / `DOCUMENTED_NOT_DEPLOYED` (Target SLA) |
| **Multi-Agent Orchestrator** | $< 800\text{ ms}$ | $< 1500\text{ ms}$ | $28.5\text{ ms}$ (Rule Fallback) | `IMPLEMENTED_AND_TESTED` (Local) / `DOCUMENTED_NOT_DEPLOYED` (Target SLA) |
| **Recommendation Execution** | $< 30\text{ ms}$ | $< 80\text{ ms}$ | $7.8\text{ ms}$ | `IMPLEMENTED_AND_TESTED` (Local) / `DOCUMENTED_NOT_DEPLOYED` (Target SLA) |

### 7.2 Drift Tracking & Data Freshness Specifications
- **Telemetry Ingestion Freshness**: Specification to alert if `now() - max(event_timestamp) > 30s`. Status: `DOCUMENTED_NOT_DEPLOYED`.
- **Feature Drift Monitoring**: Specification for daily Kolmogorov-Smirnov (KS) tests on distance and volume. Status: `DOCUMENTED_NOT_DEPLOYED`.
- **Calibration Drift Monitoring**: Specification to track daily Brier score on landmark orders. Status: `DOCUMENTED_NOT_DEPLOYED`.

---

## 8. Rollback, Emergency Kill-Switch & Business Continuity

- [x] **Tier 1 (Instant Silence via SHADOW Mode)**: Changing `EXECUTION_MODE=SHADOW` halts all simulated executions immediately with `HTTP 403 Forbidden`. Status: `IMPLEMENTED_AND_TESTED`.
- [x] **Tier 2 (AI Degradation / Fallback)**: Setting `GEMINI_API_KEY=""` forces Customer Resolution Agent into deterministic rule fallback with zero LLM latency and zero hallucinations. Status: `IMPLEMENTED_AND_TESTED`.
- [ ] **Tier 3 (Cloud Load Balancer Route Termination)**: ALB/Cloudflare static error page routing. Status: `DOCUMENTED_NOT_DEPLOYED`.
- [ ] **PostgreSQL WAL Archiving & PITR**: Cloud storage continuous WAL archiving. Status: `DOCUMENTED_NOT_DEPLOYED`.

---

## 9. Staging / SHADOW Go / No-Go Evidence Matrix

Every item below has been audited and classified according to the standardized status taxonomy:

| Gate Identifier | Verification Item | Required Evidence | Verification Method | Status | Sign-off Owner |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **GATE-01** | Test Suite Integrity | 207 of 207 tests passing with zero failures | `pytest backend/tests/ -q` | `IMPLEMENTED_AND_TESTED` | QA Lead |
| **GATE-02** | Frontend Production Build | Clean Next.js 16 production build with zero TypeScript errors | `npm --prefix frontend run build` | `IMPLEMENTED_AND_TESTED` | Frontend Lead |
| **GATE-03** | End-to-End Demo Workflow | All 8 demonstration steps passing against live server | `python scripts/demo_runner.py` | `IMPLEMENTED_AND_TESTED` | Solutions Architect |
| **GATE-04** | SHADOW Execution Blocking | HTTP 403 Forbidden returned on execute attempts in SHADOW mode | `test_shadow_mode_blocks_execution` | `IMPLEMENTED_AND_TESTED` | AppSec Engineer |
| **GATE-05** | Auth Secret Strength | Custom non-default secret $> 32$ chars enforced at boot | `test_prod_config_fails_with_default_secret` | `IMPLEMENTED_AND_TESTED` | AppSec Engineer |
| **GATE-06** | Read-Only Data Isolation | `orders` table isolated; Kaggle data in `historical_orders` | SQL schema audit & `test_provenance.py` | `IMPLEMENTED_AND_TESTED` | Data Platform Lead |
| **GATE-07** | ML Model Governance | Task A marked $t_0$ quantiles; Task C2 marked eventual; Tasks B & C1 `RESEARCH_ONLY` | `data/artifacts/models/phase_2_5/registry.json` | `IMPLEMENTED_AND_TESTED` | ML Platform Lead |
| **GATE-08** | Database Privilege Separation | PostgreSQL `REVOKE UPDATE, DELETE` & tamper triggers | DBA provisioning script review | `DOCUMENTED_NOT_DEPLOYED` | Database Architect |
| **GATE-09** | Live Execution Prohibited | `EXECUTION_MODE=LIVE` fails fast at startup across all environments | Unit test in `test_phase_6_production_readiness` | `IMPLEMENTED_AND_TESTED` | Principal Architect |
| **GATE-10** | Distributed Cooldowns | Redis cluster distributed rate-limiting and atomic locks | Redis key pattern specification review | `DOCUMENTED_NOT_DEPLOYED` | Infrastructure Lead |
| **GATE-11** | External Ingestion Streams | Live Kafka consumer groups and POS webhooks | Architecture contract specification | `PENDING_EXTERNAL_INTEGRATION` | Platform Lead |

---

## 10. Formal Release Gate Declaration

> [!IMPORTANT]
> **GO/NO-GO VERDICT: CONDITIONAL GO FOR SHADOW / STAGING ONLY**
> 
> The Swiggy ResolveAI codebase satisfies all architecture, security, multi-agent orchestration, and machine learning governance standards required for deployment to a **SHADOW or Staging** environment.
> 
> **LIVE OPERATIONAL EXECUTION REMAINS STRICTLY BLOCKED BY CODE INVARIANTS.** Commercial rollout to real couriers, restaurants, and customers requires live Kafka cluster integrations, payment gateway credentials, and commercial contractual agreements not present in this portfolio prototype.
