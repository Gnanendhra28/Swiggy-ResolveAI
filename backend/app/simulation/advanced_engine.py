"""
Swiggy ResolveAI — Advanced Operational Simulation Engine.

Provides deterministic, reproducible, counterfactual simulation for delivery lifecycles across
12 operational scenarios with configurable kitchen, fleet, route, traffic, and recovery knobs.
All simulated telemetry is labeled 'SYNTHETIC'.
"""

import math
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class SimulationConfig:
    """Configurable operational knobs for advanced delivery simulations."""
    scenario_type: str = "NORMAL_DELIVERY"
    random_seed: int = 42
    order_volume: int = 50
    prep_time_base_min: float = 16.0
    kitchen_queue_length: int = 3
    restaurant_capacity: int = 20
    courier_availability_ratio: float = 0.85
    courier_acceptance_delay_min: float = 2.0
    first_mile_distance_km: float = 2.0
    last_mile_distance_km: float = 3.8
    traffic_congestion_factor: float = 1.2
    recovery_action_effectiveness: float = 0.80  # 80% effective, 20% neutral/failed
    recovery_action_delay_min: float = 2.0
    gross_order_value_inr: float = 450.0
    contribution_margin_ratio: float = 0.20  # 20% platform commission / contribution take rate on GOV

    # Configurable economic assumptions (INR)
    cost_kitchen_ping_inr: float = 5.0
    cost_courier_prioritize_inr: float = 15.0
    cost_courier_reassign_inr: float = 35.0
    cost_customer_notification_inr: float = 2.0
    cost_apology_voucher_inr: float = 50.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_type": self.scenario_type,
            "random_seed": self.random_seed,
            "order_volume": self.order_volume,
            "prep_time_base_min": self.prep_time_base_min,
            "kitchen_queue_length": self.kitchen_queue_length,
            "restaurant_capacity": self.restaurant_capacity,
            "courier_availability_ratio": self.courier_availability_ratio,
            "courier_acceptance_delay_min": self.courier_acceptance_delay_min,
            "first_mile_distance_km": self.first_mile_distance_km,
            "last_mile_distance_km": self.last_mile_distance_km,
            "traffic_congestion_factor": self.traffic_congestion_factor,
            "recovery_action_effectiveness": self.recovery_action_effectiveness,
            "recovery_action_delay_min": self.recovery_action_delay_min,
            "gross_order_value_inr": self.gross_order_value_inr,
            "contribution_margin_ratio": self.contribution_margin_ratio,
            "cost_kitchen_ping_inr": self.cost_kitchen_ping_inr,
            "cost_courier_prioritize_inr": self.cost_courier_prioritize_inr,
            "cost_courier_reassign_inr": self.cost_courier_reassign_inr,
            "cost_customer_notification_inr": self.cost_customer_notification_inr,
            "cost_apology_voucher_inr": self.cost_apology_voucher_inr,
        }


@dataclass
class SimulatedOrderState:
    """
    Immutable baseline counterfactual state for an order before strategy intervention.
    Enables matched, identical initial conditions across all 4 recovery strategies.
    """
    order_id: str
    external_order_id: str
    seed: int
    scenario_type: str
    order_time: datetime
    promised_delivery_at: datetime
    promised_duration_min: float
    order_value_inr: float

    # Entities
    customer: Dict[str, Any]
    restaurant: Dict[str, Any]
    primary_courier: Dict[str, Any]
    alternate_courier: Dict[str, Any]

    # Route & Environment
    first_mile_km: float
    last_mile_km: float
    traffic_congestion: float
    kitchen_queue_depth: int

    # Baseline Raw Latencies (if zero intervention occurred)
    raw_prep_time_min: float
    raw_allotment_delay_min: float
    raw_courier_accept_delay_min: float
    raw_first_mile_transit_min: float
    raw_last_mile_transit_min: float

    # Cancellation propensity model parameters
    base_cancellation_propensity: float
    critical_disruption: bool  # Equipment failure or unresolvable event
    customer_consent: bool = True

    # Pre-generated initial events at t=0 to t=allotment
    initial_events: List[Dict[str, Any]] = field(default_factory=list)


class AdvancedSimulationEngine:
    """
    Advanced Simulation Engine generating matched counterfactual order batches
    across the 12 required operational scenarios.
    """

    RESTAURANTS = [
        {"id": "rest_sim_1", "name": "Meghana Foods Indiranagar", "city": "Bengaluru", "area": "Indiranagar", "rating": 4.5},
        {"id": "rest_sim_2", "name": "Empire Restaurant Koramangala", "city": "Bengaluru", "area": "Koramangala", "rating": 4.3},
        {"id": "rest_sim_3", "name": "A2B Veg HSR Layout", "city": "Bengaluru", "area": "HSR Layout", "rating": 4.4},
        {"id": "rest_sim_4", "name": "Leon Grill Whitefield", "city": "Bengaluru", "area": "Whitefield", "rating": 4.2},
    ]

    CUSTOMERS = [
        {"id": "cust_sim_1", "name": "Pooja Sharma", "phone": "+919876543211", "consent": True},
        {"id": "cust_sim_2", "name": "Aditya Verma", "phone": "+919845123457", "consent": True},
        {"id": "cust_sim_3", "name": "Kavita Rao", "phone": "+919988776658", "consent": False},  # Opted out
        {"id": "cust_sim_4", "name": "Naveen Sundaram", "phone": "+919711223349", "consent": True},
    ]

    COURIERS = [
        {"id": "dp_sim_1", "name": "Kiran Kumar", "phone": "+919655443321"},
        {"id": "dp_sim_2", "name": "Manju Gowda", "phone": "+919655443322"},
        {"id": "dp_sim_3", "name": "Santhosh Naik", "phone": "+919655443323"},
        {"id": "dp_sim_4", "name": "Raghu Prasad", "phone": "+919655443324"},
    ]

    @classmethod
    def generate_order_batch(cls, config: SimulationConfig) -> List[SimulatedOrderState]:
        """
        Deterministically produces N matched order states based on random_seed and config.
        """
        rng = random.Random(config.random_seed)
        now = datetime.now(timezone.utc)
        batch: List[SimulatedOrderState] = []

        for i in range(config.order_volume):
            order_rng = random.Random(config.random_seed * 1000 + i)
            order_id = str(uuid.uuid4())
            short_id = uuid.uuid4().hex[:6].upper()
            ext_order_id = f"SWIG-P5-{config.random_seed}-{i+1:03d}-{short_id}"

            order_time = now - timedelta(minutes=order_rng.randint(30, 90))
            promised_delivery_at = order_time + timedelta(minutes=35)
            order_val = round(order_rng.uniform(250.0, 850.0), 2)

            rest = order_rng.choice(cls.RESTAURANTS)
            cust = order_rng.choice(cls.CUSTOMERS)
            courier_p = order_rng.choice(cls.COURIERS)
            courier_alt = order_rng.choice([c for c in cls.COURIERS if c["id"] != courier_p["id"]])

            # Derive scenario factors
            stype = config.scenario_type.upper()

            # 1. Distances
            fm_dist = max(0.5, order_rng.gauss(config.first_mile_distance_km, 0.4))
            lm_dist = max(1.0, order_rng.gauss(config.last_mile_distance_km, 0.8))
            if stype == "LONG_DISTANCE_DELIVERY":
                lm_dist = max(9.0, order_rng.uniform(10.0, 16.0))

            # 2. Traffic
            traffic_fac = max(1.0, order_rng.gauss(config.traffic_congestion_factor, 0.15))
            if stype in ("TRAFFIC_CONGESTION", "DELIVERY_DELAY"):
                traffic_fac = max(1.9, order_rng.uniform(2.0, 2.7))

            # 3. Kitchen Queue & Prep
            queue_depth = config.kitchen_queue_length
            prep_base = config.prep_time_base_min
            if stype in ("RESTAURANT_PREP_DELAY", "RESTAURANT_DELAY"):
                queue_depth += order_rng.randint(3, 6)
                prep_base += order_rng.uniform(14.0, 24.0)
            elif stype == "RESTAURANT_CAPACITY_OVERLOAD":
                queue_depth += order_rng.randint(7, 12)
                prep_base += order_rng.uniform(20.0, 32.0)
            elif stype in ("COMBINED_KITCHEN_DELIVERY_DELAY", "COMBINED_KITCHEN_DELIVERY"):
                queue_depth += order_rng.randint(4, 7)
                prep_base += order_rng.uniform(15.0, 25.0)

            raw_prep = max(12.0, order_rng.gauss(prep_base, 2.5))

            # 4. Courier Allotment & Acceptance
            allot_delay = max(0.8, order_rng.gauss(2.0, 0.5))
            accept_delay = max(0.5, order_rng.gauss(config.courier_acceptance_delay_min, 0.4))

            if stype in ("COURIER_ASSIGNMENT_DELAY", "ASSIGNMENT_DELAY"):
                allot_delay = max(9.0, order_rng.uniform(10.0, 18.0))
            elif stype == "COURIER_ACCEPTANCE_DELAY":
                accept_delay = max(6.0, order_rng.uniform(7.0, 12.0))
            elif stype == "COURIER_REASSIGNMENT":
                allot_delay = max(12.0, order_rng.uniform(12.0, 19.0))
                accept_delay = max(4.0, order_rng.uniform(4.0, 8.0))

            # 5. Transit times (assumes 18 km/h nominal first-mile, 15 km/h last-mile)
            fm_speed_kmh = 18.0 / traffic_fac
            lm_speed_kmh = 15.0 / traffic_fac
            raw_fm_transit = (fm_dist / fm_speed_kmh) * 60.0
            raw_lm_transit = (lm_dist / lm_speed_kmh) * 60.0

            # 6. Cancellation propensity & critical disruption
            base_cancel = 0.02
            critical_disruption = False
            if stype == "HIGH_CANCELLATION_RISK":
                base_cancel = order_rng.uniform(0.35, 0.65)
            elif stype in ("FAILED_RECOVERY_ATTEMPT", "FAILED_RECOVERY"):
                critical_disruption = True
                base_cancel = order_rng.uniform(0.50, 0.85)

            # Build initial chronological events (ORDER_PLACED, ORDER_ACCEPTED, RIDER_ASSIGNED)
            ev_placed = {
                "order_id": order_id,
                "event_type": "ORDER_PLACED",
                "event_timestamp": order_time,
                "metadata": {
                    "last_mile_distance": round(lm_dist, 2),
                    "items_count": order_rng.randint(2, 5),
                    "customer_consent": cust.get("consent", True),
                },
                "data_source": "SYNTHETIC",
            }
            ev_accepted = {
                "order_id": order_id,
                "event_type": "ORDER_ACCEPTED",
                "event_timestamp": order_time + timedelta(minutes=order_rng.uniform(1.0, 2.5)),
                "metadata": {
                    "kitchen_queue_depth": queue_depth,
                    "estimated_prep_min": round(raw_prep, 1),
                },
                "data_source": "SYNTHETIC",
            }
            ev_assigned = {
                "order_id": order_id,
                "event_type": "RIDER_ASSIGNED",
                "event_timestamp": order_time + timedelta(minutes=allot_delay),
                "metadata": {
                    "rider_id": courier_p["id"],
                    "rider_name": courier_p["name"],
                    "first_mile_distance": round(fm_dist, 2),
                },
                "data_source": "SYNTHETIC",
            }

            initial_events = [ev_placed, ev_accepted, ev_assigned]

            state = SimulatedOrderState(
                order_id=order_id,
                external_order_id=ext_order_id,
                seed=config.random_seed * 1000 + i,
                scenario_type=stype,
                order_time=order_time,
                promised_delivery_at=promised_delivery_at,
                promised_duration_min=35.0,
                order_value_inr=order_val,
                customer=cust,
                restaurant=rest,
                primary_courier=courier_p,
                alternate_courier=courier_alt,
                first_mile_km=round(fm_dist, 2),
                last_mile_km=round(lm_dist, 2),
                traffic_congestion=round(traffic_fac, 2),
                kitchen_queue_depth=queue_depth,
                raw_prep_time_min=round(raw_prep, 1),
                raw_allotment_delay_min=round(allot_delay, 1),
                raw_courier_accept_delay_min=round(accept_delay, 1),
                raw_first_mile_transit_min=round(raw_fm_transit, 1),
                raw_last_mile_transit_min=round(raw_lm_transit, 1),
                base_cancellation_propensity=base_cancel,
                critical_disruption=critical_disruption,
                customer_consent=cust.get("consent", True),
                initial_events=initial_events,
            )
            batch.append(state)

        return batch
