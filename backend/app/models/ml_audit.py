import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.models.order import Order


class MLPredictionAudit(Base):
    __tablename__ = "ml_prediction_audits"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="2.5.0"
    )
    feature_schema_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="1.0.0"
    )
    task_a_eta_p50: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    task_a_interval_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    task_a_interval_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    task_a_is_long_tail: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    task_c2_is_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    task_c2_calibrated_prob: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    task_c2_alert_5k: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    task_c2_alert_10k: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    task_b_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    task_c1_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    provenance_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    prediction_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    order: Mapped["Order"] = relationship("Order", backref="ml_prediction_audits")

    def __repr__(self) -> str:
        return f"<MLPredictionAudit {self.id} for Order {self.order_id} (v{self.model_version})>"


# -----------------------------------------------------------------------------
# Workstream 3: Strict ORM-Level Immutability Enforcement for ML Audits
# -----------------------------------------------------------------------------
from sqlalchemy import event


@event.listens_for(MLPredictionAudit, "before_update")
def receive_ml_audit_before_update(mapper, connection, target):
    """Enforces append-only immutability. Prevents modifying historical ML prediction audit records."""
    raise PermissionError(
        f"MLPredictionAudit records are strictly immutable. "
        f"Attempted update on audit ID '{target.id}' (Order: '{target.order_id}') was rejected."
    )


@event.listens_for(MLPredictionAudit, "before_delete")
def receive_ml_audit_before_delete(mapper, connection, target):
    """Enforces append-only immutability. Prevents deleting historical ML prediction audit records."""
    raise PermissionError(
        f"MLPredictionAudit records are strictly immutable. "
        f"Attempted deletion of audit ID '{target.id}' was rejected."
    )
