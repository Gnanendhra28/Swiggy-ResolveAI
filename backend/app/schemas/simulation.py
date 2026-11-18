from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.order import OrderSummaryResponse


class ScenarioType(str, Enum):
    NORMAL_ORDER = "NORMAL_ORDER"
    RESTAURANT_DELAY = "RESTAURANT_DELAY"
    DELIVERY_DELAY = "DELIVERY_DELAY"
    ASSIGNMENT_DELAY = "ASSIGNMENT_DELAY"
    FAILED_RECOVERY = "FAILED_RECOVERY"
    SUCCESSFUL_RECOVERY = "SUCCESSFUL_RECOVERY"


class SimulationGenerateRequest(BaseModel):
    scenario: ScenarioType = Field(
        default=ScenarioType.NORMAL_ORDER,
        description="The simulation scenario to run",
    )
    count: int = Field(
        default=1,
        ge=1,
        le=50,
        description="Number of simulated orders to generate (1-50)",
    )
    seed: Optional[int] = Field(
        default=None,
        description="Optional random seed for reproducible simulation generation",
    )
    custom_params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional custom scenario parameters",
    )


class SimulationGenerateResponse(BaseModel):
    demo_run_id: str
    scenario: ScenarioType
    generated_count: int
    order_ids: List[str]
    orders: List[OrderSummaryResponse]


class SimulationInjectEventRequest(BaseModel):
    order_id: str
    event_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    data_source: str = "SYNTHETIC"
