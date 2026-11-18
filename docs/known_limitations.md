# Swiggy ResolveAI — Known Limitations & Operational Boundaries

This document details the known technical boundaries, model assumptions, operational constraints, and edge-case behaviors of the **Swiggy ResolveAI** platform as of Phase 7.

---

## 1. Simulated Operational Boundaries

> [!IMPORTANT]
> **Strict Non-Production Execution**: All physical operations (courier reassignment, merchant kitchen pings, customer SMS/push notifications, and Swiggy Money wallet credits) are strictly **simulated** in software.
>
> The system does not interface with Swiggy production APIs, live courier telematics fleets, merchant Point-of-Sale (POS) terminals, or real payment gateways. No actual money is transferred, no couriers are re-routed in real traffic, and no customers receive unsimulated push messages.

- **Telematics Resolution**: Fleet locations and kitchen queue depths are generated through high-fidelity synthetic telemetry rather than live hardware GPS polling or KDS integration.
- **Counterfactual Response Assumption**: In the Phase 5 simulation engine, merchant response to a kitchen ping recovers 4–6 minutes of preparation time. In real-world kitchens under peak dinner rushes, physical stove and fryer constraints may limit actual recovery.

---

## 2. Machine Learning Model Constraints

### 2.1 Task A (Delivery Duration Uncertainty Regressors)
- **Quantile Scope**: Predicts conditional quantiles $P10, P50, P90$ at order creation.
- **Quantile Crossing Prevention**: Monotonic post-processing strictly enforces $P10 \le P50 \le P90$.
- **Boundary Validity**: Training data distributions reflect standard metro delivery conditions (20–45 min duration). In extreme weather disruptions (e.g. monsoons, waterlogging), predictions reflect statistical uncertainty intervals rather than physical guarantees.
- **Missing Covariates**: The publicly available delivery dataset lacks granular meteorological (rainfall mm/hr) and micro-elevation features.

### 2.2 Task C2 (Landmark Post-Allotment Cancellation Risk)
- **Landmark Eligibility Gate**: Evaluated exclusively at $t \ge t_{\text{allot}} + 5\text{ min}$. Prior to this landmark, the model reports `is_eligible = false`.
- **Target Semantics**: The model predicts eventual post-landmark cancellation within the observed order lifecycle, NOT imminent cancellation within seconds.
- **Budget Gating**: To prevent false alert fatigue, the model applies strict operational budget thresholds (5/1,000 and 10/1,000 alert rates).

### 2.3 Tasks B & C1 (Research Isolation)
- **Status**: Persisted as research artifacts only (`Task B` logistic baseline; `Task C1` order-time cancellation).
- **Isolation Guarantee**: Both models are strictly isolated and are never permitted to trigger automated recovery dispatches or customer notifications.

### 2.4 Dataset Boundaries on Dynamic Stage-Specific Remaining ETA
- **Public Dataset Characteristics**: In the Kaggle food delivery dataset (`Rider-Info.csv`), intermediate milestone timestamps (e.g. precise courier arrival at restaurant, food pickup completion) are missing for 42.3% of records, and continuous GPS telematics streams are completely absent.
- **Leakage & Survival Bias Risk**: Attempting to train dynamic "remaining delivery time" models conditioned on late-stage milestones using this historical dataset introduces severe survival bias (orders that survived to pickup without cancellation) and target leakage (milestone recording times correlated with unobserved delay notes).
- **Point-in-Time Calibrated Strategy**: Task A is rigorously calibrated at order placement ($t_0$) predicting full delivery duration quantiles ($P10, P50, P90$) using 16 pre-order and static routing covariates. Dynamic intervention is governed by elapsed-time tracking relative to conditional quantiles rather than unvalidated mid-journey regressors.

---

## 3. Policy & Governance Limitations

### 3.1 Moral Hazard of Autonomous Apology Vouchers
- **Abuse Vectors**: If customers discover that reporting or experiencing deliberate delays yields automated ₹50 credits, opportunistic behavior could occur.
- **Mitigation Implemented**: Apology vouchers require explicit human-in-the-loop (HITL) operator approval, strict per-customer lifetime cooldowns, and can never be auto-approved by AI agents alone.

### 3.2 Recommendation Expiration Window
- **30-Minute Time-To-Live (TTL)**: Recommendations expire automatically 30 minutes after generation. An operator attempting to approve an expired recommendation will receive an HTTP 400 rejection to prevent executing actions on stale operational state.

### 3.3 Fleet Shortage Feasibility Gating
- **Courier Prioritization Suppression**: If zone fleet shortage exceeds 80%, courier priority actions are automatically suppressed by `PolicyEngine.check_fleet_availability_threshold` because priority dispatch without available couriers causes fleet churn without ETA improvement.

---

## 4. Systems Architecture & Infrastructure Boundaries

### 4.1 Single-Node Monolith Capacity
- **Target Scale**: Designed for up to 5,000 concurrent active orders per application worker on standard cloud compute instances (4 vCPU, 8 GB RAM).
- **SQLite vs PostgreSQL**: Local development and automated test suites utilize SQLite with Write-Ahead Logging (`WAL` mode). Multi-worker production deployments require PostgreSQL 16+ with row-level locking for concurrent idempotency key guarantees.

### 4.2 LLM Synthesis & Fallback Latency
- **Timeout Boundary**: CustomerResolutionAgent enforces a 10.0-second timeout on Google Gemini API calls.
- **Deterministic Fallback**: If Gemini times out, experiences rate limits, or if `GEMINI_API_KEY` is not provided, the platform automatically falls back to deterministic rule-grounded synthesis. While 100% reliable and functionally identical, deterministic messages lack the linguistic nuance of generative LLMs.

### 4.3 Database Cleanup & Retention
- **Audit Table Growth**: In continuous simulation runs, the `recovery_execution_audits` and `order_events` tables accumulate rows rapidly. A production deployment requires a 30-day archival and partitioning strategy.

---

## 5. Economic & Financial Modeling Boundaries

### 5.1 Platform Contribution Margin Accounting
- **Gross Order Value (GOV) vs Net Revenue**: In food delivery aggregators like Swiggy, the platform does not capture 100% of the food order value; revenue is derived primarily from a merchant commission fee (typically 18%–22% of GOV) plus nominal delivery fees.
- **Remediated Economic Model**: The simulation KPI engine models platform gross losses avoided using a calibrated `contribution_margin_ratio = 0.20` (20% of GOV). Net economic benefit is calculated as:
  $$\text{Net Benefit} = (\text{Gross Losses Avoided} \times 0.20) - \text{Intervention Costs}$$
- **Avoidance of 5x ROI Overstatement**: Treating full GOV as recovered platform cash would overstate financial returns by 500%. With 20% margin accounting, ResolveAI achieves an audited base ROI of 2.18x over intervention costs, preserving financial conservatism.
