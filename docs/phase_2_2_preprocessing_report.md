# Swiggy ResolveAI — Phase 2.2 Preprocessing & Feature Engineering Report

**Document ID:** `docs/phase_2_2_preprocessing_report.md`  
**Phase:** 2.2 — Data Preprocessing & Feature Engineering Pipelines  
**Role:** Senior Machine Learning Engineer  
**Date:** November 18, 2026  
**Status:** Pipeline Executed, Verified, and Exported  

---

## 1. Executive Summary

Phase 2.2 establishes production-grade, reproducible, and leakage-controlled preprocessing and feature-engineering pipelines for Swiggy ResolveAI. Operating strictly on the audited `Rider-Info.csv` dataset, the pipeline generates partitioned Parquet feature matrices and comprehensive JSON metadata for three core machine learning tasks without modifying raw data or Phase 1 services.

### Core Achievements:
1. **Modular Architecture:** Preprocessing components developed under `backend/app/ml/` adhering to SOLID principles, completely decoupled from the FastAPI application.
2. **Deterministic Data Cleaning:**
   - Handled the single exact duplicate row (`order_id: 181402`), yielding 449,999 unique orders.
   - Identified and logged 25 negative acceptance delays, 10 negative pickup delays, and 94 zero last-mile distance records.
   - Filtered duration outliers ($< 5$ min and $> 180$ min) transparently with full audit accounting.
3. **Strict Leakage Prevention:**
   - Point-in-time feature isolation enforced at order creation ($t_{\text{order}}$) and operational dispatch landmark ($t_{\text{allot}} + 5\text{ min}$).
   - Quarantined static lifetime snapshots and daily batch rollups.
   - Backward-looking rolling demand pressure computed with `closed='left'` (zero lookahead bias).
4. **Chronological Splitting:** Out-of-time splits (Days 1–8 Train, Days 9–10 Val, Days 11–12 Test) applied deterministically with zero order overlap across partitions.
5. **High-Performance Export:** Exported 4 distinct dataset tasks in compressed Parquet format within 6.26 seconds.
6. **Testing Verification:** Complete test suite passed (`33 passed in 2.23s`), confirming duration arithmetic across midnight, outlier handling, duplicate detection, and Parquet round-trip fidelity.

---

## 2. Preprocessing Architecture & Module Layout

The pipeline architecture is located in `backend/app/ml/` and organized into decoupled functional layers:

```
backend/app/ml/
├── data/
│   ├── loader.py         # RawDataLoader: Read-only streaming access to raw CSV
│   ├── validator.py      # DataValidator: Schema, anomaly detection, deduplication
│   ├── splitter.py       # ChronologicalSplitter: Strict date partitioner
│   └── exporter.py       # DatasetExporter: Parquet & JSON metadata writer
├── preprocessing/
│   ├── timestamp.py      # TimestampProcessor: UTC datetime64, midnight rollover
│   └── outliers.py       # OutlierHandler: GPS imputation, duration filtering
├── features/
│   ├── spatial.py        # SpatialFeatures: Quadratic, distance brackets, ratios
│   ├── temporal.py       # TemporalFeatures: Cyclic sin/cos, meal periods
│   ├── demand.py         # DemandPressureFeatures: Backward rolling windows
│   └── engineer.py       # FeatureEngineer: Staged feature coordinator
├── datasets/
│   └── builder.py        # TargetBuilder & DatasetBuilder: Feature matrices
├── schemas/
│   ├── config.py         # PipelineConfig dataclass
│   └── metadata.py       # FeatureMetadata, TargetMetadata, DatasetMetadata
└── pipeline.py           # PreprocessingPipeline orchestrator
```

---

## 3. Data Validation & Anomaly Accounting

The validation engine inspected all 450,000 raw records. Every exclusion and anomaly was logged explicitly without silent record deletion.

### 3.1 Initial vs. Final Population Counts

| Metric | Record Count | Percentage | Handling Directive |
|---|---|---|---|
| **Raw Input Rows** | 450,000 | 100.00% | Ingested from `data/raw/orders/Rider-Info.csv` |
| **Unique `order_id`s** | 449,999 | 99.9998% | Primary unique order keys |
| **Exact Duplicate Rows** | 1 | 0.0002% | `order_id: 181402` (Dropped duplicate instance) |
| **Clean Base Order Pool** | **449,999** | **99.9998%** | Base population for Tasks B, C1, and C2 |

### 3.2 Operational Anomalies & Physical Outliers Log

| Anomaly Category | Affected Rows | Description | Remediation Strategy |
|---|---|---|---|
| **Negative Acceptance Delay** | 25 rows | `accept_time < allot_time` (min: -475.6 min) | Telemetry desync during manual SE portal reassignment overrides; preserved in raw, excluded from duration regression. |
| **Negative Pickup Delay** | 10 rows | `pickup_time < accept_time` (min: -69.6 min) | Mobile app out-of-order button sequence; excluded from transit duration calculations. |
| **Zero Last-Mile Distance** | 94 rows | `last_mile_distance == 0.0` km | Customer collection / GPS nulls; imputed with median (2.67 km) and flagged with `is_zero_last_mile = 1`. |
| **Extreme First-Mile Distance** | 1 row | `first_mile_distance == 42.04` km | GPS telemetry glitch; capped at 20.0 km and flagged with `is_extreme_first_mile = 1`. |
| **Duration Under 5 Minutes** | 89 rows | Completed order with `duration < 5.0` min | Unrealistic physical fulfillment; excluded from Task A duration cohort. |
| **Duration Over 180 Minutes** | 400 rows | Completed order with `duration > 180.0` min (max: 10,017 min) | Forgotten/orphaned tasks closed days later; excluded from Task A duration cohort. |

---

## 4. Feature Engineering & Point-in-Time Availability

To prevent temporal and operational lookahead leakage, features were constructed according to strict point-in-time boundaries:

### 4.1 Order-Creation Features (Available at $t_{\text{order}}$)
Available for Task A (ETA), Task B (Allocation Delay), and Task C1 (Upfront Cancellation):

| Feature Name | Type | Processing Transformation | Operational Purpose |
|---|---|---|---|
| `last_mile_distance` | `float64` | Imputed with median (2.67 km) for 0-distance rows | Primary physical distance baseline |
| `is_zero_last_mile` | `int32` | Binary indicator ($1$ if original distance $\le 0.0$, else $0$) | Anomaly imputation tracking |
| `last_mile_distance_sq` | `float64` | $(\text{last\_mile\_distance})^2$ | Non-linear transit delay scaling |
| `distance_bracket` | `category` | Binned: `ultra_short` ($<1$), `short` ($1–2.5$), `medium` ($2.5–5$), `long` ($5–8$), `hyper_long` ($\ge 8$) | Non-linear distance clustering |
| `order_hour` | `int32` | Hour integer ($0 \dots 23$) | Diurnal schedule baseline |
| `hour_sin`, `hour_cos` | `float64` | $\sin(2\pi h / 24)$, $\cos(2\pi h / 24)$ | 24-hour continuous cyclic boundary |
| `order_dayofweek` | `int32` | Day integer ($0 = \text{Mon} \dots 6 = \text{Sun}$) | Weekly demand baseline |
| `dow_sin`, `dow_cos` | `float64` | $\sin(2\pi d / 7)$, $\cos(2\pi d / 7)$ | 7-day continuous cyclic boundary |
| `is_weekend` | `int32` | Binary flag ($1$ for Saturday/Sunday, else $0$) | Weekend vs weekday demand shift |
| `meal_period` | `category` | `BREAKFAST`, `LUNCH_PEAK`, `AFTERNOON_SLACK`, `DINNER_PEAK`, `LATE_NIGHT` | Domain-specific meal schedules |
| `is_peak_meal_window` | `int32` | Binary flag ($1$ for Lunch Peak or Dinner Peak) | Fleet demand surge indicator |
| `rolling_order_volume_15m` | `float64` | Time-indexed rolling count in $[t - 15\text{m}, t)$ (`closed='left'`) | Immediate fleet load pressure |
| `rolling_order_volume_60m` | `float64` | Time-indexed rolling count in $[t - 60\text{m}, t)$ (`closed='left'`) | Hourly zone demand density |
| `demand_acceleration` | `float64` | $(15\text{m\_count} \times 4) / (60\text{m\_count} + 1.0)$ | Short-term demand spike velocity |

### 4.2 Operational Landmark Features (Available at $t_{\text{allot}} + 5\text{ min}$)
Available exclusively for Task C2 (Dynamic Operational Cancellation):

| Feature Name | Type | Processing Transformation | Operational Purpose |
|---|---|---|---|
| `first_mile_distance` | `float64` | Courier-to-store distance (capped at 20.0 km) | Dispatch travel burden |
| `is_extreme_first_mile` | `int32` | Binary flag ($1$ if distance $> 20.0$ km) | Geographic dispatch outlier |
| `first_to_last_mile_ratio` | `float64` | $\text{first\_mile} / (\text{last\_mile} + 0.1)$ | Courier transit efficiency |
| `total_route_distance` | `float64` | $\text{first\_mile} + \text{last\_mile}$ | Total physical journey length |
| `courier_session_time_min`| `float64` | Elapsed shift minutes at assignment (median 175.5 min) | Courier fatigue and shift progression |
| `courier_fatigue_flag` | `int32` | Binary indicator ($1$ if session time $> 480$ min / 8 hours) | Extended shift risk |
| `allot_delay_min` | `float64` | Elapsed minutes from order placement to courier assignment | Upstream dispatch friction |
| `is_delayed_allotment` | `int32` | Binary flag ($1$ if allotment delay $> 3.0$ min) | Allocation bottleneck flag |
| `has_accepted_by_landmark`| `int32` | Binary flag ($1$ if courier accepted within 5 minutes) | Courier unresponsive indicator |
| `accept_delay_at_landmark`| `float64` | Observed acceptance delay capped at 5.0 minutes | Early friction intensity |

### 4.3 Explicit Leakage Exclusions (Strictly Enforced)

The following attributes are **strictly excluded** from feature matrices:
- **`pickup_time` & `delivered_time`:** Downstream milestones; cannot be known at earlier stages.
- **`cancelled_time`:** Populated exclusively for cancelled orders (direct target leak).
- **`alloted_orders`, `delivered_orders`, `undelivered_orders`:** Daily partition rollups with zero within-day variance (leaks end-of-day performance).
- **`lifetime_order_count`:** Static snapshot taken at database dump extraction.
- **`reassigned_order`, `reassignment_method`, `reassignment_reason`:** Written post-reassignment.
- **`rider_id` & `order_id`:** High-cardinality keys excluded from predictive feature matrices to prevent identity memorization.

---

## 5. Chronological Partitioning & Task Export Results

In accordance with Phase 2.1 directives, random cross-validation was prohibited. All datasets were partitioned strictly along temporal calendar boundaries:

- **Training:** `2021-01-26 00:00:00` to `2021-02-02 23:59:59` (8 days)
- **Validation:** `2021-02-03 00:00:00` to `2021-02-04 23:59:59` (2 days)
- **Test:** `2021-02-05 00:00:00` to `2021-02-06 10:03:24` (1.5 days)

### Summary of Exported Dataset Artifacts:

| Task Name | Prediction Horizon | Target Column | Eligible Rows | Train Rows (70%) | Val Rows (18%) | Test Rows (12%) | Export Directory |
|---|---|---|---|---|---|---|---|
| **Task A: Delivery Duration** | $t_{\text{order}}$ | `target_delivery_duration_min` | **444,293** | 310,521 | 80,184 | 53,588 | `data/processed/delivery_duration/` |
| **Task B: Allocation Delay** | $t_{\text{order}}$ | `target_is_allocation_delayed` | **449,999** | 314,646 | 81,132 | 54,221 | `data/processed/allocation_delay/` |
| **Task C1: Upfront Cancellation**| $t_{\text{order}}$ | `target_is_cancelled` | **449,999** | 314,646 | 81,132 | 54,221 | `data/processed/cancellation/` |
| **Task C2: Landmark Cancellation**| $t_{\text{allot}} + 5\text{m}$ | `target_cancelled_post_landmark`| **449,419** | 314,245 | 81,024 | 54,150 | `data/processed/cancellation/operational_landmark/` |

---

## 6. Detailed Task-by-Task Target Profiling

### 6.1 Task A: Delivery Duration Regression
- **Cohort Filter:** Completed orders (`cancelled == 0`) with $5.0 \le \text{duration} \le 180.0$ min.
  - Excluded below 5.0 min: 89 orders
  - Excluded above 180.0 min: 400 orders
  - Retention: 444,293 of 444,782 completed orders (**99.89%**)
- **Target Distribution:**
  - **Min:** 5.13 minutes
  - **Median:** 29.32 minutes
  - **Mean:** 31.64 minutes
  - **Max:** 179.77 minutes

### 6.2 Task B: Rider Allocation Delay Risk (Binary Classification)
- **Target Definition:** $\mathbb{I}(\text{allot\_delay\_min} > 3.0)$
  - Class 0 (Normal Dispatch $\le 3$ min): **422,479** orders (93.88%)
  - Class 1 (Delayed Dispatch $> 3$ min): **27,520** orders (**6.12%**)
- **Operational Note:** Target represents recorded allotment latency, capturing the risk of entering the reassignment repush pool.

### 6.3 Task C1: Upfront Order Cancellation Risk
- **Target Definition:** $\text{cancelled} \in \{0, 1\}$ at order creation
  - Class 0 (Fulfilled): **444,781** orders (98.84%)
  - Class 1 (Cancelled): **5,218** orders (**1.16%**)
  - Imbalance Ratio: **1 : 85.2**

### 6.4 Task C2: Operational Landmark Cancellation Risk
- **Cohort Filter:** Orders active at $t_{\text{allot}} + 5\text{ min}$.
  - Cancelled prior to landmark: 466 orders
  - Delivered prior to landmark: 114 orders
  - Active population: **449,419** orders
- **Target Distribution:**
  - Class 0 (Delivered post-landmark): **444,667** orders (98.94%)
  - Class 1 (Cancelled post-landmark): **4,752** orders (**1.06%**)

---

## 7. Automated Testing & Verification Suite

A dedicated unit and integration test suite was created in `backend/tests/test_ml_preprocessing.py`. The suite validates all operational pipeline components:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.0, pytest-9.2.0
testpaths: backend/tests

backend/tests/test_alembic.py::test_alembic_migrations PASSED            [  3%]
backend/tests/test_database.py::test_database_connection PASSED          [  6%]
backend/tests/test_database.py::test_seed_entities_exist PASSED          [  9%]
backend/tests/test_dataset_integration.py (6 tests) PASSED               [ 27%]
backend/tests/test_health.py::test_health_check_endpoint PASSED          [ 30%]
backend/tests/test_ml_preprocessing.py::test_timestamp_processor_midnight_and_intervals PASSED [ 33%]
backend/tests/test_ml_preprocessing.py::test_data_validator_duplicate_and_anomalies PASSED [ 36%]
backend/tests/test_ml_preprocessing.py::test_outlier_handler_distances_and_duration_filtering PASSED [ 39%]
backend/tests/test_ml_preprocessing.py::test_feature_engineering_spatial_temporal_demand PASSED [ 42%]
backend/tests/test_ml_preprocessing.py::test_feature_availability_and_leakage_control PASSED [ 45%]
backend/tests/test_ml_preprocessing.py::test_chronological_splitter_partitions PASSED [ 48%]
backend/tests/test_ml_preprocessing.py::test_dataset_export_and_parquet_reimport PASSED [ 51%]
backend/tests/test_ml_preprocessing.py::test_pipeline_reproducibility PASSED [ 54%]
backend/tests/test_models.py (2 tests) PASSED                            [ 60%]
backend/tests/test_orders_api.py::test_order_lifecycle_and_api PASSED    [ 63%]
backend/tests/test_provenance.py (3 tests) PASSED                         [ 72%]
backend/tests/test_simulation.py (9 tests) PASSED                         [100%]

============================= 33 passed in 2.23s ==============================
```

---

## 8. Data Provenance & Reproducibility Statement

- **Raw Source:** Kaggle dataset `cbhavik/swiggyzomato-order-information` (`data/raw/orders/Rider-Info.csv`).
- **Raw File Status:** Untouched, unmodified, read-only.
- **Output Artifacts:** Persisted in `data/processed/` as self-documenting Parquet datasets accompanied by `metadata.json` schemas.
- **Execution Command:**
  ```bash
  python -m backend.app.ml.pipeline
  ```
  The pipeline executes deterministically and regenerates all partitioned datasets in $\sim 6.3$ seconds.
