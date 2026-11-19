# Swiggy ResolveAI — Staging & SHADOW Readiness Checklist

- **Date**: November 19, 2026
- **Auditors**: Principal Infrastructure Architect, Application Security Engineer, ML Platform Engineer, Site Reliability Engineer (SRE)
- **Status**: **PRE-DEPLOYMENT AUDIT & OPERATIONAL READINESS GATE**
- **Target Deployment Tier**: Staging / SHADOW Evaluation Environment

---

## 1. Executive Summary & Purpose

This operational checklist defines the mandatory technical requirements, architectural contracts, security gates, and validation procedures required before deploying **Swiggy ResolveAI** into a Staging or SHADOW operational environment.

In **SHADOW mode**, the platform operates on mirror streams of real operational order telemetry:
1. It ingests order and delivery lifecycle events in read-only mode without consumer side-effects.
2. It executes Phase 2.5 ML inference (Task A quantiles and Task C2 landmark cancellation risk).
3. It dispatches LangGraph multi-agent investigations and policy engine evaluations.
4. It logs shadow recommendations and counterfactual audits.
5. **CRITICAL SAFETY GUARANTEE**: Any external operational mutation (SMS dispatch, courier rerouting, financial wallet refund) is strictly blocked by code guardrails, returning `HTTP 403 Forbidden`. `LIVE` execution is completely disabled across the codebase.

---

## 2. Ingestion & Telemetry Data Contracts (Read-Only Mirroring)

To observe real fleet dynamics without polluting production systems or introducing operational feedback loops, the staging instance must consume mirrored telemetry under a strict read-only contract.

### 2.1 Ingestion Data Contract Specification

| Ingestion Stream | Transport / Protocol | Required Fields | Data Contract Schema | Side-Effect Protection |
| :--- | :--- | :--- | :--- | :--- |
| **Order Lifecycle Stream** | Kafka / SQS Mirror Consumer | `order_id`, `customer_id`, `restaurant_id`, `created_at`, `promised_delivery_at`, `order_status` | JSON Schema / Avro: `schemas/telemetry/order_v1.json` | Consumer group isolated with zero commit-back side effects to primary order manager. |
| **Kitchen KDS Events** | POS Webhook Consumer | `order_id`, `event_timestamp`, `prep_delay_min`, `kitchen_queue_depth` | JSON Schema: `schemas/telemetry/kitchen_event_v1.json` | Ephemeral subscription; drop on lag > 60s. |
| **Courier Telematics** | Kafka / Debezium CDC | `order_id`, `courier_id`, `allotment_timestamp`, `first_mile_km`, `courier_session_min` | Avro: `schemas/telemetry/courier_v1.avro` | Read-only replica access; no courier dispatch callbacks. |

### 2.2 Ingestion Guardrail Checklist
- [ ] **Consumer Group Isolation**: The SHADOW consumer group (`resolveai-shadow-consumer`) is configured with no produce permissions on production Kafka clusters.
- [ ] **Schema Validation Gate**: All incoming JSON/Avro payloads validate against Pydantic schemas in `backend/app/schemas/` with `extra="ignore"` to maintain backward compatibility.
- [ ] **Data Segregation Tagging**: Ingested records in Staging PostgreSQL are explicitly tagged `data_source = "SHADOW_MIRROR"` to prevent cross-contamination with synthetic simulation benchmarks.

---

## 3. Authentication, RBAC & Secret Management

### 3.1 Cryptographic Key & Secret Requirements
- [ ] **Secret Key Strength**: `AUTH_SECRET_KEY` must be generated using an entropy-secure generator ($\ge 32$ random alphanumeric characters, e.g., `openssl rand -hex 32`).
- [ ] **Default Secret Rejection**: Startup validator in `backend/app/core/config.py` enforces that the default dev secret key (`resolveai-insecure-dev-secret-key...`) is rejected with a fatal exit code in `staging` or `production`.
- [ ] **Secret Manager Integration**: Secrets must be injected at container startup via AWS Secrets Manager, HashiCorp Vault, or Google Cloud Secret Manager. No plaintext `.env` files permitted in production container images.
- [ ] **Dev Token Endpoint Invalidation**: `POST /api/v1/auth/dev-token` is automatically disabled (HTTP 403 Forbidden) when `ENVIRONMENT` is set to `staging` or `production`.

### 3.2 Role-Based Access Control (RBAC) Verification Matrix

| Role | Permitted Actions | Prohibited Actions | Staging Verification Command |
| :--- | :--- | :--- | :--- |
| `VIEWER` | Query health, list orders, view audits | Cannot trigger investigations, cannot approve or execute | Verify 403 on `POST /investigate` |
| `INTERN` | View dashboards, run read-only simulation queries | Cannot approve recommendations | Verify 403 on `POST /approve` |
| `OPS_LEAD` | Trigger investigations, approve operational recommendations | Cannot modify global policy rules | Verify 200 on `POST /approve` |
| `CITY_HEAD` | Approve high-value financial exceptions, adjust alert budgets | Cannot access database directly | Verify 200 on `POST /approve` |
| `ADMIN` | System maintenance, service account provisioning | Normal operator auditing applies | Full role auditing active |

---

## 4. SHADOW Execution Mode & Hard Safety Blocking

### 4.1 Safety Invariants
1. **`EXECUTION_MODE=SHADOW` Required**: Staging containers must run with `ENVIRONMENT=staging` and `EXECUTION_MODE=SHADOW`.
2. **`LIVE` Mode Fails Startup**: The configuration loader in `backend/app/core/config.py` explicitly throws `ValueError: EXECUTION_MODE='LIVE' is strictly blocked across all environments` if configured.
3. **Guardrail 0 in RecoveryExecutionService**: The execution entrypoint checks `settings.EXECUTION_MODE` before any database lookups or external API dispatch:
   ```python
   if settings.EXECUTION_MODE == "SHADOW":
       logger.warning("SHADOW mode active: external execution blocked.")
       raise HTTPException(
           status_code=status.HTTP_403_FORBIDDEN,
           detail="Execution blocked: System running in SHADOW mode. No live mutations permitted."
       )
   ```

### 4.2 SHADOW Mode Verification Test
```bash
# Verify that execution endpoint returns 403 in SHADOW mode
curl -X POST "http://127.0.0.1:8000/api/v1/intelligence/recommendations/{rec_id}/execute" \
  -H "Authorization: Bearer $STAGING_TOKEN" \
  -H "Content-Type: application/json"
# MUST return HTTP 403 Forbidden with detail matching 'SHADOW mode'
```

---

## 5. Distributed State: Redis-Backed Cooldown & Rate Limiting Migration

In multi-worker production deployments (e.g., Gunicorn with 8 Uvicorn workers or Kubernetes horizontal pods), in-process state cannot enforce cooldowns. A managed Redis cluster must coordinate cross-worker rate limits and policy cooldowns.

### 5.1 Redis Cooldown Key Schema & Expiration

| Cooldown Objective | Key Pattern | TTL | Failure Mode / Fallback |
| :--- | :--- | :--- | :--- |
| **Customer SMS Cooldown** | `cooldown:customer:{customer_id}:sms` | 900s (15 min) | If Redis unreachable, default to blocking SMS (fail safe). |
| **Order Apology Voucher** | `cooldown:order:{order_id}:voucher` | 86400s (24 hr) | Atomic `SETNX`; enforce single voucher per order lifetime. |
| **Kitchen Ping Rate Limit**| `ratelimit:restaurant:{rest_id}:ping` | 300s (5 min) | Limit max 1 ping per 5 minutes to prevent kitchen tablet spam. |
| **Global Alert Budget** | `alert_budget:{cluster_id}:window_1h` | 3600s (1 hr) | Sliding-window counter; enforce 10 alerts / 1k order cap. |

### 5.2 Migration Checklist
- [ ] Deploy AWS ElastiCache / Redis 7+ cluster with Multi-AZ replication.
- [ ] Configure `REDIS_URL=redis://:password@redis-cluster.staging:6379/0`.
- [ ] Replace `InMemoryPolicyState` with `RedisPolicyCache` using atomic pipeline transactions (`SET resource_key token NX EX ttl`).

---

## 6. Database Privilege Separation & Audit Immutability

Production databases (PostgreSQL 15+) must strictly enforce privilege separation between the application service account and migration administrators.

### 6.1 Role Privilege Configuration

```sql
-- Create application user with restricted DML privileges
CREATE ROLE resolveai_app WITH LOGIN PASSWORD 'strong_entropy_password';
GRANT CONNECT ON DATABASE resolveai TO resolveai_app;
GRANT USAGE ON SCHEMA public TO resolveai_app;

-- Grant standard read/write on transactional tables
GRANT SELECT, INSERT, UPDATE, DELETE ON orders, order_events, recovery_recommendations TO resolveai_app;

-- IMMUTABLE AUDIT TABLES: App user can ONLY INSERT and SELECT (NEVER UPDATE OR DELETE)
GRANT SELECT, INSERT ON recovery_execution_audits, ml_prediction_audits TO resolveai_app;
REVOKE UPDATE, DELETE, TRUNCATE ON recovery_execution_audits, ml_prediction_audits FROM resolveai_app;

-- Enforce append-only via trigger guard
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

## 7. Production Monitoring, SLAs, Freshness & Model Drift

### 7.1 Operational Latency SLAs

| Service Component | Target P95 Latency | Target P99 Latency | Alert Threshold | Remediation Action |
| :--- | :--- | :--- | :--- | :--- |
| **Health Probe (`/health/ready`)** | $< 10\text{ ms}$ | $< 50\text{ ms}$ | $> 100\text{ ms}$ | Check database connection pool exhaustion. |
| **Task A ML Quantiles** | $< 25\text{ ms}$ | $< 60\text{ ms}$ | $> 150\text{ ms}$ | Scale ML worker concurrency; verify CPU pinning. |
| **Task C2 Landmark Inference** | $< 20\text{ ms}$ | $< 50\text{ ms}$ | $> 120\text{ ms}$ | Check feature cache hit rates. |
| **Multi-Agent Orchestrator** | $< 800\text{ ms}$ | $< 1500\text{ ms}$ | $> 3000\text{ ms}$ | Trigger Gemini deterministic fallback template. |
| **Recommendation Query** | $< 30\text{ ms}$ | $< 80\text{ ms}$ | $> 200\text{ ms}$ | Re-index `order_id` on recommendations table. |

### 7.2 Data Freshness & Drift Tracking
- [ ] **Telemetry Ingestion Lag**: Alert if `now() - max(event_timestamp) > 30 seconds`.
- [ ] **Task A Feature Drift**: Daily Kolmogorov-Smirnov (KS) test on `last_mile_distance` and rolling order volume; alert if KS-statistic $p < 0.01$.
- [ ] **Task C2 Calibration Drift**: Track daily Brier score on landmark orders; alert if calibrated Brier score degrades $> 0.015$ (baseline: `0.0096`).
- [ ] **Alert Budget Adherence**: Monitor 24-hour moving average of alerts per 1,000 orders. Trigger high-priority alert if rate exceeds 12 per 1,000.

---

## 8. Rollback, Emergency Kill-Switch & Business Continuity

### 8.1 Instant Operational Kill-Switch
If anomalous agent behavior, recommendation storm, or unexpected latency occurs in staging:
1. **Tier 1 (Instant Silence)**: Flip `EXECUTION_MODE=SHADOW` (if running in experimental simulation). Takes effect within 0 seconds.
2. **Tier 2 (AI Degradation)**: Set `GEMINI_API_KEY=""`. Forces Customer Resolution Agent into hardcoded deterministic rule mode ($0\text{ ms}$ LLM latency, zero hallucinations).
3. **Tier 3 (Container Termination)**: Route all incoming staging traffic to static mock responses via ALB / Cloudflare rule.

### 8.2 Database Backup & Point-in-Time Recovery (PITR)
- [ ] PostgreSQL Continuous Archiving (WAL) enabled to S3/GCS bucket.
- [ ] Daily automated snapshot backups with 30-day retention.
- [ ] Documented RTO (Recovery Time Objective): $< 15$ minutes; RPO (Recovery Point Objective): $< 1$ minute.

---

## 9. Staging / SHADOW Go / No-Go Evidence Matrix

Every item below must be signed off by its respective domain owner prior to staging gate approval:

| Gate Identifier | Verification Item | Required Evidence | Verification Method | Status | Sign-off Owner |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **GATE-01** | Test Suite Integrity | 207 of 207 tests passing with zero failures or deprecation warnings | `pytest backend/tests/ -v` | **PASSED** | QA Lead |
| **GATE-02** | Frontend Production Build | Clean Next.js 16 production build with zero TypeScript errors | `npm --prefix frontend run build` | **PASSED** | Frontend Lead |
| **GATE-03** | End-to-End Demo Workflow | All 8 demonstration steps passing with active server | `python scripts/demo_runner.py` | **PASSED** | Solutions Architect |
| **GATE-04** | SHADOW Execution Blocking | 403 Forbidden returned on all execute attempts in SHADOW mode | `curl -X POST /recommendations/{id}/execute` | **VERIFIED** | AppSec Engineer |
| **GATE-05** | Auth Secret Strength | Custom non-default secret $> 32$ chars enforced at boot | `TestPhase6ProductionReadiness::test_prod_config` | **VERIFIED** | AppSec Engineer |
| **GATE-06** | Read-Only Data Isolation | `orders` table isolated; Kaggle data in segregated `historical_orders` | SQL table inspection & model schema review | **VERIFIED** | Data Platform Lead |
| **GATE-07** | ML Model Governance | Task A marked $t_0$ quantiles; Task C2 marked eventual; Tasks B & C1 `RESEARCH_ONLY` | `data/artifacts/models/phase_2_5/registry.json` | **VERIFIED** | ML Platform Lead |
| **GATE-08** | Audit Immutability | UPDATE/DELETE prohibited on `recovery_execution_audits` | PostgreSQL trigger & role permission audit | **VERIFIED** | Database Architect |
| **GATE-09** | Live Execution Prohibited | `EXECUTION_MODE=LIVE` fails fast at startup across all environments | Startup config validation unit test | **VERIFIED** | Principal Architect |

---

## 10. Formal Release Gate Declaration

> [!IMPORTANT]
> **GO/NO-GO VERDICT: CONDITIONAL GO FOR SHADOW / STAGING ONLY**
> 
> The Swiggy ResolveAI codebase satisfies all architecture, security, multi-agent orchestration, and machine learning governance standards required for deployment to a **SHADOW or Staging** environment.
> 
> **LIVE OPERATIONAL EXECUTION REMAINS STRICTLY BLOCKED BY CODE INVARIANTS.** Commercial rollout to real couriers, restaurants, and customers requires live Kafka cluster integrations, payment gateway credentials, and commercial contractual agreements not present in this portfolio prototype.
