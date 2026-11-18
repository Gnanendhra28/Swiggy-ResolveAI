import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.models.order import Order


class DeliveryPartner(Base):
    __tablename__ = "delivery_partners"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    external_rider_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    availability_status: Mapped[str] = mapped_column(
        String(32), default="AVAILABLE", nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    orders: Mapped[List["Order"]] = relationship(
        "Order", back_populates="delivery_partner"
    )

    def __repr__(self) -> str:
        return f"<DeliveryPartner {self.name} ({self.id})>"
