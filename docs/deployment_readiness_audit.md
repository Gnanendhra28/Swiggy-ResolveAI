# Swiggy ResolveAI — DevOps Deployment Readiness Audit

- **Date**: November 19, 2026
- **Auditor**: Senior DevOps & Platform Engineer
- **Status**: **PRE-DEPLOYMENT CODE & CONFIGURATION AUDIT**
- **Target Deployment Platform**: Vercel (Frontend) + Container Hosting (Backend) + Hosted PostgreSQL

---

## 1. Executive Summary

This DevOps audit provides a complete evaluation of the Swiggy ResolveAI repository for cloud deployment. The inspection verified that:
1. **Frontend**: The Next.js 16 frontend is fully decoupled, compiles cleanly with Turbopack, and is **100% ready for Vercel deployment** with zero architectural changes.
2. **Backend**: The FastAPI backend contains heavy machine learning dependencies (`scipy`, `pandas`, `lightgbm`, `shap`, `scikit-learn`, `langgraph`, model binaries) exceeding Vercel's 250 MB serverless uncompressed bundle size limit. The backend is configured for deployment on a container runtime (Render, Railway, AWS App Runner) using the repository's production-ready [`backend/Dockerfile`](file:///c:/Users/ASUS/Desktop/Swiggy%20ResolveAI/backend/Dockerfile).
3. **Database**: PostgreSQL 15+ is fully supported via `psycopg2-binary>=2.9.9` and SQLAlchemy connection pooling. Alembic migrations execute cleanly.
4. **Redis**: An exhaustive code inspection confirms **zero Redis dependencies**. Redis is not required.
5. **AI Integration**: Gemini model configuration has been updated to the active Flash candidate `gemini-3.5-flash` (replacing the deprecated `gemini-1.5-flash`), compatible with `langchain-google-genai` and automatically routed to current flash generation. Deterministic rule-based fallback is fully preserved when `GEMINI_API_KEY` is omitted.
6. **Safety Governance**: Production execution requires `SHADOW` mode. `SIMULATION` is prohibited in production, and `LIVE` execution is permanently blocked across all environments.

---

## 2. Codebase & Configuration Audit

### 2.1 Backend Settings (`backend/app/core/config.py`)
- Pydantic Settings class `Settings` defines:
  - `ENVIRONMENT`: Validated to one of `{"development", "testing", "staging", "production"}`.
  - `EXECUTION_MODE`: Validated to one of `{"SIMULATION", "SHADOW", "LIVE"}`.
  - Cross-field validation:
    - `ENVIRONMENT="production"` with `EXECUTION_MODE="SIMULATION"` raises `ValueError`.
    - `EXECUTION_MODE="LIVE"` raises `ValueError` in all environments.
    - `ENVIRONMENT in ("staging", "production")` with default dev key or length $< 32$ raises `ValueError`.
- **JWT Variable Name Verification**:
  - The codebase uses `AUTH_SECRET_KEY`, **not** `JWT_SECRET_KEY`.
  - The codebase uses `AUTH_TOKEN_EXPIRE_MINUTES`, **not** `ACCESS_TOKEN_EXPIRE_MINUTES`.
  - The codebase uses `AUTH_ALGORITHM`, `AUTH_ISSUER`, and `AUTH_AUDIENCE`.
  - All token creation and verification functions in `backend/app/core/auth.py` strictly consume these exact variables.

### 2.2 Redis Dependency Verification
- **Code Search**: `git grep -i "redis"` across all application code returned zero matches.
- **Dependencies**: `backend/requirements.txt` does not include `redis` or `aioredis`.
- **Orchestration**: `docker-compose.yml` does not define a Redis container.
- **Verdict**: **Redis is NOT required**. The platform uses in-memory policy tracking and transactional PostgreSQL audit records (`RecoveryExecutionAudit.idempotency_key`) to enforce cooldowns and idempotency.

### 2.3 Gemini API & Model Verification
- In `backend/app/core/config.py`, `GEMINI_MODEL_NAME` defaults to `"gemini-3.5-flash"`.
- `CustomerResolutionAgent` in `backend/app/agents/customer_resolution.py` consumes `settings.GEMINI_MODEL_NAME` and `settings.GEMINI_TIMEOUT_SECONDS` via `ChatGoogleGenerativeAI`.
- Supported active models: `gemini-3.5-flash` (recommended default, automatically routed to current flash generation in Google AI Studio), `gemini-3.6-flash`, `gemini-3.8-flash`, and `gemini-2.0-flash`.
- Deprecation Note: `gemini-1.5-flash` has been deprecated by Google and is replaced by `gemini-3.5-flash`.
- Fallback: If `GEMINI_API_KEY` is omitted or if LLM call exceeds 10s, the system gracefully and deterministically falls back to the rule-based synthesis engine with zero 500 errors.

### 2.4 Database Drivers & Migrations
- **Driver**: `psycopg2-binary>=2.9.9` is present in `backend/requirements.txt`.
- **SQLAlchemy URL Schemes**: Supported schemes are `postgresql+psycopg2://` and `postgresql://`.
- **Connection Pooling**: `DB_POOL_SIZE` (10), `DB_MAX_OVERFLOW` (20), `DB_POOL_TIMEOUT` (30s), and `DB_POOL_RECYCLE` (1800s) are configured on PostgreSQL connections with `pool_pre_ping=True`.
- **Alembic**: 5 sequential migrations verified in `backend/alembic/versions/`. Migrations read `settings.DATABASE_URL` directly.

### 2.5 Runtime Profiling & Container Sizing
- **Model Binaries Size**: Exactly 1.99 MB (2,084,098 B) across 8 files in `data/artifacts/models/phase_2_5/`.
- **Container Build Context**: Root `.dockerignore` excludes 85MB of raw CSVs (`data/raw/`), git history (`.git`), `node_modules`, and frontend files.
- **Native Dependencies**: `libgomp1` added to `backend/Dockerfile` to supply OpenMP runtime for LightGBM C++ core.
- **Python Memory Footprint**: 135.90 MB (heap on startup) $\to$ 146.55 MB (heap with models loaded) $\to$ 147.76 MB (peak inference heap).
- **Process RSS**: ~250–350 MB operating system working set under active request handling.
- **Instance Sizing**: Render Starter (512 MB RAM, 0.5 vCPU) is the minimum viable baseline; Render Standard (1 GB to 2 GB RAM, 1 vCPU) is recommended for production concurrency to eliminate OOM termination risk.

---

## 3. Frontend & Vercel Compatibility Audit

### 3.1 Next.js 16 & Turbopack
- Framework: Next.js 16.4.6 with Turbopack and React 19.
- App Router: 9 static and dynamic routes compiled with zero errors.
- Monorepo Root Directory: `frontend` (configured in Vercel project settings).
- Build command: `npm run build`.
- Install command: `npm install`.

### 3.2 Client-Side & Server-Side API Routing
- `frontend/src/lib/api.ts` implements dynamic base URL resolution:
  1. `NEXT_PUBLIC_API_URL` if explicitly set (client and server).
  2. Browser fallback to `window.location.origin + '/api/v1'`.
  3. Server fallback to `BACKEND_URL + '/api/v1'`.
- `frontend/next.config.ts` configures server-side reverse-proxy rewrites:
  - `/api/:path*` $\to$ `${process.env.BACKEND_URL || 'http://127.0.0.1:8000'}/api/:path*`.
- Stream safety: `handleResponse()` reads `await res.text()` once, preventing `body stream already read` errors.

### 3.3 Security & Secret Isolation
- Client Bundle Inspection: Only `NEXT_PUBLIC_API_URL` is exposed to the browser.
- Secrets Protected: `DATABASE_URL`, `AUTH_SECRET_KEY`, and `GEMINI_API_KEY` do not carry `NEXT_PUBLIC_` and are never bundled into client JavaScript.
- `.gitignore`: Both root `.gitignore` and `frontend/.gitignore` ignore all `.env*` files except `.env.example` and `.env*.example`.

---

## 4. Verification Test & Build Results

All tests and compilation checks have been executed and verified:

| Verification Target | Command | Duration | Exit Code | Result |
| :--- | :--- | :---: | :---: | :--- |
| **Backend Test Suite** | `python -m pytest backend/tests/ -q` | 31.79s | `0` | **207 passed**, 0 failed |
| **Agent Unit Tests** | `python -m pytest backend/tests/test_phase_3_agents.py` | 1.34s | `0` | **15 passed**, 0 failed |
| **Frontend Production Build** | `npm --prefix frontend run build` | 7.60s | `0` | **Clean build** (9/9 routes static/hybrid) |
| **End-to-End Demo Script** | `python scripts/demo_runner.py` | 1.80s | `0` | **8/8 operational steps passed** |

---

## 5. Deployment Readiness Verdict

| Component | Target Platform | Deployment Status | Remaining Pre-requisites |
| :--- | :--- | :---: | :--- |
| **Frontend** | Vercel (Next.js 16) | **READY_FOR_DEPLOYMENT** | Set Root Directory to `frontend`. Configure `NEXT_PUBLIC_API_URL` and `BACKEND_URL`. |
| **Backend** | Container Host (Render / Railway) | **READY_FOR_DEPLOYMENT** | Build using `backend/Dockerfile`. Configure `DATABASE_URL`, `AUTH_SECRET_KEY`, `BACKEND_CORS_ORIGINS`. |
| **Database** | Hosted PostgreSQL 15+ | **READY_FOR_DEPLOYMENT** | Provision database on Neon/Supabase/Render. Run `alembic upgrade head`. |
| **Security Mode** | Production Runtime | **SHADOW_APPROVED** | `EXECUTION_MODE=SHADOW` verified. `LIVE` execution strictly disabled. |
