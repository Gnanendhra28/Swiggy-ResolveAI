from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.exceptions import register_exception_handlers
from backend.app.core.middleware import CorrelationIdMiddleware
from backend.app.database.session import SessionLocal, engine
from backend.app.database.base import Base
from backend.app.api.router import api_router
from backend.app.services.simulation_service import SimulationService


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    # Ensure tables are created if running directly (e.g. SQLite or fresh Postgres without Alembic)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created.")
        # Pre-seed initial reference entities if empty
        with SessionLocal() as db:
            SimulationService.ensure_synthetic_seed_entities(db)
            logger.info("Synthetic seed entities initialized.")
    except Exception as exc:
        logger.warning(f"Startup database initialization note: {exc}")

    yield

    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Independent proactive food delivery order intelligence & autonomous recovery platform.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Correlation ID and Request Timing Middleware
app.add_middleware(CorrelationIdMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
register_exception_handlers(app)

# Central API Router (v1)
app.include_router(api_router, prefix=settings.API_V1_STR)

# Top-level Health Probes (Interoperability for Cloud / Container Orchestrators)
from backend.app.api.routes.health import router as health_router
app.include_router(health_router, prefix="", tags=["System Health & Diagnostics"])


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
