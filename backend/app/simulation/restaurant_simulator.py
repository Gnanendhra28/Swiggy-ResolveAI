import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple


class RestaurantSimulator:
    """Simulates restaurant kitchen operations, acceptance, and preparation."""

    def __init__(self, rng: random.Random):
        self.rng = rng

    def simulate_prep_flow(
        self,
        start_time: datetime,
        delay_scenario: bool = False,
        fail_scenario: bool = False,
    ) -> Tuple[datetime, List[Dict[str, Any]], bool]:
        """
        Returns:
            (food_ready_time, list_of_events, is_delayed)
        """
        events: List[Dict[str, Any]] = []
        current_time = start_time

        # 1. Order Accepted (1 - 3 mins after placed)
        accept_delay = timedelta(minutes=self.rng.randint(1, 3), seconds=self.rng.randint(0, 59))
        current_time += accept_delay
        events.append({
            "event_type": "RESTAURANT_ACCEPTED",
            "event_timestamp": current_time,
            "metadata": {
                "kitchen_status": "busy" if delay_scenario else "normal",
                "estimated_prep_minutes": 35 if delay_scenario else 15,
            },
        })

        # 2. Preparation Started (1 - 2 mins later)
        prep_start_delay = timedelta(minutes=self.rng.randint(1, 2))
        current_time += prep_start_delay
        events.append({
            "event_type": "PREPARATION_STARTED",
            "event_timestamp": current_time,
            "metadata": {
                "kitchen_queue_position": self.rng.randint(4, 9) if delay_scenario else self.rng.randint(1, 3),
            },
        })

        if fail_scenario:
            # Kitchen encounters an unresolvable issue (e.g. inventory stockout or power outage)
            fail_delay = timedelta(minutes=self.rng.randint(8, 12))
            current_time += fail_delay
            events.append({
                "event_type": "KITCHEN_STOCKOUT_DETECTED",
                "event_timestamp": current_time,
                "metadata": {
                    "reason": "Primary ingredients out of stock / kitchen equipment failure",
                    "can_fulfill": False,
                },
            })
            return current_time, events, True

        if delay_scenario:
            # Kitchen delay event occurs during prep
            prep_delay_detected = timedelta(minutes=self.rng.randint(10, 15))
            current_time += prep_delay_detected
            events.append({
                "event_type": "KITCHEN_DELAY_DETECTED",
                "event_timestamp": current_time,
                "metadata": {
                    "reason": "High order volume / complex recipe backlog",
                    "delay_minutes": self.rng.randint(15, 25),
                },
            })
            # Prep finishes late
            remaining_prep = timedelta(minutes=self.rng.randint(12, 18))
            current_time += remaining_prep
            events.append({
                "event_type": "FOOD_READY",
                "event_timestamp": current_time,
                "metadata": {
                    "total_prep_duration_minutes": round((current_time - start_time).total_seconds() / 60, 1),
                    "packaging_sealed": True,
                },
            })
            return current_time, events, True

        # Normal prep flow (12 - 18 minutes total)
        normal_prep = timedelta(minutes=self.rng.randint(12, 16))
        current_time += normal_prep
        events.append({
            "event_type": "FOOD_READY",
            "event_timestamp": current_time,
            "metadata": {
                "total_prep_duration_minutes": round((current_time - start_time).total_seconds() / 60, 1),
                "packaging_sealed": True,
            },
        })
        return current_time, events, False
