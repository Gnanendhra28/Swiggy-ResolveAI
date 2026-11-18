import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.models.investigation import OrderInvestigation
    from backend.app.models.order import Order
    from backend.app.models.audit import RecoveryExecutionAudit


class RecoveryRecommendation(Base):
    __tablename__ = "recovery_recommendations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("order_investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    rationale: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    sensitivity_level: Mapped[str] = mapped_column(
        String(32), nullable=False, default="LOW"
    )
    estimated_impact: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True
    )
    requires_approval: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    approval_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING_APPROVAL", index=True
    )
    approved_by: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    operator_role: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    approval_notes: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )
    approval_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    execution_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING", index=True
    )
    execution_payload: Mapped[Dict[str, Any]] = mapped_column(
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

    investigation: Mapped["OrderInvestigation"] = relationship(
        "OrderInvestigation", back_populates="recommendations"
    )
    order: Mapped["Order"] = relationship("Order", backref="recommendations")
    audits: Mapped[List["RecoveryExecutionAudit"]] = relationship(
        "RecoveryExecutionAudit",
        back_populates="recommendation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<RecoveryRecommendation {self.action_type} for Order {self.order_id} [{self.approval_status}]>"
