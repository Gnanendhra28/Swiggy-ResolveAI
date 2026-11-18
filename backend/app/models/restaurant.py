import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Float, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.models.order import Order


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    area: Mapped[str] = mapped_column(String(128), nullable=False)
    cuisine: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    average_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    number_of_offers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    offer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pure_veg: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    delivery_time_listing: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    external_dataset_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    data_source: Mapped[str] = mapped_column(
        String(48), default="PUBLIC_HISTORICAL", nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    orders: Mapped[List["Order"]] = relationship("Order", back_populates="restaurant")

    def __repr__(self) -> str:
        return f"<Restaurant {self.name} in {self.city} ({self.id})>"
