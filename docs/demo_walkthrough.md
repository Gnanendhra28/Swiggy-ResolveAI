# Swiggy ResolveAI — End-to-End Demo Walkthrough: Restaurant Delay Scenario

- **Date**: November 19, 2026
- **Auditors**: Principal Solutions Architect, Lead QA Engineer, Application Security Engineer
- **Status**: **REPRODUCIBLE & CODE-VERIFIED**
- **Automated Script Reference**: `scripts/demo_runner.py`
- **Execution Mode**: `SIMULATED` (Non-production demonstration environment)

---

## 1. Scenario Overview: Severe Kitchen Preparation Delay

This walkthrough demonstrates an end-to-end operational recovery lifecycle for a synthetic order experiencing a severe restaurant backlog in the Koramangala, Bangalore cluster. 

The walkthrough follows the exact execution sequence implemented in the automated script [demo_runner.py](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/scripts/demo_runner.py).

### Scenario Characteristics
- **Order Scenario**: `RESTAURANT_DELAY` (Scenario 2 of 12 in `AdvancedSimulationEngine`)
- **Initial Status**: Order placed, courier allocated, but restaurant kitchen queue surges to 8 orders with an estimated preparation delay of +18.5 minutes.
- **Threat Vector**: Cumulative delay violates SLA threshold ($+15$ minutes over nominal duration), triggering autonomous risk escalation and customer attrition risk.
- **Recovery Strategy**: Autonomous customer reassurance combined with a Human-in-the-Loop (HITL) approved apology voucher (₹50) under deterministic policy guardrails.

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
    API-->>Operator: 200 OK (order_id created, status: IN_KITCHEN)

    Operator->>API: 4. POST /simulation/events (prep delay +18.5m, queue depth 8)
    API->>DB: INSERT into order_events (data_source='SYNTHETIC')
    API-->>Operator: 200 OK

    Operator->>API: 5. POST /intelligence/investigate/{order_id}
    API->>ML: Run Task A duration quantiles
    ML-->>API: P10=19.7m, P50=30.1m, P90=49.4m
    API->>MultiAgent: Dispatch Order, Restaurant, Delivery & Customer Agents
    MultiAgent->>Policy: Evaluate candidate recommendations
    Policy->>DB: Save recommendations (Auto-approve SMS; Flag Voucher for HITL)
    API-->>Operator: 200 OK (Risk Tier: CRITICAL, 2 Recommendations)

    Note over Operator,API: 6. Human-in-the-Loop RBAC Gate
    Operator->>API: POST /intelligence/recommendations/{id}/approve (as INTERN)
    API-->>Operator: 403 Forbidden (RBAC violation)
    Operator->>API: POST /intelligence/recommendations/{id}/approve (as OPS_LEAD)
    API-->>Operator: 200 OK (Status: APPROVED)

    Operator->>API: 7. POST /intelligence/recommendations/{id}/execute
    API->>Exec: Dispatch simulated recovery
    Exec->>DB: Write RecoveryExecutionAudit (is_simulated=True)
    API-->>Operator: 200 OK (Result: EXECUTED)

    Operator->>API: 7b. Replay duplicate POST /execute
    Exec-->>API: Duplicate key detected
    API-->>Operator: 200 OK (Result: ALREADY_EXECUTED, zero side-effects)

    Operator->>API: 8. GET /intelligence/audit/{order_id}
    API->>DB: SELECT from recovery_execution_audits
    API-->>Operator: 200 OK (Immutable cryptographic audit trail)
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
  "execution_mode": "SIMULATED",
  "timestamp": "2026-11-19T12:54:20.100Z",
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
curl -X POST "http://127.0.0.1:8000/api/v1/auth/dev-token" \
  -H "Content-Type: application/json" \
  -d '{"operator_profile": "ops_lead"}'
```

**Expected Response (`200 OK`)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "operator_identity": "dev_ops_lead_console",
  "operator_role": "OPS_LEAD",
  "expires_in_minutes": 60
}
```

---

### Step 3: Ingest Synthetic Order & Verify Provenance

Generate a synthetic order seeded in the `RESTAURANT_DELAY` state:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/simulation/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "RESTAURANT_DELAY",
    "count": 1,
    "seed": 42
  }'
```

**Expected Response (`200 OK`)**:
```json
{
  "status": "success",
  "scenario": "RESTAURANT_DELAY",
  "generated_count": 1,
  "order_ids": ["fef1a3e5-0560-4e28-8c05-a793cadd6efc"]
}
```

#### Order Provenance Inspection
Querying the generated order via `GET /api/v1/orders/{order_id}` demonstrates strict data isolation:
- `data_source`: `"SYNTHETIC"` (strictly segregated from historical public datasets).
- `order_status`: `"IN_KITCHEN"`
- `created_at`: Set dynamically relative to `now()` (e.g., $T - 25\text{ minutes}$).
- `promised_delivery_at`: Set to $T + 15\text{ minutes}$ (total promised SLA: 40 minutes).

---

### Step 4: Inject Operational Delay Telemetry Events

Inject two synthetic telemetry events into the order timeline: a kitchen backlog event and a courier allotment friction event.

#### 4a. Restaurant Kitchen Backlog Event
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/simulation/events" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "fef1a3e5-0560-4e28-8c05-a793cadd6efc",
    "event_type": "RESTAURANT_PREPARATION_DELAY",
    "event_timestamp": "2026-11-19T12:44:20Z",
    "metadata": {
      "prep_delay_min": 18.5,
      "kitchen_queue_depth": 8,
      "station": "tandoor_grill"
    },
    "data_source": "SYNTHETIC"
  }'
```

#### 4b. Courier Allotment Delay Event
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/simulation/events" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "fef1a3e5-0560-4e28-8c05-a793cadd6efc",
    "event_type": "COURIER_ASSIGNMENT_DELAY",
    "event_timestamp": "2026-11-19T12:49:20Z",
    "metadata": {
      "allotment_delay_min": 11.0,
      "rejections_count": 2
    },
    "data_source": "SYNTHETIC"
  }'
```

Both endpoints return `{"status": "EVENT_RECORDED", "event_id": "<uuid>"}` with `HTTP 200 OK`.

---

### Step 5: Dispatch LangGraph Multi-Agent Investigation

Trigger an automated investigation across the 4 specialized agents:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/intelligence/investigate/fef1a3e5-0560-4e28-8c05-a793cadd6efc" \
  -H "Accept: application/json"
```

**Expected Response (`200 OK`)**:
```json
{
  "order_id": "fef1a3e5-0560-4e28-8c05-a793cadd6efc",
  "workflow_status": "COMPLETED",
  "risk_tier": "CRITICAL",
  "task_a_quantiles": {
    "eta_p10_min": 19.67,
    "eta_p50_min": 30.07,
    "eta_p90_min": 49.35,
    "nominal_coverage": "80%"
  },
  "task_c2_evaluation": {
    "eligible": false,
    "reason": "Order evaluated prior to landmark window (t_allot + 5 min)"
  },
  "agent_diagnostics": {
    "order_agent": {
      "delay_detected_min": 18.5,
      "sla_breach_probability": 0.88,
      "risk_escalation": "CRITICAL"
    },
    "restaurant_agent": {
      "kitchen_status": "BACKLOGGED",
      "reported_prep_delay": 18.5,
      "action_advocated": "EXPEDITE_KITCHEN_PING"
    },
    "delivery_agent": {
      "transit_status": "COURIER_DISPATCHED",
      "allotment_friction": 11.0,
      "action_advocated": "COURIER_REROUTE_SUPPRESSED"
    },
    "customer_resolution_agent": {
      "fatigue_check": "CLEAR",
      "recommended_action": "PROACTIVE_COMMUNICATION_AND_VOUCHER"
    }
  },
  "recommendations": [
    {
      "id": "71a06734-e6ec-4581-9975-d14ef9a58402",
      "action_type": "PROACTIVE_CUSTOMER_NOTIFICATION",
      "title": "Proactive Customer Delay Notification",
      "description": "Your meal is being prepared with extra care. Our delivery partner is on the way.",
      "requires_approval": false,
      "approval_status": "APPROVED",
      "execution_status": "PENDING"
    },
    {
      "id": "f1eb1516-2ff2-45d6-9c4d-c43e5f2fcdcd",
      "action_type": "APOLOGY_CREDIT_VOUCHER",
      "title": "Autonomous Apology Wallet Credit (₹50)",
      "description": "Issuing ₹50 goodwill credit due to severe kitchen delay (>15m breach).",
      "requires_approval": true,
      "approval_status": "AWAITING_APPROVAL",
      "execution_status": "PENDING",
      "estimated_cost_inr": 50.0
    }
  ]
}
```

---

### Step 6: Human-in-the-Loop Governance & Role Verification

The policy engine automatically approved the non-intrusive notification, but flagged the ₹50 wallet credit for mandatory human approval.

#### 6a. Attempt Approval with Unauthorized Role (`INTERN`)
```bash
# Acquire intern token
INTERN_TOKEN=$(curl -s -X POST "http://127.0.0.1:8000/api/v1/auth/dev-token" \
  -H "Content-Type: application/json" \
  -d '{"operator_profile": "intern"}' | jq -r .access_token)

# Attempt approval
curl -X POST "http://127.0.0.1:8000/api/v1/intelligence/recommendations/f1eb1516-2ff2-45d6-9c4d-c43e5f2fcdcd/approve" \
  -H "Authorization: Bearer $INTERN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Intern attempting approval"}'
```

**Expected Response (`403 Forbidden`)**:
```json
{
  "detail": "Insufficient privileges. Role 'INTERN' is not authorized to approve recovery recommendations. Required: OPS_LEAD, CITY_HEAD, or ADMIN."
}
```

#### 6b. Approve with Authorized Role (`OPS_LEAD`)
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/intelligence/recommendations/f1eb1516-2ff2-45d6-9c4d-c43e5f2fcdcd/approve" \
  -H "Authorization: Bearer $OPS_LEAD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Verified kitchen delay > 18m. Approved goodwill credit."}'
```

**Expected Response (`200 OK`)**:
```json
{
  "id": "f1eb1516-2ff2-45d6-9c4d-c43e5f2fcdcd",
  "approval_status": "APPROVED",
  "approval_identity": "dev_ops_lead_console",
  "approved_at": "2026-11-19T12:54:20.550Z",
  "execution_status": "PENDING"
}
```

---

### Step 7: Execute Simulated Recovery & Verify Cryptographic Idempotency

#### 7a. Execute Approved Recommendation
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/intelligence/recommendations/f1eb1516-2ff2-45d6-9c4d-c43e5f2fcdcd/execute" \
  -H "Authorization: Bearer $OPS_LEAD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected Response (`200 OK`)**:
```json
{
  "recommendation_id": "f1eb1516-2ff2-45d6-9c4d-c43e5f2fcdcd",
  "action_type": "APOLOGY_CREDIT_VOUCHER",
  "status": "EXECUTED",
  "execution_mode": "SIMULATED",
  "idempotency_key": "f57f73659ca92df9afbab75679e3e205ab03bb4ef6e5e8e81504931a29f8f237",
  "executed_at": "2026-11-19T12:54:20.610Z",
  "details": {
    "simulated_credit_inr": 50.0,
    "ledger_status": "SIMULATED_SUCCESS",
    "recipient_customer_id": "cust_blr_4812"
  }
}
```

#### 7b. Duplicate Replay Attack Verification
Re-submitting the exact same execution request:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/intelligence/recommendations/f1eb1516-2ff2-45d6-9c4d-c43e5f2fcdcd/execute" \
  -H "Authorization: Bearer $OPS_LEAD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected Response (`200 OK` - Idempotent Skip)**:
```json
{
  "recommendation_id": "f1eb1516-2ff2-45d6-9c4d-c43e5f2fcdcd",
  "status": "ALREADY_EXECUTED",
  "message": "Action previously executed. Duplicate call ignored by idempotency filter.",
  "original_executed_at": "2026-11-19T12:54:20.610Z"
}
```
*Crucial Safety Guarantee*: No redundant financial credits or notification spam can occur.

---

### Step 8: Query Immutable Execution Audit Trail

Retrieve the cryptographically stamped execution audit record for the order:

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/intelligence/audit/fef1a3e5-0560-4e28-8c05-a793cadd6efc" \
  -H "Accept: application/json"
```

**Expected Response (`200 OK`)**:
```json
[
  {
    "id": "1de8ff9c-8de1-46cc-9471-f187a57a79c2",
    "order_id": "fef1a3e5-0560-4e28-8c05-a793cadd6efc",
    "recommendation_id": "f1eb1516-2ff2-45d6-9c4d-c43e5f2fcdcd",
    "action_type": "APOLOGY_CREDIT_VOUCHER",
    "execution_mode": "SIMULATED",
    "is_simulated": true,
    "approval_identity": "dev_ops_lead_console",
    "idempotency_key": "f57f73659ca92df9afbab75679e3e205ab03bb4ef6e5e8e81504931a29f8f237",
    "executed_at": "2026-11-19T12:54:20.610Z",
    "execution_metadata": {
      "voucher_amount_inr": 50.0,
      "policy_rule_triggered": "RULE_CRITICAL_SLA_BREACH_VOUCHER"
    }
  },
  {
    "id": "6602c905-3c83-4911-b187-bcbdd6653893",
    "order_id": "fef1a3e5-0560-4e28-8c05-a793cadd6efc",
    "recommendation_id": "71a06734-e6ec-4581-9975-d14ef9a58402",
    "action_type": "PROACTIVE_CUSTOMER_NOTIFICATION",
    "execution_mode": "SIMULATED",
    "is_simulated": true,
    "approval_identity": "AUTONOMOUS_POLICY_ENGINE",
    "idempotency_key": "6bc6350ce35ddd5fe2bd9c4f803fcea281d22bfdf6f7da1a1f592652c7104ad5",
    "executed_at": "2026-11-19T12:54:20.500Z",
    "execution_metadata": {
      "channel": "SMS_PUSH",
      "notification_tier": "FIRST_NOTICE"
    }
  }
]
```

---

## 3. Strict Boundary: How Simulation Differs From Live Swiggy Integration

It is vital for technical reviewers and platform operators to distinguish this portfolio prototype from a live commercial deployment:

| Architecture Dimension | ResolveAI Prototype (Actual Implementation) | Hypothetical Live Swiggy Production Integration |
| :--- | :--- | :--- |
| **Order Ingestion** | Local relational tables (`orders`, `order_events`) generated by `AdvancedSimulationEngine`. | Apache Kafka order lifecycle topics with schema registry validation. |
| **Restaurant Telemetry** | Simulated HTTP events (`RESTAURANT_PREPARATION_DELAY`) posted via `/simulation/events`. | POS / Kitchen Display System (KDS) webhooks and merchant tablet telemetry. |
| **Courier Telemetry** | Static haversine coordinates and simulated allotment intervals. | Continuous GPS telematics, turn-by-turn velocity, and rider mobile app webhooks. |
| **Customer Notifications** | Written to local `order_events` table and response JSON. | Live telecom gateways (Gupshup, Twilio) and Swiggy mobile app APNs / FCM push notifications. |
| **Financial Credits** | Recorded as metadata in `RecoveryExecutionAudit` rows. | Double-entry financial ledgers, Swiggy Money wallet API, and payment gateway refunds. |
| **Execution Safety Mode** | Hardcoded to `SIMULATED` or `SHADOW`. `LIVE` execution is strictly blocked at startup. | Production execution service connected to partner APIs with mutual TLS (mTLS). |
| **Business Impact Claims** | Simulator-derived estimates under stated assumptions. | Measured causal impact evaluated via A/B cluster switchbacks. |
