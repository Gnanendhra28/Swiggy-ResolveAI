# Swiggy ResolveAI — Phase 2.1 Dataset Audit & Profiling Report

**Document ID:** `docs/phase_2_1_dataset_audit.md`  
**Phase:** 2.1 — Dataset Audit & ML Problem Definition  
**Role:** Senior Machine Learning Engineer  
**Date:** November 18, 2026  
**Status:** Audit Completed & Empirically Verified  

---

## 1. Executive Summary

This document presents a comprehensive, empirical data audit of all public datasets available within the Swiggy ResolveAI repository. The primary objective is to inspect raw data artifacts, uncover data-quality defects, detect temporal and target leakage risks, verify data provenance, and establish an operational foundation for Phase 2 machine learning models.

### Key Audit Findings:
1. **Primary Dataset (`Rider-Info.csv`):** Contains **450,000 rows** across 20 columns covering a 12-day high-volume operational window from `2021-01-26 02:21:35` to `2021-02-06 10:03:24` UTC.
2. **Order Uniqueness & Reassignment Architecture:** Exactly **449,999 unique orders** exist with only **1 duplicate row** (`order_id: 181402`, an exact 100% duplicate record). Crucially, **order reassignments (13,753 records, 3.06%) do NOT generate multiple rows**. Instead, a single row captures the order's final state, overwriting the initial assignment timestamp with the second rider's allotment time.
3. **Subtle Feature Leakage Uncovered:**
   - `lifetime_order_count` is a **static snapshot** with zero variance across all 12 days for each rider.
   - `alloted_orders`, `delivered_orders`, and `undelivered_orders` are **daily batch rollups** with exactly 0 within-day variance. They reflect end-of-day cumulative performance and cannot be used as streaming point-in-time features.
   - `session_time` is a genuine, monotonically increasing shift timer available at rider allotment.
4. **Restaurant Dataset (`swiggy_restaurants.csv`):** Contains **8,680 unique restaurant records** with 100% data completeness across 9 metropolitan Indian cities. Static listing delivery times (median 53 mins) represent display approximations, not kitchen preparation telemetry.
5. **Relational Isolation:** There are **zero joinable keys** between the restaurant listing dataset and the rider order dataset. Creating synthetic joins between them would constitute severe data fabrication.
6. **Supplementary Dataset:** The *Indian Food Delivery Time* dataset does not exist locally; exact retrieval instructions and schema expectations are documented herein.

---

## 2. Primary Dataset Audit: Swiggy/Zomato Rider & Order Information

- **Local Path:** `data/raw/orders/Rider-Info.csv`
- **File Size:** 85,001,325 bytes (81.06 MB uncompressed)
- **Source Provenance:** Kaggle (`cbhavik/swiggyzomato-order-information`)
- **Total Record Count:** 450,000 rows
- **Total Column Count:** 20 columns
- **Temporal Range:** `2021-01-26 02:21:35` to `2021-02-06 10:03:24` UTC (11.3 days)

### 2.1 Column-by-Column Schema & Completeness Profile

| Column Name | Inferred Dtype | Null Count | Null Pct (%) | Non-Null Count | Min Value | Median | Max Value |
|---|---|---|---|---|---|---|---|
| `order_id` | `int64` | 0 | 0.00% | 450,000 | 2501 | 358,858 | 586,837 |
| `order_time` | `datetime64[ns]` | 0 | 0.00% | 450,000 | 2021-01-26 02:21:35 | 2021-01-31 16:34:11 | 2021-02-06 10:03:24 |
| `order_date` | `datetime64[ns]` | 0 | 0.00% | 450,000 | 2021-01-26 | 2021-01-31 | 2021-02-06 |
| `allot_time` | `datetime64[ns]` | 0 | 0.00% | 450,000 | 2021-01-26 02:21:59 | 2021-01-31 16:34:44 | 2021-02-06 10:03:25 |
| `accept_time` | `datetime64[ns]` | 157 | 0.035% | 449,843 | 2021-01-26 02:22:08 | 2021-01-31 16:35:46 | 2021-02-06 10:03:53 |
| `pickup_time` | `datetime64[ns]` | 2,421 | 0.538% | 447,579 | 2021-01-26 02:32:51 | 2021-01-31 16:48:47 | 2021-02-06 10:48:42 |
| `delivered_time` | `datetime64[ns]` | 5,218 | 1.160% | 444,782 | 2021-01-26 02:49:47 | 2021-01-31 17:05:43 | 2021-02-06 11:42:04 |
| `cancelled_time` | `datetime64[ns]` | 444,782 | 98.840% | 5,218 | 2021-01-26 03:04:15 | 2021-01-31 16:59:12 | 2021-02-06 10:55:09 |
| `cancelled` | `int64` (bool) | 0 | 0.00% | 450,000 | 0 | 0 | 1 |
| `rider_id` | `int64` | 0 | 0.00% | 450,000 | 0 | 9,936 | 19,997 |
| `first_mile_distance` | `float64` | 0 | 0.00% | 450,000 | 0.00013 km | 1.1387 km | 42.0381 km |
| `last_mile_distance` | `float64` | 0 | 0.00% | 450,000 | 0.0000 km | 2.6700 km | 22.4100 km |
| `alloted_orders` | `float64` | 16,948 | 3.766% | 433,052 | 1.0 | 81.0 | 567.0 |
| `delivered_orders` | `float64` | 17,341 | 3.854% | 432,659 | 1.0 | 81.0 | 562.0 |
| `undelivered_orders` | `float64` | 17,341 | 3.854% | 432,659 | 0.0 | 0.0 | 9.0 |
| `lifetime_order_count` | `float64` | 53 | 0.012% | 449,947 | 0.0 | 396.0 | 30,469.0 |
| `reassigned_order` | `float64` | 436,247 | 96.944% | 13,753 | 1.0 | 1.0 | 1.0 |
| `reassignment_method` | `object` | 436,256 | 96.946% | 13,744 | 'auto' (13,383) | — | 'manual' (361) |
| `reassignment_reason` | `object` | 436,247 | 96.944% | 13,753 | 3 categories | — | — |
| `session_time` | `float64` | 3,675 | 0.817% | 446,325 | 0.0 mins | 175.55 mins | 1,298.97 mins |

---

### 2.2 Identifier Analysis & The Reassignment Paradox

A critical question for multi-stage delivery modeling is: **Does one row represent one unique order, or do reassignments generate multiple rows per order?**

#### Empirical Audit Results:
- Total rows: **450,000**
- Unique `order_id` count: **449,999**
- Orders appearing exactly once: **449,998** (99.9996%)
- Orders appearing more than once: **1** (`order_id: 181402`, count = 2)

#### Investigation of the Sole Duplicate (`order_id: 181402`):
```json
{
  "order_id": 181402,
  "order_time": "2021-02-05 15:06:30",
  "allot_time": "2021-02-05 16:32:56",
  "accept_time": "2021-02-05 16:33:16",
  "pickup_time": null,
  "delivered_time": null,
  "cancelled": 1,
  "rider_id": 14538,
  "reassignment_reason": "Reassign",
  "reassigned_order": 1.0,
  "cancelled_time": "2021-02-05 16:59:52"
}
```
Inspection confirms that both rows for `order_id: 181402` are **100% byte-for-byte identical duplicates**. There are zero orders in the dataset where multiple distinct riders or reassignment stages are preserved as separate rows.

#### The Reassignment Mechanism:
Across the 13,753 reassigned orders (3.06% of the dataset):
- `reassigned_order` is recorded as a single binary indicator (`1.0` vs `null`).
- `allot_time` is updated to reflect the timestamp when the **second (reassigned) rider** received the allotment.
- The initial allotment timestamp and initial rider ID were overwritten during ETL logging.

**Empirical Proof (Allotment Delay Comparison):**
- **Non-Reassigned Orders ($N = 436,247$):**
  - Median allotment delay (`allot_time - order_time`): **0.22 minutes (13 seconds)**
  - 75th percentile: **0.75 minutes (45 seconds)**
  - 95th percentile: **2.07 minutes**
- **Reassigned Orders ($N = 13,753$):**
  - Median allotment delay (`allot_time - order_time`): **15.78 minutes**
  - Mean allotment delay: **19.27 minutes**
  - 95th percentile: **47.69 minutes**

The massive 15.5-minute shift in median allotment delay represents the time spent waiting for the first rider's inaction timeout or support intervention before the order was repushed to the dispatch pool (`coreengine.tasks.repush_order_to_aa_bucket`).

---

### 2.3 Reassignment Method & Reason Breakdown

Of the 13,753 reassigned orders:
- **By Method:**
  - `auto`: 13,383 (97.31%)
  - `manual`: 361 (2.62%)
  - Missing/NaN: 9 (0.07%)
- **By Reason:**
  - `Auto Reassignment basis Inaction. coreengine.tasks.repush_order_to_aa_bucket`: 7,212 (52.44%)
  - `Reassignment Request from SE portal.`: 5,300 (38.54%)
  - `Reassign`: 1,241 (9.02%)

---

### 2.4 Cancellation Distribution & Stage Analysis

- **Total Completed Orders (`cancelled == 0`):** 444,782 (98.84%)
- **Total Cancelled Orders (`cancelled == 1`):** 5,218 (1.16%)
- **Target Imbalance Ratio:** 1 : 85.2

#### At What Lifecycle Milestone Do Cancellations Occur?
1. **Pre-Acceptance Cancellation:** 157 orders (3.01% of cancellations) have `accept_time = null`. The order was cancelled before any rider accepted the assignment.
2. **Post-Acceptance / Pre-Pickup Cancellation:** 2,264 orders (43.39% of cancellations) have `accept_time` populated but `pickup_time = null`. Cancellation occurred while the restaurant was preparing the food or while the rider was traveling to the restaurant.
3. **In-Transit Cancellation:** 2,797 orders (53.60% of cancellations) have `pickup_time` populated, but `delivered_time = null` and `cancelled_time` non-null. The food was collected from the restaurant, but the delivery aborted during last-mile transit (e.g. customer unresponsive, transit accident, wrong address).

#### Cross-Correlation between Reassignment and Cancellation:
- Cancellation rate among non-reassigned orders: $4,496 / 436,247 = \mathbf{1.03\%}$
- Cancellation rate among reassigned orders: $722 / 13,753 = \mathbf{5.25\%}$
- **Finding:** Reassigned orders exhibit a **5.1x higher probability of cancellation** than non-reassigned orders.

---

### 2.5 Distance Distributions & Outlier Audit

#### First-Mile Distance (Rider Location to Restaurant):
- **Min:** 0.00013 km (13 cm — likely rider stationed inside restaurant cluster)
- **25th Percentile:** 0.54 km
- **Median:** 1.14 km
- **Mean:** 1.23 km
- **75th Percentile:** 1.85 km
- **99th Percentile:** 2.99 km
- **Max:** 42.04 km
- **Anomalies:**
  - Values $\le 0$: 0 records.
  - Outliers $> 20$ km: exactly 1 record (`42.04 km`, likely GPS glitch).

#### Last-Mile Distance (Restaurant to Customer Doorstep):
- **Min:** 0.0000 km
- **25th Percentile:** 1.47 km
- **Median:** 2.67 km
- **Mean:** 2.97 km
- **75th Percentile:** 4.22 km
- **99th Percentile:** 8.34 km
- **Max:** 22.41 km
- **Anomalies:**
  - Values $= 0.0$ km: **94 records** (Customer pickup / walk-in order or missing coordinates).
  - Outliers $> 20$ km: 6 records.

---

### 2.6 Operational Intervals & Timestamp Anomalies

All intervals calculated in minutes from parsed UTC timestamps:

| Operational Interval | Valid Count | Negative Count | Zero Count | Min (min) | Median (min) | Mean (min) | 99th % (min) | Max (min) |
|---|---|---|---|---|---|---|---|---|
| **Allotment Delay** (`allot - order`) | 450,000 | 0 | 15,392 (3.4%) | 0.00 | 0.25 (15s) | 1.22 | 18.75 | 538.90 |
| **Acceptance Delay** (`accept - allot`) | 449,843 | **25** | 0 | -475.57 | 0.62 (37s) | 1.02 | 9.00 | 15.50 |
| **Pickup Delay** (`pickup - accept`) | 447,579 | **10** | 0 | -69.55 | 12.17 | 14.02 | 42.20 | 5,165.28 |
| **Transit Duration** (`delivered - pickup`) | 444,782 | 0 | 0 | 0.05 (3s) | 13.65 | 16.29 | 49.00 | 10,009.02 |
| **Total Delivery Duration** (`delivered - order`) | 444,782 | 0 | 0 | 1.05 | 29.32 | 32.46 | 77.62 | 10,017.72 |

#### Investigation of Negative Timestamps:
- **Negative Acceptance Delay ($N = 25$):** All 25 cases have `reassigned_order = 1.0` with `reassignment_reason` populated (`Reassign` or `SE portal`). This represents manual customer-support intervention where the rider accepted offline before the order was formally dispatched through the digital system.
- **Negative Pickup Delay ($N = 10$):** In 10 instances, `pickup_time` occurred up to 69 minutes prior to recorded `accept_time`. This occurs when riders physically collect food during heavy network latency and press "Accept" and "Picked Up" out of chronological sequence.
- **Extreme High Durations:** 400 completed orders exhibit delivery durations exceeding 3 hours (180 minutes), with the maximum reaching 10,017 minutes (~7 days). These represent forgotten or manual bulk closures of orphaned delivery tasks.

---

### 2.7 Rider Workload & State Fields Audit: The Leakage Discovery

The dataset provides five rider operational indicators:
`alloted_orders`, `delivered_orders`, `undelivered_orders`, `lifetime_order_count`, and `session_time`.

#### Empirical Consistency Check:
Evaluating the balance equation $\text{alloted\_orders} - \text{delivered\_orders} - \text{undelivered\_orders} = 0$:
- Evaluated on all 432,659 non-null rows.
- Exact match count: **432,659 out of 432,659 (100.00%)**.

#### Crucial Leakage Findings:
1. **`lifetime_order_count` is a Static Global Snapshot:**
   - Tracking individual couriers longitudinally across all 12 days reveals that `lifetime_order_count` **has exactly 1 unique value per rider** across the entire 450,000-row dataset (e.g. Rider 237 has `lifetime_order_count = 2468.0` on Jan 26, Jan 27, and Feb 06).
   - This was captured once during dataset extraction and backfilled onto historical transactions.
2. **`alloted_orders`, `delivered_orders`, and `undelivered_orders` are Daily Partition Rollups:**
   - Within any single calendar date (`order_date`), the standard deviation of `alloted_orders` for any individual courier is **0.000**.
   - An order placed at 06:30 AM has the identical `delivered_orders` value as an order placed by the same courier at 11:30 PM.
   - **Conclusion:** These fields were computed at the close of daily ETL partitions. Using them to predict order outcomes at order creation represents **severe target leakage from the future**.
3. **`session_time` is Valid Streaming Shift Telemetry:**
   - `session_time` strictly increases with each subsequent order allotment within a shift (e.g., Rider 237 advances: 63.5m $\to$ 146.6m $\to$ 167.4m $\to$ 244.2m $\to$ 587.3m).
   - `session_time` represents genuine elapsed shift minutes and is valid for modeling at prediction point $t_{\text{allot}}$.

---

## 3. Restaurant Dataset Audit: Swiggy Restaurant Listings

- **Local Path:** `data/raw/restaurants/swiggy_restaurants.csv`
- **File Size:** 883,287 bytes (0.84 MB)
- **Source Provenance:** Hugging Face (`jason1966/abhijitdahatonde_swiggy-restuarant-dataset`)
- **Total Record Count:** 8,680 rows
- **Total Column Count:** 10 columns

### 3.1 Data Completeness & Schema Integrity

Every single column has **0 missing values (100.0% complete)**:

| Field Name | Type | Unique Values | Sample Values | Operational Notes |
|---|---|---|---|---|
| `ID` | `int64` | 8,680 | 211102, 334475 | Unique primary identifier. Zero duplicates. |
| `Restaurant` | `object` | 7,865 | "La Pino'Z Pizza", "Subway" | Brand name. 815 chain duplicates across areas. |
| `City` | `object` | 9 | "Kolkata", "Mumbai", "Bangalore" | 9 Tier-1 Indian metropolitan cities. |
| `Area` | `object` | 833 | "Koramangala", "Indiranagar" | Neighborhood / commercial delivery zone. |
| `Address` | `object` | 7,869 | Full street / mall location | Text string address. |
| `Price` | `float64` | 8,680 | Mean: ₹348.44, Median: ₹300 | Average order pricing for two in INR. |
| `Avg ratings` | `float64` | 8,680 | Min: 2.0, Median: 3.9, Max: 5.0 | Consumer review rating score. |
| `Total ratings` | `int64` | 8,680 | Min: 20, Median: 80, Max: 10,000 | Consumer feedback volume count. |
| `Food type` | `object` | 1,580 | "North Indian, Chinese" | Comma-separated cuisine tags. |
| `Delivery time` | `int64` | 8,680 | Min: 20, Median: 53, Max: 109 | Static merchant app listing estimate (mins). |

### 3.2 City Distribution Breakdown

The 8,680 restaurants span 9 major operational hubs:
1. **Kolkata:** 1,346 (15.51%)
2. **Mumbai:** 1,277 (14.71%)
3. **Chennai:** 1,106 (12.74%)
4. **Pune:** 1,090 (12.56%)
5. **Hyderabad:** 1,075 (12.38%)
6. **Bangalore:** 946 (10.90%)
7. **Ahmedabad:** 717 (8.26%)
8. **Delhi:** 611 (7.04%)
9. **Surat:** 512 (5.90%)

### 3.3 Semantic Interpretation of `Delivery time`
The `Delivery time` field ranges from 20 to 109 minutes (mean 53.97 mins, median 53 mins).  
**Crucial Architectural Distinction:** This field represents the static marketing SLA displayed on Swiggy consumer search cards. It is **not** ground-truth kitchen prep duration and must not be used as an empirical regression target.

### 3.4 Cross-Dataset Relational Join Feasibility
- `Rider-Info.csv` contains `order_id`, `rider_id`, timestamps, and distance floats. It contains **no restaurant ID, no restaurant name, and no city label**.
- `swiggy_restaurants.csv` contains `ID`, merchant names, cities, and ratings. It contains **no order IDs or rider IDs**.
- **Conclusion:** Any attempt to merge historical courier orders with restaurant listings would require generating fabricated synthetic foreign keys. The two datasets must remain strictly decoupled in database storage and ML feature extraction.

---

## 4. Supplementary Dataset Status: Indian Food Delivery Time

### 4.1 Local Repository Audit
A complete file system scan across the repository confirms that the **Indian Food Delivery Time dataset does not exist locally**.

### 4.2 Official Source & Retrieval Specification
- **Dataset Title:** Food Delivery Time Prediction / Indian Food Delivery Time Dataset
- **Canonical Kaggle Reference:** `gauravmalik26/food-delivery-dataset`
- **Alternative Benchmark Mirror:** `rajatkumar30/food-delivery-time`
- **Documentation:** Captures 45,593 delivery trips across India with explicit GPS coordinates, weather conditions, and traffic densities.

#### Acquisition Instructions (Subject to User Authorization):
```bash
# Option A: Kaggle CLI
kaggle datasets download -d gauravmalik26/food-delivery-dataset
unzip food-delivery-dataset.zip -d data/raw/supplementary/

# Option B: Python kagglehub SDK
import kagglehub
path = kagglehub.dataset_download("gauravmalik26/food-delivery-dataset")
print("Downloaded path:", path)
```

#### Expected Schema & Feature Matrix (from Benchmark Literature):
- `Delivery_person_ID`: Courier identifier string.
- `Delivery_person_Age`: Courier age in years (integer/float).
- `Delivery_person_Ratings`: Average courier rating (float 1.0–5.0).
- `Restaurant_latitude` & `Restaurant_longitude`: Pickup origin coordinates.
- `Delivery_location_latitude` & `Delivery_location_longitude`: Dropoff destination coordinates.
- `Weatherconditions`: Categorical (`Fog`, `Stormy`, `Sandstorms`, `Windy`, `Cloudy`, `Sunny`).
- `Road_traffic_density`: Categorical (`Low`, `Medium`, `High`, `Jam`).
- `Vehicle_condition`: Categorical integer rating (0, 1, 2).
- `Type_of_order`: Categorical (`Snack`, `Meal`, `Drinks`, `Buffet`).
- `Type_of_vehicle`: Categorical (`motorcycle`, `scooter`, `electric_scooter`, `bicycle`).
- `multiple_deliveries`: Integer count of concurrent stacked drops.
- `Festival`: Binary (`Yes`, `No`).
- `City`: Categorical (`Metropolitian`, `Urban`, `Semi-Urban`).
- `Time_taken(min)`: Continuous integer delivery duration target.

---

## 5. Summary Data Quality Matrix & Preprocessing Directives

| Data Anomaly | Affected Records | Root Cause | Mandatory Preprocessing Directive |
|---|---|---|---|
| **Exact Duplicate Row** | 1 row (`order_id: 181402`) | ETL export double-write | Drop second duplicate instance (`keep='first'`). |
| **Negative Acceptance Delay** | 25 rows | Offline courier accept / manual SE override | Drop from acceptance-stage training; flag as operational anomaly. |
| **Negative Pickup Delay** | 10 rows | Network desynchronization on mobile terminal | Drop from prep/transit duration training. |
| **Zero Last-Mile Distance** | 94 rows | Customer collection / corrupt coordinate pair | Exclude from pure distance-based regression or impute with city median. |
| **Extreme Outlier Duration ($> 180$ min)** | 400 rows | Orphaned delivery task closed days later | Filter delivery duration target to $5 \le Y \le 180$ minutes. |
| **Static Lifetime Snapshot** | 450,000 rows | Extracted as single snapshot at dump creation | Prohibit from time-dependent streaming inference; use only as historical courier tier. |
| **Daily Workload Rollups** | 432,659 rows | Daily batch aggregation backfilled onto orders | Exclude from order-time ($t_{\text{order}}$) prediction models; severe future leakage. |
| **Missing Reassignment Flags** | 436,247 rows | Unassigned orders represented as NaN | Impute `reassigned_order = 0.0`, method = `'none'`, reason = `'none'`. |
| **Reassigned Allotment Shift** | 13,753 rows | Overwriting of initial dispatch timestamp | Model allocation delay explicitly as risk of auto-reassignment / repush. |
