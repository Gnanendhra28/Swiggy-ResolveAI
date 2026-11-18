from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.simulation import (
    SimulationGenerateRequest,
    SimulationGenerateResponse,
    SimulationInjectEventRequest,
)
from backend.app.schemas.order_event import OrderEventResponse
from backend.app.simulation.scenarios import SCENARIO_METADATA, ScenarioType
from backend.app.services.simulation_service import SimulationService

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.get("/scenarios", response_model=Dict[str, Any])
def list_simulation_scenarios():
    """List all available demo simulation scenarios with their operational descriptions."""
    return {
        "scenarios": [
            {
                "id": s.value,
                "title": SCENARIO_METADATA[s]["title"],
                "description": SCENARIO_METADATA[s]["description"],
                "expected_status": SCENARIO_METADATA[s]["expected_status"],
                "has_delays": SCENARIO_METADATA[s]["has_delays"],
            }
            for s in ScenarioType
        ]
    }


@router.post("/generate", response_model=SimulationGenerateResponse)
def generate_simulation_orders(
    request: SimulationGenerateRequest,
    db: Session = Depends(get_db),
):
    """
    Generate synthetic demo orders and chronological events for a specific operational scenario.
    Marked explicitly as SYNTHETIC.
    """
    return SimulationService.generate_simulation(db=db, request=request)


@router.post("/events", response_model=OrderEventResponse)
def inject_simulation_event(
    request: SimulationInjectEventRequest,
    db: Session = Depends(get_db),
):
    """
    Inject a dynamic operational event into an existing simulated order.
    """
    event = SimulationService.inject_event(
        db=db,
        order_id=request.order_id,
        event_type=request.event_type,
        metadata=request.metadata,
        data_source=request.data_source,
    )
    return OrderEventResponse(
        id=event.id,
        order_id=event.order_id,
        event_type=event.event_type,
        event_timestamp=event.event_timestamp,
        metadata=event.event_metadata,
        data_source=event.data_source,
        created_at=event.created_at,
    )
