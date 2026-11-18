import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional


class DeliverySimulator:
    """Simulates delivery fleet logistics, rider assignment, arrival, and delivery."""

    def __init__(self, rng: random.Random):
        self.rng = rng

    def simulate_assignment(
        self,
        start_time: datetime,
        delay_assignment: bool = False,
        primary_rider_name: str = "Rider Partner",
        reassigned_rider_name: Optional[str] = None,
    ) -> Tuple[datetime, List[Dict[str, Any]], bool]:
        """
        Simulates rider search and assignment.
        Returns: (assignment_time, list_of_events, was_reassigned)
        """
        events: List[Dict[str, Any]] = []
        current_time = start_time

        # Search started
        search_start_delay = timedelta(minutes=self.rng.randint(1, 2))
        current_time += search_start_delay
        events.append({
            "event_type": "RIDER_SEARCH_STARTED",
            "event_timestamp": current_time,
            "metadata": {
                "search_radius_km": 3.0,
                "available_fleet_count": 2 if delay_assignment else 12,
            },
        })

        if delay_assignment:
            # Rider search takes long / initial rejection
            delay_duration = timedelta(minutes=self.rng.randint(8, 14))
            current_time += delay_duration
            events.append({
                "event_type": "RIDER_SEARCH_TIMEOUT",
                "event_timestamp": current_time,
                "metadata": {
                    "reason": "High fleet utilization in pickup sector",
                    "search_radius_expanded_km": 6.5,
                },
            })

            # Reassignment / Expanded search
            retry_duration = timedelta(minutes=self.rng.randint(3, 6))
            current_time += retry_duration
            events.append({
                "event_type": "RIDER_ASSIGNED",
                "event_timestamp": current_time,
                "metadata": {
                    "rider_name": reassigned_rider_name or f"Reassigned {primary_rider_name}",
                    "initial_eta_minutes": 14,
                    "reassignment_occurred": True,
                },
            })
            return current_time, events, True

        # Normal assignment (2 - 4 mins after search started)
        normal_assign_delay = timedelta(minutes=self.rng.randint(2, 4))
        current_time += normal_assign_delay
        events.append({
            "event_type": "RIDER_ASSIGNED",
            "event_timestamp": current_time,
            "metadata": {
                "rider_name": primary_rider_name,
                "initial_eta_minutes": 8,
                "reassignment_occurred": False,
            },
        })
        return current_time, events, False

    def simulate_pickup(
        self,
        ready_time: datetime,
        rider_assigned_time: datetime,
    ) -> Tuple[datetime, List[Dict[str, Any]]]:
        """
        Simulates rider arrival at restaurant and order pickup.
        Pickup happens after BOTH the food is ready and the rider has reached store.
        """
        events: List[Dict[str, Any]] = []
        # Rider travel to store: 5 - 10 mins after assignment
        rider_store_arrival = rider_assigned_time + timedelta(minutes=self.rng.randint(5, 10))
        events.append({
            "event_type": "RIDER_ARRIVED_AT_STORE",
            "event_timestamp": rider_store_arrival,
            "metadata": {
                "store_proximity_meters": 20,
            },
        })

        # Pickup occurs when both rider is at store and food is ready
        pickup_time = max(ready_time, rider_store_arrival) + timedelta(minutes=self.rng.randint(1, 3))
        events.append({
            "event_type": "ORDER_PICKED_UP",
            "event_timestamp": pickup_time,
            "metadata": {
                "otp_verified": True,
                "transit_status": "OUT_FOR_DELIVERY",
            },
        })
        return pickup_time, events

    def simulate_delivery_completion(
        self,
        arrival_time: datetime,
    ) -> Tuple[datetime, List[Dict[str, Any]]]:
        """
        Simulates final doorstep handover.
        """
        events: List[Dict[str, Any]] = []
        delivery_time = arrival_time + timedelta(minutes=self.rng.randint(1, 3))
        events.append({
            "event_type": "ORDER_DELIVERED",
            "event_timestamp": delivery_time,
            "metadata": {
                "delivery_confirmation": "DOORSTEP_HANDOVER",
                "customer_rating_prompt_sent": True,
            },
        })
        return delivery_time, events
