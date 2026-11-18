import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.models.order import Order
    from backend.app.models.recommendation import RecoveryRecommendation


class OrderInvestigation(Base):
    __tablename__ = "order_investigations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING", index=True
    )
    risk_tier: Mapped[str] = mapped_column(
        String(32), nullable=False, default="NOMINAL", index=True
    )
    trigger_event: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    eta_p10: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eta_p50: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eta_p90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eta_interval_width: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_long_tail: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cancellation_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cancellation_alert_budget_10k: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    ml_provenance: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    restaurant_evidence: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    delivery_evidence: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    agent_reasoning: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    workflow_execution: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
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

    order: Mapped["Order"] = relationship("Order", backref="investigations")
    recommendations: Mapped[List["RecoveryRecommendation"]] = relationship(
        "RecoveryRecommendation",
        back_populates="investigation",
        cascade="all, delete-orphan",
        order_by="RecoveryRecommendation.created_at",
    )

    def __repr__(self) -> str:
        return f"<OrderInvestigation {self.id} for Order {self.order_id} [{self.risk_tier}]>"
