# Swiggy ResolveAI — Model Cards Specification

- **Date**: November 19, 2026
- **Auditors**: Principal ML Platform Engineer, Application Security Engineer, QA Lead
- **Status**: **PORTFOLIO-READY & CODE-VERIFIED**
- **Artifacts Reference**: `data/artifacts/models/phase_2_5/registry.json`
- **Model Version**: 2.5.0

---

## 1. Executive Summary & Model Governance Overview

This document provides formal Model Cards for all machine learning models in **Swiggy ResolveAI**, detailing their prediction points, target semantics, input feature schemas, evaluation protocols, calibration, alert budgets, approved operational usages, and strict governance boundaries.

| Task Identifier | Model Name | Architecture | Prediction Point | Status / Governance | Primary Metric |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Task A** | Initial Delivery Duration Quantiles | LightGBM Quantile Regressors (P10, P50, P90) | Order Placement ($t_0$) | **APPROVED FOR SIMULATION** | 80% Coverage: 78.6%, P50 MAE: 9.16m |
| **Task C2** | Landmark Post-Allotment Cancellation Risk | LightGBM + Isotonic Calibrator | Landmark ($t \ge t_{\text{allot}} + 5\text{ min}$) | **APPROVED FOR CONTROLLED TRIAGE** | Test PR-AUC: 0.0829, Brier Reduction: -66.0% |
| **Task B** | Courier Allocation Delay (>3m) | LightGBM Tuned | Order Placement ($t_0$) | **RESEARCH_ONLY (PROHIBITED)** | Test PR-AUC: 0.0729 (Recall 3.8% at 10/1k) |
| **Task C1** | Upfront Order Cancellation Risk | LightGBM Tuned | Order Placement ($t_0$) | **RESEARCH_ONLY (PROHIBITED)** | Test PR-AUC: 0.0133 (Near Base Rate 1.11%) |

> [!WARNING]
> **Generalization Limitation**: Historical test performance is established strictly on a historical delivery benchmark from January 26 to February 6, 2021 (`cbhavik/swiggyzomato-order-information`). It does **not** establish generalization to other geographic cities, alternate delivery logistics operators, unobserved weather extremes, post-2021 fleet changes, or live commercial operating conditions.

---

## 2. Model Card: Task A — Initial Order Delivery Duration Quantiles

### 2.1 Model Overview
- **Model Type**: Quantile Gradient Boosted Decision Trees (`LightGBMRegressor` with objective `quantile`, $\alpha \in \{0.1, 0.5, 0.9\}$).
- **Artifact Paths**: 
  - `data/artifacts/models/phase_2_5/task_a_quantile_p10.joblib`
  - `data/artifacts/models/phase_2_5/task_a_quantile_p50.joblib`
  - `data/artifacts/models/phase_2_5/task_a_quantile_p90.joblib`
- **Inference Service**: `backend/app/services/ml_inference.py` (`predict_task_a_quantiles`)

### 2.2 Prediction Point & Target Semantics
- **Prediction Point**: Evaluated strictly at order placement ($t_0$), before kitchen confirmation or courier dispatch.
- **Target Semantics**: Total delivery duration in elapsed minutes (`target_delivery_duration_min`), defined from order creation timestamp to customer handoff completion timestamp.
- **Target Leakage Prevention**: No downstream operational timestamps (acceptance, kitchen dispatch, pickup, transit milestones) are used as features.
- **Strict Distinction**: This model predicts **initial delivery duration quantiles** at order placement. It is **NOT** a dynamic remaining-ETA model and does not update continuously during transit.

### 2.3 Input Schema & Feature Availability (16 Features)
The model consumes 16 pre-order and static routing features available at $t_0$:

| Feature Name | Type | Description |
| :--- | :--- | :--- |
| `last_mile_distance` | Float | Haversine distance between restaurant and customer (km) |
| `is_zero_last_mile` | Int | Binary indicator for zero/co-located coordinates |
| `last_mile_distance_sq` | Float | Quadratic distance term for non-linear transit scaling |
| `distance_bracket` | Int | Categorical distance bin (0 to 4) |
| `order_hour` | Int | Hour of order placement (0–23) |
| `hour_sin` | Float | Sine transform of order hour: $\sin(2\pi \cdot \text{hour} / 24)$ |
| `hour_cos` | Float | Cosine transform of order hour: $\cos(2\pi \cdot \text{hour} / 24)$ |
| `order_dayofweek` | Int | Day of week (0 = Monday, 6 = Sunday) |
| `dow_sin` | Float | Sine transform of day of week |
| `dow_cos` | Float | Cosine transform of day of week |
| `is_weekend` | Int | Binary flag for Saturday or Sunday |
| `meal_period` | Int | Categorical bucket (Breakfast, Lunch, Evening Snack, Dinner, Late Night) |
| `is_peak_meal_window` | Int | Binary flag for peak lunch (12:00–14:00) or peak dinner (19:30–22:00) |
| `rolling_order_volume_15m` | Float | Zone-level order density in previous 15 minutes |
| `rolling_order_volume_60m` | Float | Zone-level order density in previous 60 minutes |
| `demand_acceleration` | Float | Ratio of 15-minute to 60-minute volume rate |

### 2.4 Chronological Dataset Split Protocol
All data partitions follow strict chronological boundaries on `data/raw/orders/Rider-Info.csv` to eliminate future lookahead leakage:
- **Train Set**: `2021-01-26` to `2021-02-02` (314,646 rows, 69.9% of volume)
- **Validation Set**: `2021-02-03` to `2021-02-04` (81,132 rows, 18.0% of volume)
- **Test Set**: `2021-02-05` to `2021-02-06` (54,222 rows, 12.1% of volume)
- **Total Dataset**: 450,000 raw records (449,999 unique orders, 1 duplicate row with `order_id=181402`).

### 2.5 Quantitative Evaluation & Uncertainty Performance

#### Pinball Loss Metrics
- **P10 Pinball Loss**: `1.5760`
- **P50 Pinball Loss**: `4.5814` (vs baseline point regressor MAE: `4.6925`)
- **P90 Pinball Loss**: `2.6949`
- **Point Baseline MAE (P50)**: `9.163` minutes on test set.

#### Uncertainty Interval Coverage (Nominal 80% Coverage $[P_{10}, P_{90}]$)
- **Empirical Coverage**: `78.60%` (Nominal Target: 80.00%)
- **Mean Interval Width**: `27.92` minutes
- **Below P10 (Faster than expected)**: `10.99%`
- **Above P90 (Slower than expected)**: `10.42%`
- **Crossing-Corrected Violations**: `0` violations in test set. Monotonic ordering ($P_{10} \le P_{50} \le P_{90}$) is guaranteed via runtime sorting post-processing:
  $$\hat{y}_{P10} = \min(\hat{y}_{P10}, \hat{y}_{P50}), \quad \hat{y}_{P90} = \max(\hat{y}_{P90}, \hat{y}_{P50})$$

#### Duration-Bucket Breakdown

| Delivery Duration Bucket | % of Test Volume | Empirical Coverage ($[P_{10}, P_{90}]$) | Mean Width | P50 MAE | Above P90 Rate |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **< 20 minutes** | 15.57% | 42.86% | 26.75m | 10.96m | 0.00% |
| **20 to 35 minutes** | 50.89% | **95.86%** | 27.86m | **4.59m** | 0.03% |
| **35 to 50 minutes** | 24.87% | **88.29%** | 28.44m | 10.08m | 11.71% |
| **> 50 minutes (Long Tail)** | 8.67% | **13.68%** | 28.86m | 30.15m | **86.32%** |

### 2.6 Uncertainty Limitations & Known Caveats
1. **Severe Long-Tail Undercoverage**: For orders exceeding 50 minutes (8.67% of volume), the empirical coverage is only 13.68%, and 86.32% of orders exceed the predicted P90 upper bound. This occurs because the public historical dataset lacks real-time kitchen preparation queue telemetry.
2. **Short-Order Underprediction**: For orders delivered under 20 minutes (15.57% of volume), 57.14% fall below the P10 bound due to fixed minimum delivery travel assumptions.
3. **No Continuous GPS Updates**: The model operates only at $t_0$. It does not track live traffic jams, weather shifts, or courier stops after dispatch.

### 2.7 Governance & Approved Usage
- **APPROVED USAGE**:
  - Operational simulation scenario seeding and variance stress-testing.
  - Multi-agent context grounding (providing Order Intelligence Agent with expected duration bounds).
  - Customer communication that explicitly surfaces duration intervals ($[P_{10}, P_{90}]$) rather than single-point numbers.
- **PROHIBITED INTERPRETATIONS**:
  - Point predictions ($P_{50}$) **MUST NEVER** be presented to customers or operators without the $[P_{10}, P_{90}]$ interval bounds.
  - **MUST NEVER** be interpreted as dynamic remaining travel time.
  - **MUST NEVER** be used to penalize delivery couriers for late deliveries without live kitchen handoff telemetry.

---

## 3. Model Card: Task C2 — Landmark Post-Allotment Cancellation Risk

### 3.1 Model Overview
- **Model Type**: Gradient Boosted Decision Tree (`LightGBMClassifier`) with post-hoc **Isotonic Regression Calibration**.
- **Artifact Paths**:
  - `data/artifacts/models/phase_2_5/task_c2_improved_model.joblib`
  - `data/artifacts/models/phase_2_5/task_c2_calibrator.joblib`
- **Inference Service**: `backend/app/services/ml_inference.py` (`predict_task_c2_landmark_cancellation`)

### 3.2 Prediction Point & Target Semantics
- **Prediction Point**: Evaluated strictly at landmark timestamp $t_{\text{landmark}} = t_{\text{allot}} + 5\text{ min}$ (5 minutes after courier allotment has occurred).
- **Target Semantics**: Binary indicator (`target_cancelled_post_landmark`) of whether the order is **eventually cancelled** post-landmark within its observed lifecycle.
- **Strict Distinction**: This model predicts **eventual cancellation risk** over the remainder of the order lifecycle. It does **NOT** predict imminent cancellation within seconds, nor does it predict fixed 5-minute horizon cancellations.

### 3.3 Input Schema & Feature Availability (26 Features)
The model combines 16 initial order features with 10 post-allotment operational features available at the 5-minute landmark:

| Category | Feature Name | Description |
| :--- | :--- | :--- |
| **Initial Order Features (16)** | `last_mile_distance`, `is_zero_last_mile`, `last_mile_distance_sq`, `distance_bracket`, `order_hour`, `hour_sin`, `hour_cos`, `order_dayofweek`, `dow_sin`, `dow_cos`, `is_weekend`, `meal_period`, `is_peak_meal_window`, `rolling_order_volume_15m`, `rolling_order_volume_60m`, `demand_acceleration` | Pre-order temporal, geographic, and demand velocity features |
| **Landmark Dispatch Features (10)** | `first_mile_distance` | Distance from courier location at allotment to restaurant (km) |
| | `is_extreme_first_mile` | Binary indicator for courier pickup distance > 5.0 km |
| | `first_to_last_mile_ratio` | Ratio of courier approach distance to customer delivery distance |
| | `total_route_distance` | Sum of first-mile and last-mile distances |
| | `courier_session_time_min` | Duration active on shift prior to order assignment |
| | `courier_fatigue_flag` | Binary indicator for extended shift length (> 300 minutes) |
| | `is_delayed_allotment` | Flag indicating allotment took longer than nominal SLA (> 3 min) |
| | `allot_delay_min` | Actual minutes elapsed between order creation and courier allotment |
| | `has_accepted_by_landmark` | Binary indicator whether courier accepted assignment within 5 min |
| | `accept_delay_at_landmark` | Minutes between courier notification and acceptance at landmark |

### 3.4 Quantitative Evaluation & Alert Budget Operating Points
Evaluated on strict chronological test set (54,150 orders evaluated post-landmark; base rate prevalence: 1.01%, 546 actual cancellations).

- **Area Under PR Curve (PR-AUC)**: `0.0829` (Validation: `0.0595`)
- **Area Under ROC Curve (ROC-AUC)**: `0.7814`

#### Alert Budget Operating Table (Test Set Performance)

| Target Budget | Threshold | Alerts / 1,000 | Precision | Recall | F1 Score | Specificity | False Positive Rate | True Positives | False Positives |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **5 per 1,000** | `0.6686` | **4.06** | **25.00%** | **10.07%** | **0.1436** | 99.69% | 0.31% | 55 | 165 |
| **10 per 1,000** | `0.5113` | **8.68** | **16.38%** | **14.10%** | **0.1516** | 99.27% | 0.73% | 77 | 393 |
| **25 per 1,000** | `0.3499` | 23.71 | 8.88% | 20.88% | 0.1246 | 97.82% | 2.18% | 114 | 1,170 |
| **50 per 1,000** | `0.2668` | 49.34 | 5.28% | 25.82% | 0.0876 | 95.28% | 4.72% | 141 | 2,531 |

### 3.5 Calibration Diagnostics & Reliability
Because raw GBDT predictions under extreme class imbalance (1.01% positive class) suffer from severe overconfidence, an **Isotonic Regression Calibrator** was fitted on the validation set.

- **Brier Score (Uncalibrated)**: `0.028316`
- **Brier Score (Calibrated)**: `0.009617` (**66.04% Brier Score Reduction**)
- **Expected Calibration Error (ECE)**: `0.0003` (reduced from `0.1181`)
- **Maximum Calibration Error (MCE)**: `0.3750`
- **True Test Prevalence**: `1.01%` (Calibrated mean probability: `1.01%` vs Uncalibrated mean: `12.82%`)

### 3.6 Uncertainty Limitations & False Alarm Tradeoffs
1. **High False Positive Burden**: At the approved operational operating point (5 to 10 alerts per 1,000 orders), precision is **16.38% to 25.00%**. This means **75% to 84% of all generated alerts are false alarms** (orders that would have completed normally).
2. **Strict Landmark Timing Requirement**: The model cannot be evaluated prior to $t_{\text{allot}} + 5\text{ min}$. Calling this model before courier allotment generates undefined feature inputs and is strictly blocked by `MLInferenceService`.
3. **No Direct Customer Intent Signals**: The model infers cancellation risk strictly from delivery friction proxies (allotment delay, first-mile distance). It does not observe customer support chat, app cancellations clicks, or merchant phone calls.

### 3.7 Governance & Approved Usage
- **APPROVED USAGE**:
  - Gated triage queue for human operations specialists (`OPS_LEAD`) under strict 5-to-10 alerts per 1,000 order budget.
  - Multi-agent investigation trigger for Customer Resolution Agent to draft gentle status reassurance.
  - Operational health dashboard monitoring.
- **PROHIBITED INTERPRETATIONS**:
  - **AUTOMATED CANCELLATION IS STRICTLY PROHIBITED**: The system must NEVER automatically cancel orders or issue unilateral refunds based on this model's output.
  - **MUST NEVER** be interpreted as a certainty of cancellation.
  - **MUST NEVER** trigger intrusive customer-facing alarms without operator confirmation.

---

## 4. Research-Only Artifacts: Tasks B and C1

The repository preserves Phase 2.5 research models to prevent silent regression, but both are strictly classified as **`RESEARCH_ONLY`** and barred from triggering operational workflows.

### 4.1 Task B: Courier Allocation Delay Risk (> 3 minutes)
- **Model**: `data/artifacts/models/phase_2_5/task_b_improved_model.joblib`
- **Prediction Point**: Order placement ($t_0$)
- **Target**: Whether courier allocation takes longer than 3 minutes (`target_is_allocation_delayed`).
- **Validation PR-AUC**: `0.0706` | **Test PR-AUC**: `0.0729` (Baseline prior: ~6.0%)
- **Test Performance at 10/1k Budget**: Precision `11.73%`, Recall **`3.77%`** (misses 96.2% of allocation delays).
- **Governance Classification**: **`NOT_APPROVED` / `RESEARCH_ONLY`**
- **Justification**: At acceptable alert budgets, recall is negligible (< 4%). At maximum F1, over 58% of all platform orders are flagged, yielding a 93% false alarm rate. Standalone operational alarms are strictly prohibited.

### 4.2 Task C1: Upfront Cancellation Risk
- **Model**: `data/artifacts/models/phase_2_5/task_c1_improved_model.joblib`
- **Prediction Point**: Order placement ($t_0$)
- **Target**: Order cancellation (`target_is_cancelled`).
- **Validation PR-AUC**: `0.0141` | **Test PR-AUC**: `0.0133` (Base rate prior: **1.11%**)
- **Governance Classification**: **`RESEARCH_ONLY`**
- **Justification**: Static coordinates and pre-order timestamps contain near-zero signal regarding whether a customer will cancel 40 minutes later. The model exhibits zero actionable lift over the random baseline prior. Operational triggering is strictly prohibited.

---

## 5. Dataset Provenance & Representativeness Boundaries

### 5.1 Kaggle Delivery Fleet Dataset (`cbhavik/swiggyzomato-order-information`)
- **Canonical Kaggle Reference**: `cbhavik/swiggyzomato-order-information`
- **Local File**: `data/raw/orders/Rider-Info.csv` (85 MB)
- **Verified Row Counts**:
  - **Total Raw Rows**: `450,000`
  - **Unique `order_id` Values**: `449,999`
  - **Duplicate Rows**: Exactly `1` duplicate row (`order_id = 181402`, identical records at index 420455 and 420456).
  - **Ingestion Table**: `historical_orders` (strictly segregated from operational `orders` table).
- **Resolution of 45,593 Discrepancy**:
  The 45,593 number appeared in early Phase 2.1 documentation due to reviewing an initial candidate benchmark dataset (`gauravmalik26/food-delivery-dataset`, which contained 45,593 rows). The project subsequently selected and placed `cbhavik/swiggyzomato-order-information` (450,000 rows) into `data/raw/orders/Rider-Info.csv`.
- **Representativeness Gaps**:
  1. **Missing Kitchen Milestones**: 42.3% of raw historical records lack restaurant food preparation timestamps.
  2. **No Live Telematics**: Historical records contain point coordinates, not continuous GPS breadcrumbs or turn-by-turn velocity.
  3. **Synthetic Post-Processing**: Landmark dispatch intervals were derived through verified temporal simulations to enable landmark evaluation.

### 5.2 Hugging Face Restaurant Dataset
- **Source**: Curated Bangalore restaurant dataset.
- **Ingestion Table**: `restaurants` (`data_source = "PUBLIC_HISTORICAL"`).
- **Usage**: Provides realistic cuisine profiles, price brackets, and historical average prep times.
- **Representativeness Gaps**: Contains static menu and rating snapshots; does not reflect live kitchen backlogs, seasonal closures, or power outages.

---

## 6. Summary Checklist for Engineering & Audit Teams

- [x] Task A documented as $t_0$ conditional duration quantile model ($P_{10}, P_{50}, P_{90}$).
- [x] Task A prohibited from being described as dynamic remaining-ETA.
- [x] Task A crossing prevention ($P_{10} \le P_{50} \le P_{90}$) verified and documented.
- [x] Task C2 documented as $t_{\text{allot}} + 5\text{ min}$ eventual cancellation model.
- [x] Task C2 prohibited from being described as imminent cancellation.
- [x] Task C2 Isotonic calibration and alert budgets (5/1k, 10/1k) verified.
- [x] Tasks B and C1 explicitly stamped `RESEARCH_ONLY` with operational deployment prohibited.
- [x] Explicit warning alert added: historical test performance does not establish generalization to new cities, time periods, or live operating conditions.
- [x] Exact raw row counts (450,000), unique IDs (449,999), duplicates (1), and Kaggle dataset source reconciled.
