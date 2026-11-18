"""Phase 4 Resilience, Expiration, and ML Prediction Audits schema

Revision ID: 004_phase_4_resilience_and_audits
Revises: 003_phase_3_multi_agent_schema
Create Date: 2026-11-18 19:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_phase_4_resilience_and_audits"
down_revision: Union[str, None] = "003_phase_3_multi_agent_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add operator_role and expires_at to recovery_recommendations
    with op.batch_alter_table("recovery_recommendations") as batch_op:
        batch_op.add_column(sa.Column("operator_role", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_recovery_recommendations_expires_at", ["expires_at"], unique=False)

    # 2. Create ml_prediction_audits table
    op.create_table(
        "ml_prediction_audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False, server_default="2.5.0"),
        sa.Column("feature_schema_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("task_a_eta_p50", sa.Float(), nullable=True),
        sa.Column("task_a_interval_min", sa.Float(), nullable=True),
        sa.Column("task_a_interval_max", sa.Float(), nullable=True),
        sa.Column("task_a_is_long_tail", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("task_c2_is_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("task_c2_calibrated_prob", sa.Float(), nullable=True),
        sa.Column("task_c2_alert_5k", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("task_c2_alert_10k", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("task_b_score", sa.Float(), nullable=True),
        sa.Column("task_c1_score", sa.Float(), nullable=True),
        sa.Column("provenance_metadata", sa.JSON(), nullable=False),
        sa.Column("prediction_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ml_prediction_audits_order_id", "ml_prediction_audits", ["order_id"], unique=False)
    op.create_index("ix_ml_prediction_audits_prediction_timestamp", "ml_prediction_audits", ["prediction_timestamp"], unique=False)


def downgrade() -> None:
    op.drop_table("ml_prediction_audits")
    with op.batch_alter_table("recovery_recommendations") as batch_op:
        batch_op.drop_index("ix_recovery_recommendations_expires_at")
        batch_op.drop_column("expires_at")
        batch_op.drop_column("operator_role")
