from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.models.customer import Customer
from backend.app.models.restaurant import Restaurant
from backend.app.models.delivery_partner import DeliveryPartner
from backend.app.models.order import Order
from backend.app.models.order_event import OrderEvent


def test_database_connection(db_session: Session):
    result = db_session.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_seed_entities_exist(db_session: Session):
    customers = db_session.query(Customer).all()
    restaurants = db_session.query(Restaurant).all()
    riders = db_session.query(DeliveryPartner).all()

    assert len(customers) > 0
    assert len(restaurants) > 0
    assert len(riders) > 0
