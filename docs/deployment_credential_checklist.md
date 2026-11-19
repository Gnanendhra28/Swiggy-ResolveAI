# Swiggy ResolveAI — Deployment Credential Acquisition Checklist

- **Date**: November 19, 2026
- **Auditor**: Senior DevOps & Application Security Engineer
- **Status**: **SECURITY COMPLIANCE & CREDENTIAL ACQUISITION PROTOCOL**

---

## 1. Master Credential Checklist

The following credentials must be acquired or generated manually by the system administrator before deploying Swiggy ResolveAI. **Never commit, share, or hardcode these values in repository files.**

| Credential Item | Provider / Source | Dashboard / Generation Method | Target Environment Variable | Required Action & Security Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Hosted PostgreSQL URI** | Cloud Database Provider (Neon, Supabase, Render, Railway, AWS RDS) | Provider Console $\to$ Database Settings $\to$ Connection String | `DATABASE_URL` (Backend Host) | Provision a PostgreSQL 15+ instance. Copy the connection string. Ensure the scheme is `postgresql+psycopg2://` (or `postgresql://`). Enable SSL (`sslmode=require`). **Never expose to frontend.** |
| **Application Auth Secret** | Local System (Internal Cryptographic Generation) | Terminal CLI: `openssl rand -hex 32` | `AUTH_SECRET_KEY` (Backend Host) | Generate a random 64-character hex string (32 bytes entropy). Must be $\ge 32$ characters and different from dev default. Store securely in backend host environment variables. |
| **Google Gemini API Key** | Google AI Studio | [Google AI Studio API Keys Console](https://aistudio.google.com/app/apikey) | `GEMINI_API_KEY` (Backend Host) | Click **Create API Key**. Restrict key to Gemini API. Copy to backend environment variables. Optional: if omitted, system automatically falls back to deterministic rule synthesis. |
| **Deployed Backend API URL** | Backend Hosting Provider (Render, Railway, AWS App Runner) | Provider Dashboard $\to$ Service Settings $\to$ Default URL | `NEXT_PUBLIC_API_URL` (Vercel Frontend) | Obtain HTTPS URL of deployed backend service (e.g., `https://swiggy-resolveai-api.onrender.com`), append `/api/v1`, and set as `NEXT_PUBLIC_API_URL` on Vercel. |
| **Backend Internal Service URL** | Backend Hosting Provider | Provider Dashboard $\to$ Service Settings $\to$ Default URL | `BACKEND_URL` (Vercel Frontend) | Set the bare HTTPS URL (without `/api/v1`) as `BACKEND_URL` on Vercel for Next.js server-side rewrites. |
| **Frontend Production URL** | Vercel | Vercel Project Dashboard $\to$ Settings $\to$ Domains | `BACKEND_CORS_ORIGINS` (Backend Host) | Copy the Vercel production domain (e.g., `https://swiggy-resolveai.vercel.app`) and configure it in the backend's `BACKEND_CORS_ORIGINS`. |
| **Redis URL / Host** | N/A (Not Required) | N/A | None | **NO ACTION REQUIRED**. The codebase has zero Redis dependencies. Do not provision a Redis cluster. |

---

## 2. Step-by-Step Acquisition Procedures

### 2.1 Generating the Application Authentication Secret (`AUTH_SECRET_KEY`)
The backend enforces that in `staging` and `production` environments, `AUTH_SECRET_KEY` must not match the hardcoded development default and must be at least 32 characters long.

Run **either** of the following commands in your secure terminal:

```bash
# Option A: OpenSSL (Recommended)
openssl rand -hex 32

# Option B: Python secrets module
python -c "import secrets; print(secrets.token_hex(32))"
```

*Security Guardrail*: Do not commit the generated secret to Git. Paste it directly into your backend hosting provider's environment variables dashboard.

---

### 2.2 Hosted PostgreSQL Database Acquisition (`DATABASE_URL`)

Choose any standard hosted PostgreSQL provider (PostgreSQL 15 or 16):

#### Option A: Neon (Serverless PostgreSQL)
1. Navigate to [Neon Console](https://console.neon.tech/).
2. Create a project named `swiggy-resolveai`.
3. In the project dashboard, select **Connection Details** $\to$ **Connection string**.
4. Select **SQLAlchemy** or **Connection Pooling**.
5. Copy the connection string. Ensure the scheme is formatted as:
   `postgresql+psycopg2://<user>:<password>@<ep-pooler-id>.neon.tech/<dbname>?sslmode=require`

#### Option B: Supabase
1. Navigate to [Supabase Console](https://supabase.com/dashboard).
2. Create a project named `swiggy-resolveai`.
3. Navigate to **Project Settings** $\to$ **Database** $\to$ **Connection String**.
4. Select **URI** and choose **Session Pooler** (port `5432` or `6543`).
5. Replace `[YOUR-PASSWORD]` with your actual database password:
   `postgresql+psycopg2://postgres.<project-ref>:[PASSWORD]@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require`

#### Option C: Render / Railway Managed PostgreSQL
1. Create a **PostgreSQL** resource in the same region as your web service.
2. Render/Railway provides an **Internal Database URL** for zero-latency VPC networking.
3. Replace the `postgres://` prefix with `postgresql+psycopg2://` if required by SQLAlchemy.

---

### 2.3 Google Gemini API Key Acquisition & Compromised Key Revocation Protocol

#### How to Revoke a Compromised Key
If an API key was previously pasted in a public chat, log, or git commit:
1. Open [Google AI Studio API Keys](https://aistudio.google.com/app/apikey).
2. Locate the compromised key in the list.
3. Click the **Delete** (trash icon) button immediately next to the key.
4. Confirm deletion. The revoked key becomes unusable immediately across all Google APIs.

#### Generating a Clean Replacement Key
1. In [Google AI Studio API Keys](https://aistudio.google.com/app/apikey), click **Create API Key**.
2. Select your Google Cloud project (or generate a free tier project).
3. Copy the newly generated key (`AIzaSy...`).
4. Paste it directly into the backend hosting environment variables as `GEMINI_API_KEY`.
5. Verify model configuration: Set `GEMINI_MODEL_NAME=gemini-1.5-flash` (or `gemini-2.0-flash`). **Never use non-existent identifiers like `gemini-2.5-flash` or `gemini-3.5-flash`.**

---

### 2.4 Backend Deployed URL & Vercel CORS Integration

1. Once the backend container is deployed on Render/Railway, copy its assigned public HTTPS URL:
   `https://swiggy-resolveai-backend.onrender.com`
2. In Vercel Project Settings $\to$ **Environment Variables**:
   - `NEXT_PUBLIC_API_URL`: `https://swiggy-resolveai-backend.onrender.com/api/v1`
   - `BACKEND_URL`: `https://swiggy-resolveai-backend.onrender.com`
3. In Backend Hosting Settings $\to$ **Environment Variables**:
   - `BACKEND_CORS_ORIGINS`: `https://swiggy-resolveai.vercel.app,http://localhost:3000`

---

## 3. Credential Security Guardrails & Verification Rules

- [x] **No Hardcoded Secrets**: Scan confirmed zero credentials in `.env.example`, `.env.*.example`, or committed Git files.
- [x] **Git Ignored**: Root `.env` and `frontend/.env.local` are verified to be ignored by `.gitignore`.
- [x] **Zero Secret Leakage to Client Bundle**: `DATABASE_URL`, `AUTH_SECRET_KEY`, and `GEMINI_API_KEY` do not carry `NEXT_PUBLIC_` and are never accessible to client browser bundles.
- [x] **Strict Invariant**: `EXECUTION_MODE` is set to `SHADOW` in production. `LIVE` execution is permanently blocked across all environments.
