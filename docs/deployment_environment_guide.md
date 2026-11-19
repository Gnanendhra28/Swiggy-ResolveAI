# Swiggy ResolveAI — Production Deployment Architecture & Environment Guide

- **Date**: November 19, 2026
- **Auditor**: Senior DevOps & Platform Engineer
- **Status**: **PORTFOLIO DEPLOYMENT SPECIFICATION**

---

## 1. Target Deployment Architecture

The recommended production architecture decouples the Next.js 16 frontend from the ML-powered FastAPI backend, pairing each component with its optimal hosting runtime:

```mermaid
flowchart TD
    subgraph ClientBrowser ["1. Client Browsers"]
        User["End Users & Operations Leads\n(HTTPS Web Browser)"]
    end

    subgraph VercelEdge ["2. Frontend Hosting: Vercel"]
        VercelCDN["Vercel Global Edge Network\n(Turbopack Static Cache / SSR)"]
        NextServer["Next.js 16 App Router\n• Root Directory: frontend\n• Server-Side Rewrites: /api/:path*"]
        VercelCDN --> NextServer
    end

    subgraph ContainerHosting ["3. Backend Hosting: Render / Railway / AWS App Runner"]
        BackendContainer["FastAPI Modular Monolith\n(backend/Dockerfile, Python 3.12-slim)\n• MLInferenceService (LightGBM Quantiles & C2)\n• LangGraph Multi-Agent Engine\n• PolicyEngine & RecoveryExecutionService"]
        HealthProbe["Health Probes\nGET /api/v1/health/live\nGET /api/v1/health/ready"]
    end

    subgraph DataTier ["4. Persistent Data Tier: Hosted PostgreSQL"]
        PostgresDB[("Hosted PostgreSQL 15+\n(Neon / Supabase / Render / AWS RDS)\n• orders & order_events\n• recovery_execution_audits\n• ml_prediction_audits\n• restaurants & historical_orders")]
    end

    subgraph ExternalAI ["5. External AI Services"]
        GeminiAPI["Google Gemini API\n(gemini-3.5-flash)\n[Structured Root-Cause Synthesis]"]
    end

    User -->|HTTPS: Direct Client Fetch\nNEXT_PUBLIC_API_URL| BackendContainer
    User -->|HTTPS: Web Page Load| VercelCDN
    NextServer -->|Server-Side Rewrites\nBACKEND_URL| BackendContainer
    BackendContainer -->|SQLAlchemy + Psycopg2 Pool\nDATABASE_URL (sslmode=require)| PostgresDB
    BackendContainer -->|HTTPS: Optional LLM Synthesis\nGEMINI_API_KEY| GeminiAPI
    BackendContainer --> HealthProbe
```

---

## 2. Technical Evaluation: Why the Backend Cannot Run on Vercel Serverless

Vercel provides preview support for Python serverless functions, but deploying the existing **Swiggy ResolveAI FastAPI backend directly on Vercel Serverless is not viable** without major architectural compromises:

1. **Uncompressed Bundle Size Limit (250 MB)**:
   - Vercel Serverless Functions enforce a strict hard limit of 250 MB uncompressed (50 MB zipped).
   - Swiggy ResolveAI is a data-science and machine learning monolith. Its core Python dependencies include `scipy` (~150MB), `scikit-learn` (~70MB), `pandas` (~100MB), `pyarrow` (~120MB), `lightgbm` (~30MB), `shap` (~40MB), `matplotlib` (~50MB), and `langgraph`.
   - Combined with native C++ compilation bindings (OpenMP) and serialized model artifacts in `data/artifacts/models/phase_2_5/` (~2 MB), the uncompressed container environment exceeds **650 MB**, which immediately fails Vercel's serverless packaging limits.
2. **Cold Start Latency vs Hobby/Pro Function Timeouts**:
   - Initializing LightGBM regressors (`joblib.load`) and compiling LangGraph state graphs takes 5 to 15 seconds on a cold serverless invocation.
   - Vercel Hobby tier functions have a strict 10-second execution timeout; Pro functions timeout at 60 seconds but incur severe cold-start latency spikes that degrade user experience.
3. **C++ Native Extensions**:
   - LightGBM and Scipy require native Linux shared libraries (`libgomp`, `libpq-dev`). Vercel's default Amazon Linux 2 serverless runtime lacks pre-installed scientific build tools.
4. **Clean Monolith Architecture**:
   - The repository already includes a production-grade, hardened Dockerfile ([`backend/Dockerfile`](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/backend/Dockerfile)) with non-root security compliance (`appuser`), multi-stage caching, and curl healthchecks. Running this container on a dedicated container platform requires **zero architectural changes**.

---

## 3. Frontend Deployment Guide (Vercel)

### 3.1 Project Import & Monorepo Settings
When importing the Git repository into Vercel:

| Vercel Configuration Field | Required Value | Notes |
| :--- | :--- | :--- |
| **Framework Preset** | `Next.js` | Automatically detected. |
| **Root Directory** | `frontend` | **CRITICAL**: Set to `frontend` so Vercel builds only the Next.js app. |
| **Build Command** | `npm run build` | Default (Turbopack enabled). |
| **Install Command** | `npm install` | Default. |
| **Output Directory** | `.next` | Automatically handled by Next.js. |
| **Node.js Version** | `20.x` or `22.x` | Set in Project Settings $\to$ General. |

### 3.2 Vercel Environment Variables Configuration
In Vercel Project Dashboard $\to$ **Settings** $\to$ **Environment Variables**, configure the following variables across all target environments (**Production**, **Preview**, and **Development**):

| Variable Name | Environment Scope | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Production, Preview, Dev | `https://swiggy-resolveai-api.onrender.com/api/v1` | Public backend base URL used by browser fetch calls. Must use HTTPS in production. |
| `BACKEND_URL` | Production, Preview, Dev | `https://swiggy-resolveai-api.onrender.com` | Internal target URL used by Next.js server-side reverse-proxy rewrites (`/api/:path*`). |

### 3.3 Next.js Rewrites & Reverse Proxy Verification
The frontend includes built-in reverse-proxy rewrites in [`frontend/next.config.ts`](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/frontend/next.config.ts):

```typescript
async rewrites() {
  const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:8000";
  return [
    {
      source: "/api/:path*",
      destination: `${backendUrl}/api/:path*`,
    },
  ];
}
```

This configuration guarantees that API requests to `/api/v1/...` made from the frontend domain are transparently forwarded to the backend container, eliminating CORS hurdles in environments where direct cross-origin requests are blocked.

---

## 4. Backend Deployment Guide (Render / Railway / AWS)

### 4.1 Deployment using `backend/Dockerfile`
The backend deploys directly as a Docker Web Service on **Render** (or Railway / AWS App Runner):

1. **Create Web Service**:
   - Environment: `Docker`
   - Context Directory: `.` (repository root)
   - Dockerfile Path: `backend/Dockerfile`
   - Plan: Standard (minimum 1GB RAM recommended for ML inference and scikit-learn).
2. **Health Check Path**:
   - Path: `/api/v1/health/live`
   - Port: `8000`
3. **Backend Environment Variables**:

| Variable Name | Required Value | Notes |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Enforces production security controls. |
| `EXECUTION_MODE` | `SHADOW` | **CRITICAL**: `SIMULATION` is blocked in prod; `LIVE` is blocked everywhere. |
| `DATABASE_URL` | `postgresql+psycopg2://<user>:<password>@<host>:5432/<dbname>?sslmode=require` | Hosted PostgreSQL connection string. |
| `AUTH_SECRET_KEY` | `<your-generated-32-char-hex-secret>` | Generate via `openssl rand -hex 32`. |
| `BACKEND_CORS_ORIGINS` | `https://<your-project>.vercel.app` | Exact URL of your deployed Vercel frontend. |
| `GEMINI_API_KEY` | `AIzaSy...` (Optional) | Key from Google AI Studio. Fallback active if omitted. |
| `GEMINI_MODEL_NAME` | `gemini-3.5-flash` | Supported official model (routed to current flash generation). |
| `LOG_LEVEL` | `INFO` | Standard logging verbosity. |

### 4.2 Runtime Resource Profiling & Render Instance Sizing

Empirical runtime profiling of the backend Docker container establishes:

| Metric | Measured Baseline | Operational Impact |
| :--- | :---: | :--- |
| **Model Artifacts on Disk** | **1.99 MB** (8 files) | Deserialized on startup from `data/artifacts/models/phase_2_5/`. |
| **Container Cold Startup** | **4.2s – 15.3s** | Includes Python import tree, database engine setup, and LightGBM model loading. |
| **Traced Python Heap (Idle)** | **146.55 MB** | In-memory FastAPI routers, SQLAlchemy connection pools, and loaded estimators. |
| **Traced Python Heap (Inference)** | **147.76 MB** | Peak memory during Task A multi-quantile predictions and Task C2 landmark scoring. |
| **OS Working Set (RSS)** | **~250 MB – 350 MB** | Real OS memory footprint per worker process. |

#### Hardware Recommendations:
- **Minimum Viable Plan**: **Render Starter (512 MB RAM, 0.5 vCPU)**. Sufficient for single-user testing, evaluation scripts, and non-concurrent staging.
- **Recommended Production Plan**: **Render Standard (1 GB – 2 GB RAM, 1 vCPU)**. Provides head-room for concurrent LangGraph multi-agent synthesis, multiple worker processes, and spike handling without risk of out-of-memory container termination.

#### Docker Hardening & Optimization:
- **OpenMP Native Support**: `libgomp1` is explicitly installed in [`backend/Dockerfile`](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/backend/Dockerfile) to guarantee native CPU parallelism for LightGBM.
- **Context Exclusion**: Root [`.dockerignore`](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/.dockerignore) strips raw datasets (`data/raw/` ~85MB), test artifacts (`.pytest_cache`), git history (`.git`), and the frontend workspace, keeping Docker context uploads under 10 MB.
- **Health Probes**: Liveness probe configured at `GET /api/v1/health/live` (lightweight check); readiness probe configured at `GET /api/v1/health/ready` (validates database connectivity and model registry status).

### 4.3 Database Migration Execution (Alembic)
Once the database is provisioned and `DATABASE_URL` is configured, apply database migrations:

```bash
# Run migrations using the project's alembic configuration
alembic -c backend/alembic.ini upgrade head
```

In automated CI/CD pipelines or Render build commands, migrations can be run as a pre-deploy command:
```bash
python -m alembic -c backend/alembic.ini upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

> [!TIP]
> **Neon Lakebase Postgres Integration Notes**:
> - **Pooled vs. Direct Routing**: The web service uses the connection pooler URL (`-pooler`) for high-concurrency request handling. `backend/alembic/env.py` automatically routes schema migrations to the direct unpooled endpoint, eliminating PgBouncer startup parameter limitations.
> - **Alembic Version Identifier Length**: `backend/alembic/env.py` enforces `VARCHAR(64)` on the `alembic_version` table, preventing PostgreSQL string truncation errors on descriptive migration revisions.
> - **Standard OS DNS Resolution**: Standard OS-level DNS resolution is preserved with pure system resolution and standard SQLAlchemy connection pooling (`pool_size=10`, `max_overflow=20`, `pool_recycle=1800`, `pool_pre_ping=True`).
> - **Mandatory Password Rotation**: Before public release, rotate the `neondb_owner` role password in the Neon Console and update production environment variables.

---

## 5. Security & Operational Release Invariants

1. **`LIVE` Execution Mode is Permanently Blocked**:
   The startup validator in `backend/app/core/config.py` explicitly throws `ValueError: LIVE execution mode is strictly disabled by safety governance policy.` if configured.
2. **`SIMULATION` Mode is Blocked in Production**:
   Configuring `ENVIRONMENT=production` and `EXECUTION_MODE=SIMULATION` triggers a fatal startup crash. Production operations must run in `SHADOW` mode.
3. **Secret Key Length Validation**:
   `AUTH_SECRET_KEY` must have a length $\ge 32$ characters and must differ from the development default.
4. **Development Token Generator Disabled**:
   `POST /api/v1/auth/dev-token` automatically returns `HTTP 403 Forbidden` when `ENVIRONMENT` is `staging` or `production`.
5. **No Database Secrets Exposed to Frontend**:
   All database URIs and JWT secrets reside exclusively in backend environment variables.
