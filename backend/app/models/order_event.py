import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict
from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.models.order import Order


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    # Using 'event_metadata' attribute or 'metadata_' since 'metadata' is reserved on Base
    # We map column name to "metadata" in the database table!
    event_metadata: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    data_source: Mapped[str] = mapped_column(
        String(48), default="SYNTHETIC", nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    order: Mapped["Order"] = relationship("Order", back_populates="events")

    def __repr__(self) -> str:
        return f"<OrderEvent {self.event_type} for Order {self.order_id} at {self.event_timestamp}>"
