"""Phase 3 Multi-Agent Intelligence and Autonomous Recovery schema

Revision ID: 003_phase_3_multi_agent_schema
Revises: 002_public_datasets_integration
Create Date: 2026-11-18 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003_phase_3_multi_agent_schema"
down_revision: Union[str, None] = "002_public_datasets_integration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create order_investigations table
    op.create_table(
        "order_investigations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("risk_tier", sa.String(length=32), nullable=False, server_default="NOMINAL"),
        sa.Column("trigger_event", sa.String(length=64), nullable=True),
        sa.Column("eta_p10", sa.Float(), nullable=True),
        sa.Column("eta_p50", sa.Float(), nullable=True),
        sa.Column("eta_p90", sa.Float(), nullable=True),
        sa.Column("eta_interval_width", sa.Float(), nullable=True),
        sa.Column("is_long_tail", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cancellation_probability", sa.Float(), nullable=True),
        sa.Column("cancellation_alert_budget_10k", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ml_provenance", sa.JSON(), nullable=False),
        sa.Column("restaurant_evidence", sa.JSON(), nullable=False),
        sa.Column("delivery_evidence", sa.JSON(), nullable=False),
        sa.Column("agent_reasoning", sa.JSON(), nullable=False),
        sa.Column("workflow_execution", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_investigations_order_id", "order_investigations", ["order_id"], unique=False)
    op.create_index("ix_order_investigations_status", "order_investigations", ["status"], unique=False)
    op.create_index("ix_order_investigations_risk_tier", "order_investigations", ["risk_tier"], unique=False)
    op.create_index("ix_order_investigations_created_at", "order_investigations", ["created_at"], unique=False)

    # 2. Create recovery_recommendations table
    op.create_table(
        "recovery_recommendations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("sensitivity_level", sa.String(length=32), nullable=False, server_default="LOW"),
        sa.Column("estimated_impact", sa.String(length=256), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("approval_status", sa.String(length=32), nullable=False, server_default="PENDING_APPROVAL"),
        sa.Column("approved_by", sa.String(length=64), nullable=True),
        sa.Column("approval_notes", sa.String(length=512), nullable=True),
        sa.Column("approval_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("execution_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["order_investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recovery_recommendations_investigation_id", "recovery_recommendations", ["investigation_id"], unique=False)
    op.create_index("ix_recovery_recommendations_order_id", "recovery_recommendations", ["order_id"], unique=False)
    op.create_index("ix_recovery_recommendations_action_type", "recovery_recommendations", ["action_type"], unique=False)
    op.create_index("ix_recovery_recommendations_approval_status", "recovery_recommendations", ["approval_status"], unique=False)
    op.create_index("ix_recovery_recommendations_execution_status", "recovery_recommendations", ["execution_status"], unique=False)

    # 3. Create recovery_execution_audits table
    op.create_table(
        "recovery_execution_audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("recommendation_id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("initial_order_status", sa.String(length=48), nullable=False),
        sa.Column("final_order_status", sa.String(length=48), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("trigger_reason", sa.String(length=256), nullable=False),
        sa.Column("ml_model_version", sa.String(length=32), nullable=False, server_default="2.5.0"),
        sa.Column("approval_identity", sa.String(length=64), nullable=True),
        sa.Column("approval_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_result", sa.JSON(), nullable=False),
        sa.Column("recovery_outcome", sa.String(length=32), nullable=False, server_default="SUCCESS"),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recovery_recommendations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recovery_execution_audits_recommendation_id", "recovery_execution_audits", ["recommendation_id"], unique=False)
    op.create_index("ix_recovery_execution_audits_order_id", "recovery_execution_audits", ["order_id"], unique=False)
    op.create_index("ix_recovery_execution_audits_idempotency_key", "recovery_execution_audits", ["idempotency_key"], unique=True)
    op.create_index("ix_recovery_execution_audits_action_type", "recovery_execution_audits", ["action_type"], unique=False)
    op.create_index("ix_recovery_execution_audits_executed_at", "recovery_execution_audits", ["executed_at"], unique=False)


def downgrade() -> None:
    op.drop_table("recovery_execution_audits")
    op.drop_table("recovery_recommendations")
    op.drop_table("order_investigations")
