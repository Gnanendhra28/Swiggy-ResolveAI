from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DeliveryPartnerBase(BaseModel):
    name: str
    availability_status: str = "AVAILABLE"
    external_rider_id: Optional[str] = None


class DeliveryPartnerCreate(DeliveryPartnerBase):
    pass


class DeliveryPartnerResponse(DeliveryPartnerBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
