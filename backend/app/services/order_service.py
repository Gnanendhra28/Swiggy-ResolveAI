from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, desc, or_

from backend.app.core.exceptions import EntityNotFoundError
from backend.app.models.order import Order
from backend.app.models.order_event import OrderEvent
from backend.app.models.customer import Customer
from backend.app.models.restaurant import Restaurant
from backend.app.models.historical_order import HistoricalOrder
from backend.app.schemas.order import OrderSummaryResponse, OrderDetailResponse
from backend.app.schemas.customer import CustomerResponse
from backend.app.schemas.restaurant import RestaurantResponse
from backend.app.schemas.delivery_partner import DeliveryPartnerResponse
from backend.app.schemas.order_event import OrderEventResponse


class OrderService:
    @staticmethod
    def _is_delayed(order: Order) -> bool:
        if order.order_status in ["ESCALATED", "FAILED_RECOVERY"]:
            return True
        for ev in order.events:
            if "DELAY" in ev.event_type or "TIMEOUT" in ev.event_type:
                return True
        if order.order_status not in ["DELIVERED", "RECOVERED"]:
            now = datetime.now(timezone.utc)
            p_at = order.promised_delivery_at
            if p_at:
                if p_at.tzinfo is None:
                    p_at = p_at.replace(tzinfo=timezone.utc)
                if now > p_at:
                    return True
        return False

    @staticmethod
    def _historical_to_summary(h: HistoricalOrder) -> OrderSummaryResponse:
        order_status = "CANCELLED" if h.cancelled else "DELIVERED"
        promised_at = h.allot_time or h.order_time or h.created_at
        created_at = h.order_time or h.created_at
        updated_at = h.delivered_time or h.cancelled_time or created_at
        is_delayed = bool(h.reassigned_order or h.cancelled)

        event_count = 3
        if h.delivered_time:
            event_count += 1
        if h.cancelled_time:
            event_count += 1
        if h.reassigned_order:
            event_count += 1

        return OrderSummaryResponse(
            id=h.id,
            external_order_id=f"KGL-{h.order_id}",
            customer_id=None,
            customer_name="Customer unassigned in historical dataset",
            restaurant_id=None,
            restaurant_name="Restaurant unavailable in source dataset",
            restaurant_city="N/A (Historical Kaggle Dataset)",
            delivery_partner_id=f"rider_{h.rider_id}" if h.rider_id else None,
            delivery_partner_name=f"Courier #{h.rider_id}" if h.rider_id else "Unassigned Courier",
            order_status=order_status,
            order_value=350.0,
            promised_delivery_at=promised_at,
            created_at=created_at,
            updated_at=updated_at,
            demo_run_id=None,
            data_source="PUBLIC_HISTORICAL",
            event_count=event_count,
            is_delayed=is_delayed,
        )

    @staticmethod
    def list_orders(
        db: Session,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        demo_run_id: Optional[str] = None,
        data_source: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[OrderSummaryResponse], int]:
        # If user explicitly filtered by PUBLIC_HISTORICAL
        if data_source == "PUBLIC_HISTORICAL":
            hist_stmt = select(HistoricalOrder).order_by(desc(HistoricalOrder.order_time))
            if status:
                if status in ["DELIVERED", "RECOVERED"]:
                    hist_stmt = hist_stmt.where(HistoricalOrder.cancelled.is_(False))
                elif status in ["CANCELLED", "ESCALATED", "FAILED_RECOVERY"]:
                    hist_stmt = hist_stmt.where(HistoricalOrder.cancelled.is_(True))
                else:
                    return [], 0
            if search:
                search_term = f"%{search.strip()}%"
                hist_stmt = hist_stmt.where(
                    or_(
                        HistoricalOrder.order_id.ilike(search_term),
                        HistoricalOrder.rider_id.ilike(search_term),
                    )
                )
            total = db.scalar(select(func.count()).select_from(hist_stmt.subquery())) or 0
            offset = (page - 1) * limit
            hist_items = db.scalars(hist_stmt.offset(offset).limit(limit)).all()
            return [OrderService._historical_to_summary(h) for h in hist_items], total

        # Query synthetic orders
        synth_stmt = (
            select(Order)
            .options(
                joinedload(Order.customer),
                joinedload(Order.restaurant),
                joinedload(Order.delivery_partner),
                joinedload(Order.events),
            )
            .order_by(desc(Order.created_at))
        )

        if status:
            synth_stmt = synth_stmt.where(Order.order_status == status)

        if demo_run_id:
            synth_stmt = synth_stmt.where(Order.demo_run_id == demo_run_id)

        if data_source == "SYNTHETIC":
            synth_stmt = synth_stmt.where(Order.data_source == "SYNTHETIC")

        if search:
            search_term = f"%{search.strip()}%"
            synth_stmt = synth_stmt.join(Order.customer).join(Order.restaurant).where(
                or_(
                    Order.external_order_id.ilike(search_term),
                    Customer.name.ilike(search_term),
                    Restaurant.name.ilike(search_term),
                    Restaurant.city.ilike(search_term),
                )
            )

        synth_total = db.scalar(select(func.count()).select_from(synth_stmt.subquery())) or 0

        # If data_source == "SYNTHETIC" or demo_run_id is specified, return only synthetic
        if data_source == "SYNTHETIC" or demo_run_id:
            offset = (page - 1) * limit
            synth_orders = db.scalars(synth_stmt.offset(offset).limit(limit)).unique().all()
            results = [
                OrderSummaryResponse(
                    id=o.id,
                    external_order_id=o.external_order_id,
                    customer_id=o.customer_id,
                    customer_name=o.customer.name if o.customer else "Customer unassigned",
                    restaurant_id=o.restaurant_id,
                    restaurant_name=o.restaurant.name if o.restaurant else "Restaurant unavailable",
                    restaurant_city=o.restaurant.city if o.restaurant else "City unavailable",
                    delivery_partner_id=o.delivery_partner_id,
                    delivery_partner_name=o.delivery_partner.name if o.delivery_partner else "Pending Assignment",
                    order_status=o.order_status,
                    order_value=o.order_value,
                    promised_delivery_at=o.promised_delivery_at,
                    created_at=o.created_at,
                    updated_at=o.updated_at,
                    demo_run_id=o.demo_run_id,
                    data_source=o.data_source,
                    event_count=len(o.events),
                    is_delayed=OrderService._is_delayed(o),
                )
                for o in synth_orders
            ]
            return results, synth_total

        # Combined query: Synthetic orders followed by Historical orders
        hist_stmt = select(HistoricalOrder).order_by(desc(HistoricalOrder.order_time))
        if status:
            if status in ["DELIVERED", "RECOVERED"]:
                hist_stmt = hist_stmt.where(HistoricalOrder.cancelled.is_(False))
            elif status in ["CANCELLED", "ESCALATED", "FAILED_RECOVERY"]:
                hist_stmt = hist_stmt.where(HistoricalOrder.cancelled.is_(True))
            else:
                hist_stmt = hist_stmt.where(HistoricalOrder.cancelled == -1)

        hist_total = db.scalar(select(func.count()).select_from(hist_stmt.subquery())) or 0
        total = synth_total + hist_total

        offset = (page - 1) * limit
        results: List[OrderSummaryResponse] = []

        # If offset falls within synthetic range
        if offset < synth_total:
            needed_from_synth = min(limit, synth_total - offset)
            synth_orders = db.scalars(synth_stmt.offset(offset).limit(needed_from_synth)).unique().all()
            results.extend([
                OrderSummaryResponse(
                    id=o.id,
                    external_order_id=o.external_order_id,
                    customer_id=o.customer_id,
                    customer_name=o.customer.name if o.customer else "Customer unassigned",
                    restaurant_id=o.restaurant_id,
                    restaurant_name=o.restaurant.name if o.restaurant else "Restaurant unavailable",
                    restaurant_city=o.restaurant.city if o.restaurant else "City unavailable",
                    delivery_partner_id=o.delivery_partner_id,
                    delivery_partner_name=o.delivery_partner.name if o.delivery_partner else "Pending Assignment",
                    order_status=o.order_status,
                    order_value=o.order_value,
                    promised_delivery_at=o.promised_delivery_at,
                    created_at=o.created_at,
                    updated_at=o.updated_at,
                    demo_run_id=o.demo_run_id,
                    data_source=o.data_source,
                    event_count=len(o.events),
                    is_delayed=OrderService._is_delayed(o),
                )
                for o in synth_orders
            ])

            # If more slots needed on this page, fetch from historical
            remaining = limit - len(results)
            if remaining > 0 and hist_total > 0:
                hist_items = db.scalars(hist_stmt.offset(0).limit(remaining)).all()
                results.extend([OrderService._historical_to_summary(h) for h in hist_items])
        else:
            # Entire page comes from historical
            hist_offset = offset - synth_total
            hist_items = db.scalars(hist_stmt.offset(hist_offset).limit(limit)).all()
            results.extend([OrderService._historical_to_summary(h) for h in hist_items])

        return results, total

    @staticmethod
    def get_order_by_id(db: Session, order_id: str) -> OrderDetailResponse:
        clean_id = order_id.removeprefix("KGL-")
        # Check synthetic orders
        stmt = (
            select(Order)
            .options(
                joinedload(Order.customer),
                joinedload(Order.restaurant),
                joinedload(Order.delivery_partner),
                joinedload(Order.events),
            )
            .where(or_(Order.id == order_id, Order.external_order_id == order_id))
        )
        order = db.scalars(stmt).unique().first()
        if order:
            events = [
                OrderEventResponse(
                    id=e.id,
                    order_id=e.order_id,
                    event_type=e.event_type,
                    event_timestamp=e.event_timestamp,
                    event_metadata=e.event_metadata,
                    data_source=e.data_source,
                    created_at=e.created_at,
                )
                for e in sorted(order.events, key=lambda x: x.event_timestamp)
            ]

            return OrderDetailResponse(
                id=order.id,
                external_order_id=order.external_order_id,
                order_status=order.order_status,
                order_value=order.order_value,
                promised_delivery_at=order.promised_delivery_at,
                created_at=order.created_at,
                updated_at=order.updated_at,
                demo_run_id=order.demo_run_id,
                data_source=order.data_source,
                customer=order.customer,
                restaurant=order.restaurant,
                delivery_partner=order.delivery_partner,
                events=events,
                is_delayed=OrderService._is_delayed(order),
            )

        # Check HistoricalOrder
        h_stmt = select(HistoricalOrder).where(
            or_(
                HistoricalOrder.id == order_id,
                HistoricalOrder.order_id == order_id,
                HistoricalOrder.order_id == clean_id,
            )
        )
        h = db.scalars(h_stmt).first()
        if not h:
            raise EntityNotFoundError("Order", order_id)

        base_time = h.order_time or h.created_at
        historical_events: List[OrderEventResponse] = []

        historical_events.append(
            OrderEventResponse(
                id=f"ev_{h.id}_placed",
                order_id=h.id,
                event_type="ORDER_PLACED",
                event_timestamp=base_time,
                event_metadata={
                    "order_date": h.order_date,
                    "first_mile_distance_km": h.first_mile_distance,
                    "last_mile_distance_km": h.last_mile_distance,
                },
                data_source="PUBLIC_HISTORICAL",
                created_at=base_time,
            )
        )

        if h.allot_time:
            historical_events.append(
                OrderEventResponse(
                    id=f"ev_{h.id}_allot",
                    order_id=h.id,
                    event_type="RIDER_ASSIGNED",
                    event_timestamp=h.allot_time,
                    event_metadata={
                        "rider_id": h.rider_id,
                        "allotted_orders": h.allotted_orders,
                        "session_time_minutes": h.session_time,
                    },
                    data_source="PUBLIC_HISTORICAL",
                    created_at=h.allot_time,
                )
            )

        if h.accept_time:
            historical_events.append(
                OrderEventResponse(
                    id=f"ev_{h.id}_accept",
                    order_id=h.id,
                    event_type="RIDER_ACCEPTED",
                    event_timestamp=h.accept_time,
                    event_metadata={"rider_id": h.rider_id},
                    data_source="PUBLIC_HISTORICAL",
                    created_at=h.accept_time,
                )
            )

        if h.pickup_time:
            historical_events.append(
                OrderEventResponse(
                    id=f"ev_{h.id}_pickup",
                    order_id=h.id,
                    event_type="ORDER_PICKED_UP",
                    event_timestamp=h.pickup_time,
                    event_metadata={"rider_id": h.rider_id},
                    data_source="PUBLIC_HISTORICAL",
                    created_at=h.pickup_time,
                )
            )

        if h.reassigned_order:
            historical_events.append(
                OrderEventResponse(
                    id=f"ev_{h.id}_reassign",
                    order_id=h.id,
                    event_type="RIDER_REASSIGNED",
                    event_timestamp=h.allot_time or base_time,
                    event_metadata={
                        "method": h.reassignment_method or "auto",
                        "reason": h.reassignment_reason or "Operational delay",
                    },
                    data_source="PUBLIC_HISTORICAL",
                    created_at=h.allot_time or base_time,
                )
            )

        if h.cancelled and h.cancelled_time:
            historical_events.append(
                OrderEventResponse(
                    id=f"ev_{h.id}_cancel",
                    order_id=h.id,
                    event_type="ORDER_CANCELLED",
                    event_timestamp=h.cancelled_time,
                    event_metadata={"cancelled": True},
                    data_source="PUBLIC_HISTORICAL",
                    created_at=h.cancelled_time,
                )
            )
        elif h.delivered_time:
            historical_events.append(
                OrderEventResponse(
                    id=f"ev_{h.id}_deliver",
                    order_id=h.id,
                    event_type="ORDER_DELIVERED",
                    event_timestamp=h.delivered_time,
                    event_metadata={"delivered_orders_in_shift": h.delivered_orders},
                    data_source="PUBLIC_HISTORICAL",
                    created_at=h.delivered_time,
                )
            )

        order_status = "CANCELLED" if h.cancelled else "DELIVERED"
        promised_at = h.allot_time or base_time
        updated_at = h.delivered_time or h.cancelled_time or base_time

        return OrderDetailResponse(
            id=h.id,
            external_order_id=f"KGL-{h.order_id}",
            order_status=order_status,
            order_value=350.0,
            promised_delivery_at=promised_at,
            created_at=base_time,
            updated_at=updated_at,
            demo_run_id=None,
            data_source="PUBLIC_HISTORICAL",
            customer=CustomerResponse(
                id="historical-customer",
                name="Customer unassigned in historical dataset",
                phone="Not recorded in dataset",
                created_at=base_time,
            ),
            restaurant=RestaurantResponse(
                id="historical-restaurant",
                name="Restaurant unavailable in source dataset",
                city="N/A (Historical Kaggle Dataset)",
                area="N/A",
                cuisine="Historical Courier Telemetry",
                number_of_offers=0,
                pure_veg=False,
                created_at=base_time,
            ),
            delivery_partner=DeliveryPartnerResponse(
                id=f"rider_{h.rider_id}",
                name=f"Courier #{h.rider_id}" if h.rider_id else "Unassigned Courier",
                external_rider_id=h.rider_id,
                availability_status="OFFLINE",
                created_at=base_time,
            ),
            events=sorted(historical_events, key=lambda x: x.event_timestamp),
            is_delayed=bool(h.reassigned_order or h.cancelled),
        )

    @staticmethod
    def get_order_events(db: Session, order_id: str) -> List[OrderEventResponse]:
        # Delegate to get_order_by_id which supports both synthetic and historical orders
        order = OrderService.get_order_by_id(db, order_id)
        return order.events

    @staticmethod
    def get_dashboard_metrics(db: Session) -> Dict[str, Any]:
        orders = db.scalars(
            select(Order).options(joinedload(Order.events))
        ).unique().all()

        synthetic_count = len(orders)
        historical_total = db.scalar(select(func.count(HistoricalOrder.id))) or 0
        historical_cancelled = db.scalar(select(func.count(HistoricalOrder.id)).where(HistoricalOrder.cancelled.is_(True))) or 0
        historical_reassigned = db.scalar(select(func.count(HistoricalOrder.id)).where(HistoricalOrder.reassigned_order.is_(True))) or 0
        historical_delivered = historical_total - historical_cancelled

        total_orders = synthetic_count + historical_total

        active_statuses = {"PLACED", "CONFIRMED", "PREPARING", "READY_FOR_PICKUP", "OUT_FOR_DELIVERY"}
        delivered_statuses = {"DELIVERED", "RECOVERED"}

        active_orders = sum(1 for o in orders if o.order_status in active_statuses)
        delivered_orders = sum(1 for o in orders if o.order_status in delivered_statuses) + historical_delivered
        delayed_orders = sum(1 for o in orders if OrderService._is_delayed(o)) + historical_cancelled + historical_reassigned

        # Status distribution
        status_distribution: Dict[str, int] = {}
        for o in orders:
            status_distribution[o.order_status] = status_distribution.get(o.order_status, 0) + 1

        if historical_delivered > 0:
            status_distribution["DELIVERED"] = status_distribution.get("DELIVERED", 0) + historical_delivered
        if historical_cancelled > 0:
            status_distribution["CANCELLED"] = status_distribution.get("CANCELLED", 0) + historical_cancelled

        # Recent activity (latest 10 events from synthetic orders)
        recent_events = db.scalars(
            select(OrderEvent)
            .options(joinedload(OrderEvent.order).joinedload(Order.restaurant))
            .order_by(desc(OrderEvent.event_timestamp))
            .limit(10)
        ).all()

        activity = [
            {
                "id": ev.id,
                "order_id": ev.order_id,
                "external_order_id": ev.order.external_order_id if ev.order else "UNKNOWN",
                "restaurant_name": ev.order.restaurant.name if ev.order and ev.order.restaurant else "Restaurant unavailable in source dataset",
                "event_type": ev.event_type,
                "event_timestamp": ev.event_timestamp.isoformat(),
                "metadata": ev.event_metadata,
                "data_source": ev.data_source,
            }
            for ev in recent_events
        ]

        return {
            "total_orders": total_orders,
            "active_orders": active_orders,
            "delivered_orders": delivered_orders,
            "delayed_orders": delayed_orders,
            "status_distribution": status_distribution,
            "recent_activity": activity,
        }
