"""Initial schema for ResolveAI Phase 1

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-18 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Customers
    op.create_table(
        "customers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customers_phone"), "customers", ["phone"], unique=False)

    # 2. Restaurants
    op.create_table(
        "restaurants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=128), nullable=False),
        sa.Column("area", sa.String(length=128), nullable=False),
        sa.Column("cuisine", sa.String(length=255), nullable=False),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=True),
        sa.Column("average_price", sa.Float(), nullable=True),
        sa.Column("number_of_offers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("offer_name", sa.String(length=255), nullable=True),
        sa.Column("pure_veg", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_restaurants_name"), "restaurants", ["name"], unique=False)
    op.create_index(op.f("ix_restaurants_city"), "restaurants", ["city"], unique=False)
    op.create_index(op.f("ix_restaurants_cuisine"), "restaurants", ["cuisine"], unique=False)

    # 3. Delivery Partners
    op.create_table(
        "delivery_partners",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("external_rider_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("availability_status", sa.String(length=32), nullable=False, server_default="AVAILABLE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_delivery_partners_external_rider_id"), "delivery_partners", ["external_rider_id"], unique=False)
    op.create_index(op.f("ix_delivery_partners_availability_status"), "delivery_partners", ["availability_status"], unique=False)

    # 4. Orders
    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("external_order_id", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("restaurant_id", sa.String(length=36), nullable=False),
        sa.Column("delivery_partner_id", sa.String(length=36), nullable=True),
        sa.Column("order_status", sa.String(length=48), nullable=False, server_default="PLACED"),
        sa.Column("order_value", sa.Float(), nullable=False),
        sa.Column("promised_delivery_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("demo_run_id", sa.String(length=64), nullable=True),
        sa.Column("data_source", sa.String(length=48), nullable=False, server_default="SYNTHETIC"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["delivery_partner_id"], ["delivery_partners.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_order_id"),
    )
    op.create_index(op.f("ix_orders_external_order_id"), "orders", ["external_order_id"], unique=True)
    op.create_index(op.f("ix_orders_customer_id"), "orders", ["customer_id"], unique=False)
    op.create_index(op.f("ix_orders_restaurant_id"), "orders", ["restaurant_id"], unique=False)
    op.create_index(op.f("ix_orders_delivery_partner_id"), "orders", ["delivery_partner_id"], unique=False)
    op.create_index(op.f("ix_orders_order_status"), "orders", ["order_status"], unique=False)
    op.create_index(op.f("ix_orders_created_at"), "orders", ["created_at"], unique=False)
    op.create_index(op.f("ix_orders_demo_run_id"), "orders", ["demo_run_id"], unique=False)
    op.create_index(op.f("ix_orders_data_source"), "orders", ["data_source"], unique=False)

    # 5. Order Events
    op.create_table(
        "order_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("data_source", sa.String(length=48), nullable=False, server_default="SYNTHETIC"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_events_order_id"), "order_events", ["order_id"], unique=False)
    op.create_index(op.f("ix_order_events_event_type"), "order_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_order_events_event_timestamp"), "order_events", ["event_timestamp"], unique=False)
    op.create_index(op.f("ix_order_events_data_source"), "order_events", ["data_source"], unique=False)


def downgrade() -> None:
    op.drop_table("order_events")
    op.drop_table("orders")
    op.drop_table("delivery_partners")
    op.drop_table("restaurants")
    op.drop_table("customers")
