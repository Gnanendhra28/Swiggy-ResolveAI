from fastapi import APIRouter
from backend.app.api.routes import (
    health,
    orders,
    simulation,
    ingestion,
    intelligence,
    simulation_experiments,
    auth,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(orders.router)
api_router.include_router(simulation.router)
api_router.include_router(ingestion.router)
api_router.include_router(intelligence.router)
api_router.include_router(simulation_experiments.router)
api_router.include_router(auth.router)

