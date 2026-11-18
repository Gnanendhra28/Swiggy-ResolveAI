# Swiggy ResolveAI — Phase 2.5 Model Improvement, Uncertainty & Cancellation Intelligence Report

**Document ID:** `docs/phase_2_5_model_improvement_report.md`  
**Phase:** 2.5 — Advanced Model Optimization, ETA Uncertainty & Cancellation Intelligence  
**Role:** Senior Machine Learning Engineer & ML Architect  
**Date:** November 18, 2026  
**Status:** Complete, Reconciled, and Verified  

---

## 1. Executive Summary

Phase 2.5 executes advanced model optimization across all four operational machine learning tasks of Swiggy ResolveAI. Addressing the diagnostic findings and claims audit from Phases 2.4 and 2.4.1, this phase implements:
1. **Conditional Quantile Regression for Task A:** Replaces scalar point predictions with a mathematically principled 80% prediction interval ($[P_{10}, P_{90}]$) anchored by $P_{50}$, enforcing monotonic quantile ordering.
2. **Alert-Budget Constrained Optimization for Tasks B, C1, and C2:** Replaces arbitrary F1-maximal thresholds with realistic operational alert budgets ($5, 10, 25, 50$ alerts per 1,000 orders).
3. **Hyperparameter Tuning via Optuna on Validation Data:** Conducts disciplined parameter searches strictly within the validation partition, leaving the test partition untouched for one-time historical benchmark comparison.
4. **Isotonic Probability Calibration for Task C2:** Calibrates distorted ranking scores into true Bayesian posterior probabilities, slashing test Brier score by **66.04%** and reducing Expected Calibration Error (ECE) to **0.0003**.
5. **Final Model Registry & Decision Matrix:** Classifies all candidate models under formal ML governance statuses (`APPROVED_FOR_CONTROLLED_TRIAGE`, `APPROVED_FOR_SIMULATION`, `NOT_APPROVED`, `RESEARCH_ONLY`).

---

## 2. Repository & Artifact Audit

Before beginning optimization, existing artifacts, datasets, and codebase foundations were audited:

### 2.1 Preserved Architecture & Immutability
- **FastAPI Backend & Next.js Frontend:** Unmodified; no API routing or inference hooks added in Phase 2.5.
- **PostgreSQL Database & Alembic Migrations:** Preserved with zero schema changes.
- **Processed Datasets:** All models trained strictly on approved Phase 2.2.1 Parquet partitions (`data/processed/delivery_duration/`, `allocation_delay/`, `cancellation/`, `cancellation/operational_landmark/`). No raw data modified.
- **Phase 2.3 Baseline Artifacts:** Fully preserved in `data/artifacts/models/` for regression testing and historical comparison.
- **Phase 2.4 & 2.4.1 Diagnostics:** Verified and archived in `data/artifacts/diagnostics/`.

### 2.2 Strict Evaluation Protocol
- **Training Partition (70.2%):** `2021-01-26` to `2021-02-02` — used exclusively for fitting model weights, quantile trees, and feature scalers.
- **Validation Partition (18.0%):** `2021-02-03` to `2021-02-04` — used exclusively for Optuna hyperparameter optimization, threshold quantile selection for alert budgets, and calibration fitting.
- **Test Partition (11.8%):** `2021-02-05` to `2021-02-06` — evaluated strictly once. Because Phase 2.3 test results have already been inspected, test results in this report are formally designated as **iterative historical benchmark comparisons**, not fresh independent evaluations.

---

## 3. Task A: ETA Quantile Regression & Uncertainty Estimation

### 3.1 Model Architecture & Quantile Objectives

To resolve the limitation identified in Phase 2.4.1 (where the baseline point predictor could not produce prediction intervals), three separate LightGBM models were trained targeting the 10th, 50th, and 90th percentiles using the Pinball (tilted absolute) loss:

$$L_q(y, \hat{y}) = \max(q(y - \hat{y}), (q - 1)(y - \hat{y})), \quad q \in \{0.10, 0.50, 0.90\}$$

- **Inputs (16 features):** Approved order-time features (`last_mile_distance`, `meal_period`, `rolling_order_volume_60m`, etc.). Zero kitchen features used.
- **Hyperparameters:** `n_estimators=150`, `learning_rate=0.05`, `num_leaves=31`, `min_child_samples=30`, `random_state=42`.
- **Artifacts Saved:** `task_a_quantile_p10.joblib`, `task_a_quantile_p50.joblib`, `task_a_quantile_p90.joblib`.

### 3.2 Monotonic Quantile Ordering & Crossing Correction

In independent quantile regression, tree splits can occasionally produce quantile crossing ($P_{10} > P_{50}$ or $P_{50} > P_{90}$).
- **Crossing Rate on Test Set:** **0.0000%** (0 out of 53,588 orders exhibited crossing out-of-the-box).
- **Enforcement Layer:** A monotonic sorting post-processor (`np.sort([p10, p50, p90], axis=1)`) was embedded to mathematically guarantee $P_{10} \le P_{50} \le P_{90}$ for all inference queries.

### 3.3 Pinball Loss & P50 vs. Point Baseline

| Metric Dimension | Point Baseline (Phase 2.3) | Quantile P50 (Phase 2.5) | Pinball Loss Improvement |
| :--- | :---: | :---: | :---: |
| **Pinball Loss (q = 0.10)** | N/A | **1.5760** | Baseline cannot evaluate P10 |
| **Pinball Loss (q = 0.50)** | 4.6925 | **4.5814** | **-2.37% (P50 directly optimizes median)** |
| **Pinball Loss (q = 0.90)** | N/A | **2.6949** | Baseline cannot evaluate P90 |
| **Test MAE** | 9.385 min | **9.163 min** | **-0.22 min improvement** |
| **Test RMSE** | 12.766 min | 13.048 min | Expected (P50 optimizes L1, not L2) |

### 3.4 80% Prediction Interval ($[P_{10}, P_{90}]$) Coverage Analysis

Evaluated on 53,588 completed test orders:
- **Nominal Target Coverage:** 80.00%
- **Empirical Coverage on Test Set:** **78.60%** (within 1.4% of nominal coverage)
- **Mean 80% Interval Width:** **27.92 minutes**
- **Below $P_{10}$ (Deliveries faster than lower bound):** 10.99% (nominal: 10.0%)
- **Above $P_{90}$ (Deliveries slower than upper bound):** 10.42% (nominal: 10.0%)

![Task A Quantile Intervals](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/data/artifacts/diagnostics/phase_2_5/plots/task_a_quantile_intervals.png)

### 3.5 Bucket-Level Calibration & The Long-Tail Undercoverage Reality

Breaking down interval coverage and width across delivery-duration subgroups:

| Duration Subgroup | Subgroup Size ($N$) | % of Total Orders | Empirical 80% Coverage | Mean Interval Width | $P_{50}$ MAE | Point Baseline MAE | Deliveries $> P_{90}$ (Undercoverage) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ultra-Fast (< 20 min)** | 8,343 | 15.57% | 42.86% | 26.75 min | 10.96 min | 13.12 min | 0.00% |
| **Core SLA Zone (20–35 min)** | **27,271** | **50.89%** | **95.86%** | **27.86 min** | **4.59 min** | **5.81 min** | **0.03%** |
| **Extended Trip (35–50 min)** | 13,326 | 24.87% | 88.29% | 28.44 min | 10.08 min | 7.98 min | 11.71% |
| **Long Tail (> 50 min)** | 4,648 | 8.67% | **13.68%** | 28.86 min | 30.15 min | 27.70 min | **86.32%** |

#### Critical Engineering Insight:
1. **Core Operating Zone (20–35 min, 51% of volume):** The model is outstanding. Empirical coverage is **95.86%**, $P_{50}$ MAE is only **4.59 minutes**, and upper-bound breaches are virtually zero (0.03%).
2. **The Long-Tail Blindspot (> 50 min, 8.7% of volume):** In the extreme tail, empirical coverage collapses to **13.68%**, and **86.32% of deliveries blow past $P_{90}$**. Because order-time features cannot observe restaurant prep bottlenecks or courier re-allocation delays, the model predicts an interval of $[22\text{ min}, 51\text{ min}]$ for an order that takes 85 minutes.
3. **Governance Ruling:** The model is **APPROVED FOR SIMULATION** and for customer display *provided the full $[P_{10}, P_{90}]$ band is shown*. The "ETA + 15 min" intervention rule remains an unvalidated heuristic policy.

---

## 4. Task B: Allocation Delay Model Improvement & Alert Budgets

### 4.1 Optimization Protocol & Hyperparameters

Task B (`target_is_allocation_delayed`) was tuned using Optuna over 8 trials on the validation partition maximizing PR-AUC:
- **Best Hyperparameters:** `n_estimators=100`, `learning_rate=0.0398`, `num_leaves=15`, `max_depth=5`, `min_child_samples=35`, `scale_pos_weight=4.80`, `reg_alpha=0.454`, `reg_lambda=0.404`.
- **Validation PR-AUC:** **0.0706** (vs Phase 2.3 baseline `0.0698`).
- **Test PR-AUC:** **0.0729** (vs Phase 2.3 baseline `0.0728`).

### 4.2 Explicit Operational Alert Budget Analysis

Evaluating thresholds strictly calibrated on validation data to meet operational volume budgets on the test partition ($N = 54,221$, 3,344 true delays):

| Operational Alert Budget | Selected Threshold ($\tau$) | Test Alerts / 1,000 Orders | Test Precision | Test Recall | Test F1 | True Positives (TP) | False Positives (FP) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **5 alerts / 1,000 orders** | $\tau = 0.4539$ | 16.60 | **10.67%** | 2.87% | 0.0452 | 96 | 804 |
| **10 alerts / 1,000 orders** | $\tau = 0.4246$ | 19.81 | **11.73%** | 3.77% | 0.0570 | 126 | 948 |
| **25 alerts / 1,000 orders** | $\tau = 0.3684$ | 41.53 | 9.99% | 6.73% | 0.0804 | 225 | 2,027 |
| **50 alerts / 1,000 orders** | $\tau = 0.3204$ | 77.07 | 8.88% | 11.09% | 0.0987 | 371 | 3,808 |
| **Baseline Optimal F1** | $\tau = 0.4700$ | 580.97 | 6.64% | 62.59% | 0.1201 | 2,093 | 29,408 |

### 4.3 Governance Assessment: Model Not Approved

> [!CAUTION]
> **Operational Ruling:**  
> Task B is **NOT APPROVED** for operational alerting. To achieve 11.73% precision, recall is restricted to an unusable **3.77%** (missing 96.2% of allocation delays). Conversely, achieving 62.6% recall requires alerting on **58.1% of platform volume**. Downstream courier batching utility remains an **untested experimental hypothesis**.

---

## 5. Task C1: Upfront Cancellation Model Optimization

### 5.1 Optimization Protocol & Results

Task C1 (`target_is_cancelled`) was tuned using Optuna over 8 trials on the validation partition:
- **Best Hyperparameters:** `n_estimators=120`, `learning_rate=0.0381`, `num_leaves=11`, `max_depth=4`, `min_child_samples=89`, `scale_pos_weight=1.23`, `reg_alpha=0.076`, `reg_lambda=0.174`.
- **Validation PR-AUC:** **0.0135** (vs Logistic Regression baseline `0.0134`, Dummy `0.0110`).
- **Test PR-AUC:** **0.0175** (vs Logistic Regression `0.0152`).

### 5.2 Alert Budget Performance on Test Partition ($N = 54,221$, 603 cancellations)

| Alert Budget | Selected Threshold ($\tau$) | Test Alerts / 1,000 | Test Precision | Test Recall | Test F1 | TP | FP |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **5 alerts / 1,000** | $\tau = 0.2312$ | 4.30 | **1.72%** | 0.66% | 0.0096 | 4 | 229 |
| **10 alerts / 1,000** | $\tau = 0.2063$ | 8.24 | **1.79%** | 1.33% | 0.0152 | 8 | 439 |
| **25 alerts / 1,000** | $\tau = 0.1720$ | 22.65 | **1.79%** | 3.65% | 0.0240 | 22 | 1,206 |
| **50 alerts / 1,000** | $\tau = 0.1553$ | 49.57 | **1.60%** | 7.13% | 0.0261 | 43 | 2,645 |

### 5.3 Governance Assessment: Research Only

**Finding:**  
Even with extensive regularization and Optuna search, test precision peaks at **1.79%** against a 1.11% prior prevalence (1.6x lift). At 10 alerts per 1,000 orders, 439 customers are falsely alarmed for every 8 cancellations captured.
- **Status:** **RESEARCH_ONLY**. Model retained for benchmark continuity; prohibited from production deployment.

---

## 6. Task C2: Operational Landmark Cancellation Model (High Priority)

### 6.1 Hyperparameter Search & Model Improvement

Task C2 (`target_cancelled_post_landmark`) is the core intelligence component of ResolveAI. Tuned using Optuna over 12 trials on validation PR-AUC:
- **Best Hyperparameters:** `n_estimators=120`, `learning_rate=0.0445`, `num_leaves=26`, `max_depth=6`, `min_child_samples=69`, `scale_pos_weight=17.59`, `reg_alpha=0.169`, `reg_lambda=0.290`.
- **Validation PR-AUC:** **0.0595** (vs Phase 2.3 baseline `0.0550`, +8.2% relative gain).
- **Test PR-AUC:** **0.0829** (vs Phase 2.3 baseline `0.0727`, **+14.0% relative gain**).

![Task C2 PR Curve Comparison](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/data/artifacts/diagnostics/phase_2_5/plots/task_c2_pr_comparison.png)

### 6.2 Alert-Budget Constrained Operational Performance

Evaluated on the landmark-eligible test partition ($N = 54,150$, 546 true post-landmark cancellations):

| Operational Alert Budget | Selected Threshold ($\tau$) | Test Alerts / 1,000 Orders | Test Precision | Test Recall | Test F1 | Intercepted Cancels (TP) | False Alerts (FP) | Missed Cancels (FN) | Lift over Prior |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **5 alerts / 1,000** | $\tau = 0.6686$ | **4.06** | **25.00%** | **10.07%** | **0.1436** | **55** | **165** | 491 | **24.8x** |
| **10 alerts / 1,000** | $\tau = 0.5113$ | **8.68** | **16.38%** | **14.10%** | **0.1516** | **77** | **393** | 469 | **16.2x** |
| **25 alerts / 1,000** | $\tau = 0.3499$ | 23.71 | **8.88%** | **20.88%** | **0.1246** | 114 | 1,170 | 432 | 8.8x |
| **50 alerts / 1,000** | $\tau = 0.2668$ | 49.34 | **5.28%** | **25.82%** | **0.0876** | 141 | 2,531 | 405 | 5.2x |

![Task C2 Alert Budgets](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/data/artifacts/diagnostics/phase_2_5/plots/task_c2_alert_budgets.png)

#### Operational Takeaways:
1. **5 alerts per 1,000 budget ($\tau = 0.6686$):** Precision is **25.00%** (1 in 4 flagged orders cancels). Alerts only **4.06 orders per 1,000**, intercepting 55 cancellations with only 165 false alarms across 54,150 orders.
2. **10 alerts per 1,000 budget ($\tau = 0.5113$):** Captures **77 cancellations** (a +22.2% increase over Phase 2.3's 63 cancellations) at **16.38% precision** and max F1 of **0.1516**.

### 6.3 Isotonic Probability Calibration

To eliminate the probability distortion caused by `scale_pos_weight`, an `IsotonicRegression` model was fitted strictly on the validation partition probabilities:

| Calibration Metric | Uncalibrated Model | Isotonic Calibrated Model | Operational Improvement |
| :--- | :---: | :---: | :---: |
| **Brier Score Loss** | 0.028316 | **0.009617** | **-66.04% Brier Score Reduction** |
| **Expected Calibration Error (ECE)** | 0.1181 | **0.0003** | **Near-zero calibration error** |
| **Maximum Calibration Error (MCE)** | 0.6198 | **0.3750** | Substantially dampened extreme error |
| **Mean Predicted Probability** | 0.1282 | **0.0101** | **Matches exact test prevalence (0.0101)** |

![Task C2 Calibration Comparison](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/data/artifacts/diagnostics/phase_2_5/plots/task_c2_calibration_comparison.png)

```
Test Quantile Calibration Bins (Calibrated Model):
Bin [0.0, 0.1]: 53,998 orders | Mean Confidence: 0.94% | Empirical Accuracy: 0.93% | Error: 0.01%
Bin [0.1, 0.2]:     92 orders | Mean Confidence: 16.44% | Empirical Accuracy: 18.48% | Error: 2.04%
Bin [0.2, 0.5]:     60 orders | Mean Confidence: 31.25% | Empirical Accuracy: 30.00% | Error: 1.25%
```

### 6.4 Target Semantics & Operational Language

> [!IMPORTANT]
> **Canonical Target Definition:**  
> The target variable represents **"eventual post-landmark cancellation within the observed lifecycle."**  
> - It is **NOT** a fixed-horizon prediction (e.g. not "will cancel in the next 15 minutes").  
> - It does **NOT** imply that flagged orders will imminently cancel.  
> - At the recommended 5–10 alert budget, the model detects **10.1% to 14.1% of test cancellations** (86%–90% go undetected).  
> - **Operational Mandate:** Triaged orders must receive **non-intrusive monitoring** (e.g. priority courier re-route or KDS readiness ping). Proactive customer-facing cancellation refunds are prohibited.

---

## 7. Model Explainability & SHAP Analysis

Using `shap.TreeExplainer` on 1,000 test samples of the improved Task C2 model:

![Task C2 Improved SHAP Summary](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/data/artifacts/diagnostics/phase_2_5/plots/shap_summary_task_c2_improved.png)

### 7.1 Key Feature Drivers & Directional Impact
1. **`accept_delay_at_landmark` (Mean \|SHAP\| = 0.245):** Couriers taking $> 3.5$ minutes to accept the order after assignment strongly drive positive cancellation risk (red points to the right).
2. **`allot_delay_min` (Mean \|SHAP\| = 0.218):** Dispatch delays in finding a courier compound acceptance delays, pushing log-odds higher.
3. **`first_mile_distance` & `first_to_last_mile_ratio` (Mean \|SHAP\| = 0.182):** Long first-mile transit (> 3.5 km) strongly correlates with courier dropouts and eventual cancellation.
4. **`last_mile_distance` (Mean \|SHAP\| = 0.165):** Longer delivery journeys increase customer fatigue and cancellation probability.

### 7.2 Non-Causality Disclaimer
SHAP values represent observational conditional associations learned by tree structures. They **do not prove causal intervention effects**. Clamping `allot_delay_min` by forcing dispatch to distant couriers will likely degrade performance due to longer first-mile transit.

---

## 8. Final Model Decision Matrix

The complete four-task comparison matrix with formal ML governance classifications:

| Task | Phase 2.3 Baseline | Phase 2.5 Candidate | Validation Performance | Test Performance | Operational Governance Status | Operational Justification |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **Task A: ETA Regression** | LightGBM Point Regressor (MAE: 9.38m) | LightGBM Quantile Regressors (P10, P50, P90) | P50 Pinball: 4.581<br>80% Coverage: 78.6% | P50 MAE: **9.16m**<br>80% Coverage: **78.6%**<br>Mean Width: **27.9m** | **APPROVED_FOR_SIMULATION** | Approved for operations simulation and display of $[P_{10}, P_{90}]$ intervals. Point predictions prohibited without intervals. ETA + 15m rule remains unvalidated. |
| **Task B: Allocation Delay** | LightGBM Classifier (Val PR-AUC: 0.0698) | LightGBM Optuna Tuned (`scale_pos_weight=4.8`) | Val PR-AUC: **0.0706** | Test PR-AUC: **0.0729**<br>Budget 10/1k: Prec 11.7%, Rec 3.8% | **NOT_APPROVED** | Not approved for standalone alerting. At max F1, flags 58% of volume. At 10/1k budget, recall is only 3.8%. Downstream batching is an untested hypothesis. |
| **Task C1: Upfront Cancel** | Logistic / LightGBM (Val PR-AUC: 0.0134 / 0.0123) | LightGBM Optuna Tuned (Val PR-AUC: 0.0135) | Val PR-AUC: **0.0135** (Prior: 1.10%) | Test PR-AUC: **0.0175** (Prior: 1.11%) | **RESEARCH_ONLY** | Static order features cannot predict upfront cancellation prior to kitchen/courier dynamics. Retain baseline; prohibited from deployment. |
| **Task C2: Landmark Cancel** | LightGBM Baseline (Val PR-AUC: 0.0550, Test: 0.0727) | LightGBM Optuna Tuned + Isotonic Calibrated | Val PR-AUC: **0.0595**<br>Brier Reduction: **-66.0%** | Test PR-AUC: **0.0829**<br>Budget 5/1k: Prec **25.0%**, Rec **10.1%**<br>Budget 10/1k: Prec **16.4%**, Rec **14.1%** | **APPROVED_FOR_CONTROLLED_TRIAGE** | Approved for controlled triage queue under 5-to-10 alert budget. Captures 55–77 cancellations at 16%–25% precision. Monitoring only; non-intrusive. |

---

## 9. Verification Artifacts & Test Suite Evidence

### 9.1 Generated Model Artifacts (`data/artifacts/models/phase_2_5/`)
- `task_a_quantile_p10.joblib`
- `task_a_quantile_p50.joblib`
- `task_a_quantile_p90.joblib`
- `task_b_improved_model.joblib`
- `task_c1_improved_model.joblib`
- `task_c2_improved_model.joblib`
- `task_c2_calibrator.joblib`
- [data/artifacts/models/phase_2_5/registry.json](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/data/artifacts/models/phase_2_5/registry.json)

### 9.2 Generated Diagnostic Visualizations (`data/artifacts/diagnostics/phase_2_5/plots/`)
- [task_a_quantile_intervals.png](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/data/artifacts/diagnostics/phase_2_5/plots/task_a_quantile_intervals.png)
- [task_c2_alert_budgets.png](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/data/artifacts/diagnostics/phase_2_5/plots/task_c2_alert_budgets.png)
- [task_c2_calibration_comparison.png](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/data/artifacts/diagnostics/phase_2_5/plots/task_c2_calibration_comparison.png)
- [task_c2_pr_comparison.png](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/data/artifacts/diagnostics/phase_2_5/plots/task_c2_pr_comparison.png)
- [shap_summary_task_c2_improved.png](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/data/artifacts/diagnostics/phase_2_5/plots/shap_summary_task_c2_improved.png)

### 9.3 Automated Test Suite Execution
- **Phase 2.5 Tests (`test_ml_phase_2_5.py`):** 11 passed (covering quantiles, pinball loss, coverage, alert budgets, calibration, registry).
- **Phase 2.4 / 2.4.1 Diagnostics (`test_ml_diagnostics.py`):** 17 passed.
- **Phase 2.3 Baseline Models (`test_ml_models.py`):** 9 passed.
- **Phase 2.2 Preprocessing (`test_ml_preprocessing.py`):** 11 passed.
- **Phase 1 Infrastructure & APIs:** 25 passed.
- **Total:** **73 passed in 13.90s (100% pass rate)**.
