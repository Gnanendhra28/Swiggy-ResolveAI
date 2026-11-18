# Swiggy ResolveAI — Public Datasets & Data Provenance Report
**Document Path:** `docs/datasets.md`  
**Date:** November 18, 2026  
**Status:** Ingested & Verified

---

## 1. Overview & Non-Integration Principles

ResolveAI integrates two real-world public datasets for historical research and operational baseline modeling.

> [!IMPORTANT]
> **Data Provenance & Isolation Rules:**
> - Neither dataset represents proprietary, private Swiggy production APIs or databases.
> - Public dataset records are strictly marked as `PUBLIC_HISTORICAL`.
> - Simulated orders and runtime events are strictly marked as `SYNTHETIC`.
> - **Zero Synthetic Fabrication:** No latitude/longitude coordinates, fake customer IDs, or synthetic restaurant relationships are invented for historical orders.

---

## 2. Directory Structure

```
data/
├── raw/
│   ├── restaurants/
│   │   └── swiggy_restaurants.csv       # Hugging Face export (8,680 rows, 1.0 MB)
│   └── orders/
│       └── Rider-Info.csv               # Kaggle export (450,000 rows, 85.0 MB)
├── processed/                           # Prepared data caches
└── synthetic/                           # Seed configurations & simulation fixtures
```

---

## 3. Dataset 1: Swiggy Restaurant Listings

- **Source:** Hugging Face Hub
- **Dataset ID:** `jason1966/abhijitdahatonde_swiggy-restuarant-dataset`
- **Local Path:** `data/raw/restaurants/swiggy_restaurants.csv`
- **Total Rows Inspected:** 8,680 rows
- **Duplicate ID Count:** 0 (100% unique primary keys)

### Column Mapping & Semantics:

| Source Column | Canonical DB Field | Type | Handling & Provenance Rule |
|---|---|---|---|
| `ID` | `external_dataset_id` | VARCHAR(64) | Unique external identifier from dataset. Used for idempotent re-ingestion. |
| `Restaurant` | `name` | VARCHAR(255) | Restaurant brand name. |
| `City` | `city` | VARCHAR(128) | City (e.g. Bangalore, Mumbai, Delhi, Hyderabad). |
| `Area` | `area` | VARCHAR(128) | Locality/Neighborhood (e.g. Koramangala, Indiranagar). |
| `Food type` | `cuisine` | VARCHAR(255) | Cuisines and food categories. |
| `Avg ratings` | `rating` | FLOAT | Customer rating (nullable). |
| `Total ratings` | `rating_count` | INTEGER | Aggregate rating count. |
| `Price` | `average_price` | FLOAT | Average pricing in INR. |
| `Address` | `location` | VARCHAR(255) | Locality address string. |
| `Delivery time` | `delivery_time_listing` | VARCHAR(64) | **Source listing value only** (e.g. "45 mins"). *Not verified kitchen prep time.* |
| *(None in source)* | `latitude` / `longitude` | FLOAT (NULL) | **Never fabricated.** Retained as NULL. |
| *(None in source)* | `data_source` | VARCHAR(48) | Tagged explicitly as `PUBLIC_HISTORICAL`. |

### Ingestion Data Quality Findings:
- Total rows ingested into `restaurants` table: **8,680**.
- Idempotency verified: re-running ingestion skips all 8,680 existing records without duplicate rows.
- Used to populate realistic restaurant profiles into the Order Simulator and Dashboard.

---

## 4. Dataset 2: Swiggy/Zomato Rider & Order Information

- **Source:** Kaggle
- **Dataset ID:** `cbhavik/swiggyzomato-order-information`
- **Local Path:** `data/raw/orders/Rider-Info.csv`
- **Total Rows Inspected:** 450,000 rows (85.0 MB uncompressed)
- **Destination Table:** `historical_orders` (*Completely isolated from `orders`*)

### Column Schema & Data Quality Profiling:

| Source Column | Canonical Field | Type | Null Count | Data Quality Notes |
|---|---|---|---|---|
| `order_id` | `order_id` | VARCHAR(64) | 0 | Unique integer/string order identifiers. |
| `order_time` | `order_time` | TIMESTAMP (UTC) | 0 | Baseline order placement timestamp. |
| `order_date` | `order_date` | VARCHAR(32) | 0 | Date partition string. |
| `allot_time` | `allot_time` | TIMESTAMP (UTC) | 0 | Rider dispatch/allotment timestamp. |
| `accept_time` | `accept_time` | TIMESTAMP (UTC) | 157 | Timestamp when rider accepted the allotment. |
| `pickup_time` | `pickup_time` | TIMESTAMP (UTC) | 2,421 | Timestamp when order was collected from merchant. |
| `delivered_time` | `delivered_time` | TIMESTAMP (UTC) | 5,218 | Timestamp of delivery handover (Null for cancellations). |
| `cancelled_time` | `cancelled_time` | TIMESTAMP (UTC) | 444,782 | Timestamp when order was aborted/cancelled. |
| `cancelled` | `cancelled` | BOOLEAN | 0 | Boolean flag (0 = Fulfilled: 444,782; 1 = Cancelled: 5,218). |
| `rider_id` | `rider_id` | VARCHAR(64) | 0 | Assigned courier fleet partner ID. |
| `first_mile_distance` | `first_mile_distance` | FLOAT | 0 | Travel distance from rider location to merchant. |
| `last_mile_distance` | `last_mile_distance` | FLOAT | 0 | Travel distance from merchant to customer doorstep. |
| `alloted_orders` | `allotted_orders` | INTEGER | 16,948 | Active concurrent orders assigned to rider. |
| `delivered_orders` | `delivered_orders` | INTEGER | 17,341 | Orders delivered by rider in current shift. |
| `undelivered_orders` | `undelivered_orders` | INTEGER | 17,341 | Orders pending delivery by rider. |
| `lifetime_order_count` | `lifetime_order_count` | INTEGER | 53 | Historical career orders fulfilled by rider. |
| `reassigned_order` | `reassigned_order` | BOOLEAN | 436,247 nulls | 13,753 reassigned orders (3.06% reassignment rate). |
| `reassignment_method` | `reassignment_method` | VARCHAR(64) | 436,256 nulls | Method (e.g. auto, dispatch manual). |
| `reassignment_reason` | `reassignment_reason` | VARCHAR(255) | 436,247 nulls | Operational cause for courier reassignment. |
| `session_time` | `session_time` | FLOAT | 3,675 | Total rider logged-in active duration. |

### Architectural Isolation:
- Historical orders have **no customer or restaurant foreign keys** because the public Kaggle dataset does not contain merchant or customer identifiers.
- ResolveAI **does not invent fake customer or restaurant IDs** to force relational joins.
- Records are stored in a dedicated `historical_orders` table, preserving historical baseline operational telemetry for Phase 2 duration models and reassignment analysis.

---

## 5. Ingestion Architecture

The ingestion pipeline in `backend/app/services/ingestion/` contains 5 modular components:

1. **`ColumnMapper`**: Standardizes column names from arbitrary CSV headers to canonical database attributes.
2. **`DatasetValidator`**: Validates required columns, parses ISO/custom datetime strings to UTC, and handles numeric boundaries.
3. **`DataQualityReport`**: Captures total rows, null counts, duplicate detection, and execution timings.
4. **`RestaurantDatasetLoader`**: Idempotent loader reading from Hugging Face or `data/raw/restaurants/` with batch transactions.
5. **`OrderHistoryDatasetLoader`**: Chunked batch loader (`batch_size=1000`) for the 450,000-row Kaggle dataset with cancellation handling.
