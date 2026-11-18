# Swiggy ResolveAI — Phase 2.4.1 Diagnostic Reconciliation and Operational Claims Audit Report

**Document ID:** `docs/phase_2_4_1_diagnostic_reconciliation_report.md`  
**Phase:** 2.4.1 — Diagnostic Reconciliation and Operational Claims Audit  
**Role:** Senior Machine Learning Engineer  
**Date:** November 18, 2026  
**Status:** Audit Complete, Reconciled, and Regression-Tested  

---

## 1. Executive Summary & Audit Mandate

Phase 2.4.1 conducts a formal engineering audit and reconciliation of the diagnostic evaluations and operational claims made in Phase 2.4. Operating under strict ML governance constraints, this audit verifies model capabilities, reconciles evaluation cohorts, audits operational claims, and records dual-track model selection **without redesigning the system architecture or unnecessarily retraining baseline models**.

### Core Audit Outcomes:
1. **Task A (ETA Intervals & Heuristics):** Persisted LightGBM model is verified as a point predictor ($E[Y|X]$) with no native quantile support. Prediction intervals are marked as **Future Work**, and the "ETA + 15-minute" intervention rule is labeled as an **unvalidated policy proposal**.
2. **Task B (Alert Burden & Batching Hypothesis):** Verified that the tuned threshold ($\tau = 0.47$) produces **580.97 alerts per 1,000 orders** (58.1% volume flagged). The model is formally designated as **NOT APPROVED** for standalone alerting, and downstream batching utility is labeled as an **untested hypothesis requiring comparative evaluation**.
3. **Task C1 (Model Selection Reconciliation):** Verified that on the declared primary validation metric (PR-AUC), **Logistic Regression** was the validation-best model (`0.0134` vs LightGBM `0.0123`). Both artifacts are preserved, test performance is rejected as a selection criterion, and the registry metadata is reconciled.
4. **Task C2 (Cohort Accounting & Denominator):** Reconciled the 71 excluded test orders (57 cancelled prior to landmark, 14 delivered prior to landmark). Verified that the scored population denominator is strictly **54,150**, yielding an exact test prevalence of **1.01%** (546 cancellations), **24.32% precision**, **11.54% recall**, and **4.78 alerts per 1,000 orders**.
5. **Task C2 (Operational Language):** Updated target terminology to *"eventual post-landmark cancellation within the observed lifecycle"*, discarded "fixed-horizon" and "imminent cancellation" claims, and emphasized that the model detects **only 11.54%** of cancellations.
6. **Regression Testing:** Added 5 new regression tests in `backend/tests/test_ml_diagnostics.py`. All **62 backend tests pass (100%)**.

---

## 2. Task A — ETA Prediction Intervals & Intervention Policy Audit

### 2.1 Persisted LightGBM Model Architecture Inspection

Inspection of `data/artifacts/models/delivery_duration/selected_model.joblib`:
- **Model Class:** `lightgbm.sklearn.LGBMRegressor`
- **Objective Function:** Default L2 regression (`objective=None`, defaulting to mean squared error).
- **Output:** Scalar real-valued point prediction $\hat{y} \in \mathbb{R}$ representing conditional mean delivery duration in minutes.
- **Conditional Quantiles:** **NOT SUPPORTED.** The model does not estimate conditional percentiles (e.g. $P_{25}, P_{75}$).

```python
# Verification from backend/tests/test_ml_diagnostics.py
preds = model.predict(X_sample)
assert len(preds.shape) == 1  # 1D scalar point prediction
```

### 2.2 Prediction Interval Claims: Marked as Future Work

> [!WARNING]
> **Governance Finding:**  
> Phase 2.4 presented empirical subgroup error spreads from global diagnostic analysis as potential uncertainty intervals $[P_{25}, P_{75}]$. Presenting point predictions alongside global descriptive percentiles as model-generated uncertainty intervals is methodologically invalid.

**Resolution:**
- Point predictions must **never** be presented to operators or customers as uncertainty bands.
- Conditional prediction intervals are formally logged as **Future Work**, requiring either:
  1. Training dedicated Pinball Loss Quantile Regressors (`LGBMRegressor(objective='quantile', alpha=0.25)` and `alpha=0.75`).
  2. Implementing distribution-free **Conformal Prediction** (e.g. Conformalized Quantile Regression) on the validation partition.

### 2.3 Intervention Policy Audit: ETA + 15-Minute Heuristic

The proposed rule *"Flag orders exceeding predicted ETA + 15 minutes as Suspected Kitchen / Transit Delay"* was audited:
- **Status:** **UNVALIDATED POLICY PROPOSAL.**
- **Evaluation:** No retrospective counterfactual analysis or discrete-event simulation has been conducted to determine the false-alarm rate, driver re-allocation cost, or customer satisfaction impact of an arbitrary 15-minute threshold.
- **Directive:** This rule must not be implemented in production dispatch without offline simulation against historical courier trajectories.

---

## 3. Task B — Ranking Utility & Standalone Alert Restrictions

### 3.1 Verification of Selected Threshold & Alert Volume

Task B targets rider allocation delays exceeding 3.0 minutes (`target_is_allocation_delayed`). Evaluated on the chronological test partition ($N = 54,221$):

| Parameter / Metric | Exact Evaluated Value | Verification Source |
| :--- | :---: | :--- |
| **Selected Decision Threshold ($\tau$)** | **0.47** | Validation F1 optimization grid sweep |
| **Test Positive Prevalence** | **6.17%** | 3,344 delayed orders / 54,221 total |
| **True Positives (TP)** | 2,093 | `task_b_allocation_diagnostics.json` |
| **False Positives (FP)** | 29,408 | `task_b_allocation_diagnostics.json` |
| **Total Flagged Orders (TP + FP)** | 31,501 | 58.10% of total platform volume |
| **Alerts per 1,000 Orders** | **580.97** | $31,501 / 54,221 \times 1,000$ |
| **Precision** | **6.64%** | $2,093 / (2,093 + 29,408)$ |
| **Recall (Sensitivity)** | **62.59%** | $2,093 / 3,344$ |
| **False Positive Rate (FPR)** | **57.81%** | $29,408 / (29,408 + 21,469)$ |

### 3.2 Formal Restriction: Standalone Alerting Prohibited

> [!CAUTION]
> **Operational Restriction:**  
> At $\tau = 0.47$, Task B flags **581 out of every 1,000 orders**, with **93.36% of alerts being false alarms** (14 false alerts for every 1 true delay). Deploying this model as a notification trigger for human dispatchers or automated support popups will cause catastrophic alert fatigue and operational gridlock.

**Decision:**
- Task B is **NOT APPROVED** for standalone alerting, automated customer communication, or human operator triage queues.

### 3.3 Downstream Batching: Hypothesized Utility vs. Evidence

Phase 2.4 suggested incorporating the Task B prediction as a feature in courier batching heuristics:
- **Audit Assessment:** This is an **untested hypothesis**, not an established capability.
- **Evidence Gap:** No empirical experiment has demonstrated that adding Task B risk scores outperforms Swiggy's existing spatial proximity heuristics or Dijkstra dispatch algorithms.
- **Requirement:** Any future integration must be benchmarked against existing dispatch baselines in simulation before operational claims can be made.

---

## 4. Task C1 — Model Selection Reconciliation

### 4.1 Audit of Phase 2.3 Selection & Discrepancy

In Phase 2.3 baseline modeling, `cancellation_upfront/selected_model.joblib` was persisted as LightGBM despite reported validation PR-AUC metrics favoring Logistic Regression.

#### Chronological Validation Set Audit ($N = 81,132$):

| Model Candidate | Validation PR-AUC | Validation ROC-AUC | Primary Selection Rule | Selection Outcome |
| :--- | :---: | :---: | :---: | :--- |
| **Dummy Stratified** | 0.0110 | 0.4979 | Benchmark | Reference baseline |
| **Logistic Regression** | **0.0134** | **0.5368** | Highest Validation PR-AUC | **VALIDATION-BEST MODEL** |
| **LightGBM Classifier** | 0.0123 | 0.5229 | Hardcoded in `trainer.py` | Originally persisted artifact |

#### Root Cause:
`backend/app/ml/models/trainer.py` hardcoded `best_name = "lightgbm"` when exporting `selected_model.joblib`. Strictly following the pre-declared validation PR-AUC criterion, **Logistic Regression should have been selected**.

### 4.2 Governance Rule: Test Set Snooping Prohibited

On the untouched test partition ($N = 54,221$), LightGBM happened to achieve a test PR-AUC of `0.0207` compared to Logistic Regression's `0.0152`.
- **Governance Mandate:** A model must **never** be retroactively selected based on test partition performance. Test data must remain an unbiased, one-time out-of-sample evaluation.
- Selecting LightGBM because it performed better on the test set would violate core leakage controls.

### 4.3 Dual-Track Registry Reconciliation

To maintain absolute provenance without breaking existing pipelines:
1. **Preserve Persisted Artifacts:** `selected_model.joblib` (LightGBM) remains on disk to preserve Phase 2.3 pipeline continuity. `baseline_logistic.joblib` remains preserved in the same directory.
2. **Reconciled Registry Metadata:** `data/artifacts/models/cancellation_upfront/selected_model_metadata.json` has been updated with explicit selection metadata:
   - `selection_criterion`: `"validation_pr_auc"`
   - `selection_partition`: `"validation"`
   - `validation_best_model`: `"logistic_regression"`
   - `original_persisted_model`: `"lightgbm"`
   - `audit_status`: `"RECONCILED"`
   - `operational_approval`: `false`
3. **Operational Conclusion:** Both models hover near the random base rate prior (1.11%). Neither model is approved for production deployment.

---

## 5. Task C2 — Cohort Reconciliation & Denominator Accounting

### 5.1 Waterfall Reconciliation of Test Populations

A discrepancy was identified between the 54,221 test orders reported in Task C1 and the 54,150 test orders evaluated in Task C2.

```
                           TEST PARTITION WATERFALL
                                  (54,221)
                                      |
              +-----------------------+-----------------------+
              |                                               |
     Excluded Orders (71)                       Eligible Test Cohort (54,150)
              |                                               |
     +--------+--------+                             +--------+--------+
     |                 |                             |                 |
Cancelled Prior   Delivered Prior               Active Non-Cancels  Post-Landmark
  to Landmark       to Landmark                    (Fulfilled)        Cancels
     (57)              (14)                          (53,604)           (546)
```

#### Detailed Accounting:
1. **Original Test Partition Size ($N_{\text{raw}}$):** **54,221 orders** (`2021-02-05` to `2021-02-06`).
2. **Excluded Orders ($N_{\text{excluded}}$):** Exactly **71 orders** were excluded:
   - **57 orders:** Cancelled prior to or at the 5-minute operational landmark ($t \le t_{\text{allot}} + 5\text{ min}$).
   - **14 orders:** Delivered prior to or at the 5-minute operational landmark ($t \le t_{\text{allot}} + 5\text{ min}$).
   - *Exclusion Rationale:* An order that has already terminated (cancelled or delivered) before the 5-minute milestone cannot physically be in the active pool at the landmark checkpoint.
3. **Landmark-Eligible Test Population ($N_{\text{eligible}}$):** $54,221 - 71 =$ **54,150 orders**.
4. **Scored Population ($N_{\text{scored}}$):** **54,150 orders** (100% of eligible orders scored).

### 5.2 Scored Population Label Distribution & Denominator

In the scored test population of 54,150 orders:
- **Positive Labels ($Y = 1$):** **546 orders** (orders active at milestone that eventually cancelled).
- **Negative Labels ($Y = 0$):** **53,604 orders** (orders active at milestone that were fulfilled).
- **Check:** $546 + 53,604 = 54,150$.

### 5.3 Exact Confusion Matrix Denominator Verification

Evaluated on the locked model at the validation-optimized threshold $\tau = 0.87$:

$$\text{Scored Population} = \text{TP} + \text{FP} + \text{FN} + \text{TN}$$
$$54,150 = 63 + 196 + 483 + 53,408$$

- **Positive Column Sum ($\text{TP} + \text{FN}$):** $63 + 483 = \mathbf{546}$ (Exact positive count)
- **Negative Column Sum ($\text{TN} + \text{FP}$):** $53,408 + 196 = \mathbf{53,604}$ (Exact negative count)
- **Total Denominator:** Strictly **54,150**. No metric blends the raw 54,221 cohort with the landmark-eligible cohort.

### 5.4 Recomputed Evaluation Metrics (Eligible Cohort)

| Metric | Formula | Recomputed Value | Notes |
| :--- | :--- | :---: | :--- |
| **Test Prevalence** | $\frac{\text{Positives}}{N_{\text{eligible}}}$ | **1.008%** (1.01%) | $546 / 54,150$ |
| **Precision** | $\frac{\text{TP}}{\text{TP} + \text{FP}}$ | **24.32%** | $63 / (63 + 196) = 63 / 259$ |
| **Recall (Sensitivity)** | $\frac{\text{TP}}{\text{TP} + \text{FN}}$ | **11.54%** | $63 / (63 + 483) = 63 / 546$ |
| **Alerts per 1,000 Orders** | $\frac{\text{TP} + \text{FP}}{N_{\text{eligible}}} \times 1,000$ | **4.783** | $259 / 54,150 \times 1,000$ |
| **Lift over Prevalence** | $\frac{\text{Precision}}{\text{Prevalence}}$ | **24.12x** (24.08x) | $0.2432 / 0.01008$ |
| **Specificity** | $\frac{\text{TN}}{\text{TN} + \text{FP}}$ | **99.63%** | $53,408 / 53,604$ |
| **False Positive Rate** | $\frac{\text{FP}}{\text{TN} + \text{FP}}$ | **0.37%** | $196 / 53,604$ |

---

## 6. Task C2 — Operational Language & Recall Caveats

### 6.1 Target Semantics: Canonical Terminology

The target variable for Task C2 is formally defined as:
> **"Eventual post-landmark cancellation within the observed lifecycle."**

#### Required Disclaimers:
1. **NOT a Fixed-Horizon Prediction:** The model does **NOT** predict cancellation within a bounded time window (e.g. "will cancel in the next 10 minutes"). It predicts terminal failure conditional on having survived to the 5-minute landmark.
2. **NOT an Imminent Cancellation Claim:** Flagged orders may cancel 15, 30, or 45 minutes later (e.g. at the doorstep or after repeated reassignments). Describing flagged orders as "imminent cancellations" is scientifically inaccurate.

### 6.2 The Low-Recall Reality: 88.46% of Cancellations Missed

While Phase 2.4 highlighted the 24.32% precision and 24x lift at $\tau = 0.87$, the operational trade-off must be stated transparently:
- **Detected Cancellations (Recall):** **11.54%** (63 out of 546 cancellations).
- **Undetected Cancellations (Miss Rate):** **88.46%** (483 out of 546 cancellations proceed to cancellation without triggering an alert).
- **False Alarm Ratio:** Even at 24.32% precision, **75.68% of flagged orders (196 out of 259) are successfully delivered**.

```
                TASK C2 TEST PREDICTIONS AT THRESHOLD 0.87
                         (Total Test Orders = 54,150)
  
  [True Cancellations: 546]            [Delivered Orders: 53,604]
  +-----------------------+            +---------------------------------+
  | [TP: 63]  | [FN: 483] |            | [FP: 196] |      [TN: 53,408]   |
  |  (11.5%)  |  (88.5%)  |            |  (0.37%)  |        (99.63%)     |
  +-----------------------+            +---------------------------------+
       ^                                    ^
       +----------- FLAGGED ORDERS ---------+
                    (Total = 259)
                Precision = 63 / 259 = 24.32%
```

### 6.3 Operational Action Policy: Non-Intrusive Monitoring

Because 3 out of 4 flagged orders are delivered, any intervention triggered at $\tau = 0.87$ must be **strictly non-intrusive**:
- **Permitted:** Routing order to a secondary telemetry monitor, checking kitchen KDS status, or giving subtle routing priority to nearby couriers.
- **Prohibited:** Proactively offering cancellation refunds to customers, calling customers to suggest cancellation, or cancelling orders automatically.

---

## 7. Status of Issues: Resolved vs. Unresolved

| Issue ID | Description | Phase 2.4 State | Phase 2.4.1 Audit Resolution | Current Status |
| :---: | :--- | :--- | :--- | :---: |
| **ISSUE-01** | Task A Prediction Intervals | Claimed $[P_{25}, P_{75}]$ uncertainty bands. | Verified model is a point predictor. Marked true intervals as Future Work (Quantile LGBM / Conformal). | **RESOLVED** |
| **ISSUE-02** | Task A ETA + 15m Intervention Rule | Proposed as an operational rule. | Formally classified as an unvalidated policy requiring simulation before deployment. | **RESOLVED** |
| **ISSUE-03** | Task B Standalone Alerting | Evaluated at $\tau = 0.47$ (F1 optimal). | Verified 581 alerts/1,000 orders. Model explicitly marked NOT APPROVED for standalone alerting. | **RESOLVED** |
| **ISSUE-04** | Task B Downstream Batching | Claimed operational utility in dispatch. | Reclassified as an untested hypothesis requiring comparative benchmarking. | **RESOLVED** |
| **ISSUE-05** | Task C1 Model Selection Discrepancy | Persisted LightGBM despite Logistic having higher val PR-AUC. | Reconciled: Logistic Regression documented as validation-best. Dual-track registry recorded; test selection rejected. | **RESOLVED** |
| **ISSUE-06** | Task C2 Cohort Accounting (71 Orders) | 54,221 vs 54,150 test rows unexplained. | Waterfall audit: 57 cancelled and 14 delivered prior to milestone. Denominator verified as strictly 54,150. | **RESOLVED** |
| **ISSUE-07** | Task C2 Imminent Cancellation Claims | Implied flagged orders are imminent cancellations. | Replaced with "eventual post-landmark cancellation". Emphasized 11.54% recall and 75.68% false-alarm share. | **RESOLVED** |
| **ISSUE-08** | Quantile Loss Training | LGBM trained on default MSE. | Not trained in Phase 2.4; deferred to future quantile regression / conformal iteration. | **OPEN (Future Work)** |
| **ISSUE-09** | KDS & Kitchen Telemetry Integration | Missing kitchen prep signals causing 27m tail error. | Requires Phase 3+ ingestion of live KDS timestamps. | **OPEN (Future Work)** |

---

## 8. Verification Artifacts & Test Suite Evidence

### 8.1 Reconciled Registry & Diagnostic Metadata

1. `data/artifacts/models/cancellation_upfront/selected_model_metadata.json`
   - Reconciled with `selection_criterion: "validation_pr_auc"`, `selection_partition: "validation"`, and `validation_best_model: "logistic_regression"`.
2. `data/artifacts/models/delivery_duration/selected_model_metadata.json`
   - Reconciled with `conditional_quantiles_supported: false` and `prediction_intervals: "FUTURE_WORK"`.
3. `data/artifacts/models/allocation_delay/selected_model_metadata.json`
   - Reconciled with `approved_for_standalone_alerts: false`.
4. `data/artifacts/models/cancellation_landmark/selected_model_metadata.json`
   - Reconciled with canonical target semantics and detection recall caveats.
5. `data/artifacts/diagnostics/task_c_cancellation_diagnostics.json`
   - Enriched with full `cohort_reconciliation` breakdown and `operational_language_audit`.

### 8.2 Automated Regression Test Suite

Added class `TestPhase241ReconciliationAndClaimsAudit` to `backend/tests/test_ml_diagnostics.py`:
- `test_task_a_model_is_point_predictor_and_intervals_marked_future_work`
- `test_task_b_not_approved_for_standalone_alerts`
- `test_task_c1_model_selection_metadata_and_reconciliation`
- `test_task_c2_cohort_reconciliation_and_exact_denominators`
- `test_task_c2_operational_language_and_recall_caveat`

### 8.3 Complete Test Execution Results

```powershell
pytest backend/tests/ -q
# 62 passed, 1 warning in 13.67s (100%)
```

All 62 tests across the backend test suite pass with zero failures:
- **Phase 2.4 & 2.4.1 Diagnostics:** 17 passed
- **Phase 2.3 Baseline Models:** 9 passed
- **Phase 2.2 Preprocessing:** 11 passed
- **Phase 1 Infrastructure & APIs:** 25 passed
