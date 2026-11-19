# Swiggy ResolveAI — User-Friendly Product Language & Dashboard Refinement Report

**Document Version:** 1.0.0  
**Target Audience:** Restaurant Partners, Delivery Operations Managers, Business Stakeholders, Product Leadership, and Technical Evaluators  
**Scope:** Frontend Presentation Layer, Terminology Dictionary, Two-Level Information Architecture, and Operations Dashboard Refinements  
**Status:** Implemented, Built, and Verified

---

## Executive Summary

Swiggy ResolveAI was originally constructed with highly precise engineering, ML, and multi-agent terminology (`Task A Quantiles`, `Task C2 Landmark Classifier`, `PolicyEngine Gating`, `Counterfactual Evaluation`, `Idempotency Keys`, `Synthetic Live`). While technically rigorous, this cognitive load made it difficult for restaurant operators, dispatch managers, and non-technical stakeholders to understand within 30 seconds what the system does, why an order needs attention, and what action is being taken.

This refinement pass elevates the user experience across all 7 frontend views by establishing a **clear, business-oriented language system** and implementing a **two-level information architecture**:
1. **Level 1 (Default Business Surface):** Clean, intuitive, title-case language, plain-English status indicators, visual delivery time ranges, simple cancellation risk percentages, clear recommended actions, and manager approval statuses.
2. **Level 2 (Expandable Technical Drawers):** Granular engineering specifications, ML model versions, quantile intervals (P10/P50/P90), isotonic calibration details, idempotency keys, and database connection telemetry preserved on demand for engineers and technical interviews.

All changes are strictly confined to the presentation layer (`frontend/src/`). **Zero modifications** were made to backend logic, API schemas, database models, Alembic migrations, or ML model artifacts.

---

## 1. Product Language & Terminology Dictionary

The table below catalogs the standardized terminology mappings applied across the frontend application:

| Original Engineering / ML Term | User-Friendly Business Term | UI Placement & Context |
| :--- | :--- | :--- |
| **Order Intelligence** | **Order Insights** | Page titles, navigation, and summary headers |
| **Multi-Agent Investigation** | **AI Order Investigation** | Order analysis workflows and investigation cards |
| **Operational Risk Tier** | **Order Risk** | Risk categorization (`Critical Delay`, `High Risk`, `Needs Monitoring`, `On Track`) |
| **ETA Quantiles (P10 / P50 / P90)** | **Estimated Delivery Time Range** | Default shows `28–42 mins (most likely ~34 mins)`; P10/P50/P90 in drawer |
| **Cancellation Probability** | **Cancellation Risk** | Shown as clean percentage (e.g., `12% Risk`); Isotonic calibration details in drawer |
| **Restaurant Coordination Agent** | **Restaurant Status Check** | Kitchen delay, food preparation, and dispatch readiness verification |
| **Delivery Intelligence Agent** | **Delivery Partner Status** | Courier transit speed, reassignment counts, and road traffic monitoring |
| **Customer Resolution Agent** | **Resolution Assistant** | Customer messaging, apology credit, and delay notification assistance |
| **Recovery Recommendation** | **Suggested Action** | Recommended operational remedy (e.g., Apology Credit, Courier Priority) |
| **Human-in-the-Loop (HITL)** | **Requires Manager Approval** | Action approval badge and operational sign-off requirement |
| **PolicyEngine / Gating** | **Action Approval Rules** | Governance rules defining which remedies run automatically vs need approval |
| **Recovery Executor** | **Action Processor** | The system component executing approved interventions |
| **Idempotency / Idempotency Key** | **Duplicate Action Protection Key** | Ensures no customer or restaurant receives a duplicate remedy or credit |
| **Counterfactual Evaluation** | **Recovery Strategy Comparison** | Benchmark comparing ResolveAI against baseline and simple rule approaches |
| **Model Prediction Audit** | **Prediction History** | Historical log of ML inferences and model outputs |
| **ML Provenance Metadata** | **Prediction Details** | Feature inputs, timestamps, and model checkpoint references |
| **Synthetic Live Order** | **Demo Order (Simulated)** | Clearly identifies mock or scenario-driven test orders |
| **Public Historical Dataset** | **Historical Order Data** | Identifies benchmark orders loaded from historical delivery datasets |
| **Database Health / Telemetry** | **Data Connection Status** | Status of connection to PostgreSQL / Neon data store |
| **Shadow Mode** | **Monitoring Only (Simulation)** | Safe execution state where actions are recorded but not physically dispatched |
| **Execution Audit Log** | **Action History** | Permanent record of all automated and approved operational remedies |

---

## 2. Five Core Operational Questions Implementation

To ensure instant operational clarity for restaurant partners and delivery supervisors, the Order Details page (`/orders/[id]`) and AI Insights page (`/intelligence`) now answer **five core business questions** directly on a prominent **Operations Summary Card**:

```
+----------------------------------------------------------------------------------------------------+
|  Operations Summary: Order #ORD-1042                                                               |
|  Plain-English operational breakdown generated from order milestones, road telemetry, and AI checks |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  1. Current Situation                                                                              |
|     Kitchen Began Preparation (18 mins in kitchen, 6 mins behind target).                          |
|                                                                                                    |
|  2. Underlying Cause                                                                               |
|     Heavy kitchen backlog during dinner peak hours delayed food handover to the courier.           |
|                                                                                                    |
|  3. AI Forecast                                                                                    |
|     Expected arrival between 38-52 mins (most likely ~44 mins). Estimated 16% risk of              |
|     customer cancellation if delay remains unaddressed.                                            |
|                                                                                                    |
|  4. Suggested Action                                                                               |
|     Issue Customer Apology Credit (Rs 50 voucher) and notify customer of updated kitchen progress. |
|                                                                                                    |
|  5. Manager Review                                                                                 |
|     Requires Supervisor Approval (Approval required for credits over Rs 30).                       |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

### Dynamic Story Generation Engine (`frontend/src/lib/presentation.ts`)
The `getOrderOperationalStory(...)` utility function synthesizes order status, kitchen elapsed time, courier transit events, ML quantiles, and recommended actions into natural, business-ready sentences:
- **What happened?** Analyzes milestone timestamps, elapsed minutes, and SLA thresholds.
- **Why did it happen?** Correlates courier reassignment counts, transit delay events, and kitchen backlog flags.
- **What could happen next?** Translates Task A P10/P50/P90 and Task C2 calibrated cancellation probability into an actionable risk forecast.
- **What action is recommended?** Displays humanized action labels (e.g., "Issue Customer Apology Credit", "Prioritize Courier Assignment", "Notify Customer of Delay").
- **Does it require manager approval?** Clearly indicates whether the action runs automatically under policy thresholds or requires supervisor/lead sign-off.

---

## 3. Two-Level Information Architecture

To satisfy both non-technical operational users and technical evaluators or engineers, every primary interface employs a **two-level information design**:

```
+-----------------------------------------------------------------------------------+
|  LEVEL 1: BUSINESS-FRIENDLY DEFAULT SURFACE                                       |
|  * Clean title-case status indicators ("Preparing in Kitchen", "Delivered on Time") |
|  * Plain-English delivery range ("Estimated Arrival: 32-44 mins")                |
|  * Percentage cancellation risk ("Cancellation Risk: 14%")                        |
|  * Plain action recommendations ("Apology Credit (Rs 50)")                        |
|  * Governance badges ("Requires Manager Approval", "Duplicate Protection Active") |
+-----------------------------------------------------------------------------------+
                                         |
                       [Expand Technical Drawer] (Click to inspect)
                                         v
+-----------------------------------------------------------------------------------+
|  LEVEL 2: TECHNICAL SPECIFICATIONS & AUDIT TRACES (EXPANDABLE)                    |
|  * Task A Quantile Loss & Intervals: P10 = 31.8m, P50 = 37.2m, P90 = 43.9m        |
|  * Task C2 Calibration: Landmark Isotonic Regression, Brier Score, ROC-AUC        |
|  * Model Version: Registry v2.5.0 LightGBM (data/artifacts/models/phase_2_5)      |
|  * Action Processing: Idempotency Key UUIDs, PolicyEngine rule matrix, RBAC roles |
|  * Database Diagnostics: PostgreSQL Neon pool size, query latency (ms), Alembic 005|
+-----------------------------------------------------------------------------------+
```

---

## 4. Page-by-Page Transformation Details

### 4.1 Navigation & Shell (`Sidebar.tsx`, `TopHeader.tsx`, `AppShell.tsx`)
- **Navigation Items:** Replaced internal phase names with intuitive workflow destinations:
  - `Overview` (`/`): High-level operational pulse.
  - `All Orders` (`/orders`): Searchable, filterable order directory.
  - `AI Insights` (`/intelligence`): Investigation, predictions, and action approvals.
  - `Try Scenarios` (`/simulation`): Test operational scenarios and compare recovery strategies.
  - `Performance` (`/health`): Connection health and system diagnostic status.
  - `Activity History` (`/intelligence#activity-history`): Log of past operational actions.
- **Top Header:** Simplified search placeholder to *"Search orders by ID, restaurant, or customer name..."*, updated primary action button to *"Try Scenarios"*, and changed status badge to *"System Active"*.
- **Footer:** Refined to *"Swiggy ResolveAI — Automated Order Support & Resolution Platform • Operations Console • Demo and historical order simulation"*.

### 4.2 Operations Overview (`page.tsx`)
- **KPI Metrics:**
  - `Total Orders Monitored`: Cumulative active and completed orders under management.
  - `Orders in Progress`: Active orders in kitchen preparation or courier transit.
  - `Delivered on Time`: Percentage of orders successfully completed within promised SLA.
  - `Needs Attention`: Flagged orders currently delayed or requiring operational intervention.
- **Section Headings:**
  - *"Recent Orders & Live Progress"* with humanized status badges.
  - *"Recent Activity & Resolved Orders"* showcasing automated resolutions.
  - *"Automated Delay Resolution in Action"* explaining proactive intervention logic in 3 simple steps (Detect Early $\to$ Verify Cause $\to$ Resolve Safely).

### 4.3 All Orders Directory (`orders/page.tsx`)
- **Filter Tabs:** Streamlined into plain business categories:
  - `All Orders`, `Order Placed`, `Preparing in Kitchen`, `Out for Delivery`, `Delivered on Time`, `Resolved with Support`, `Needs Attention`.
- **Table Columns:** `Order`, `Customer & Destination`, `Restaurant`, `Status`, `Estimated Delivery Range`, `Order Risk`, `Data Source`.
- **Data Source Badges:**
  - `Demo Order (Simulated)`: Purple badge for test and scenario orders.
  - `Historical Order Data`: Slate badge for historical dataset records.

### 4.4 Order Details & Simulation Console (`orders/[id]/page.tsx`)
- **Operations Summary Card:** Answers the 5 core operational questions at the very top of the page.
- **Status & Milestones:** Human-readable timeline milestones ("Order Received", "Kitchen Began Preparation", "Food Packed & Ready", "Transit Delay / Heavy Road Traffic", "Apology Credit Issued").
- **Simulate Events Console:** Allows testing order events using plain-English action buttons:
  - *"Simulate Kitchen Delay"* (+10 mins preparation time).
  - *"Simulate Traffic Delay"* (courier transit slowdown).
  - *"Food Ready for Pickup"* (restaurant handover milestone).
  - *"Simulate Successful Delivery"* (order marked delivered on time).

### 4.5 AI Order Insights (`intelligence/page.tsx`)
- **Order Risk Card:** Clear risk level (`Critical Delay`, `High Risk`, `Needs Monitoring`, `On Track`) with explanatory operational notes.
- **Estimated Delivery Time Range Card:** Visual range showing most likely arrival with low/high bounds, plus expandable technical drawer for P10/P50/P90 numbers.
- **Cancellation Risk Card:** Prominent percentage risk indicator with plain-English urgency explanation and expandable calibration drawer.
- **Restaurant Status Check & Delivery Partner Status Cards:** Clear indicators for kitchen delay (+mins) and courier reassignments.
- **Suggested Actions & Action Approval Rules:**
  - Action cards displaying action name, benefit, approval status (`Approved`, `Pending Manager Approval`, `Completed`), and execution mode (`Monitoring Only`).
  - Human-in-the-loop approval banner showing required manager roles (`OPS_LEAD`, `OPERATOR`, `SUPERVISOR`) and one-click approval button.
- **Action History Table:** Columns for `Action Taken`, `Order`, `Trigger Reason`, `Approval Status`, `Mode`, `Duplicate Protection Key`, and `Timestamp`.

### 4.6 Scenarios & Strategy Comparisons (`simulation/page.tsx`)
- **Compare Recovery Strategies Tab:** Replaced "Counterfactual Policy Evaluation" with a side-by-side comparison of 4 approaches:
  1. *Baseline (No Intervention)*: Natural order progression without recovery.
  2. *Simple Rule-Based Alerts*: Standard delay notifications without ML predictions.
  3. *Early Risk Alerting*: ML predictions with alert thresholds.
  4. *ResolveAI Autonomous Recovery*: Combined multi-agent coordination, ML predictions, and policy approval rules.
- **Create Demo Orders Tab:** Replaced raw synthetic generation controls with intuitive sliders for order count and scenario selection (e.g., "Heavy Kitchen Backlog", "Courier Traffic Delay", "Smooth Delivery").

### 4.7 System Performance & Data Connection Status (`health/page.tsx`)
- **4 Operational Pillars:**
  1. *Application Server*: Order processing API service status and HTTP response speed.
  2. *Data Connection*: PostgreSQL / Neon connection status and query latency.
  3. *AI Assistant*: Gemini API connection status with automatic rule fallback standby.
  4. *Prediction Engine*: LightGBM model readiness and calibration status.
- **Operational Safety Overview:** Explains manager approval requirements, duplicate action protection, and simulated demo isolation.
- **Expandable Technical Diagnostics:** Contains full API endpoint URLs, Task A pinball loss specifications, Task C2 landmark classifier details, ML artifact directories, and database engine specifications.

---

## 5. Build & Verification Evidence

### 5.1 Next.js Production Build
The frontend build was executed using Turbopack and TypeScript:
```bash
npm --prefix frontend run build
```
**Build Output:**
```text
▲ Next.js 16.4.6 (Turbopack)
- Environments: .env.local

✓ Running next.config.ts took 65ms
- Cache Components enabled
- Partial Prefetching enabled

  Creating an optimized production build ...
✓ Compiled successfully in 935ms
  Running TypeScript ...
  Finished TypeScript in 2.3s ...
  Collecting page data using 7 workers ...
✓ Generating static pages using 7 workers (9/9) in 1294ms
  Finalizing page optimization ...

Route (app)
┌ ○ /
├ ○ /_not-found
├ ○ /health
├ ○ /intelligence
├ ○ /orders
├   /orders/[id]
│ └ ◐ /orders/[id]
└ ○ /simulation

○  (Static)             prerendered as static content
◐  (Partial Prerender)  prerendered as static HTML with dynamic server-streamed content
```
**Result:** 0 TypeScript errors, 0 compilation errors across all 9 application routes.

### 5.2 HTTP Route Verification
All routes were tested against the local server (`http://localhost:3000`):
- `/` $\to$ `200 OK`
- `/orders` $\to$ `200 OK`
- `/intelligence` $\to$ `200 OK`
- `/simulation` $\to$ `200 OK`
- `/health` $\to$ `200 OK`

---

## 6. Safety, Governance, and Integrity Guarantees

1. **Zero False Claims:** The user interface prominently states that the platform operates on demo orders and historical operational data. No live Swiggy courier dispatch or real financial transactions are claimed.
2. **Strict Governance Preservation:** All RBAC role definitions (`OPS_LEAD`, `OPERATOR`, `SUPERVISOR`, `JUNIOR_INTERN`), human-in-the-loop approval thresholds, idempotency validation, and `SHADOW` execution mode remain 100% active and enforced.
3. **Backend & Model Integrity:** No changes were made to backend routes, database schemas, Alembic migrations, or LightGBM model artifacts. All presentation enhancements wrap existing API response fields transparently.

---

## Conclusion

With this refinement pass, Swiggy ResolveAI achieves complete operational clarity. Restaurant operators and delivery managers can immediately understand order health, projected delays, and recommended remedies within seconds, while technical evaluators retain full access to underlying machine learning models, statistical distributions, and architectural diagnostics through an elegant, progressive disclosure design.
