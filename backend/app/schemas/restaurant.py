from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class RestaurantBase(BaseModel):
    name: str
    city: str
    area: str
    cuisine: str
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    average_price: Optional[float] = None
    number_of_offers: int = 0
    offer_name: Optional[str] = None
    pure_veg: bool = False
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantResponse(RestaurantBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
