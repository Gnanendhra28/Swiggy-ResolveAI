from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CustomerBase(BaseModel):
    name: str
    phone: str


class CustomerCreate(CustomerBase):
    pass


class CustomerResponse(CustomerBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
