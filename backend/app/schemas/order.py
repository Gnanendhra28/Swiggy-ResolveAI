from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.customer import CustomerResponse
from backend.app.schemas.restaurant import RestaurantResponse
from backend.app.schemas.delivery_partner import DeliveryPartnerResponse
from backend.app.schemas.order_event import OrderEventResponse


class OrderBase(BaseModel):
    external_order_id: str
    order_status: str
    order_value: float
    promised_delivery_at: datetime
    data_source: str = "SYNTHETIC"
    demo_run_id: Optional[str] = None


class OrderCreate(BaseModel):
    customer_id: str
    restaurant_id: str
    delivery_partner_id: Optional[str] = None
    external_order_id: Optional[str] = None
    order_status: str = "PLACED"
    order_value: float
    promised_delivery_at: datetime
    demo_run_id: Optional[str] = None
    data_source: str = "SYNTHETIC"


class OrderSummaryResponse(BaseModel):
    id: str
    external_order_id: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    restaurant_id: Optional[str] = None
    restaurant_name: Optional[str] = None
    restaurant_city: Optional[str] = None
    delivery_partner_id: Optional[str] = None
    delivery_partner_name: Optional[str] = None
    order_status: str
    order_value: float
    promised_delivery_at: datetime
    created_at: datetime
    updated_at: datetime
    demo_run_id: Optional[str] = None
    data_source: str
    event_count: int = 0
    is_delayed: bool = False

    model_config = ConfigDict(from_attributes=True)


class OrderDetailResponse(BaseModel):
    id: str
    external_order_id: str
    order_status: str
    order_value: float
    promised_delivery_at: datetime
    created_at: datetime
    updated_at: datetime
    demo_run_id: Optional[str] = None
    data_source: str
    customer: Optional[CustomerResponse] = None
    restaurant: Optional[RestaurantResponse] = None
    delivery_partner: Optional[DeliveryPartnerResponse] = None
    events: List[OrderEventResponse] = []
    is_delayed: bool = False

    model_config = ConfigDict(from_attributes=True)
