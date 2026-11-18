import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple


class TrafficSimulator:
    """Simulates transit route traffic, bottlenecks, weather, and ETA revisions."""

    def __init__(self, rng: random.Random):
        self.rng = rng

    def simulate_transit(
        self,
        pickup_time: datetime,
        promised_time: datetime,
        delay_transit: bool = False,
    ) -> Tuple[datetime, List[Dict[str, Any]], bool]:
        """
        Simulates rider journey from restaurant to customer.
        Returns: (arrival_time, list_of_events, is_breached)
        """
        events: List[Dict[str, Any]] = []
        current_time = pickup_time

        # Normal transit duration: 12 - 18 minutes
        normal_transit_minutes = self.rng.randint(12, 18)

        if delay_transit:
            # Transit encounters traffic congestion or heavy rain
            mid_journey = pickup_time + timedelta(minutes=self.rng.randint(5, 8))
            events.append({
                "event_type": "TRAFFIC_CONGESTION_DETECTED",
                "event_timestamp": mid_journey,
                "metadata": {
                    "congestion_level": "HEAVY",
                    "route_segment": "Outer Ring Road Junction",
                    "average_speed_kmh": round(self.rng.uniform(8.5, 12.0), 1),
                    "weather_condition": self.rng.choice(["WATERLOGGED_ROAD", "HEAVY_MONSOON_RAIN", "ROAD_CONSTRUCTION"]),
                },
            })

            # ETA revised later than promised time
            revised_transit_minutes = normal_transit_minutes + self.rng.randint(20, 35)
            revised_arrival_time = pickup_time + timedelta(minutes=revised_transit_minutes)

            eta_warning_time = mid_journey + timedelta(minutes=2)
            events.append({
                "event_type": "DELIVERY_DELAY_PREDICTED",
                "event_timestamp": eta_warning_time,
                "metadata": {
                    "original_eta": promised_time.isoformat(),
                    "revised_eta": revised_arrival_time.isoformat(),
                    "predicted_delay_minutes": round((revised_arrival_time - promised_time).total_seconds() / 60, 1),
                    "sla_breach_risk": "HIGH",
                },
            })

            is_breached = revised_arrival_time > promised_time
            return revised_arrival_time, events, is_breached

        # Normal transit
        arrival_time = pickup_time + timedelta(minutes=normal_transit_minutes)
        is_breached = arrival_time > promised_time
        return arrival_time, events, is_breached
