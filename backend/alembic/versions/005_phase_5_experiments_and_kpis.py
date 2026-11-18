"""Phase 5 Simulation Experiments, Counterfactuals, and KPI Tracking schema

Revision ID: 005_phase_5_experiments_and_kpis
Revises: 004_phase_4_resilience_and_audits
Create Date: 2026-11-18 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "005_phase_5_experiments_and_kpis"
down_revision: Union[str, None] = "004_phase_4_resilience_and_audits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "simulation_experiments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("scenario_type", sa.String(length=64), nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=False),
        sa.Column("num_orders", sa.Integer(), nullable=False),
        sa.Column("config_parameters", sa.JSON(), nullable=False),
        sa.Column("strategies_evaluated", sa.JSON(), nullable=False),
        sa.Column("kpi_results", sa.JSON(), nullable=False),
        sa.Column("counterfactual_comparisons", sa.JSON(), nullable=False),
        sa.Column("action_effectiveness", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_simulation_experiments_name", "simulation_experiments", ["name"], unique=False)
    op.create_index("ix_simulation_experiments_scenario_type", "simulation_experiments", ["scenario_type"], unique=False)
    op.create_index("ix_simulation_experiments_created_at", "simulation_experiments", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("simulation_experiments")
