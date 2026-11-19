# Swiggy ResolveAI — Environment Configuration Guide

## 1. Overview
This guide provides an exhaustive configuration inventory for the Swiggy ResolveAI platform across backend and frontend environments. Every environment variable used by the application is documented with its purpose, default value, secrecy level, and source component.

---

## 2. Environment Variable Inventory

| Variable Name | Required? | Secret? | Component | Safe Dev Default | Description & Instructions |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `PROJECT_NAME` | Optional | No | Backend (`Settings`) | `"Swiggy ResolveAI"` | Human-readable title for application and OpenAPI documentation. |
| `VERSION` | Optional | No | Backend (`Settings`) | `"0.1.0"` | SemVer release version of the platform. |
| `API_V1_STR` | Optional | No | Backend (`Settings`) | `"/api/v1"` | Base prefix for all REST API endpoints. |
| `ENVIRONMENT` | Optional | No | Backend (`Settings`) | `"development"` | Active runtime mode: `development`, `testing`, `staging`, or `production`. Validated on startup. |
| `EXECUTION_MODE` | Optional | No | Backend (`Settings`) | `"SIMULATION"` | Recovery execution mode: `SIMULATION` (permitted only in non-production; rejected at startup in `production`), `SHADOW` (inference only, action execution rejected with 403), or `LIVE` (fails startup safely across all environments). |
| `AUTH_SECRET_KEY` | **Required** in Prod | **Yes** | Backend (`auth`) | `"resolveai-insecure-dev-secret-key-change-in-production-12345678"` | Cryptographic HMAC-SHA256 secret key for signing bearer tokens. In `staging` and `production`, must be non-default with minimum 32 characters. |
| `AUTH_ALGORITHM` | Optional | No | Backend (`auth`) | `"HS256"` | Cryptographic signature algorithm for JWT bearer tokens. |
| `AUTH_ISSUER` | Optional | No | Backend (`auth`) | `"swiggy-resolveai"` | Expected token issuer claim (`iss`). Verified on every incoming bearer token. |
| `AUTH_AUDIENCE` | Optional | No | Backend (`auth`) | `"resolveai-ops"` | Expected token audience claim (`aud`). Verified on every incoming bearer token. |
| `AUTH_TOKEN_EXPIRE_MINUTES` | Optional | No | Backend (`auth`) | `120` | Token expiration duration in minutes (2 hours). |
| `LOG_LEVEL` | Optional | No | Backend (`logging`) | `"INFO"` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. |
| `DATABASE_URL` | **Required** | **Yes** (in Prod) | Backend (`database`) | `sqlite:///./resolveai.db` | SQLAlchemy connection string. For PostgreSQL: `postgresql+psycopg2://user:pass@host:5432/db`. |
| `DB_POOL_SIZE` | Optional | No | Backend (`database`) | `10` | Base connection pool size for PostgreSQL connections. |
| `DB_MAX_OVERFLOW` | Optional | No | Backend (`database`) | `20` | Max overflow connections above pool size during traffic surges. |
| `DB_POOL_TIMEOUT` | Optional | No | Backend (`database`) | `30` | Seconds to wait before timing out when obtaining a connection from pool. |
| `DB_POOL_RECYCLE` | Optional | No | Backend (`database`) | `1800` | Seconds (30 min) after which stale connections are recycled. |
| `REQUEST_TIMEOUT_SECONDS` | Optional | No | Backend (`middleware`) | `30.0` | Global HTTP request execution timeout in seconds. |
| `BACKEND_CORS_ORIGINS` | Optional | No | Backend (`main`) | `http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000` | Comma-separated list or JSON array of allowed frontend origins for CORS. |
| `GEMINI_API_KEY` | Optional | **Yes** | AI Agents (`CustomerResolution`) | `None` / omitted | Google Gemini API key. If absent, system gracefully falls back to deterministic rule synthesis. Obtain via Google AI Studio. |
| `GEMINI_MODEL_NAME` | Optional | No | AI Agents (`CustomerResolution`) | `"gemini-1.5-flash"` | Target Gemini model identifier for structured resolution synthesis. |
| `GEMINI_TIMEOUT_SECONDS`| Optional | No | AI Agents (`CustomerResolution`) | `10.0` | Max timeout for Gemini API calls before triggering deterministic fallback. |
| `ML_ARTIFACTS_DIR` | Optional | No | ML Platform (`MLInferenceService`) | `"data/artifacts/models/phase_2_5"` | Relative or absolute path to serialized Phase 2.5 models and metadata. |
| `POSTGRES_USER` | Optional | No | Docker Compose | `postgres` | Username for containerized PostgreSQL instance. |
| `POSTGRES_PASSWORD` | Optional | **Yes** | Docker Compose | `postgres` | Password for containerized PostgreSQL instance. |
| `POSTGRES_DB` | Optional | No | Docker Compose | `resolveai` | Database name for containerized PostgreSQL instance. |
| `NEXT_PUBLIC_API_URL` | **Required** | No | Frontend (Next.js) | `http://localhost:8000/api/v1` | Public backend base URL consumed by client-side browser fetches. |
| `BACKEND_URL` | Optional | No | Frontend (Next.js) | `http://localhost:8000` | Server-side backend base URL consumed by Next.js server components. |

---

## 3. Environment Separation

### 3.1 Local Development
For standalone local development, the backend defaults to SQLite (`resolveai.db`) and requires zero manual environment configuration. The frontend uses `http://localhost:8000/api/v1`.

### 3.2 Testing (`ENVIRONMENT=testing`)
Testing harnesses use in-memory SQLite (`sqlite:///:memory:`) or transient test databases (`sqlite:///./test_ci.db`) to ensure complete test isolation and zero data pollution.

### 3.3 Staging and Production (`ENVIRONMENT=production`)
In production environments:
1. `DATABASE_URL` must point to an enterprise PostgreSQL 15+ cluster.
2. `AUTH_SECRET_KEY` must be provisioned via a dedicated secret manager and rotated periodically. Setting the default dev secret key causes a fatal startup failure.
3. `EXECUTION_MODE` must be set to `SHADOW`. Setting `EXECUTION_MODE=SIMULATION` in production is rejected at startup. Setting `EXECUTION_MODE=LIVE` fails safely at startup across all environments.
4. `POST /api/v1/auth/dev-token` is automatically disabled (HTTP 403 Forbidden) when `ENVIRONMENT` is `staging` or `production`.
5. `BACKEND_CORS_ORIGINS` must be explicitly restricted to approved frontend domains (never `*`).
6. `GEMINI_API_KEY` must be provisioned via secret manager (AWS Secrets Manager, HashiCorp Vault, or Google Cloud Secret Manager).
7. `LOG_LEVEL` should be set to `INFO` or `WARNING`.

---

## 4. Execution Mode Enforcement Matrix

| Mode | Allowed Environments | Inference & Multi-Agent Investigation | Recovery Execution Behavior | Audit Log |
| :--- | :--- | :---: | :--- | :---: |
| `SIMULATION` | `development`, `testing`, `staging` | Enabled | Simulated state transitions & synthetic effects | Full Write |
| `SIMULATION` | `production` | **Blocked** | **Blocked** (Startup Fatal Error) | N/A |
| `SHADOW` | `staging`, `production`, `development` | Enabled | **Strictly Blocked** (HTTP 403 Forbidden returned to caller) | Action Blocked Record |
| `LIVE` | None (Governance Block) | Disabled | **Startup Fatal Guard** (System refuses to start) | N/A |

---

## 5. Secret Management Best Practices
1. **Never commit `.env` files**: All environment files containing secrets are ignored by `.gitignore`.
2. **Never prefix secrets with `NEXT_PUBLIC_`**: In Next.js, any variable prefixed with `NEXT_PUBLIC_` is baked into client-side JavaScript bundles and visible to all end users. Private API keys and database credentials must never use this prefix.
3. **Graceful Degraded Startup**: Missing `GEMINI_API_KEY` does not crash the server; the platform automatically activates its verified deterministic fallback engine.
