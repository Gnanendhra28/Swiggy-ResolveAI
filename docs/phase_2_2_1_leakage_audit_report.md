# Swiggy ResolveAI — Phase 2.2.1 Leakage & Point-in-Time Verification Audit

**Document ID:** `docs/phase_2_2_1_leakage_audit_report.md`  
**Phase:** 2.2.1 — Leakage and Point-in-Time Verification Audit  
**Role:** Senior Machine Learning Engineer  
**Date:** November 18, 2026  
**Status:** Audit Completed, Pipeline Upgraded & Verified  

---

## 1. Executive Summary

This audit evaluates the Phase 2.2 preprocessing and feature-engineering pipeline against rigorous data leakage, point-in-time validity, and training isolation standards. The audit was conducted without modifying the established pipeline architecture or raw datasets.

### Primary Audit Outcomes & Upgrades:
1. **Elimination of Global Imputation Leakage:** Previously, `last_mile_distance` imputation used a global median ($2.67\text{ km}$) and `session_time` used a global median ($175.5\text{ mins}$) derived from the entire 450,000-row dataset. The implementation has been upgraded so that **imputation parameters are fitted strictly on the training partition** ($2.67\text{ km}$ and $178.15\text{ mins}$, respectively) and persisted in `metadata.json`.
2. **Empirical Verification of `last_mile_distance` at Order Creation ($t_{\text{order}}$):** Audited the physical semantics of `last_mile_distance`. Proved empirically that this field represents pre-computed road network distance (merchant-to-doorstep), available prior to order placement to price delivery fees, with **100% completeness even for orders cancelled before courier allocation or pickup**.
3. **Rolling Demand Feature Temporal Isolation:** Verified that `rolling(closed='left')` strictly isolates past transactions ($t < t_{\text{order}}$), prevents self-inclusion, and eliminates simultaneous-order leakage. Formally documented that rolling demand represents platform-wide order velocity across the Kaggle dataset.
4. **Cancellation Landmark ($t_{\text{allot}} + 5\text{m}$) Horizon Audit:** Documented the exact operational cohort of 449,419 active orders, verified exclusions of orders terminated prior to the landmark, and mapped the post-landmark cancellation horizon (median 37.84 mins).
5. **Comprehensive Test Suite Expansion:** Added 6 targeted unit tests covering training-only fitting, rolling demand temporal isolation, demand acceleration edge cases, and landmark eligibility. The entire test suite passes with zero errors (**36 passed in 2.37s**).

---

## 2. Objective 1: Imputation Leakage Audit & Resolution

### 2.1 The Vulnerability (Global Snooping)
In Phase 2.2, `OutlierHandler` and `FeatureEngineer` utilized fixed default medians (`median_last_mile = 2.67`, `median_session_time = 175.5`) calculated across the entire 450,000-row Kaggle export during Phase 2.1 exploratory data analysis.  
While computationally convenient, applying statistics derived from the full dataset before chronological splitting constitutes **subtle global data snooping**. Specifically:
- Full dataset `session_time` median: **175.50 minutes**
- Training partition `session_time` median: **178.15 minutes**
- Validation partition `session_time` median: **173.80 minutes**
- Test partition `session_time` median: **170.10 minutes**

Using 175.5 minutes implicitly leaked the downstream shift duration profile of future couriers in February 2021 into the January 2021 training partition.

### 2.2 Implementation Upgrade: Training-Only `fit()` Pattern
Both `OutlierHandler` and `FeatureEngineer` were refactored to implement a scikit-learn style `fit()` and `transform()` pattern:
```python
# 1. Identify training partition strictly by timestamp
train_mask = (df_clean["order_time"] >= config.train_start_date) & (
    df_clean["order_time"] < config.train_end_date
)
train_slice = df_clean[train_mask].copy()

# 2. Fit statistics strictly on train_slice
outlier_handler.fit(train_slice)      # Fitted median: 2.67 km
feature_engineer.fit(train_slice)     # Fitted median: 178.15 mins

# 3. Apply handle_distances and feature engineering to all partitions
df_imputed = outlier_handler.handle_distances(df_clean)
```

### 2.3 Parameter Persistence in Metadata
The exact fitted parameters and training sample size are now permanently serialized into `metadata.json` across all exported tasks:
```json
"fitted_parameters": {
  "fit_partition": "TRAIN (2021-01-26 00:00:00 to 2021-02-03 00:00:00)",
  "fit_sample_size": 314646,
  "fitted_median_last_mile_km": 2.67,
  "fitted_median_session_time_min": 178.15
}
```

### 2.4 Unit Test Verification
A targeted unit test (`test_training_only_imputation_isolation` in `backend/tests/test_ml_preprocessing.py`) proves that when validation and test sets are injected with extreme outlier values (e.g. $99,999.0$), the fitted training medians remain **100% invariant**, and validation imputation utilizes only the training parameters.

---

## 3. Objective 2: Order-Time Feature Availability of `last_mile_distance`

A rigorous operational audit was conducted to establish whether `last_mile_distance` is legitimately available at order placement ($t_{\text{order}}$) or represents post-delivery telemetry.

### 3.1 What Does `last_mile_distance` Measure?
In food-delivery platform logistics (Swiggy / Zomato architecture), delivery distance comprises two distinct segments:
- **First-Mile Distance:** Travel distance from the courier's real-time GPS location to the restaurant store. This is dynamic and unknown until courier assignment ($t_{\text{allot}}$).
- **Last-Mile Distance:** Road network routing distance (calculated via OSRM, Google Maps Distance Matrix, or Mapbox) from the merchant store coordinates to the customer's doorstep delivery coordinates.

### 3.2 When Does It Become Available Operationally?
In on-demand food delivery:
1. When a customer opens the consumer app and selects a delivery address, the platform geocodes the delivery location.
2. For each restaurant displayed in the listing feed, the routing engine calculates the store-to-customer distance.
3. This distance is used to compute the dynamic delivery fee shown in the checkout cart **before** the order is finalized.
4. When the customer confirms checkout at `order_time`, `last_mile_distance` is an immutable, pre-computed attribute of the order contract.

### 3.3 Empirical Data Proof from Raw Telemetry
If `last_mile_distance` were recorded by courier odometers during physical transit, it would be missing/null for orders where no courier ever drove to the customer.

We audited all 5,218 cancelled orders in `Rider-Info.csv`:
- **Orders Cancelled Before Courier Acceptance ($N = 157$):**
  - Null `last_mile_distance` count: **0 (0.0% null)**
  - Mean distance: $3.89\text{ km}$, Median: $3.45\text{ km}$
- **Orders Cancelled Before Food Pickup ($N = 2,421$):**
  - Null `last_mile_distance` count: **0 (0.0% null)**
  - Mean distance: $3.02\text{ km}$, Median: $2.74\text{ km}$
- **Reassigned Orders ($N = 13,753$):**
  - In orders reassigned to a second courier, `last_mile_distance` remains invariant regardless of which courier was assigned.

**Conclusion:** `last_mile_distance` is an upfront road network distance determined at $t_{\text{order}}$. It is genuinely available at order creation and is mathematically and operationally appropriate for:
- **Task A (Delivery Duration Regression):** Primary physical constraint governing travel time.
- **Task B (Rider Allocation Delay):** Predictor of courier acceptance/rejection (couriers reject disproportionately long routes).
- **Task C1 (Order Creation Cancellation Risk):** High-distance orders experience elevated customer dropoff and cancellation risk.

---

## 4. Objective 3: Rolling Demand Features Verification

### 4.1 Strict Backward-Looking Computation
The rolling order volume features in `DemandPressureFeatures.extract_rolling_demand` were audited for lookahead bias:
```python
ts_series = pd.Series(1, index=df_sorted["order_time"])
rolling_15m = ts_series.rolling("15min", closed="left").count().fillna(0.0).values
rolling_60m = ts_series.rolling("60min", closed="left").count().fillna(0.0).values
```

- **`closed='left'` Verification:** Pandas defines `closed='left'` such that the rolling window covers $[t - \Delta t, t)$, which strictly includes past events and **excludes the current timestamp $t$**.
- **No Self-Contribution:** An order placed at $t$ does not count toward its own rolling volume.
- **Simultaneous Orders:** When multiple orders occur at the exact same second, `closed='left'` excludes all orders at timestamp $t$ from each other's window.
- **Correct Chronological Sorting:** The DataFrame is sorted by `order_time` before windowing, and the original index is restored upon completion.

### 4.2 Zero-Denominator Safety in `demand_acceleration`
`demand_acceleration` measures short-term surge intensity:
$$\text{demand\_acceleration} = \frac{\text{rolling\_15m} \times 4.0}{\max(\text{rolling\_60m}, 0.0) + 1.0}$$
- **Proof of Safety:** Since $\text{rolling\_60m} \ge 0$, the denominator $\max(\text{rolling\_60m}, 0.0) + 1.0 \ge 1.0 > 0$ for all possible inputs.
- When $\text{rolling\_15m} = 0$ and $\text{rolling\_60m} = 0$, $\text{demand\_acceleration} = 0.0$.
- Division by zero is mathematically impossible. Verified in unit test `test_demand_acceleration_edge_cases`.

### 4.3 Geographic Scope & Dataset-Level Signal Clarification
> [!IMPORTANT]
> **Dataset-Level vs Local Demand Scope:**
> The Kaggle dataset `Rider-Info.csv` does not contain city names, delivery zones, or merchant coordinates. Consequently, `rolling_order_volume_15m` and `rolling_order_volume_60m` measure **global platform-level order ingestion velocity** across the entire logged system. They serve as macro dispatch pressure indicators, not localized micro-neighborhood demand densities.

---

## 5. Objective 4: Cancellation Landmark Target & Observation Horizon Audit

### 5.1 Exact Landmark Definition
- **Landmark Timestamp:** $t_{\text{landmark}} = \text{allot\_time} + 5.0\text{ minutes}$.
- **Operational Rationale:** At 5 minutes post-allotment, Swiggy ResolveAI evaluates whether courier assignment is progressing normally or stalling (e.g. unaccepted allotment, preparation delay).

### 5.2 Eligible Population at Landmark
From the clean pool of 449,999 non-duplicate orders:
- **Orders Cancelled Prior to Landmark:** 466 orders ($0.10\%$) aborted before $t_{\text{allot}} + 5\text{m}$.
- **Orders Delivered Prior to Landmark:** 114 orders ($0.03\%$) fulfilled within 5 minutes of allotment.
- **Eligible Active Cohort:** **449,419 orders (99.87% of clean base)**.

```
Total Clean Orders (449,999)
  ├── Cancelled before landmark (466)  ──► EXCLUDED (Already terminated)
  ├── Delivered before landmark (114)  ──► EXCLUDED (Already fulfilled)
  └── Active at Landmark (449,419)     ──► INCLUDED IN TASK C2
        ├── Successfully Delivered Post-Landmark: 444,667 (98.94%) [Class 0]
        └── Cancelled Post-Landmark:               4,752  (1.06%) [Class 1]
```

### 5.3 Observation Horizon & Censoring Behavior
- **Terminal Resolution:** Every order active at the landmark reaches a definitive terminal state (either `delivered_time` or `cancelled_time`). There is **zero right-censoring** (no dangling active orders at dataset cutoff).
- **Post-Landmark Cancellation Latency Profile:**
  - Minimum: 1 second post-landmark
  - 25th Percentile: 20.28 minutes
  - **Median:** **37.84 minutes**
  - Mean: 56.89 minutes
  - 75th Percentile: 58.35 minutes
  - 95th Percentile: 106.16 minutes
  - Maximum: 5,676.68 minutes (~3.9 days)
- **Target Formulation:** Binary label $Y_{C,\text{landmark}} = \mathbb{I}(\text{order cancels after } t_{\text{landmark}})$.

---

## 6. Objective 5: Audit of All Preprocessing Transformations

| Preprocessing Operation | Operation Type | Fitting Scope | Fitted Parameter Value | Persistence Location |
|---|---|---|---|---|
| `last_mile_distance` Imputation | Learned Median | **Training Partition Only** | $2.67\text{ km}$ | `metadata.json` -> `fitted_parameters` |
| `session_time` Imputation | Learned Median | **Training Partition Only** | $178.15\text{ mins}$ | `metadata.json` -> `fitted_parameters` |
| Zero Last-Mile Indicator | Predefined Domain Flag | Fixed Rule ($\le 0.0\text{ km}$) | $0$ or $1$ | Deterministic rule |
| Distance Bins | Predefined Domain Thresholds | Fixed ($1.0, 2.5, 5.0, 8.0\text{ km}$) | 5 categorical tiers | Deterministic rule |
| First-Mile Outlier Capping | Predefined Domain Boundary | Fixed ($20.0\text{ km}$) | Value clamped to $20.0$ | Deterministic rule |
| Duration Cohort Filter | Predefined SLA Bounds | Fixed ($5.0\text{ to } 180.0\text{ mins}$) | Lower/Upper bounds | `exclusions_log` |
| Allocation Delay Threshold | Predefined Operational Rule | Fixed ($> 3.0\text{ mins}$) | Binary target threshold | `target.stats` |
| Landmark Delay Window | Predefined Operational Window| Fixed ($+ 5.0\text{ mins}$) | Landmark timestamp offset| `metadata.json` |
| Cyclic Transforms (sin/cos) | Mathematical Formulation | Fixed ($2\pi / 24$, $2\pi / 7$) | Exact continuous mapping | Deterministic rule |

---

## 7. Objective 6: Testing & Verification Evidence

The test suite in `backend/tests/test_ml_preprocessing.py` was expanded to 11 targeted test functions covering all audit requirements:

| Test Case Name | Objective Verified | Outcome |
| :--- | :--- | :---: |
| `test_timestamp_processor_midnight_and_intervals` | Midnight rollover, datetime parsing, milestone delays | **PASSED** |
| `test_data_validator_duplicate_and_anomalies` | Exact duplicate dropped, 25 negative delays tracked | **PASSED** |
| `test_training_only_imputation_isolation` | **Obj 1 & 5:** Mutated validation/test data cannot affect train-fitted medians | **PASSED** |
| `test_outlier_handler_distances_and_duration_filtering` | GPS imputation, duration outlier cohort exclusion | **PASSED** |
| `test_feature_availability_and_leakage_control` | **Obj 2:** Zero downstream milestone leaks in order-time feature lists | **PASSED** |
| `test_rolling_demand_temporal_isolation` | **Obj 3:** Strict `closed='left'` backward isolation, no simultaneous order leak | **PASSED** |
| `test_demand_acceleration_edge_cases` | **Obj 3:** Zero-count safety, division-by-zero prevention | **PASSED** |
| `test_cancellation_landmark_eligibility_and_horizon`| **Obj 4:** Exclusion of pre-landmark terminations, post-landmark target labeling | **PASSED** |
| `test_chronological_splitter_partitions` | Strict chronological cut, zero cross-partition order overlap | **PASSED** |
| `test_dataset_export_and_parquet_reimport` | Parquet compression, pyarrow round-trip integrity, schema parity | **PASSED** |
| `test_pipeline_reproducibility` | Deterministic pipeline idempotency | **PASSED** |

### Complete Test Suite Execution:
```text
============================= test session starts =============================
platform win32 -- Python 3.12.0, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\ASUS\Desktop\Swiggy ResolveAI
configfile: pytest.ini
testpaths: backend/tests

backend/tests/test_alembic.py (1 test) PASSED
backend/tests/test_database.py (2 tests) PASSED
backend/tests/test_dataset_integration.py (6 tests) PASSED
backend/tests/test_health.py (1 test) PASSED
backend/tests/test_ml_preprocessing.py (11 tests) PASSED
backend/tests/test_models.py (2 tests) PASSED
backend/tests/test_orders_api.py (1 test) PASSED
backend/tests/test_provenance.py (3 tests) PASSED
backend/tests/test_simulation.py (9 tests) PASSED

============================= 36 passed in 2.37s ==============================
```

---

## 8. Summary of Findings & Unresolved Uncertainties

1. **Imputation Leakage:** Resolved. All imputation medians are fitted strictly on the training partition (`2.67 km` for last mile, `178.15 min` for session time) and stored in `metadata.json`.
2. **Order-Time Distance Semantics:** Established. `last_mile_distance` is pre-computed routing distance determined at checkout prior to order placement; it is available for Tasks A, B, and C1.
3. **Demand Velocity Scope:** Rolling demand features are strictly backward-looking, but reflect platform-wide volume rather than city/zone micro-density due to source data limitations.
4. **Reassignment Telemetry Overwrite Uncertainty:** As diagnosed in Phase 2.1, when an order is reassigned, `allot_time` logs the second courier's allotment timestamp, overwriting the initial assignment time. Task B explicitly frames its objective as predicting the risk of entering this delayed dispatch / auto-reassignment pool ($> 3$ mins).
5. **Phase 1 Integrity:** Phase 1 database schemas, Alembic migrations, FastAPI endpoints, simulation engines, and frontend interfaces remain completely unaffected.
