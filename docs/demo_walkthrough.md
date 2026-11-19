# Swiggy ResolveAI — End-to-End Demo Walkthrough: Restaurant Delay Scenario

- **Date**: November 19, 2026
- **Auditors**: Principal Solutions Architect, Lead QA Engineer, Application Security Engineer
- **Status**: **REPRODUCIBLE & CODE-VERIFIED**
- **Automated Script Reference**: `scripts/demo_runner.py`
- **Execution Mode**: `SIMULATED` (Non-production demonstration environment)

---

## 1. Scenario Overview: Kitchen Preparation Delay

This walkthrough demonstrates an end-to-end operational recovery lifecycle for a synthetic order experiencing a kitchen backlog in the Koramangala, Bangalore cluster. 

The walkthrough follows the exact execution sequence implemented in the automated verification script [demo_runner.py](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/scripts/demo_runner.py).

### Scenario Characteristics
- **Order Scenario**: `RESTAURANT_DELAY` (One of 6 canonical demo scenarios in [`backend/app/simulation/scenarios.py`](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/backend/app/simulation/scenarios.py))
- **Initial Status**: Order placed, courier allocated, but kitchen queue surges with an estimated preparation delay of +18.5 minutes.
- **Threat Vector**: Cumulative delay violates SLA threshold ($+15$ minutes over nominal duration), triggering autonomous risk escalation and customer dissatisfaction risk.
- **Recovery Strategy**: Autonomous customer reassurance combined with a Human-in-the-Loop (HITL) approved apology voucher (₹50) under deterministic policy guardrails.
- **Strict Simulation Boundary**: All operational actions (notifications, courier flags, wallet credits) are strictly simulated in local database state. No real SMS gateways, mobile push systems, or banking ledgers are invoked.

---

## 2. Step-by-Step Walkthrough

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Operations Lead (OPS_LEAD)
    participant API as FastAPI Backend (/api/v1)
    participant Sim as Simulation Engine
    participant ML as ML Inference Service
    participant MultiAgent as LangGraph Multi-Agent Engine
    participant Policy as Deterministic Policy Engine
    participant Exec as Recovery Execution Service
    participant DB as Operational Database (SQLite/PostgreSQL)

    Operator->>API: 1. GET /health/ready
    API-->>Operator: 200 OK (All 4 Pillars Healthy)

    Operator->>API: 2. POST /auth/dev-token (role: ops_lead)
    API-->>Operator: 200 OK (Signed Bearer JWT)

    Operator->>API: 3. POST /simulation/generate (scenario: RESTAURANT_DELAY)
    API->>Sim: Seed order with dynamic timestamps
    Sim->>DB: INSERT into orders (data_source='SYNTHETIC')
    API-->>Operator: 200 OK (ORDER_ID created, status: IN_KITCHEN)

    Operator->>API: 4. POST /simulation/events (prep delay +18.5m, queue depth 8)
    API->>DB: INSERT into order_events (data_source='SYNTHETIC')
    API-->>Operator: 200 OK (OrderEventResponse)

    Operator->>API: 5. POST /intelligence/investigate/$ORDER_ID
    API->>ML: Run Task A duration quantiles
    ML-->>API: P10=19.7m, P50=30.1m, P90=49.4m
    API->>MultiAgent: Dispatch Order, Restaurant, Delivery & Customer Agents
    MultiAgent->>Policy: Evaluate candidate recommendations
    Policy->>DB: Save recommendations (Auto-approve SMS; Flag Voucher for HITL)
    API-->>Operator: 200 OK (InvestigationResponse: CRITICAL risk, 2 Recommendations)

    Note over Operator,API: 6. Human-in-the-Loop RBAC Gate
    Operator->>API: POST /intelligence/recommendations/$REC_ID/approve (as INTERN)
    API-->>Operator: 403 Forbidden (RBAC violation: INTERN role not permitted)
    Operator->>API: POST /intelligence/recommendations/$REC_ID/approve (as OPS_LEAD)
    API-->>Operator: 200 OK (RecommendationResponse: APPROVED)

    Operator->>API: 7. POST /intelligence/recommendations/$REC_ID/execute
    API->>Exec: Dispatch simulated recovery
    Exec->>DB: Write RecoveryExecutionAudit (is_simulated=True)
    API-->>Operator: 200 OK (status: EXECUTED)

    Operator->>API: 7b. Replay duplicate POST /execute
    Exec-->>API: Duplicate key detected
    API-->>Operator: 200 OK (status: ALREADY_EXECUTED, zero side-effects)

    Operator->>API: 8. GET /intelligence/audit/$ORDER_ID
    API->>DB: SELECT from recovery_execution_audits
    API-->>Operator: 200 OK (List of ExecutionAuditResponse)
```

---

### Step 1: Health & Readiness Check

Verify that all four critical pillars (Database, ML Artifacts, Configuration, and Multi-Agent Orchestrator) are healthy:

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/health/ready" -H "Accept: application/json"
```

**Expected Response (`200 OK`)**:
```json
{
  "status": "ready",
  "environment": "development",
  "execution_mode": "SIMULATION",
  "timestamp": "2026-11-19T13:00:00.000Z",
  "checks": {
    "database": { "status": "healthy", "engine": "sqlite" },
    "ml_artifacts": { "status": "healthy", "version": "2.5.0", "task_a": true, "task_c2": true },
    "configuration": { "status": "healthy", "auth_mode": "jwt_dev_enabled" },
    "orchestrator": { "status": "healthy", "langgraph": "initialized" }
  }
}
```

---

### Step 2: Acquire Operator Demonstration Credentials

Acquire a cryptographically signed HMAC-SHA256 bearer token for an `OPS_LEAD` console session:

```bash
export OPS_LEAD_TOKEN=$(curl -s -X POST "http://127.0.0.1:8000/api/v1/auth/dev-token" \
  -H "Content-Type: application/json" \
  -d '{"operator_profile": "ops_lead"}' | jq -r .access_token)
```

**Expected Response Shape (`200 OK`)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "operator_identity": "dev_ops_lead_console",
  "operator_role": "OPS_LEAD",
  "expires_in_seconds": 7200,
  "environment": "development",
  "warning": "DEVELOPMENT ONLY: This token generator is strictly disabled in staging and production."
}
```

---

### Step 3: Ingest Synthetic Order & Verify Provenance

Generate a synthetic order seeded in the `RESTAURANT_DELAY` state:

```bash
GEN_RESP=$(curl -s -X POST "http://127.0.0.1:8000/api/v1/simulation/generate" \
  -H "Content-Type: application/json" \
  -d '{"scenario": "RESTAURANT_DELAY", "count": 1, "seed": 42}')

export ORDER_ID=$(echo $GEN_RESP | jq -r '.order_ids[0]')
echo "Generated Order ID: $ORDER_ID"
```

**Actual Response Shape (`SimulationGenerateResponse`, `200 OK`)**:
```json
{
  "status": "success",
  "scenario": "RESTAURANT_DELAY",
  "generated_count": 1,
  "order_ids": [
    "<generated-order-uuid>"
  ],
  "run_id": "demo_restaurant_delay_3a7f8b9c",
  "data_source": "SYNTHETIC",
  "created_at": "2026-11-19T13:00:01.120Z"
}
```

#### Order Provenance Inspection
Querying the generated order demonstrates strict data isolation:
- `data_source`: `"SYNTHETIC"` (segregated from historical public datasets).
- `order_status`: `"IN_KITCHEN"`
- `created_at`: Set dynamically relative to `now()` ($T - 25\text{ minutes}$).
- `promised_delivery_at`: Set to $T + 15\text{ minutes}$ (total promised SLA: 40 minutes).

---

### Step 4: Inject Operational Delay Telemetry Events

Inject two synthetic telemetry events into the order timeline: a kitchen backlog event and a courier allotment friction event.

#### 4a. Restaurant Kitchen Backlog Event
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/simulation/events" \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER_ID\",
    \"event_type\": \"RESTAURANT_PREPARATION_DELAY\",
    \"metadata\": {
      \"prep_delay_min\": 18.5,
      \"kitchen_queue_depth\": 8,
      \"station\": \"tandoor_grill\"
    },
    \"data_source\": \"SYNTHETIC\"
  }"
```

**Actual Response Shape (`OrderEventResponse`, `200 OK`)**:
```json
{
  "id": "<event-uuid-1>",
  "order_id": "<generated-order-uuid>",
  "event_type": "RESTAURANT_PREPARATION_DELAY",
  "event_timestamp": "2026-11-19T12:50:00.000Z",
  "metadata": {
    "prep_delay_min": 18.5,
    "kitchen_queue_depth": 8,
    "station": "tandoor_grill"
  },
  "data_source": "SYNTHETIC",
  "created_at": "2026-11-19T13:00:02.000Z"
}
```

#### 4b. Courier Allotment Delay Event
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/simulation/events" \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER_ID\",
    \"event_type\": \"COURIER_ASSIGNMENT_DELAY\",
    \"metadata\": {
      \"allotment_delay_min\": 11.0,
      \"rejections_count\": 2
    },
    \"data_source\": \"SYNTHETIC\"
  }"
```

---

### Step 5: Dispatch LangGraph Multi-Agent Investigation

Trigger an automated investigation across the 4 specialized agents:

```bash
INV_RESP=$(curl -s -X POST "http://127.0.0.1:8000/api/v1/intelligence/investigate/$ORDER_ID" \
  -H "Accept: application/json")

export REC_ID=$(echo $INV_RESP | jq -r '.recommendations[] | select(.action_type=="APOLOGY_CREDIT_VOUCHER") | .id')
echo "Target Voucher Recommendation ID: $REC_ID"
```

**Actual Response Shape (`InvestigationResponse`, `200 OK`)**:
```json
{
  "id": "<investigation-uuid>",
  "order_id": "<generated-order-uuid>",
  "status": "COMPLETED",
  "risk_tier": "CRITICAL",
  "trigger_event": "MANUAL_OPERATOR_TRIGGER",
  "eta_p10": 19.67,
  "eta_p50": 30.07,
  "eta_p90": 49.35,
  "eta_interval_width": 29.68,
  "is_long_tail": true,
  "cancellation_probability": null,
  "cancellation_alert_budget_10k": false,
  "ml_provenance": {
    "model_version": "2.5.0",
    "task_a_quantile": "P10_P50_P90",
    "task_c2_evaluated": false,
    "task_c2_reason": "Order evaluated prior to landmark window (t_allot + 5 min)"
  },
  "restaurant_evidence": {
    "reported_prep_delay_min": 18.5,
    "kitchen_queue_depth": 8
  },
  "delivery_evidence": {
    "allotment_delay_min": 11.0
  },
  "agent_reasoning": {
    "order_intelligence": "Predicted P90 duration of 49.4m exceeds SLA threshold. Risk escalated to CRITICAL.",
    "restaurant_coordination": "Kitchen backlog confirmed (+18.5m). Expedite kitchen notification recommended.",
    "delivery_intelligence": "Courier allotment delayed (+11m). Alternate courier reassignment evaluated.",
    "customer_resolution": "High dissatisfaction risk. Proactive notification and goodwill credit voucher recommended."
  },
  "workflow_execution": {
    "nodes_visited": ["order_agent", "restaurant_agent", "delivery_agent", "customer_resolution_agent"],
    "execution_time_ms": 28.5
  },
  "recommendations": [
    {
      "id": "<rec-uuid-1>",
      "investigation_id": "<investigation-uuid>",
      "order_id": "<generated-order-uuid>",
      "action_type": "PROACTIVE_CUSTOMER_NOTIFICATION",
      "title": "Proactive Customer Delay Notification",
      "rationale": "Order elapsed time approaching promised delivery window with active kitchen backlog.",
      "sensitivity_level": "LOW",
      "estimated_impact": "WISMO reduction (-35%)",
      "requires_approval": false,
      "approval_status": "APPROVED",
      "approved_by": "AUTONOMOUS_POLICY_ENGINE",
      "operator_role": null,
      "approval_notes": "Auto-approved by PolicyEngine under non-intrusive threshold.",
      "approval_timestamp": "2026-11-19T13:00:03.500Z",
      "expires_at": "2026-11-19T13:30:03.500Z",
      "execution_status": "PENDING",
      "execution_payload": {
        "channel": "SIMULATED_PUSH_NOTIFICATION",
        "headline": "We're closely tracking your order"
      },
      "created_at": "2026-11-19T13:00:03.500Z",
      "updated_at": "2026-11-19T13:00:03.500Z"
    },
    {
      "id": "<rec-uuid-2>",
      "investigation_id": "<investigation-uuid>",
      "order_id": "<generated-order-uuid>",
      "action_type": "APOLOGY_CREDIT_VOUCHER",
      "title": "Autonomous Apology Wallet Credit (₹50)",
      "rationale": "Severe cumulative delay exceeding +18m SLA breach requires financial appeasement.",
      "sensitivity_level": "HIGH",
      "estimated_impact": "Customer churn mitigation (0.94 score)",
      "requires_approval": true,
      "approval_status": "AWAITING_APPROVAL",
      "approved_by": null,
      "operator_role": null,
      "approval_notes": null,
      "approval_timestamp": null,
      "expires_at": "2026-11-19T13:30:03.500Z",
      "execution_status": "PENDING",
      "execution_payload": {
        "credit_amount_inr": 50.0,
        "wallet_type": "SIMULATED_SWIGGY_MONEY"
      },
      "created_at": "2026-11-19T13:00:03.500Z",
      "updated_at": "2026-11-19T13:00:03.500Z"
    }
  ],
  "created_at": "2026-11-19T13:00:03.500Z",
  "updated_at": "2026-11-19T13:00:03.500Z"
}
```

---

### Step 6: Human-in-the-Loop Governance & Role Verification

The policy engine automatically approved the non-intrusive notification, but flagged the ₹50 wallet credit for mandatory human approval.

#### 6a. Attempt Approval with Unauthorized Role (`INTERN`)
```bash
# Acquire intern bearer token
INTERN_TOKEN=$(curl -s -X POST "http://127.0.0.1:8000/api/v1/auth/dev-token" \
  -H "Content-Type: application/json" \
  -d '{"operator_profile": "intern"}' | jq -r .access_token)

# Attempt approval as INTERN
curl -X POST "http://127.0.0.1:8000/api/v1/intelligence/recommendations/$REC_ID/approve" \
  -H "Authorization: Bearer $INTERN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Unauthorized intern approval attempt"}'
```

**Actual Response (`HTTP 403 Forbidden`)**:
```json
{
  "detail": "Authorization denied: Role 'INTERN' is not permitted to approve recovery operations."
}
```
*Role Enforcement Proof*: As defined in [`PolicyEngine.AUTHORIZED_ROLES`](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/backend/app/services/policy_engine.py), only `OPERATOR`, `OPS_LEAD`, `ADMIN`, or `SUPERVISOR` can approve sensitive actions.

#### 6b. Approve with Authorized Role (`OPS_LEAD`)
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/intelligence/recommendations/$REC_ID/approve" \
  -H "Authorization: Bearer $OPS_LEAD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Verified kitchen delay > 18m. Approved simulated goodwill credit."}'
```

**Actual Response Shape (`RecommendationResponse`, `200 OK`)**:
```json
{
  "id": "<rec-uuid-2>",
  "investigation_id": "<investigation-uuid>",
  "order_id": "<generated-order-uuid>",
  "action_type": "APOLOGY_CREDIT_VOUCHER",
  "title": "Autonomous Apology Wallet Credit (₹50)",
  "rationale": "Severe cumulative delay exceeding +18m SLA breach requires financial appeasement.",
  "sensitivity_level": "HIGH",
  "estimated_impact": "Customer churn mitigation (0.94 score)",
  "requires_approval": true,
  "approval_status": "APPROVED",
  "approved_by": "dev_ops_lead_console",
  "operator_role": "OPS_LEAD",
  "approval_notes": "Verified kitchen delay > 18m. Approved simulated goodwill credit.",
  "approval_timestamp": "2026-11-19T13:00:04.100Z",
  "expires_at": "2026-11-19T13:30:03.500Z",
  "execution_status": "PENDING",
  "execution_payload": {
    "credit_amount_inr": 50.0,
    "wallet_type": "SIMULATED_SWIGGY_MONEY"
  },
  "created_at": "2026-11-19T13:00:03.500Z",
  "updated_at": "2026-11-19T13:00:04.100Z"
}
```

---

### Step 7: Execute Simulated Recovery & Verify Cryptographic Idempotency

#### 7a. Execute Approved Recommendation
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/intelligence/recommendations/$REC_ID/execute" \
  -H "Authorization: Bearer $OPS_LEAD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Actual Response Shape (`200 OK`)**:
```json
{
  "status": "EXECUTED",
  "audit_id": "<audit-uuid-1>",
  "action_type": "APOLOGY_CREDIT_VOUCHER",
  "execution_result": {
    "action": "APOLOGY_CREDIT_VOUCHER",
    "amount_inr": 50.0,
    "wallet_credited": true,
    "churn_mitigation_score": 0.94
  },
  "is_simulated": true,
  "idempotency_key": "d280ee725a841427dba53fbad503fc39f7543bead893708e1a631f478a514d7a",
  "executed_at": "2026-11-19T13:00:04.500Z"
}
```

#### 7b. Duplicate Replay Attack Verification
Re-submitting the exact same execution request:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/intelligence/recommendations/$REC_ID/execute" \
  -H "Authorization: Bearer $OPS_LEAD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Actual Response Shape (`200 OK` - Idempotent Skip)**:
```json
{
  "status": "ALREADY_EXECUTED",
  "message": "Recommendation was already executed (idempotent replay).",
  "audit_id": "<audit-uuid-1>",
  "idempotency_key": "d280ee725a841427dba53fbad503fc39f7543bead893708e1a631f478a514d7a",
  "execution_result": {
    "action": "APOLOGY_CREDIT_VOUCHER",
    "amount_inr": 50.0,
    "wallet_credited": true,
    "churn_mitigation_score": 0.94
  }
}
```
*Crucial Safety Guarantee*: No redundant financial credits or notification spam can occur on replayed calls.

---

### Step 8: Query Immutable Execution Audit Trail

Retrieve the cryptographically stamped execution audit record for the order:

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/intelligence/audit/$ORDER_ID" \
  -H "Accept: application/json"
```

**Actual Response Shape (`List[ExecutionAuditResponse]`, `200 OK`)**:
```json
[
  {
    "id": "<audit-uuid-1>",
    "recommendation_id": "<rec-uuid-2>",
    "order_id": "<generated-order-uuid>",
    "action_type": "APOLOGY_CREDIT_VOUCHER",
    "initial_order_status": "IN_KITCHEN",
    "final_order_status": "IN_KITCHEN",
    "idempotency_key": "d280ee725a841427dba53fbad503fc39f7543bead893708e1a631f478a514d7a",
    "trigger_reason": "Severe cumulative delay exceeding +18m SLA breach requires financial appeasement.",
    "ml_model_version": "2.5.0",
    "approval_identity": "dev_ops_lead_console",
    "approval_timestamp": "2026-11-19T13:00:04.100Z",
    "execution_result": {
      "action": "APOLOGY_CREDIT_VOUCHER",
      "amount_inr": 50.0,
      "wallet_credited": true,
      "churn_mitigation_score": 0.94
    },
    "recovery_outcome": "SUCCESS",
    "is_simulated": true,
    "executed_at": "2026-11-19T13:00:04.500Z"
  },
  {
    "id": "<audit-uuid-2>",
    "recommendation_id": "<rec-uuid-1>",
    "order_id": "<generated-order-uuid>",
    "action_type": "PROACTIVE_CUSTOMER_NOTIFICATION",
    "initial_order_status": "IN_KITCHEN",
    "final_order_status": "IN_KITCHEN",
    "idempotency_key": "203a7eb9fcc6f214333c9f807a75734a8e2cb3788ff3925c162fbd65cfb12de9",
    "trigger_reason": "Order elapsed time approaching promised delivery window with active kitchen backlog.",
    "ml_model_version": "2.5.0",
    "approval_identity": "AUTONOMOUS_POLICY_ENGINE",
    "approval_timestamp": "2026-11-19T13:00:03.500Z",
    "execution_result": {
      "action": "PROACTIVE_CUSTOMER_NOTIFICATION",
      "channel": "SIMULATED_IN_APP_PUSH",
      "delivery_success": true,
      "wismo_deflection_probability": 0.88
    },
    "recovery_outcome": "SUCCESS",
    "is_simulated": true,
    "executed_at": "2026-11-19T13:00:03.550Z"
  }
]
```

---

## 3. Strict Boundary: How Simulation Differs From Live Swiggy Integration

It is vital for technical reviewers and platform operators to distinguish this portfolio prototype from a live commercial deployment:

| Architecture Dimension | ResolveAI Prototype (Actual Implementation) | Hypothetical Live Swiggy Production Integration (Future) |
| :--- | :--- | :--- |
| **Order Ingestion** | Local relational tables (`orders`, `order_events`) generated by `OrderSimulator`. | Apache Kafka order lifecycle topics with schema registry validation. |
| **Restaurant Telemetry** | Simulated HTTP events (`RESTAURANT_PREPARATION_DELAY`) posted via `/simulation/events`. | POS / Kitchen Display System (KDS) webhooks and merchant tablet telemetry. |
| **Courier Telemetry** | Static haversine coordinates and simulated allotment intervals. | Continuous GPS telematics, turn-by-turn velocity, and rider mobile app webhooks. |
| **Customer Notifications** | Written to local `order_events` table (`SIMULATED_PUSH_NOTIFICATION`). | Live telecom gateways (Gupshup, Twilio) and Swiggy mobile app APNs / FCM push notifications. |
| **Financial Credits** | Recorded as metadata in `RecoveryExecutionAudit` rows (`SIMULATED_SWIGGY_MONEY`). | Double-entry financial ledgers, Swiggy Money wallet API, and payment gateway refunds. |
| **Execution Safety Mode** | Hardcoded to `SIMULATION` or `SHADOW`. `LIVE` execution is strictly blocked at startup. | Production execution service connected to partner APIs with mutual TLS (mTLS). |
| **Business Impact Claims** | Simulator-derived estimates under stated assumptions. | Measured causal impact evaluated via A/B cluster switchbacks. |
