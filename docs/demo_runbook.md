# Swiggy ResolveAI — Reconciled Reproducible Demonstration Runbook

This runbook provides step-by-step instructions to reproduce the complete **Swiggy ResolveAI** demonstration locally or in containerized staging environments.

All commands have been audited and reconciled against the live application router and authentication trust boundary.

---

## 1. Quick Automated Demonstration (One Command)

To execute the entire 8-step demonstration automatically with dynamic relative timestamps and verified token authentication:

```bash
# Ensure backend server is running in a separate terminal:
# python -m uvicorn backend.app.main:app --port 8000

python scripts/demo_runner.py
```

The script:
1. Validates backend readiness (`GET /api/v1/health/ready`).
2. Acquires signed demonstration bearer token (`POST /api/v1/auth/dev-token`).
3. Generates fresh synthetic disrupted orders (`POST /api/v1/simulation/generate`).
4. Injects operational delay telemetry (`POST /api/v1/simulation/events`).
5. Dispatches LangGraph multi-agent investigations (`POST /api/v1/intelligence/investigate/{id}`).
6. Demonstrates unauthorized role rejection (403 on Intern) and authorized approval (200 on OPS_LEAD).
7. Executes simulated recovery action and validates cryptographic idempotency deduplication.
8. Retrieves and verifies immutable execution audit records (`GET /api/v1/intelligence/audit/{id}`).

---

## 2. Five-Part Manual Walkthrough (cURL / PowerShell)

### Environment Prerequisites
- Backend running at `http://127.0.0.1:8000`
- Frontend running at `http://localhost:3000`

```bash
# Set Base URL
BASE="http://127.0.0.1:8000/api/v1"
```

---

### Part A: Authentication & Token Acquisition

Acquire a cryptographically signed HMAC-SHA256 bearer token for an authorized Operations Lead:

```bash
# Acquire OPS_LEAD demonstration token
curl -X POST "$BASE/auth/dev-token" \
  -H "Content-Type: application/json" \
  -d '{"operator_profile": "ops_lead"}'
```
*Extract `"access_token"` from the JSON response and set as `TOKEN`:*
```bash
TOKEN="<PASTE_ACCESS_TOKEN_HERE>"
```

---

### Part B: Order Ingestion & Telemetry Injection

#### Step B1: Generate Synthetic Disrupted Order
```bash
curl -X POST "$BASE/simulation/generate" \
  -H "Content-Type: application/json" \
  -d '{"scenario": "COMBINED_DELAY", "count": 1, "seed": 42}'
```
*Note the returned `"generated_order_ids"` (e.g., `ORDER_ID`).*

#### Step B2: Inject Operational Delay Telemetry Events
```bash
# Inject Restaurant Preparation Delay
curl -X POST "$BASE/simulation/events" \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER_ID\",
    \"event_type\": \"RESTAURANT_PREPARATION_DELAY\",
    \"metadata\": {\"prep_delay_min\": 19.5, \"kitchen_queue_depth\": 8},
    \"data_source\": \"SYNTHETIC\"
  }"

# Inject Courier Assignment Delay
curl -X POST "$BASE/simulation/events" \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER_ID\",
    \"event_type\": \"COURIER_ASSIGNMENT_DELAY\",
    \"metadata\": {\"allotment_delay_min\": 10.0},
    \"data_source\": \"SYNTHETIC\"
  }"
```

---

### Part C: Multi-Agent Investigation & Synthesis

Trigger the LangGraph 4-agent investigation:

```bash
curl -X POST "$BASE/intelligence/investigate/$ORDER_ID"
```

*Verification Points*:
- `risk_tier`: Evaluates to `HIGH_RISK` or `CRITICAL`.
- `ml_predictions.task_a_eta`: Displays monotonic quantiles $P10 \le P50 \le P90$.
- `recommendations`: Lists prioritized recovery actions with `requires_approval: true` for sensitive actions.

*Note the returned `recommendation.id` (e.g. `REC_ID`).*

---

### Part D: Human-in-the-Loop Governance & Execution Idempotency

#### Step D1: Verify Unauthorized Role Rejection (403 Forbidden)
```bash
# Acquire unauthorized intern token
INTERN_TOKEN=$(curl -s -X POST "$BASE/auth/dev-token" -H "Content-Type: application/json" -d '{"operator_profile": "intern"}' | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Attempt approval with intern token -> Expected: 403 Forbidden
curl -X POST "$BASE/intelligence/recommendations/$REC_ID/approve" \
  -H "Authorization: Bearer $INTERN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Unauthorized approval attempt"}'
```

#### Step D2: Authorize Recommendation with Verified OPS_LEAD Token
```bash
curl -X POST "$BASE/intelligence/recommendations/$REC_ID/approve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Verified kitchen prep backlog; approved courier dispatch escalation."}'
```
*Expected Status: `200 OK`, `approval_status: "APPROVED"`.*

#### Step D3: Execute Action & Prove Idempotency
```bash
# Call 1: Initial Execution
curl -X POST "$BASE/intelligence/recommendations/$REC_ID/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'

# Call 2: Immediate Duplicate Replay (Returns cached audit, no duplicate dispatch)
curl -X POST "$BASE/intelligence/recommendations/$REC_ID/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```
*Expected: Call 1 returns `"status": "EXECUTED"`; Call 2 returns `"status": "ALREADY_EXECUTED"` with identical `audit_id` and `idempotency_key`.*

---

### Part E: Immutable Audit Trail & Health Diagnostics

#### Step E1: Query Immutable Audit Records
```bash
curl -X GET "$BASE/intelligence/audit/$ORDER_ID" \
  -H "Authorization: Bearer $TOKEN"
```

#### Step E2: Verify 4-Pillar Health Diagnostics
```bash
curl -X GET "$BASE/health"
```
```json
{
  "status": "healthy",
  "app_name": "Swiggy ResolveAI",
  "components": {
    "database": {"status": "connected"},
    "model_registry": {"status": "loaded", "version": "2.5.0"}
  }
}
```
