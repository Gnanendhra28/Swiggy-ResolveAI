import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from backend.app.models.customer import Customer
from backend.app.models.restaurant import Restaurant
from backend.app.models.delivery_partner import DeliveryPartner
from backend.app.models.order import Order
from backend.app.models.order_event import OrderEvent


def test_restaurant_fields_preservation(db_session: Session):
    """Verify that restaurant dataset fields preserve exact meaning and coordinates are nullable."""
    rest = Restaurant(
        id=str(uuid.uuid4()),
        name="Test Dhaba",
        city="Chandigarh",
        area="Sector 17",
        cuisine="North Indian",
        rating=4.1,
        rating_count=350,
        average_price=300.0,
        number_of_offers=1,
        offer_name="10% OFF",
        pure_veg=False,
        location="Sector 17 Market",
        latitude=None,  # No coordinates invented
        longitude=None,
    )
    db_session.add(rest)
    db_session.commit()
    db_session.refresh(rest)

    assert rest.latitude is None
    assert rest.longitude is None
    assert rest.pure_veg is False
    assert rest.number_of_offers == 1
    assert rest.created_at is not None


def test_order_model_relationships_and_cascade(db_session: Session):
    """Verify order relationships and event cascade deletion."""
    customer = db_session.query(Customer).first()
    restaurant = db_session.query(Restaurant).first()
    rider = db_session.query(DeliveryPartner).first()

    now = datetime.now(timezone.utc)
    order = Order(
        id=str(uuid.uuid4()),
        external_order_id=f"TEST-ORD-{uuid.uuid4().hex[:6]}",
        customer_id=customer.id,
        restaurant_id=restaurant.id,
        delivery_partner_id=rider.id,
        order_status="PLACED",
        order_value=450.50,
        promised_delivery_at=now + timedelta(minutes=35),
        created_at=now,
        updated_at=now,
        data_source="SYNTHETIC",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    # Add events
    event1 = OrderEvent(
        id=str(uuid.uuid4()),
        order_id=order.id,
        event_type="ORDER_PLACED",
        event_timestamp=now,
        event_metadata={"step": 1},
        data_source="SYNTHETIC",
    )
    event2 = OrderEvent(
        id=str(uuid.uuid4()),
        order_id=order.id,
        event_type="RESTAURANT_ACCEPTED",
        event_timestamp=now + timedelta(minutes=2),
        event_metadata={"step": 2},
        data_source="SYNTHETIC",
    )
    db_session.add_all([event1, event2])
    db_session.commit()
    db_session.refresh(order)

    assert len(order.events) == 2
    assert order.customer.id == customer.id
    assert order.restaurant.id == restaurant.id
    assert order.delivery_partner.id == rider.id

    # Test cascade delete: removing order removes its events
    order_id = order.id
    db_session.delete(order)
    db_session.commit()

    remaining_events = db_session.query(OrderEvent).filter(OrderEvent.order_id == order_id).all()
    assert len(remaining_events) == 0
