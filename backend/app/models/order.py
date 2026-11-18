import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.models.customer import Customer
    from backend.app.models.restaurant import Restaurant
    from backend.app.models.delivery_partner import DeliveryPartner
    from backend.app.models.order_event import OrderEvent


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    external_order_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    restaurant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("restaurants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    delivery_partner_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("delivery_partners.id", ondelete="SET NULL"), nullable=True, index=True
    )
    order_status: Mapped[str] = mapped_column(
        String(48), nullable=False, index=True, default="PLACED"
    )
    order_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    promised_delivery_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    demo_run_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    data_source: Mapped[str] = mapped_column(
        String(48), default="SYNTHETIC", nullable=False, index=True
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="orders")
    delivery_partner: Mapped[Optional["DeliveryPartner"]] = relationship(
        "DeliveryPartner", back_populates="orders"
    )
    events: Mapped[List["OrderEvent"]] = relationship(
        "OrderEvent",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderEvent.event_timestamp",
    )

    def __repr__(self) -> str:
        return f"<Order {self.external_order_id} [{self.order_status}] ({self.id})>"
