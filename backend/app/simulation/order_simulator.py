import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from backend.app.schemas.simulation import ScenarioType
from backend.app.simulation.restaurant_simulator import RestaurantSimulator
from backend.app.simulation.delivery_simulator import DeliverySimulator
from backend.app.simulation.traffic_simulator import TrafficSimulator


class OrderSimulator:
    """
    Core Order Simulator that generates end-to-end reproducible scenarios
    with chronologically ordered events and realistic operational metadata.
    """

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        self.rng = random.Random(seed)
        self.restaurant_sim = RestaurantSimulator(self.rng)
        self.delivery_sim = DeliverySimulator(self.rng)
        self.traffic_sim = TrafficSimulator(self.rng)

    def generate_scenario(
        self,
        scenario: ScenarioType,
        customer: Dict[str, Any],
        restaurant: Dict[str, Any],
        primary_rider: Dict[str, Any],
        alternate_rider: Optional[Dict[str, Any]] = None,
        base_time: Optional[datetime] = None,
        custom_params: Optional[Dict[str, Any]] = None,
        demo_run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes a deterministic or random scenario generation.
        Returns a dict containing:
          - order: dict with initial/final order fields
          - events: list of chronological event dicts
          - assigned_rider: Dict[str, Any]
        """
        if base_time is None:
            # Anchor around now minus 45 minutes to simulate a freshly resolved or active order
            base_time = datetime.now(timezone.utc) - timedelta(minutes=self.rng.randint(35, 60))

        order_id = str(uuid.uuid4())
        short_code = uuid.uuid4().hex[:4].upper()
        ext_order_id = f"SWIG-SIM-{self.rng.randint(1000, 9999)}-{short_code}"
        promised_delivery_at = base_time + timedelta(minutes=35)
        order_value = round(self.rng.uniform(220.0, 980.0), 2)
        demo_run_id = demo_run_id or f"run_{uuid.uuid4().hex[:10]}"

        events: List[Dict[str, Any]] = []

        # 1. ORDER_PLACED event
        events.append({
            "order_id": order_id,
            "event_type": "ORDER_PLACED",
            "event_timestamp": base_time,
            "metadata": {
                "items_count": self.rng.randint(1, 4),
                "payment_mode": self.rng.choice(["UPI", "CREDIT_CARD", "SWIGGY_MONEY"]),
                "cuisine": restaurant.get("cuisine", "North Indian"),
                "city": restaurant.get("city", "Bengaluru"),
                "promised_delivery_at": promised_delivery_at.isoformat(),
            },
            "data_source": "SYNTHETIC",
        })

        active_rider = primary_rider
        final_status = "DELIVERED"
        last_timestamp = base_time

        if scenario == ScenarioType.NORMAL_ORDER:
            # 2. Restaurant acceptance & prep
            prep_ready_time, prep_events, _ = self.restaurant_sim.simulate_prep_flow(
                start_time=base_time, delay_scenario=False
            )
            for e in prep_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(prep_events)

            # 3. Rider search and assignment
            assign_time, assign_events, _ = self.delivery_sim.simulate_assignment(
                start_time=base_time,
                delay_assignment=False,
                primary_rider_name=primary_rider["name"],
            )
            for e in assign_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(assign_events)

            # 4. Pickup
            pickup_time, pickup_events = self.delivery_sim.simulate_pickup(
                ready_time=prep_ready_time, rider_assigned_time=assign_time
            )
            for e in pickup_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(pickup_events)

            # 5. Normal Transit
            transit_arrival_time, transit_events, _ = self.traffic_sim.simulate_transit(
                pickup_time=pickup_time,
                promised_time=promised_delivery_at,
                delay_transit=False,
            )
            for e in transit_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(transit_events)

            # 6. Delivery completion
            deliv_time, deliv_events = self.delivery_sim.simulate_delivery_completion(transit_arrival_time)
            for e in deliv_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(deliv_events)
            final_status = "DELIVERED"
            last_timestamp = deliv_time

        elif scenario == ScenarioType.RESTAURANT_DELAY:
            # Kitchen Delay
            assign_time, assign_events, _ = self.delivery_sim.simulate_assignment(
                start_time=base_time,
                delay_assignment=False,
                primary_rider_name=primary_rider["name"],
            )
            for e in assign_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(assign_events)

            prep_ready_time, prep_events, _ = self.restaurant_sim.simulate_prep_flow(
                start_time=base_time, delay_scenario=True
            )
            for e in prep_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(prep_events)

            pickup_time, pickup_events = self.delivery_sim.simulate_pickup(
                ready_time=prep_ready_time, rider_assigned_time=assign_time
            )
            for e in pickup_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(pickup_events)

            transit_arrival_time, transit_events, _ = self.traffic_sim.simulate_transit(
                pickup_time=pickup_time,
                promised_time=promised_delivery_at,
                delay_transit=False,
            )
            for e in transit_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(transit_events)

            deliv_time, deliv_events = self.delivery_sim.simulate_delivery_completion(transit_arrival_time)
            for e in deliv_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(deliv_events)
            final_status = "DELIVERED"
            last_timestamp = deliv_time

        elif scenario == ScenarioType.DELIVERY_DELAY:
            # Traffic/Transit Delay
            prep_ready_time, prep_events, _ = self.restaurant_sim.simulate_prep_flow(
                start_time=base_time, delay_scenario=False
            )
            for e in prep_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(prep_events)

            assign_time, assign_events, _ = self.delivery_sim.simulate_assignment(
                start_time=base_time,
                delay_assignment=False,
                primary_rider_name=primary_rider["name"],
            )
            for e in assign_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(assign_events)

            pickup_time, pickup_events = self.delivery_sim.simulate_pickup(
                ready_time=prep_ready_time, rider_assigned_time=assign_time
            )
            for e in pickup_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(pickup_events)

            # Heavy traffic transit
            transit_arrival_time, transit_events, _ = self.traffic_sim.simulate_transit(
                pickup_time=pickup_time,
                promised_time=promised_delivery_at,
                delay_transit=True,
            )
            for e in transit_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(transit_events)

            deliv_time, deliv_events = self.delivery_sim.simulate_delivery_completion(transit_arrival_time)
            for e in deliv_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(deliv_events)
            final_status = "DELIVERED"
            last_timestamp = deliv_time

        elif scenario == ScenarioType.ASSIGNMENT_DELAY:
            # Assignment Delay & Reassignment
            alt_name = alternate_rider["name"] if alternate_rider else "Alternate Fleet Partner"
            active_rider = alternate_rider if alternate_rider else primary_rider

            prep_ready_time, prep_events, _ = self.restaurant_sim.simulate_prep_flow(
                start_time=base_time, delay_scenario=False
            )
            for e in prep_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(prep_events)

            assign_time, assign_events, _ = self.delivery_sim.simulate_assignment(
                start_time=base_time,
                delay_assignment=True,
                primary_rider_name=primary_rider["name"],
                reassigned_rider_name=alt_name,
            )
            for e in assign_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(assign_events)

            pickup_time, pickup_events = self.delivery_sim.simulate_pickup(
                ready_time=prep_ready_time, rider_assigned_time=assign_time
            )
            for e in pickup_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(pickup_events)

            transit_arrival_time, transit_events, _ = self.traffic_sim.simulate_transit(
                pickup_time=pickup_time,
                promised_time=promised_delivery_at,
                delay_transit=False,
            )
            for e in transit_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(transit_events)

            deliv_time, deliv_events = self.delivery_sim.simulate_delivery_completion(transit_arrival_time)
            for e in deliv_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(deliv_events)
            final_status = "DELIVERED"
            last_timestamp = deliv_time

        elif scenario == ScenarioType.FAILED_RECOVERY:
            # Critical unresolvable operational issue
            assign_time, assign_events, _ = self.delivery_sim.simulate_assignment(
                start_time=base_time,
                delay_assignment=False,
                primary_rider_name=primary_rider["name"],
            )
            for e in assign_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(assign_events)

            fail_time, fail_events, _ = self.restaurant_sim.simulate_prep_flow(
                start_time=base_time, fail_scenario=True
            )
            for e in fail_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(fail_events)

            # Recovery attempt
            attempt_time = fail_time + timedelta(minutes=3)
            events.append({
                "order_id": order_id,
                "event_type": "RECOVERY_ATTEMPTED",
                "event_timestamp": attempt_time,
                "metadata": {
                    "action": "AUTO_REORDER_NEARBY_MERCHANT",
                    "target_merchant_id": "RESTAURANT_BRANCH_2",
                },
                "data_source": "SYNTHETIC",
            })

            # Recovery failed
            recovery_fail_time = attempt_time + timedelta(minutes=4)
            events.append({
                "order_id": order_id,
                "event_type": "RECOVERY_FAILED",
                "event_timestamp": recovery_fail_time,
                "metadata": {
                    "reason": "Alternate merchant has 45+ minute prep queue, SLA breached",
                    "retry_count_exceeded": True,
                },
                "data_source": "SYNTHETIC",
            })

            # Escalation
            escalation_time = recovery_fail_time + timedelta(minutes=2)
            events.append({
                "order_id": order_id,
                "event_type": "ORDER_ESCALATED",
                "event_timestamp": escalation_time,
                "metadata": {
                    "assigned_tier": "OPERATIONS_DESK_LEVEL_2",
                    "recommended_action": "ISSUE_FULL_REFUND_AND_APOLOGY_CALL",
                    "priority": "HIGH",
                },
                "data_source": "SYNTHETIC",
            })
            final_status = "ESCALATED"
            last_timestamp = escalation_time

        elif scenario == ScenarioType.SUCCESSFUL_RECOVERY:
            # Issue detected, autonomous recovery succeeds!
            prep_ready_time, prep_events, _ = self.restaurant_sim.simulate_prep_flow(
                start_time=base_time, delay_scenario=False
            )
            for e in prep_events:
                e["order_id"] = order_id
                e["data_source"] = "SYNTHETIC"
            events.extend(prep_events)

            # Initial rider assigned
            assign_time = base_time + timedelta(minutes=3)
            events.append({
                "order_id": order_id,
                "event_type": "RIDER_ASSIGNED",
                "event_timestamp": assign_time,
                "metadata": {
                    "rider_name": primary_rider["name"],
                    "vehicle": "Two-Wheeler EV",
                },
                "data_source": "SYNTHETIC",
            })

            # Rider breakdown anomaly detected
            anomaly_time = assign_time + timedelta(minutes=5)
            events.append({
                "order_id": order_id,
                "event_type": "OPERATIONAL_ANOMALY_DETECTED",
                "event_timestamp": anomaly_time,
                "metadata": {
                    "anomaly_type": "RIDER_VEHICLE_BREAKDOWN",
                    "reported_by": primary_rider["name"],
                    "location": "Near Koramangala 5th Block",
                },
                "data_source": "SYNTHETIC",
            })

            # Autonomous recovery engine triggers reassignment & coupon
            recovery_time = anomaly_time + timedelta(minutes=2)
            events.append({
                "order_id": order_id,
                "event_type": "RECOVERY_TRIGGERED",
                "event_timestamp": recovery_time,
                "metadata": {
                    "policy": "PRIORITY_FLEET_REALLOCATION",
                    "appeasement": "CREDITED_100_RESOLVEAI_WALLET",
                    "customer_notified": True,
                },
                "data_source": "SYNTHETIC",
            })

            # Alternate rider reassigned
            alt_name = alternate_rider["name"] if alternate_rider else "VIP Priority Courier"
            active_rider = alternate_rider if alternate_rider else primary_rider
            reassign_time = recovery_time + timedelta(minutes=3)
            events.append({
                "order_id": order_id,
                "event_type": "RIDER_REASSIGNED",
                "event_timestamp": reassign_time,
                "metadata": {
                    "new_rider_name": alt_name,
                    "dispatch_priority": "P0_EMERGENCY",
                },
                "data_source": "SYNTHETIC",
            })

            # Fast pickup by alternate rider
            pickup_time = max(prep_ready_time, reassign_time) + timedelta(minutes=4)
            events.append({
                "order_id": order_id,
                "event_type": "ORDER_PICKED_UP",
                "event_timestamp": pickup_time,
                "metadata": {
                    "picked_up_by": alt_name,
                    "transit_status": "EXPRESS_ROUTE",
                },
                "data_source": "SYNTHETIC",
            })

            # Transit
            transit_arrival_time = pickup_time + timedelta(minutes=11)
            events.append({
                "order_id": order_id,
                "event_type": "RECOVERY_SUCCESSFUL",
                "event_timestamp": transit_arrival_time,
                "metadata": {
                    "sla_status": "SLA_PRESERVED_UNDER_40_MIN",
                    "effective_recovery_duration_minutes": 5.0,
                },
                "data_source": "SYNTHETIC",
            })

            # Delivered
            deliv_time = transit_arrival_time + timedelta(minutes=2)
            events.append({
                "order_id": order_id,
                "event_type": "ORDER_DELIVERED",
                "event_timestamp": deliv_time,
                "metadata": {
                    "delivery_confirmation": "DOORSTEP_HANDOVER",
                    "customer_feedback": "Appreciated proactive proactive notification",
                },
                "data_source": "SYNTHETIC",
            })
            final_status = "RECOVERED"
            last_timestamp = deliv_time

        # Ensure strict chronological sorting by event_timestamp
        events.sort(key=lambda x: x["event_timestamp"])

        order_data = {
            "id": order_id,
            "external_order_id": ext_order_id,
            "customer_id": customer["id"],
            "restaurant_id": restaurant["id"],
            "delivery_partner_id": active_rider["id"] if active_rider else None,
            "order_status": final_status,
            "order_value": order_value,
            "promised_delivery_at": promised_delivery_at,
            "created_at": base_time,
            "updated_at": last_timestamp,
            "demo_run_id": demo_run_id,
            "data_source": "SYNTHETIC",
        }

        return {
            "order": order_data,
            "events": events,
            "assigned_rider": active_rider,
        }
