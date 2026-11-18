"""Integrate public datasets: restaurant extensions and historical orders table

Revision ID: 002_public_datasets_integration
Revises: 001_initial_schema
Create Date: 2026-11-18 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_public_datasets_integration"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add fields to restaurants table
    with op.batch_alter_table("restaurants") as batch_op:
        batch_op.add_column(sa.Column("delivery_time_listing", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("external_dataset_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("data_source", sa.String(length=48), nullable=False, server_default="PUBLIC_HISTORICAL"))
        batch_op.create_index("ix_restaurants_external_dataset_id", ["external_dataset_id"], unique=False)
        batch_op.create_index("ix_restaurants_data_source", ["data_source"], unique=False)

    # 2. Create historical_orders table
    op.create_table(
        "historical_orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=64), nullable=False),
        sa.Column("order_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("order_date", sa.String(length=32), nullable=True),
        sa.Column("allot_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accept_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pickup_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rider_id", sa.String(length=64), nullable=True),
        sa.Column("first_mile_distance", sa.Float(), nullable=True),
        sa.Column("last_mile_distance", sa.Float(), nullable=True),
        sa.Column("allotted_orders", sa.Integer(), nullable=True),
        sa.Column("delivered_orders", sa.Integer(), nullable=True),
        sa.Column("undelivered_orders", sa.Integer(), nullable=True),
        sa.Column("lifetime_order_count", sa.Integer(), nullable=True),
        sa.Column("reassigned_order", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reassignment_method", sa.String(length=64), nullable=True),
        sa.Column("reassignment_reason", sa.String(length=255), nullable=True),
        sa.Column("session_time", sa.Float(), nullable=True),
        sa.Column("data_source", sa.String(length=48), nullable=False, server_default="PUBLIC_HISTORICAL"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_historical_orders_order_id", "historical_orders", ["order_id"], unique=False)
    op.create_index("ix_historical_orders_rider_id", "historical_orders", ["rider_id"], unique=False)
    op.create_index("ix_historical_orders_order_time", "historical_orders", ["order_time"], unique=False)
    op.create_index("ix_historical_orders_cancelled", "historical_orders", ["cancelled"], unique=False)
    op.create_index("ix_historical_orders_reassigned_order", "historical_orders", ["reassigned_order"], unique=False)
    op.create_index("ix_historical_orders_data_source", "historical_orders", ["data_source"], unique=False)


def downgrade() -> None:
    op.drop_table("historical_orders")
    with op.batch_alter_table("restaurants") as batch_op:
        batch_op.drop_index("ix_restaurants_data_source")
        batch_op.drop_index("ix_restaurants_external_dataset_id")
        batch_op.drop_column("data_source")
        batch_op.drop_column("external_dataset_id")
        batch_op.drop_column("delivery_time_listing")
