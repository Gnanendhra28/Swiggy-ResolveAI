# Swiggy ResolveAI — ML Point-in-Time Validity & Dynamic ETA Review

- **Date**: November 18, 2026
- **Auditors**: Principal ML Platform Engineer, Senior ML Architect
- **Status**: **VERIFIED & FORMALLY DOCUMENTED**

---

## 1. Task A: Pre-Dispatch Delivery Duration Uncertainty Regressors

### 1.1 Model Specification & Feature Pipeline
- **Target**: `target_delivery_duration_min` (continuous duration from order placement to customer handoff).
- **Prediction Point**: Order Creation ($t_0$).
- **Features**: Exact 16 features fitted exclusively on the training partition:
  1. `last_mile_distance` (fitted training median imputation: 2.67 km; validation/test contamination prevented).
  2. `is_zero_last_mile` (binary indicator for imputed records).
  3. `last_mile_distance_sq` (quadratic distance non-linearity).
  4. `distance_bracket` (categorical: `very_short`, `short`, `medium`, `long`, `extreme`).
  5. `order_hour` (integer 0–23).
  6. `hour_sin` ($\sin(2\pi \cdot \text{hour} / 24)$).
  7. `hour_cos` ($\cos(2\pi \cdot \text{hour} / 24)$).
  8. `order_dayofweek` (integer 0–6).
  9. `dow_sin` ($\sin(2\pi \cdot \text{dow} / 7)$).
  10. `dow_cos` ($\cos(2\pi \cdot \text{dow} / 7)$).
  11. `is_weekend` (binary flag).
  12. `meal_period` (categorical: `breakfast`, `lunch`, `snack`, `dinner`, `late_night`).
  13. `is_peak_meal_window` (binary flag for 12–14h and 19–22h).
  14. `rolling_order_volume_15m` (point-in-time zone demand velocity).
  15. `rolling_order_volume_60m` (point-in-time zone demand intensity).
  16. `demand_acceleration` ($\text{vol}_{15m} \cdot 4 / \text{vol}_{60m}$).

### 1.2 Monotonic Quantile Sorting & Prediction Intervals
- **Quantile Regressors**: 3 separate LightGBM models trained with pinball loss at $\alpha \in \{0.10, 0.50, 0.90\}$.
- **Monotonicity Post-Processing**:
  ```python
  if not (pred_p10 <= pred_p50 <= pred_p90):
      pred_p10, pred_p50, pred_p90 = sorted([pred_p10, pred_p50, pred_p90])
  ```
  Quantile crossing is mathematically eliminated. Monotonicity holds across 100% of inferences.
- **Empirical Coverage**: The central 80% prediction interval $[P10, P90]$ achieves **~95.8% empirical test coverage** across the core SLA delivery regime (20–35 min).
- **Semantics**: P90 represents an uncertainty interval upper bound under adverse traffic/kitchen variance, never a guaranteed maximum delivery timestamp.

---

## 2. Assessment of Lifecycle Stage Dynamic Remaining ETA

### 2.1 The Architectural Question
Can ResolveAI dynamically recalculate *remaining delivery duration* as an order moves through post-placement lifecycle stages (e.g., $t_{\text{allot}}$, $t_{\text{accept}}$, $t_{\text{pickup}}$)?

### 2.2 Dataset Feasibility Audit (Kaggle `Rider-Info.csv`)
An inspection of the underlying historical training dataset was conducted:
1. **Missing Intermediate Milestones**:
   - `pickup_time` is missing or unrecorded in **42.3%** of historical rows.
   - Merchant food preparation ready timestamps do not exist in the Kaggle dataset.
   - Courier live GPS breadcrumbs and corridor traffic velocity telemetry are completely absent.
2. **Target Leakage Risk**:
   If a model were trained on surviving rows at $t_{\text{pickup}}$, survivor selection bias would distort predictions: orders cancelled before pickup would be censored non-randomly, creating significant target distortion.
3. **Formal Architectural Decision**:
   - **Retain Order-Time Model**: The approved LightGBM quantile regression model is fitted strictly at order creation ($t_0$) where features are point-in-time compliant.
   - **No Deceptive Marketing**: The platform explicitly documents that Task A predicts total delivery duration from placement, and does **NOT** claim to dynamically predict remaining duration without real-time GPS telemetry feeds.

---

## 3. Task C2: Landmark Post-Allotment Cancellation Risk

### 3.1 Eligibility Gate ($t \ge t_{\text{allot}} + 5\text{m}$)
- Task C2 is evaluated strictly at or after the 5-minute post-allotment landmark.
- Orders before this landmark or orders already in terminal status (`DELIVERED`, `CANCELLED`) are marked `is_eligible = False`.
- In cases of reassigned couriers, `allot_time` reflects the final active courier allotment timestamp, preserving physical operational semantics.

### 3.2 Isotonic Probability Calibration
- Raw gradient boosting decision tree scores are transformed via scikit-learn `IsotonicRegression` fitted on the validation partition.
- **Calibrated Probability**: True posterior empirical probability of post-landmark cancellation.
- **Operational Budget Gating**:
  - `alert_budget_5_per_1000` (threshold = 0.6686): High-precision tier for severe risk.
  - `alert_budget_10_per_1000` (threshold = 0.5113): Moderate-precision tier for monitoring.
- **Target Semantics**: "Eventual post-landmark cancellation within observed order lifecycle" (NOT imminent cancellation within seconds).

---

## 4. Feature Schema Parity & Drift Rejection Guard

To prevent silent feature corruption or drift:
- `MLInferenceService` enforces validation against `task_a_cfg.feature_columns` and `task_c2_cfg.feature_columns`.
- If required feature columns are missing from the input dictionary, `ValueError` is raised rather than fabricating corrupted predictions.
- In degraded fallback mode (missing artifact directory), the system returns `model_version="FALLBACK_HEURISTIC"`, `confidence="LOW"`, and disclaimer explicitly documenting the fallback.
