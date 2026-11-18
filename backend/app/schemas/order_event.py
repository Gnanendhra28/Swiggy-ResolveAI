from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict, Field


class OrderEventBase(BaseModel):
    event_type: str
    event_timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata")
    data_source: str = "SYNTHETIC"


class OrderEventCreate(BaseModel):
    order_id: str
    event_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    event_timestamp: datetime = Field(default_factory=datetime.utcnow)
    data_source: str = "SYNTHETIC"


class OrderEventResponse(BaseModel):
    id: str
    order_id: str
    event_type: str
    event_timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="event_metadata")
    data_source: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
