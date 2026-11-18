import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.core.exceptions import EntityNotFoundError, SimulationError
from backend.app.core.logging import logger
from backend.app.models.customer import Customer
from backend.app.models.restaurant import Restaurant
from backend.app.models.delivery_partner import DeliveryPartner
from backend.app.models.order import Order
from backend.app.models.order_event import OrderEvent
from backend.app.schemas.simulation import (
    ScenarioType,
    SimulationGenerateRequest,
    SimulationGenerateResponse,
)
from backend.app.schemas.order import OrderSummaryResponse
from backend.app.simulation.order_simulator import OrderSimulator


# Synthetic reference entities for realistic simulation
SYNTHETIC_RESTAURANTS = [
    {
        "name": "Meghana Foods",
        "city": "Bengaluru",
        "area": "Koramangala",
        "cuisine": "Biryani, Andhra",
        "rating": 4.4,
        "rating_count": 12500,
        "average_price": 450.0,
        "number_of_offers": 2,
        "offer_name": "Flat 20% OFF above ₹399",
        "pure_veg": False,
        "location": "5th Block, Koramangala, Bengaluru",
        "latitude": 12.9352,
        "longitude": 77.6245,
    },
    {
        "name": "Empire Restaurant",
        "city": "Bengaluru",
        "area": "Indiranagar",
        "cuisine": "North Indian, Kebabs, Biryani",
        "rating": 4.2,
        "rating_count": 8900,
        "average_price": 500.0,
        "number_of_offers": 1,
        "offer_name": "Free Delivery on orders above ₹499",
        "pure_veg": False,
        "location": "100 Feet Road, Indiranagar, Bengaluru",
        "latitude": 12.9719,
        "longitude": 77.6412,
    },
    {
        "name": "A2B - Adyar Ananda Bhavan",
        "city": "Bengaluru",
        "area": "HSR Layout",
        "cuisine": "South Indian, Sweets, Chaat",
        "rating": 4.3,
        "rating_count": 15600,
        "average_price": 250.0,
        "number_of_offers": 3,
        "offer_name": "15% OFF up to ₹75",
        "pure_veg": True,
        "location": "Sector 3, HSR Layout, Bengaluru",
        "latitude": 12.9116,
        "longitude": 77.6389,
    },
    {
        "name": "Truffles Ice & Spice",
        "city": "Bengaluru",
        "area": "St. Marks Road",
        "cuisine": "Burgers, Continental, Desserts",
        "rating": 4.5,
        "rating_count": 24000,
        "average_price": 380.0,
        "number_of_offers": 1,
        "offer_name": "Combo treat ₹299",
        "pure_veg": False,
        "location": "St. Marks Road, Ashok Nagar, Bengaluru",
        "latitude": 12.9723,
        "longitude": 77.6015,
    },
]

SYNTHETIC_CUSTOMERS = [
    {"name": "Aarav Sharma", "phone": "+91-9876543210"},
    {"name": "Priyanka Nair", "phone": "+91-9845123456"},
    {"name": "Rohan Deshmukh", "phone": "+91-9988776655"},
    {"name": "Ananya Iyer", "phone": "+91-9711223344"},
    {"name": "Vikram Malhotra", "phone": "+91-9655443322"},
]

SYNTHETIC_RIDERS = [
    {"name": "Manjunath K.", "external_rider_id": "RIDER-BLR-0101", "availability_status": "AVAILABLE"},
    {"name": "Syed Farhan", "external_rider_id": "RIDER-BLR-0202", "availability_status": "AVAILABLE"},
    {"name": "Ramesh Gowda", "external_rider_id": "RIDER-BLR-0303", "availability_status": "AVAILABLE"},
    {"name": "Deepak Kumar", "external_rider_id": "RIDER-BLR-0404", "availability_status": "AVAILABLE"},
]


class SimulationService:
    @staticmethod
    def ensure_synthetic_seed_entities(db: Session) -> Tuple[List[Customer], List[Restaurant], List[DeliveryPartner]]:
        """Ensures that default synthetic entities exist in database."""
        # Customers
        customers = db.scalars(select(Customer)).all()
        if not customers:
            customers = [Customer(**c) for c in SYNTHETIC_CUSTOMERS]
            db.add_all(customers)
            db.commit()
            for c in customers:
                db.refresh(c)

        # Restaurants (sample up to 100 from public historical dataset or synthetic seed)
        restaurants = db.scalars(select(Restaurant).limit(100)).all()
        if not restaurants:
            restaurants = [Restaurant(**r) for r in SYNTHETIC_RESTAURANTS]
            db.add_all(restaurants)
            db.commit()
            for r in restaurants:
                db.refresh(r)

        # Riders
        riders = db.scalars(select(DeliveryPartner)).all()
        if not riders:
            riders = [DeliveryPartner(**r) for r in SYNTHETIC_RIDERS]
            db.add_all(riders)
            db.commit()
            for r in riders:
                db.refresh(r)

        return list(customers), list(restaurants), list(riders)

    @staticmethod
    def generate_simulation(
        db: Session,
        request: SimulationGenerateRequest,
    ) -> SimulationGenerateResponse:
        logger.info(
            f"Starting simulation run: scenario={request.scenario.value}, count={request.count}, seed={request.seed}"
        )

        customers, restaurants, riders = SimulationService.ensure_synthetic_seed_entities(db)
        if not customers or not restaurants or not riders:
            raise SimulationError("Unable to initialize synthetic reference data for simulation")

        simulator = OrderSimulator(seed=request.seed)
        demo_run_id = f"demo_{request.scenario.value.lower()}_{uuid.uuid4().hex[:8]}"

        generated_orders: List[Order] = []
        generated_order_ids: List[str] = []

        try:
            for i in range(request.count):
                cust = simulator.rng.choice(customers)
                rest = simulator.rng.choice(restaurants)
                primary_rider = simulator.rng.choice(riders)
                alt_riders = [r for r in riders if r.id != primary_rider.id]
                alt_rider = simulator.rng.choice(alt_riders) if alt_riders else primary_rider

                sim_result = simulator.generate_scenario(
                    scenario=request.scenario,
                    customer={"id": cust.id, "name": cust.name, "phone": cust.phone},
                    restaurant={"id": rest.id, "name": rest.name, "city": rest.city, "cuisine": rest.cuisine},
                    primary_rider={"id": primary_rider.id, "name": primary_rider.name},
                    alternate_rider={"id": alt_rider.id, "name": alt_rider.name},
                    custom_params=request.custom_params,
                    demo_run_id=demo_run_id,
                )

                order_dict = sim_result["order"]
                order_events_data = sim_result["events"]

                # Create Order model instance
                db_order = Order(**order_dict)
                db.add(db_order)
                db.flush()  # to register order PK for events foreign key

                for ev_data in order_events_data:
                    db_event = OrderEvent(
                        id=str(uuid.uuid4()),
                        order_id=db_order.id,
                        event_type=ev_data["event_type"],
                        event_timestamp=ev_data["event_timestamp"],
                        event_metadata=ev_data["metadata"],
                        data_source="SYNTHETIC",
                    )
                    db.add(db_event)

                generated_orders.append(db_order)
                generated_order_ids.append(db_order.id)

            db.commit()

            # Refresh and prepare response summaries
            order_summaries: List[OrderSummaryResponse] = []
            for o in generated_orders:
                db.refresh(o)
                # Compute delay status: any delayed event or final delivery > promised delivery time
                is_delayed = False
                if o.order_status in ["ESCALATED", "FAILED_RECOVERY"]:
                    is_delayed = True
                for ev in o.events:
                    if "DELAY" in ev.event_type or "TIMEOUT" in ev.event_type:
                        is_delayed = True
                        break

                order_summaries.append(
                    OrderSummaryResponse(
                        id=o.id,
                        external_order_id=o.external_order_id,
                        customer_id=o.customer_id,
                        customer_name=o.customer.name if o.customer else "Unknown",
                        restaurant_id=o.restaurant_id,
                        restaurant_name=o.restaurant.name if o.restaurant else "Unknown",
                        restaurant_city=o.restaurant.city if o.restaurant else "Unknown",
                        delivery_partner_id=o.delivery_partner_id,
                        delivery_partner_name=o.delivery_partner.name if o.delivery_partner else None,
                        order_status=o.order_status,
                        order_value=o.order_value,
                        promised_delivery_at=o.promised_delivery_at,
                        created_at=o.created_at,
                        updated_at=o.updated_at,
                        demo_run_id=o.demo_run_id,
                        data_source=o.data_source,
                        event_count=len(o.events),
                        is_delayed=is_delayed,
                    )
                )

            logger.info(
                f"Completed simulation run {demo_run_id}: successfully generated {len(order_summaries)} orders"
            )

            return SimulationGenerateResponse(
                demo_run_id=demo_run_id,
                scenario=request.scenario,
                generated_count=len(order_summaries),
                order_ids=generated_order_ids,
                orders=order_summaries,
            )

        except Exception as exc:
            db.rollback()
            logger.error(f"Error during simulation generation: {exc}")
            raise SimulationError(f"Failed to generate simulation: {str(exc)}")

    @staticmethod
    def inject_event(
        db: Session,
        order_id: str,
        event_type: str,
        metadata: Dict[str, Any],
        data_source: str = "SYNTHETIC",
    ) -> OrderEvent:
        order = db.get(Order, order_id)
        if not order:
            raise EntityNotFoundError("Order", order_id)

        now = datetime.now(timezone.utc)
        event = OrderEvent(
            id=str(uuid.uuid4()),
            order_id=order.id,
            event_type=event_type,
            event_timestamp=now,
            event_metadata=metadata,
            data_source=data_source,
        )
        db.add(event)

        # Update order's updated_at timestamp
        order.updated_at = now
        db.commit()
        db.refresh(event)
        return event
