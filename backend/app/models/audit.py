import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.models.order import Order
    from backend.app.models.recommendation import RecoveryRecommendation


class RecoveryExecutionAudit(Base):
    __tablename__ = "recovery_execution_audits"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    recommendation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("recovery_recommendations.id", ondelete="CASCADE"),
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
    initial_order_status: Mapped[str] = mapped_column(
        String(48), nullable=False
    )
    final_order_status: Mapped[str] = mapped_column(
        String(48), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    trigger_reason: Mapped[str] = mapped_column(
        String(256), nullable=False
    )
    ml_model_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="2.5.0"
    )
    approval_identity: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    approval_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    execution_result: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    recovery_outcome: Mapped[str] = mapped_column(
        String(32), nullable=False, default="SUCCESS"
    )
    is_simulated: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    recommendation: Mapped["RecoveryRecommendation"] = relationship(
        "RecoveryRecommendation", back_populates="audits"
    )
    order: Mapped["Order"] = relationship("Order", backref="recovery_audits")

    def __repr__(self) -> str:
        return f"<RecoveryExecutionAudit {self.action_type} on Order {self.order_id} ({self.recovery_outcome})>"


# -----------------------------------------------------------------------------
# Workstream 6: Strict ORM-Level Immutability Enforcement
# -----------------------------------------------------------------------------
from sqlalchemy import event


@event.listens_for(RecoveryExecutionAudit, "before_update")
def receive_audit_before_update(mapper, connection, target):
    """Enforces append-only immutability. Prevents modifying historical audit records."""
    raise PermissionError(
        f"RecoveryExecutionAudit records are strictly immutable. "
        f"Attempted update on audit ID '{target.id}' (idempotency key: '{target.idempotency_key}') was rejected."
    )


@event.listens_for(RecoveryExecutionAudit, "before_delete")
def receive_audit_before_delete(mapper, connection, target):
    """Enforces append-only immutability. Prevents deleting historical audit records."""
    raise PermissionError(
        f"RecoveryExecutionAudit records are strictly immutable. "
        f"Attempted deletion of audit ID '{target.id}' was rejected."
    )
