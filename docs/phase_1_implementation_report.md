# Swiggy ResolveAI — Phase 1 Product Foundation Report
**Document Path:** `docs/phase_1_implementation_report.md`  
**Date:** November 18, 2026  
**Status:** Complete, Ingested & Verified  
**Project:** Swiggy ResolveAI (Proactive Order Intelligence & Autonomous Recovery)

---

## 1. Product Context & Non-Integration Notice

ResolveAI is an independent, AI-powered proactive delivery intelligence and autonomous recovery platform. It detects potential operational anomalies, food-delivery order delays, and coordinates recovery events.

> [!IMPORTANT]
> **Independent System & Provenance Notice:**  
> ResolveAI is **NOT** rebuilding Swiggy and has **NO** access to internal Swiggy proprietary APIs, databases, or production networks.
> - All live runtime records generated during demonstrations are tagged as `SYNTHETIC`.
> - Public datasets (Hugging Face restaurant listings and Kaggle order lifecycle data) are preserved with strict source provenance (`PUBLIC_HISTORICAL`) and are never merged without verified primary keys.
> - Zero synthetic fabrication: No coordinates are invented when absent, and historical orders are strictly isolated from customer/restaurant foreign keys.
> - Do not claim real Swiggy integration.

---

## 2. Repository Changes & Architecture Summary

The repository was built from the ground up utilizing Clean Architecture, SOLID principles, and strict separation of concerns without introducing microservices, Kafka, or unnecessary operational overhead.

### Architectural Layout

```
Swiggy ResolveAI/
├── .env.example                       # Documented environment variables
├── .env                               # Active local configuration
├── docker-compose.yml                 # PostgreSQL, Backend, Frontend orchestration
├── pytest.ini                         # Pytest configuration
├── docs/
│   ├── phase_1_implementation_report.md # Complete Phase 1 & Addendum Documentation
│   └── datasets.md                    # Data provenance and data quality report
├── data/
│   ├── raw/
│   │   ├── restaurants/
│   │   │   └── swiggy_restaurants.csv # Hugging Face dataset (8,680 rows)
│   │   └── orders/
│   │       └── Rider-Info.csv         # Kaggle order lifecycle dataset (450,000 rows)
│   ├── processed/                     # Caching & staging directory
│   └── synthetic/                     # Deterministic seed data & fixtures
├── backend/
│   ├── Dockerfile                     # Multi-stage Python 3.12 container
│   ├── requirements.txt               # Pinned dependencies
│   ├── alembic.ini                    # Alembic configuration
│   ├── alembic/
│   │   ├── env.py                     # Alembic migration environment
│   │   ├── script.py.mako             # Migration template
│   │   └── versions/
│   │       ├── 001_initial_schema.py  # Initial database DDL revision
│   │       └── 002_public_datasets_integration.py # Historical orders & restaurant dataset fields
│   └── app/
│       ├── main.py                    # FastAPI application initialization & lifespan
│       ├── api/
│       │   ├── router.py              # Centralized route registration
│       │   └── routes/
│       │       ├── health.py          # GET /health
│       │       ├── orders.py          # GET /orders, /orders/metrics, /orders/{id}, /events
│       │       ├── simulation.py      # POST /simulation/generate, /events, GET /scenarios
│       │       └── ingestion.py       # POST /ingest/restaurants, POST /ingest/orders/history, GET /status
│       ├── core/
│       │   ├── config.py              # Pydantic v2 settings & environment variables
│       │   ├── logging.py             # Structured application logger
│       │   └── exceptions.py          # Custom domain exceptions & global handlers
│       ├── database/
│       │   ├── base.py                # SQLAlchemy 2.x DeclarativeBase
│       │   └── session.py             # Engine & SessionLocal lifecycle manager
│       ├── models/
│       │   ├── customer.py            # Customer entity
│       │   ├── restaurant.py          # Restaurant entity
│       │   ├── delivery_partner.py    # DeliveryPartner entity
│       │   ├── order.py               # Order entity (synthetic runtime state)
│       │   ├── order_event.py         # OrderEvent append-only history entity
│       │   └── historical_order.py    # HistoricalOrder entity (Kaggle public dataset)
│       ├── schemas/                   # Pydantic validation & response contracts
│       ├── services/
│       │   ├── order_service.py       # Order domain operations & analytics
│       │   ├── simulation_service.py  # Simulation orchestration & persistence
│       │   └── ingestion/             # Modular dataset ingestion engine
│       │       ├── column_mapper.py   # Normalization of arbitrary headers to canonical keys
│       │       ├── dataset_validator.py # Schema & boundary validation
│       │       ├── quality_report.py  # Ingestion metrics, null counting & timing
│       │       ├── restaurant_loader.py # Batch idempotent restaurant ingestion
│       │       └── order_history_loader.py # Chunked batch loader for 450K historical orders
│       └── simulation/
│           ├── order_simulator.py     # Master scenario orchestrator
│           ├── restaurant_simulator.py# Kitchen prep & backlog simulator
│           ├── delivery_simulator.py  # Rider search, assignment & pickup simulator
│           ├── traffic_simulator.py   # Route congestion & dynamic ETA simulator
│           └── scenarios.py           # Scenario definitions & metadata
├── frontend/
│   ├── package.json                   # Next.js 16, React 19, Tailwind CSS v4, Lucide
│   ├── Dockerfile                     # Multi-stage production container
│   └── src/
│       ├── lib/
│       │   ├── types.ts               # TypeScript data models
│       │   └── api.ts                 # Backend API client functions
│       ├── components/
│       │   ├── Navbar.tsx             # Global navigation & live health monitor
│       │   ├── StatCard.tsx           # KPI metric card component
│       │   ├── OrderStatusBadge.tsx   # Color-coded operational status badge
│       │   └── EventTimeline.tsx      # Chronological vertical event timeline
│       └── app/
│           ├── layout.tsx             # Root layout with Suspense wrappers
│           ├── page.tsx               # A. Operations Dashboard
│           ├── orders/
│           │   ├── page.tsx           # B. Orders Management (filtering/search)
│           │   └── [id]/
│           │       └── page.tsx       # C. Order Details & Event Injection
│           ├── simulation/
│           │   └── page.tsx           # D. Simulation Control Panel
│           └── health/
│               └── page.tsx           # E. System Diagnostic & Health
```

---

## 3. Database Schema & Migration Details

Alembic revisions manage database migrations with clean forward upgrades:
- `001_initial_schema.py`: Initial schema creation for core entities.
- `002_public_datasets_integration.py`: Extension of `restaurants` with dataset metadata and introduction of `historical_orders`.

### 1. `customers`
- `id` (VARCHAR(36), PK): UUID
- `name` (VARCHAR(128), NOT NULL)
- `phone` (VARCHAR(32), NOT NULL, INDEX)
- `created_at` (TIMESTAMP WITH TIME ZONE, UTC)

### 2. `restaurants`
- `id` (VARCHAR(36), PK): UUID
- `external_dataset_id` (VARCHAR(64), NULLABLE, UNIQUE, INDEX): Original Hugging Face ID (e.g. `28405`) for idempotent ingestion
- `name` (VARCHAR(255), NOT NULL, INDEX)
- `city` (VARCHAR(128), NOT NULL, INDEX)
- `area` (VARCHAR(128), NOT NULL)
- `cuisine` (VARCHAR(255), NOT NULL, INDEX)
- `rating` (FLOAT, NULLABLE)
- `rating_count` (INTEGER, NULLABLE)
- `average_price` (FLOAT, NULLABLE)
- `number_of_offers` (INTEGER, DEFAULT 0)
- `offer_name` (VARCHAR(255), NULLABLE)
- `pure_veg` (BOOLEAN, DEFAULT FALSE)
- `location` (VARCHAR(255), NULLABLE)
- `delivery_time_listing` (VARCHAR(64), NULLABLE): Preserved source listing value (e.g. "45 mins"), not verified kitchen prep time
- `latitude` (FLOAT, NULLABLE) — **Explicitly preserved as NULL; never fabricated**
- `longitude` (FLOAT, NULLABLE) — **Explicitly preserved as NULL; never fabricated**
- `data_source` (VARCHAR(48), DEFAULT 'SYNTHETIC', INDEX): `PUBLIC_HISTORICAL` or `SYNTHETIC`
- `created_at` (TIMESTAMP WITH TIME ZONE, UTC)

### 3. `delivery_partners`
- `id` (VARCHAR(36), PK): UUID
- `external_rider_id` (VARCHAR(64), NULLABLE, INDEX)
- `name` (VARCHAR(128), NOT NULL)
- `availability_status` (VARCHAR(32), DEFAULT 'AVAILABLE', INDEX)
- `created_at` (TIMESTAMP WITH TIME ZONE, UTC)

### 4. `orders` (Current Operational Synthetic State)
- `id` (VARCHAR(36), PK): UUID
- `external_order_id` (VARCHAR(64), UNIQUE, INDEX)
- `customer_id` (VARCHAR(36), FK `customers.id`, RESTRICT, INDEX)
- `restaurant_id` (VARCHAR(36), FK `restaurants.id`, RESTRICT, INDEX)
- `delivery_partner_id` (VARCHAR(36), FK `delivery_partners.id`, SET NULL, NULLABLE, INDEX)
- `order_status` (VARCHAR(48), NOT NULL, INDEX)
- `order_value` (FLOAT, NOT NULL)
- `promised_delivery_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)
- `created_at` (TIMESTAMP WITH TIME ZONE, NOT NULL, INDEX)
- `updated_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)
- `demo_run_id` (VARCHAR(64), NULLABLE, INDEX)
- `data_source` (VARCHAR(48), DEFAULT 'SYNTHETIC', INDEX)

### 5. `order_events` (Append-Only Event Ledger)
- `id` (VARCHAR(36), PK): UUID
- `order_id` (VARCHAR(36), FK `orders.id`, CASCADE, NOT NULL, INDEX)
- `event_type` (VARCHAR(64), NOT NULL, INDEX)
- `event_timestamp` (TIMESTAMP WITH TIME ZONE, NOT NULL, INDEX)
- `metadata` (JSON, NOT NULL)
- `data_source` (VARCHAR(48), DEFAULT 'SYNTHETIC', INDEX)
- `created_at` (TIMESTAMP WITH TIME ZONE, UTC)

### 6. `historical_orders` (Isolated Kaggle Public Dataset)
- `id` (VARCHAR(36), PK): UUID
- `order_id` (VARCHAR(64), UNIQUE, NOT NULL, INDEX): Kaggle order identifier
- `order_time` (TIMESTAMP WITH TIME ZONE, NOT NULL, INDEX): Placement timestamp
- `order_date` (VARCHAR(32), NOT NULL, INDEX): Partition date
- `allot_time` (TIMESTAMP WITH TIME ZONE, NOT NULL): Rider dispatch timestamp
- `accept_time` (TIMESTAMP WITH TIME ZONE, NULLABLE): Rider acceptance timestamp
- `pickup_time` (TIMESTAMP WITH TIME ZONE, NULLABLE): Store collection timestamp
- `delivered_time` (TIMESTAMP WITH TIME ZONE, NULLABLE): Customer handover timestamp
- `cancelled_time` (TIMESTAMP WITH TIME ZONE, NULLABLE): Cancellation timestamp
- `cancelled` (BOOLEAN, DEFAULT FALSE, INDEX): Boolean status
- `rider_id` (VARCHAR(64), NOT NULL, INDEX): Courier fleet ID
- `first_mile_distance` (FLOAT, NOT NULL): Rider to restaurant distance (km)
- `last_mile_distance` (FLOAT, NOT NULL): Restaurant to customer distance (km)
- `allotted_orders` (INTEGER, NULLABLE): Concurrent orders in shift
- `delivered_orders` (INTEGER, NULLABLE): Cumulative completed shift orders
- `undelivered_orders` (INTEGER, NULLABLE): Pending shift orders
- `lifetime_order_count` (INTEGER, NULLABLE): Career order count
- `reassigned_order` (BOOLEAN, NULLABLE): Whether order was reassigned
- `reassignment_method` (VARCHAR(64), NULLABLE): e.g. auto, manual dispatch
- `reassignment_reason` (VARCHAR(255), NULLABLE): Operational cause
- `session_time` (FLOAT, NULLABLE): Rider shift duration (minutes)
- `data_source` (VARCHAR(48), DEFAULT 'PUBLIC_HISTORICAL', INDEX)
- `ingested_at` (TIMESTAMP WITH TIME ZONE, UTC)

> [!NOTE]
> **Strict Entity Isolation:**  
> Historical orders are stored in `historical_orders` and are **never** relationally joined or forced into the `orders` table. Because the Kaggle dataset lacks restaurant or customer identifiers, no fake IDs are generated.

---

## 4. REST API Endpoint Documentation

All endpoints are prefixed with `/api/v1` and document OpenAPI schemas at `/docs`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Application status, PostgreSQL connectivity, version, and UTC timestamp |
| `GET` | `/api/v1/orders/metrics` | Real-time dashboard KPI metrics, status distribution, and recent activity stream |
| `GET` | `/api/v1/orders` | Paginated orders list with filtering by `status`, `demo_run_id`, `data_source`, and `search` |
| `GET` | `/api/v1/orders/{order_id}` | Complete order details including customer, restaurant, rider, and full event timeline |
| `GET` | `/api/v1/orders/{order_id}/events` | Chronological event list for an order |
| `GET` | `/api/v1/simulation/scenarios` | Metadata and descriptions for the 6 reproducible simulation scenarios |
| `POST` | `/api/v1/simulation/generate` | Generates batches of synthetic orders and chronological events with deterministic random seeds |
| `POST` | `/api/v1/simulation/events` | Injects a runtime operational event into an existing order's event history |
| `POST` | `/api/v1/ingest/restaurants` | Ingests restaurant CSV or Hugging Face dataset idempotently with column normalization |
| `POST` | `/api/v1/ingest/orders/history` | Ingests Kaggle rider order lifecycle CSV into `historical_orders` |
| `GET` | `/api/v1/ingest/status` | Dataset counts, ingestion timestamps, and raw file availability |

---

## 5. Public Datasets Integration & Ingestion Pipeline

### A. Ingestion Architecture

The ingestion pipeline (`backend/app/services/ingestion/`) separates data extraction, normalization, validation, and persistence:

1. **`ColumnMapper`**: Standardizes diverse CSV naming conventions into canonical internal keys.
2. **`DatasetValidator`**: Validates required columns, parses date/time strings with fallback to multiple formats, safely converts floats/ints/booleans, and handles missing/null values.
3. **`DataQualityReport`**: Profiles total rows, ingested rows, skipped duplicates, null frequencies, and execution elapsed time.
4. **`RestaurantDatasetLoader`**: Loads Hugging Face restaurant data (`swiggy_restaurants.csv`) in transactions of 1,000 records. Ensures idempotency via `external_dataset_id`.
5. **`OrderHistoryDatasetLoader`**: Loads Kaggle order history (`Rider-Info.csv`) in streaming batches of 1,000 records, safely handling cancellation timestamps and reassignment fields.

### B. Ingested Datasets Summary

| Metric / Property | Dataset 1: Restaurant Listings | Dataset 2: Rider & Order History |
|---|---|---|
| **Source** | Hugging Face: `jason1966/abhijitdahatonde_swiggy-restuarant-dataset` | Kaggle: `cbhavik/swiggyzomato-order-information` |
| **Local File** | `data/raw/restaurants/swiggy_restaurants.csv` | `data/raw/orders/Rider-Info.csv` |
| **File Size / Rows** | 1.0 MB / 8,680 rows | 85.0 MB / 450,000 rows |
| **Target Table** | `restaurants` | `historical_orders` |
| **Provenance** | `PUBLIC_HISTORICAL` | `PUBLIC_HISTORICAL` |
| **Key Findings** | 100% unique IDs; 7 chain duplicate tuples; 0 coordinates fabricated; `Delivery time` preserved as listing string | 5,218 cancellations (1.16%); 13,753 reassignments (3.06%); 0 customer/merchant IDs present |

---

## 6. Simulator Scenario Documentation

The simulator comprises four modular services:
- **`OrderSimulator`**: Scenario coordinator and lifecycle builder.
- **`RestaurantSimulator`**: Kitchen acceptance, prep duration, and backlog simulator.
- **`DeliverySimulator`**: Rider search, timeout, assignment, store arrival, and pickup simulator.
- **`TrafficSimulator`**: Route congestion, rain/waterlogging, and dynamic ETA revision simulator.

### Supported Scenarios:

1. **`NORMAL_ORDER`**  
   - Lifecycle: `ORDER_PLACED` &rarr; `RESTAURANT_ACCEPTED` &rarr; `RIDER_SEARCH_STARTED` &rarr; `RIDER_ASSIGNED` &rarr; `PREPARATION_STARTED` &rarr; `FOOD_READY` &rarr; `RIDER_ARRIVED_AT_STORE` &rarr; `ORDER_PICKED_UP` &rarr; `ORDER_DELIVERED`.  
   - Expected status: `DELIVERED` (on-time).

2. **`RESTAURANT_DELAY`**  
   - Lifecycle: Kitchen experiences high order volume, generating `KITCHEN_DELAY_DETECTED` with delayed prep.  
   - Expected status: `DELIVERED` (delayed).

3. **`DELIVERY_DELAY`**  
   - Lifecycle: Rider encounters heavy route congestion/waterlogging during transit (`TRAFFIC_CONGESTION_DETECTED` & `DELIVERY_DELAY_PREDICTED`). Dynamic ETA exceeds promised SLA.  
   - Expected status: `DELIVERED` (delayed).

4. **`ASSIGNMENT_DELAY`**  
   - Lifecycle: Initial rider search times out due to sector demand (`RIDER_SEARCH_TIMEOUT`). Expanded search reassigns order (`RIDER_ASSIGNED` with alternate courier).  
   - Expected status: `DELIVERED` (reassigned).

5. **`FAILED_RECOVERY`**  
   - Lifecycle: Kitchen equipment breakdown / inventory stockout occurs (`KITCHEN_STOCKOUT_DETECTED`). Automated recovery is attempted (`RECOVERY_ATTEMPTED`), fails due to branch backlog (`RECOVERY_FAILED`), and is escalated to human support desk (`ORDER_ESCALATED`).  
   - Expected status: `ESCALATED`.

6. **`SUCCESSFUL_RECOVERY`**  
   - Lifecycle: Initial rider vehicle breakdown is detected (`OPERATIONAL_ANOMALY_DETECTED`). Autonomous recovery engine triggers emergency dispatch and wallet credit appeasement (`RECOVERY_TRIGGERED` & `RIDER_REASSIGNED`). Alternate rider completes express delivery (`RECOVERY_SUCCESSFUL`).  
   - Expected status: `RECOVERED`.

---

## 7. Frontend Page Summary

Built using **Next.js 16.4.6**, **React 19**, **TypeScript**, and **Tailwind CSS**.

1. **Operations Dashboard (`/`)**:
   - Live KPI cards: Total Orders, Active In-Transit, Delivered Successfully, Delayed / Escalated.
   - Status distribution breakdown with dynamic percentage progress meters.
   - Live Operational Event Feed streaming real-time events.
2. **Orders Management (`/orders`)**:
   - Filterable, searchable data table with pagination controls.
   - Multi-field search (Order ID, Customer, Restaurant, City).
   - Provenance filtering (`SYNTHETIC` vs `PUBLIC_HISTORICAL`).
3. **Order Details & Investigation (`/orders/[id]`)**:
   - Detailed Merchant, Customer, Delivery Fleet Partner, and SLA Financial cards.
   - Interactive chronological vertical event timeline with event badges and expandable JSON metadata.
   - Runtime Event Injection Console to simulate real-time operator overrides.
4. **Simulation Control Panel (`/simulation`)**:
   - Interactive scenario cards with status pills and descriptions.
   - Order count slider (1–25 orders) and reproducible random seed input.
   - Generated batch summary card with demo run ID and direct links to generated orders.
5. **System Diagnostic & Health (`/health`)**:
   - Real-time backend and database connectivity indicators.
   - Ping latency measurement and platform release diagnostics.

---

## 8. Commands to Start Backend & Frontend

### Option A: Local Development (Native)

#### 1. Backend:
```bash
# Run migrations
alembic upgrade head

# Start FastAPI server
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

#### 2. Frontend:
```bash
cd frontend
npm run dev
# Or run production build:
# npm run build
# npm start
```
Frontend App: [http://localhost:3000](http://localhost:3000)

### Option B: Docker Compose (All Services)
```bash
docker compose up --build
```
- PostgreSQL: `localhost:5432`
- Backend API & Docs: `http://localhost:8000/docs`
- Frontend Dashboard: `http://localhost:3000`

### Option C: Trigger Dataset Ingestion via API
```bash
# Ingest Restaurant Dataset (Hugging Face / CSV)
curl -X POST "http://localhost:8000/api/v1/ingest/restaurants"

# Ingest Kaggle Historical Orders (first 10,000 rows sample or complete file)
curl -X POST "http://localhost:8000/api/v1/ingest/orders/history?limit=10000"

# Check Dataset Status & Row Counts
curl -X GET "http://localhost:8000/api/v1/ingest/status"
```

---

## 9. Environment Variable Configuration (`.env.example`)

```env
# ResolveAI Environment Configuration
PROJECT_NAME="Swiggy ResolveAI"
VERSION="0.1.0"
ENVIRONMENT="development"
LOG_LEVEL="INFO"

# Database Configuration (PostgreSQL)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=resolveai
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/resolveai

# Fallback for local development without live PostgreSQL:
# DATABASE_URL=sqlite:///./resolveai.db

# Frontend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 10. Tests Executed & Actual Results

Backend test suite executed with Pytest (`python -m pytest`):

```
backend/tests/test_alembic.py::test_alembic_migrations PASSED            [  4%]
backend/tests/test_database.py::test_database_connection PASSED          [  8%]
backend/tests/test_database.py::test_seed_entities_exist PASSED          [ 12%]
backend/tests/test_dataset_integration.py::test_column_mapper_normalization PASSED [ 16%]
backend/tests/test_dataset_integration.py::test_dataset_validator_required_columns PASSED [ 20%]
backend/tests/test_dataset_integration.py::test_dataset_validator_parsers PASSED [ 24%]
backend/tests/test_dataset_integration.py::test_restaurant_dataset_loader_and_idempotency PASSED [ 28%]
backend/tests/test_order_history_dataset_loader.py::test_order_history_dataset_loader PASSED [ 32%]
backend/tests/test_dataset_integration.py::test_missing_and_cancelled_values_handling PASSED [ 36%]
backend/tests/test_health.py::test_health_check_endpoint PASSED          [ 40%]
backend/tests/test_models.py::test_restaurant_fields_preservation PASSED [ 44%]
backend/tests/test_models.py::test_order_model_relationships_and_cascade PASSED [ 48%]
backend/tests/test_orders_api.py::test_order_lifecycle_and_api PASSED    [ 52%]
backend/tests/test_provenance.py::test_synthetic_data_provenance PASSED  [ 56%]
backend/tests/test_provenance.py::test_historical_dataset_ingestion_provenance PASSED [ 60%]
backend/tests/test_provenance.py::test_invalid_request_handling PASSED   [ 64%]
backend/tests/test_simulation.py::test_all_simulation_scenarios[NORMAL_ORDER-DELIVERED] PASSED [ 68%]
backend/tests/test_simulation.py::test_all_simulation_scenarios[RESTAURANT_DELAY-DELIVERED] PASSED [ 72%]
backend/tests/test_simulation.py::test_all_simulation_scenarios[DELIVERY_DELAY-DELIVERED] PASSED [ 76%]
backend/tests/test_simulation.py::test_all_simulation_scenarios[ASSIGNMENT_DELAY-DELIVERED] PASSED [ 80%]
backend/tests/test_simulation.py::test_all_simulation_scenarios[FAILED_RECOVERY-ESCALATED] PASSED [ 84%]
backend/tests/test_simulation.py::test_all_simulation_scenarios[SUCCESSFUL_RECOVERY-RECOVERED] PASSED [ 88%]
backend/tests/test_simulation.py::test_simulation_seed_reproducibility PASSED [ 92%]
backend/tests/test_simulation.py::test_inject_event_api PASSED           [ 96%]
backend/tests/test_simulation.py::test_list_simulation_scenarios PASSED  [100%]

============================= 25 passed in 1.87s ==============================
```

Frontend build and TypeScript verification:
```
▲ Next.js 16.4.6 (Turbopack)
✓ Compiled successfully
✓ Finished TypeScript in 2.7s
✓ Generating static pages using 7 workers (8/8) in 690ms
```

---

## 11. Known Limitations & Phase 2 Outlook

1. **No Production ML Models (By Design for Phase 1):**  
   Delay prediction in Phase 1 is generated deterministically by the `TrafficSimulator` and `RestaurantSimulator` operational logic. Machine learning feature stores, embeddings, and XGBoost/LightGBM delay forecasting using the ingested `historical_orders` dataset are explicitly scoped for Phase 2.
2. **No Autonomous AI Agents or LangGraph (Phase 2):**  
   Agentic workflow orchestrators, LLM reasoning loops, and multi-agent recovery teams (Customer Agent, Restaurant Agent, Rider Agent, Orchestrator) are intentionally scoped for Phase 2.
3. **Historical Orders Relational Boundary:**  
   The Kaggle dataset contains no customer or merchant keys. Rather than polluting domain tables with fabricated entities, `historical_orders` remains an isolated operational baseline table for downstream training and delay analytics.
