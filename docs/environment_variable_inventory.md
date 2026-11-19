# Swiggy ResolveAI — Environment Variable Inventory

- **Date**: November 19, 2026
- **Auditor**: Senior DevOps & Platform Engineer
- **Status**: **CODE-VERIFIED INVENTORY**
- **Authority**: Evaluated directly against `backend/app/core/config.py`, `backend/app/core/auth.py`, `backend/app/agents/customer_resolution.py`, and `frontend/src/lib/api.ts`.

---

## 1. Master Environment Variable Inventory

| Variable Name | Used By | Required? | Type / Secrecy | Default Value (Dev) | Purpose | Where to Obtain |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **`ENVIRONMENT`** | Backend (`Settings`, `auth`, `recovery_executor`) | **Required** in Prod | Public | `"development"` | Active runtime mode (`development`, `testing`, `staging`, `production`). In production, enforces strict secret validation, disables dev token generator, and blocks `SIMULATION` mode. | Set via deployment dashboard (`"production"` or `"staging"`). |
| **`EXECUTION_MODE`** | Backend (`Settings`, `recovery_executor`) | **Required** in Prod | Public | `"SIMULATION"` | Autonomous execution boundary (`SIMULATION`, `SHADOW`, `LIVE`). In production, `SIMULATION` is rejected at startup, and `LIVE` is strictly disabled across all environments. Production requires `"SHADOW"`. | Set via deployment dashboard (`"SHADOW"` for production). |
| **`DATABASE_URL`** | Backend (`Settings`, `session.py`, `alembic`) | **Required** | **Secret** | `"sqlite:///./resolveai.db"` | SQLAlchemy database connection string. In production, must be an enterprise PostgreSQL 15+ URI using the `postgresql+psycopg2://` scheme. | Hosted PostgreSQL provider (Neon, Supabase, Render, Railway, AWS RDS). |
| **`AUTH_SECRET_KEY`** | Backend (`Settings`, `auth.py`) | **Required** in Prod | **Secret** | `"resolveai-insecure-dev-secret-key..."` | HMAC-SHA256 cryptographic secret key used for signing and verifying JWT bearer tokens. In `staging`/`production`, must be non-default with minimum 32 characters. | Cryptographically generate: `openssl rand -hex 32`. |
| **`BACKEND_CORS_ORIGINS`** | Backend (`Settings`, `main.py`) | **Required** in Prod | Public | `http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000` | Comma-separated list or JSON array of permitted frontend origins allowed to make browser cross-origin requests. | Vercel production frontend domain (`https://<project>.vercel.app`). |
| **`NEXT_PUBLIC_API_URL`** | Frontend (`api.ts`) | **Required** on Vercel | Public | `http://localhost:8000/api/v1` | Public backend base URL consumed by client-side browser fetches. Must use `https://` in production. | Deployed backend URL + `/api/v1` (`https://<backend-host>/api/v1`). |
| **`BACKEND_URL`** | Frontend (`next.config.ts`, `api.ts`) | Optional (Recommended) | Public/Server | `http://127.0.0.1:8000` | Target URL for Next.js server-side reverse-proxy rewrites (`/api/:path*`) and Server-Side Rendering (SSR). | Deployed backend URL (`https://<backend-host>`). |
| **`GEMINI_API_KEY`** | Backend (`Settings`, `CustomerResolutionAgent`) | Optional | **Secret** | `None` / omitted | Google Gemini API key used by Customer Resolution Agent for structured root-cause synthesis. If omitted, automated deterministic fallback engine is used. | Google AI Studio (`https://aistudio.google.com/app/apikey`). |
| **`GEMINI_MODEL_NAME`** | Backend (`Settings`, `CustomerResolutionAgent`) | Optional | Public | `"gemini-1.5-flash"` | Target Google Gemini model identifier. Supported official models: `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.0-flash`. | Google AI Studio documentation. |
| **`GEMINI_TIMEOUT_SECONDS`** | Backend (`Settings`, `CustomerResolutionAgent`) | Optional | Public | `10.0` | Maximum timeout in seconds before aborting Gemini call and triggering deterministic rule fallback. | DevOps configuration (default: 10s). |
| **`AUTH_ALGORITHM`** | Backend (`Settings`, `auth.py`) | Optional | Public | `"HS256"` | Cryptographic signature algorithm for JWT bearer tokens. | Codebase default (`"HS256"`). |
| **`AUTH_ISSUER`** | Backend (`Settings`, `auth.py`) | Optional | Public | `"swiggy-resolveai"` | Expected JWT issuer claim (`iss`). Verified on every incoming bearer token. | Codebase default. |
| **`AUTH_AUDIENCE`** | Backend (`Settings`, `auth.py`) | Optional | Public | `"resolveai-ops"` | Expected JWT audience claim (`aud`). Verified on every incoming bearer token. | Codebase default. |
| **`AUTH_TOKEN_EXPIRE_MINUTES`** | Backend (`Settings`, `auth.py`) | Optional | Public | `120` | JWT bearer token lifetime in minutes (2 hours). | DevOps configuration. |
| **`DB_POOL_SIZE`** | Backend (`Settings`, `session.py`) | Optional | Public | `10` | SQLAlchemy base connection pool size (applies to PostgreSQL only). | DevOps configuration. |
| **`DB_MAX_OVERFLOW`** | Backend (`Settings`, `session.py`) | Optional | Public | `20` | SQLAlchemy max overflow connections beyond pool size during surges. | DevOps configuration. |
| **`DB_POOL_TIMEOUT`** | Backend (`Settings`, `session.py`) | Optional | Public | `30` | Seconds to wait before throwing a connection pool timeout error. | DevOps configuration. |
| **`DB_POOL_RECYCLE`** | Backend (`Settings`, `session.py`) | Optional | Public | `1800` | Seconds after which idle PostgreSQL connections are recycled (30 min). | DevOps configuration. |
| **`REQUEST_TIMEOUT_SECONDS`** | Backend (`Settings`, `middleware`) | Optional | Public | `30.0` | Global HTTP request execution timeout in seconds. | DevOps configuration. |
| **`LOG_LEVEL`** | Backend (`Settings`, `logging`) | Optional | Public | `"INFO"` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). | DevOps configuration. |
| **`PROJECT_NAME`** | Backend (`Settings`) | Optional | Public | `"Swiggy ResolveAI"` | Human-readable title displayed in Swagger UI and OpenAPI schemas. | Codebase default. |
| **`VERSION`** | Backend (`Settings`) | Optional | Public | `"0.1.0"` | SemVer release version of the platform. | Codebase default. |
| **`API_V1_STR`** | Backend (`Settings`) | Optional | Public | `"/api/v1"` | Base route prefix for API endpoints. | Codebase default. |
| **`ML_ARTIFACTS_DIR`** | Backend (`Settings`, `ml_inference.py`) | Optional | Public | `"data/artifacts/models/phase_2_5"` | Filesystem path to serialized Phase 2.5 LightGBM models and calibrator. | Container filesystem. |

---

## 2. Detailed Variable Categorization & Findings

### 2.1 Required Production Variables
These variables **must be explicitly provisioned** in production:
1. **`ENVIRONMENT=production`**: Triggers mandatory production security constraints in `backend/app/core/config.py`.
2. **`EXECUTION_MODE=SHADOW`**: Mandatory for production. Setting `EXECUTION_MODE=SIMULATION` in production causes a fatal startup failure; `EXECUTION_MODE=LIVE` is blocked across all environments.
3. **`DATABASE_URL`**: Must point to an active hosted PostgreSQL instance (`postgresql+psycopg2://...`). SQLite is not permitted in production.
4. **`AUTH_SECRET_KEY`**: Must be a custom, cryptographically generated secret with at least 32 characters. Using the dev default fails startup validation.
5. **`BACKEND_CORS_ORIGINS`**: Must include the exact HTTPS origin of the deployed Vercel frontend.
6. **`NEXT_PUBLIC_API_URL`**: Configured in Vercel to point to `https://<deployed-backend-host>/api/v1`.

### 2.2 Optional Variables with Safe Defaults
- `GEMINI_API_KEY`: If not provided, `CustomerResolutionAgent` automatically degrades to deterministic rule synthesis. The application functions completely without an API key.
- `GEMINI_MODEL_NAME`: Defaults to `"gemini-1.5-flash"`.
- `GEMINI_TIMEOUT_SECONDS`: Defaults to `10.0` seconds.
- `BACKEND_URL`: Used for Next.js SSR and server-side rewrites.
- `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`: Defaults are tuned for PostgreSQL micro/standard instances.
- `LOG_LEVEL`: Defaults to `"INFO"`.

### 2.3 Unused, Obsolete & Conflicting Variables
The audit identified several variables that have appeared in discussions or generic examples but **do not exist or are not used** by the codebase:

| Variable Name | Status | Verified Codebase Finding | Required Action |
| :--- | :---: | :--- | :--- |
| `JWT_SECRET_KEY` | **OBSOLETE / INVALID** | The application code exclusively reads `AUTH_SECRET_KEY` in `backend/app/core/config.py` and `backend/app/core/auth.py`. | **Do NOT use `JWT_SECRET_KEY`**. Use `AUTH_SECRET_KEY`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | **OBSOLETE / INVALID** | The application code exclusively reads `AUTH_TOKEN_EXPIRE_MINUTES`. | **Do NOT use `ACCESS_TOKEN_EXPIRE_MINUTES`**. Use `AUTH_TOKEN_EXPIRE_MINUTES`. |
| `REDIS_URL` / `REDIS_HOST` | **UNUSED** | The codebase has **zero Redis dependencies**. Redis is not in `requirements.txt`, not in `config.py`, and not imported in any Python file. | **Do NOT provision Redis**. It is not required. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | **LOCAL ONLY** | These variables are used exclusively in `docker-compose.yml` for local container orchestration. The FastAPI backend does not read them directly; it consumes `DATABASE_URL`. | Use `DATABASE_URL` directly in cloud deployments. |

### 2.4 Critical Security Boundary: `NEXT_PUBLIC_` Prefix Rules
Next.js automatically exposes any environment variable prefixed with `NEXT_PUBLIC_` to the client-side browser JavaScript bundle.

> [!CAUTION]
> **STRICT SECURITY INVARIANT**: The following variables **MUST NEVER** carry the `NEXT_PUBLIC_` prefix:
> - `DATABASE_URL` (Database credentials)
> - `AUTH_SECRET_KEY` (JWT signature secret)
> - `GEMINI_API_KEY` (Google AI Studio API key)
> - Any database passwords, API tokens, or server secrets.
> 
> The **ONLY** variable permitted with the `NEXT_PUBLIC_` prefix is:
> - `NEXT_PUBLIC_API_URL`: Points to the public backend HTTP endpoint.

---

## 3. Gemini Model Identification & Support Audit

Official Google AI Studio documentation defines the following model naming convention:
- **`gemini-1.5-flash`**: High-frequency, low-latency, economical model supporting structured output (`with_structured_output`). **(Recommended default)**.
- **`gemini-1.5-pro`**: Higher capacity reasoning model for deep analysis.
- **`gemini-2.0-flash`**: New generation multimodal model (current preview / GA).
- **`gemini-2.0-flash-lite`**: Ultra-lightweight model.

> [!WARNING]
> Identifiers such as `gemini-2.5-flash` and `gemini-3.5-flash` **do not exist** in Google's official Gemini API catalog. Calling the API with non-existent identifiers causes a runtime `NotFound` error. Ensure `GEMINI_MODEL_NAME` is set to `gemini-1.5-flash` or `gemini-2.0-flash`.
