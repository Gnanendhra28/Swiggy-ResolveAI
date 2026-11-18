import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Float, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base


class HistoricalOrder(Base):
    """
    Historical order lifecycle entity imported from public research datasets (e.g., Kaggle).
    Preserves raw operational telemetry (rider allocation, pickup, delivery, reassignments, cancellations).
    Completely isolated from synthetic live orders. Does not invent fake customer or restaurant IDs.
    """
    __tablename__ = "historical_orders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    order_id: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )
    order_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    order_date: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )
    allot_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accept_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pickup_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    rider_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    first_mile_distance: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    last_mile_distance: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    allotted_orders: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    delivered_orders: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    undelivered_orders: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    lifetime_order_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    reassigned_order: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    reassignment_method: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    reassignment_reason: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    session_time: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    data_source: Mapped[str] = mapped_column(
        String(48), default="PUBLIC_HISTORICAL", nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<HistoricalOrder {self.order_id} (Rider: {self.rider_id})>"
