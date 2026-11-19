# Swiggy ResolveAI — System Architecture Blueprint

## 1. Executive Architecture Overview

**Swiggy ResolveAI** is an autonomous, AI-driven order resolution and proactive customer experience recovery platform designed for high-throughput food delivery ecosystems. The system detects operational disruptions in real time (merchant kitchen bottlenecks, delivery courier assignment delays, transit corridor congestion, and post-allotment order cancellation risks), conducts structured multi-agent investigations, and executes calibrated recovery workflows under strict human-in-the-loop and policy guardrails.

The platform follows a **Modular Monolith** pattern adhering strictly to **Clean Architecture** and **SOLID** principles, ensuring clear separation of concerns, high testability, low operational complexity, and seamless local or containerized deployment without distributed microservices overhead.

```mermaid
flowchart TD
    subgraph ClientLayer["Presentation Layer (Client)"]
        UI["Next.js 16 / React 19 Dashboard\n(SSR + Turbopack + TailwindCSS)"]
        CLI["Ops CLI / Automated Telemetry Stream"]
    end

    subgraph APILayer["FastAPI Presentation & Ingestion Layer"]
        CORS["CORS & Request Correlation Middleware"]
        Router["FastAPI Application Router (37 Endpoints)"]
        Health["4-Pillar Health Diagnostics\n(/health, /health/live, /health/ready)"]
    end

    subgraph IntelligenceLayer["Application & Intelligence Core"]
        OrderSvc["Order & Telemetry Management Service"]
        MLService["MLInferenceService (Phase 2.5 Multi-Task Pipeline)\n• Task A: LightGBM P10/P50/P90 ETA Regressors\n• Task C2: Isotonic Landmark Cancellation Risk\n• Tasks B/C1: Isolated Research Models"]
        LangGraphWorkflow["LangGraph Multi-Agent Investigation StateGraph"]
        PolicyEngine["PolicyEngine & Safety Guardrails\n• Role-Based Access Control (RBAC)\n• Communication Consent Verification\n• 30-Minute Recommendation Expiration\n• Order State Drift Prevention\n• Cryptographic Idempotency Enforcement"]
        RecoveryExec["RecoveryExecutionService (Simulated Actions Engine)"]
        SimEngine["Monte Carlo Simulation & Experimentation Engine\n• 12 Delivery Scenarios\n• 4 Comparative Recovery Strategies\n• Paired Bootstrap 95% Confidence Intervals"]
    end

    subgraph DataLayer["Infrastructure & Persistence Layer"]
        DB[(PostgreSQL / SQLite Storage Engine\nSQLAlchemy 2.x ORM + Alembic Migrations 001-005)]
        Cache[(Redis Event & Telemetry Cache - Optional)]
        MLStore["Serialized Model Artifacts (data/artifacts/models/phase_2_5)"]
    end

    UI --> Router
    CLI --> Router
    Router --> OrderSvc
    Router --> IntelligenceLayer
    OrderSvc --> DB
    IntelligenceLayer --> DB
    MLService --> MLStore
    IntelligenceLayer --> Cache
```

---

## 2. Clean Architecture Layering

The codebase is organized into four concentric layers to decouple business domain entities from external libraries, database drivers, and UI frameworks:

```mermaid
flowchart LR
    subgraph Layer4["Presentation Layer"]
        API["FastAPI Endpoints\n(backend/app/api)"]
        WebUI["Next.js Pages & Components\n(frontend/src)"]
    end

    subgraph Layer3["Application Services Layer"]
        IntellSvc["IntelligenceService"]
        OrderSvc2["OrderService"]
        SimSvc["SimulationService"]
        Policy["PolicyEngine"]
        RecExec["RecoveryExecutionService"]
    end

    subgraph Layer2["Domain Intelligence Layer"]
        MultiAgent["LangGraph Multi-Agent Core\n(Order, Restaurant, Delivery, Resolution)"]
        MLPlatform["MLInferenceService & Preprocessing Pipeline"]
    end

    subgraph Layer1["Core Domain & Data Layer"]
        Models["SQLAlchemy Declarative Models\n(Order, Event, Customer, Restaurant, Audit)"]
        Schemas["Pydantic Domain Schemas"]
        DBBase["Database Session & Base Engine"]
    end

    Layer4 --> Layer3
    Layer3 --> Layer2
    Layer2 --> Layer1
```

### 2.1 Core Domain Layer (`backend/app/models/`)
Contains declarative SQLAlchemy entities with zero business logic dependencies:
- **`Order`**: Tracks lifecycle state (`PLACED`, `IN_KITCHEN`, `ALLOTTED`, `PICKED_UP`, `DELIVERED`, `CANCELLED`), order values, timestamps, and customer/restaurant references.
- **`OrderEvent`**: Append-only telemetry log capturing milestones and synthetic operational anomalies.
- **`Customer` & `Restaurant` & `DeliveryPartner`**: Core physical entities.
- **`OrderInvestigation` & `RecoveryRecommendation`**: AI investigation records and prioritized recovery candidate actions.
- **`RecoveryExecutionAudit`**: Cryptographically verifiable audit log with unique idempotency keys, operator identities, before/after states, and simulated execution payloads.

### 2.2 Application Services Layer (`backend/app/services/`)
Coordinates use cases, orchestrates transactions, and enforces operational policies:
- **`OrderService`**: Lifecycle mutations, validation, and historical order querying.
- **`IntelligenceService`**: Facade exposing investigation invocation, recommendation retrieval, operator approval gating, and execution triggering.
- **`PolicyEngine`**: Pure deterministic rule validator evaluating RBAC, customer consent, cooldown periods, time-to-live expiration, and state drift.
- **`RecoveryExecutionService`**: Executes approved recovery actions atomically with audit persistence.
- **`SimulationService` / `AdvancedSimulationEngine`**: Scientific evaluation framework running counterfactual policy comparisons.

### 2.3 Presentation Layer (`backend/app/api/` & `frontend/src/`)
- **FastAPI**: 37 type-safe REST endpoints with automated OpenAPI documentation and correlation ID tracking across authentication, orders, investigations, simulations, and system health.
- **Next.js 16**: Server-side and client-side React 19 dashboard featuring real-time telemetry tables, investigation debug drawers, interactive HITL approval consoles, and Monte Carlo simulation visualizers.

---

## 3. Machine Learning Intelligence Pipeline

ResolveAI integrates two distinct operational ML models persisted in Phase 2.5 (`data/artifacts/models/phase_2_5/`), alongside two isolated research models:

```mermaid
flowchart TD
    OrderInput["Incoming Order & Historical Telemetry"] --> FeatureExtract["Deterministic Preprocessing & Feature Extraction\n(Fitted Imputation: last_mile_distance = 2.67 km)"]
    
    FeatureExtract --> TaskA["Task A: Delivery Duration Uncertainty Regressors\n• 3 x LightGBM Regressors (objective='quantile')\n• alpha = 0.10, 0.50, 0.90\n• Monotonic Sorting Guarantee: P10 <= P50 <= P90"]
    
    FeatureExtract --> Eligibility{"Landmark Eligibility Check\nt >= t_allot + 5 min\nStatus != Terminal"}
    
    Eligibility -- "Eligible" --> TaskC2["Task C2: Landmark Post-Allotment Cancellation Risk\n• LightGBM Binary Classifier\n• Isotonic Calibrator (Strict Probability Calibration)\n• Alert Budget Thresholds:\n  - 5/1000 Alert Budget (Thresh = 0.6686)\n  - 10/1000 Alert Budget (Thresh = 0.5113)"]
    
    Eligibility -- "Ineligible" --> DegradedC2["Task C2 Marked Ineligible\nis_eligible=False\nOperational Action: Standby"]
    
    FeatureExtract -.-> ResearchB["Task B: Research Courier Assignment Model\n(Isolated from Automated Triggering)"]
    FeatureExtract -.-> ResearchC1["Task C1: Research Order-Time Cancellation Model\n(Isolated from Automated Triggering)"]

    TaskA --> OutputBundle["Unified MLInferenceResult Object"]
    TaskC2 --> OutputBundle
    DegradedC2 --> OutputBundle
```

### 3.1 Task A — Delivery Duration Uncertainty Regressors
- **Architecture**: 3 LightGBM regressors trained with pinball quantile loss at $\alpha \in \{0.10, 0.50, 0.90\}$.
- **Guarantee**: Monotonicity post-processing ensures $P10 \le P50 \le P90$ for every prediction without quantile crossing.
- **Interval Coverage**: 80% central prediction interval $[P10, P90]$ achieves ~95.8% empirical coverage across core delivery regimes (20–35 min).
- **Long-Tail Diagnostics**: Flags orders where $P90 - P50 > 15\text{ min}$ as extreme delivery uncertainty.

### 3.2 Task C2 — Calibrated Post-Allotment Cancellation Risk
- **Landmark Eligibility Gate**: Evaluated exclusively at $t \ge t_{\text{allot}} + 5\text{ minutes}$. Earlier orders or terminal orders are marked ineligible.
- **Model Architecture**: LightGBM binary classifier paired with scikit-learn `IsotonicRegression` probability calibrator.
- **Dual Budget Thresholds**:
  - `alert_budget_5_per_1000` (threshold = 0.6686): High-precision tier for severe risk.
  - `alert_budget_10_per_1000` (threshold = 0.5113): Medium-precision tier for active monitoring.
- **Safety Policy**: Does not trigger disruptive interventions; restricted to non-intrusive operational monitoring and proactive communication.

---

## 4. LangGraph Multi-Agent Architecture

When an order disruption or manual operator trigger occurs, the platform initiates a multi-agent debate and synthesis workflow orchestrated via **LangGraph**:

```mermaid
sequenceDiagram
    autonumber
    actor Ops as Operations Console / Telemetry Stream
    participant Router as Intelligence Router
    participant Graph as LangGraph Orchestrator
    participant OIA as OrderIntelligenceAgent
    participant RCA as RestaurantCoordinationAgent
    participant DIA as DeliveryIntelligenceAgent
    participant CRA as CustomerResolutionAgent
    participant Policy as PolicyEngine
    participant Exec as RecoveryExecutor
    participant DB as Audit & Persistence Store

    Ops->>Router: POST /api/v1/intelligence/investigate/{id}
    Router->>Graph: Invoke MultiAgentInvestigationState
    Graph->>OIA: Evaluate order lifecycle & run ML inference
    OIA-->>Graph: Populate Task A/C2 predictions & initial RiskTier
    
    par Parallel Investigation
        Graph->>RCA: Investigate kitchen latency & backlog
        Graph->>DIA: Investigate fleet allotment & transit route
    end
    RCA-->>Graph: RestaurantEvidence (prep delay, queue depth)
    DIA-->>Graph: DeliveryEvidence (allotment delay, reassignments)
    
    Graph->>CRA: Synthesize unified recovery plan
    Note over CRA: Gemini API LLM Synthesis\n(Falls back to deterministic rules on timeout/missing key)
    CRA-->>Graph: CustomerResolutionSynthesis & Ranked Recommendations
    Graph-->>Router: Completed MultiAgentInvestigationState
    
    Router->>Policy: Evaluate policy gates (Auto-Approve vs HITL)
    alt Auto-Approved (Low Sensitivity)
        Policy->>Exec: Dispatch simulated execution
        Exec->>DB: Record RecoveryExecutionAudit (Idempotency Key)
    else Requires Human Approval (High Sensitivity)
        Policy->>DB: Persist RecoveryRecommendation (AWAITING_APPROVAL)
    end
    Router-->>Ops: Return Investigation Response & Recommendations
```

### Specialized Agents:
1. **`OrderIntelligenceAgent`**:
   - Assesses lifecycle eligibility (rejects terminal orders).
   - Ingests Task A quantiles and Task C2 calibrated cancellation probabilities.
   - Computes projected delay against customer promised delivery time.
   - Assigns operational risk tier: `NOMINAL`, `MONITORED`, `HIGH_RISK`, or `CRITICAL`.
2. **`RestaurantCoordinationAgent`**:
   - Evaluates merchant acceptance latency and kitchen preparation timeline.
   - Distinguishes physical KDS telemetry from simulated peak backlogs.
   - Formulates kitchen bottleneck diagnoses.
3. **`DeliveryIntelligenceAgent`**:
   - Analyzes courier allotment latency, acceptance delays, and reassignment churn.
   - Detects extreme first-mile transit distances (>3.0 km) and corridor traffic congestion.
4. **`CustomerResolutionAgent`**:
   - Synthesizes findings from Order, Kitchen, and Fleet agents into a root cause explanation.
   - Invokes Google Gemini (`gemini-3.5-flash`) via structured JSON schema prompts.
   - Graceful Degradation: If `GEMINI_API_KEY` is absent, invalid, or times out (>10s), automatically falls back to deterministic rule-grounded synthesis without raising errors.

---

## 5. Governance, PolicyEngine & HITL Gating

To prevent reckless automated actions, financial waste, or operational panic, every AI recommendation is evaluated against the deterministic **PolicyEngine**:

```mermaid
flowchart TD
    RecCandidate["AI Recovery Recommendation"] --> CheckRole["1. Operator Role Authorization (RBAC)\nAllowed: OPERATOR, SUPERVISOR, OPS_LEAD, ADMIN\nRejected: GUEST, INTERN -> HTTP 403"]
    CheckRole --> CheckConsent["2. Customer Consent Check\nOrder metadata customer_consent == False?\n-> Block customer notifications"]
    CheckConsent --> CheckExpiry["3. Expiration Check (TTL = 30 min)\nnow > expires_at?\n-> Reject execution (400 Bad Request)"]
    CheckExpiry --> CheckDrift["4. Order State Drift Check\nAction compatible with current order status?\n(e.g., Cannot ping kitchen if DELIVERED)"]
    CheckDrift --> CheckFleet["5. Fleet Availability Threshold\nFleet deficit > 80%?\n-> Suppress courier priority (futile)"]
    CheckDrift --> CheckIdempotency["6. Idempotency Key Validation\nSHA-256(order_id + action_type + rec_id)\nDuplicate execution detected?\n-> Return cached audit record without redispatch"]
    CheckIdempotency --> CheckSensitivity{"7. Sensitivity Level & HITL Gate\nLow: MONITOR_ORDER, EXPEDITE_KITCHEN_PING\nMedium: PROACTIVE_CUSTOMER_NOTIFICATION\nHigh: REASSIGN_COURIER, APOLOGY_CREDIT_VOUCHER"}

    CheckSensitivity -- "Low / Medium" --> AutoApprove["AUTO_APPROVED\nImmediate autonomous execution"]
    CheckSensitivity -- "High / Sensitive" --> RequireHuman["AWAITING_APPROVAL\nPersisted to dashboard queue\nRequires human operator sign-off"]
```

---

## 6. Simulation & Evaluation Framework (Phase 5)

The platform includes a high-fidelity Monte Carlo simulation engine (`backend/app/simulation/`) designed to evaluate autonomous recovery against baseline operational policies:

```mermaid
flowchart LR
    ScenarioBank["Scenario Generator\n(12 Real-World Delivery Scenarios)"] --> Engine["AdvancedSimulationEngine\n(1,000 Order Batches)"]
    
    Engine --> Strategy1["Strategy 1: No Intervention (Status Quo)"]
    Engine --> Strategy2["Strategy 2: Naive Static Threshold Heuristic"]
    Engine --> Strategy3["Strategy 3: Autonomous Full AI (ResolveAI)"]
    Engine --> Strategy4["Strategy 4: Human-in-the-Loop AI Gated"]
    
    Strategy1 --> KPIEngine["Business KPI Calculator\n• Delivery Delay Reduction (min)\n• WISMO Ticket Deflection Rate (%)\n• Cancellation Avoidance Rate (%)\n• Net Economic ROI (INR/order)"]
    Strategy2 --> KPIEngine
    Strategy3 --> KPIEngine
    Strategy4 --> KPIEngine
    
    KPIEngine --> Bootstrap["Paired Bootstrap Resampling\n(1,000 iterations -> 95% Confidence Intervals)"]
```

---

## 7. Container Topology & Deployment Architecture

```mermaid
flowchart TD
    subgraph Host["Production Host / Cloud VM"]
        subgraph DockerCompose["Docker Compose Multi-Container Mesh"]
            FrontendContainer["swiggy-resolveai-frontend:latest\nNode.js 20 Alpine\nNext.js 16.4.6 SSR\nPort: 3000"]
            BackendContainer["swiggy-resolveai-backend:latest\nPython 3.12 Slim\nFastAPI + Uvicorn (Workers: 4)\nPort: 8000"]
            PostgresContainer["postgres:16-alpine\nPersistent Data Volume\nPort: 5432"]
            RedisContainer["redis:7-alpine\nEphemeral Telemetry Cache\nPort: 6379"]
        end
        ReverseProxy["Nginx / Cloudflare Edge\n(SSL Termination & Rate Limiting)"]
    end

    ReverseProxy --> FrontendContainer
    ReverseProxy --> BackendContainer
    FrontendContainer --> BackendContainer
    BackendContainer --> PostgresContainer
    BackendContainer --> RedisContainer
```

### Health Diagnostics:
- **`GET /health`**: Unified status across Database, Redis, Model Registry, and Application uptime.
- **`GET /health/live`**: Kubernetes/Docker liveness probe verifying process responsiveness.
- **`GET /health/ready`**: Kubernetes/Docker readiness probe verifying database connectivity and ML artifact availability.

---

## 8. Security Architecture, Authentication & Execution Safeguards

### 8.1 Cryptographic Authentication & RBAC Boundary
- **RFC 7519 HMAC-SHA256 Bearer Tokens**: All sensitive administrative and operational actions (`approve_recommendation`, `reject_recommendation`, `execute_recommendation`) require verified bearer tokens signed with `AUTH_SECRET_KEY`.
- **Identity Trust Boundary Elimination**: Client requests cannot forge operator identities or roles via request body parameters (`operator_id`, `operator_role`). Identity and role claims (`sub`, `role`, `name`) are resolved exclusively on the server from validated cryptographic tokens.
- **Gated Development Endpoint**: In local environments (`ENVIRONMENT=development`), `POST /api/v1/auth/dev-token` issues test tokens for certified personas (`ops_lead`, `admin`, `operator`, `intern`). In staging and production environments, this endpoint is strictly disabled (HTTP 403 Forbidden).

### 8.2 Execution Safety Modes
The backend enforces three runtime execution modes configured via `EXECUTION_MODE`:
1. **`SIMULATION`** (Default): Recovery actions execute against local database state; synthetic side-effects (e.g. merchant push, courier re-dispatch) are simulated and logged.
2. **`SHADOW`**: Complete pipeline executes (order ingestion, ML inference, multi-agent debate, recommendation ranking); physical execution of recovery actions is blocked at the execution boundary and rejected with HTTP 403 Forbidden.
3. **`LIVE`**: Protected production mode. The system raises a fatal initialization error if configured for live recovery, guaranteeing safety until external Swiggy production APIs and telematics systems are formally certified.

### 8.3 Append-Only Audit Immutability
- **ORM Event Listeners**: SQLAlchemy event listeners (`before_update` and `before_delete`) are attached to the `RecoveryExecutionAudit` model.
- **Tamper Prevention**: Any programmatic attempt within the ORM to modify or delete historical audit records raises a fatal `PermissionError`, ensuring an unalterable compliance ledger for all automated and HITL recovery actions.
