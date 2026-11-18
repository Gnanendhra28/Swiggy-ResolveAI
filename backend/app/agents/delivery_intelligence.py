from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.app.core.logging import logger
from backend.app.agents.schemas import DeliveryEvidence
from backend.app.agents.state import MultiAgentInvestigationState


class DeliveryIntelligenceAgent:
    """
    Delivery Intelligence Agent:
    - Investigates courier assignment status and allotment latency.
    - Inspects courier acceptance latency, first-mile distance, and reassignments.
    - Evaluates transit conditions using simulated traffic telemetry.
    - Does NOT claim access to live external Swiggy fleet GPS or live municipal traffic systems.
    - Generates evidence-grounded operational impact and suspected fleet bottlenecks.
    """

    def investigate(self, state: MultiAgentInvestigationState) -> MultiAgentInvestigationState:
        order_ctx = state.get("order_context", {})
        events = state.get("order_events", [])
        delivery_partner = order_ctx.get("delivery_partner") or {}
        external_order_id = state.get("external_order_id", "UNKNOWN")

        logger.info(f"DeliveryIntelligenceAgent investigating fleet status for order {external_order_id}")

        created_at = order_ctx.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except Exception:
                created_at = datetime.now(timezone.utc)
        elif created_at is None:
            created_at = datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        # 1. Courier allotment
        allot_time: Optional[datetime] = None
        for ev in events:
            if ev.get("event_type") in ("RIDER_ASSIGNED", "COURIER_ALLOTTED", "RIDER_ALLOTTED"):
                ts = ev.get("event_timestamp")
                if isinstance(ts, str):
                    try:
                        allot_time = datetime.fromisoformat(ts)
                    except Exception:
                        pass
                elif isinstance(ts, datetime):
                    allot_time = ts
                break

        now_dt = datetime.now(timezone.utc)
        if allot_time:
            if allot_time.tzinfo is None:
                allot_time = allot_time.replace(tzinfo=timezone.utc)
            allotment_latency_min = max(0.0, (allot_time - created_at).total_seconds() / 60.0)
            courier_assigned = True
        else:
            allotment_latency_min = max(0.0, (now_dt - created_at).total_seconds() / 60.0)
            courier_assigned = False

        is_allotment_delayed = allotment_latency_min > 3.0

        # 2. First mile distance
        first_mile = 1.85
        for ev in events:
            meta = ev.get("metadata", {}) or ev.get("event_metadata", {}) or {}
            if "first_mile_distance" in meta and meta["first_mile_distance"] is not None:
                first_mile = float(meta["first_mile_distance"])
                break
        is_extreme_first_mile = first_mile > 3.0

        # 3. Courier acceptance
        accept_time: Optional[datetime] = None
        for ev in events:
            if ev.get("event_type") in ("RIDER_ACCEPTED", "COURIER_ACCEPTED"):
                ts = ev.get("event_timestamp")
                if isinstance(ts, str):
                    try:
                        accept_time = datetime.fromisoformat(ts)
                    except Exception:
                        pass
                elif isinstance(ts, datetime):
                    accept_time = ts
                break

        if accept_time and allot_time:
            if accept_time.tzinfo is None:
                accept_time = accept_time.replace(tzinfo=timezone.utc)
            courier_acceptance_latency_min = max(0.0, (accept_time - allot_time).total_seconds() / 60.0)
            courier_accepted = True
        elif allot_time:
            courier_acceptance_latency_min = max(0.0, (now_dt - allot_time).total_seconds() / 60.0)
            courier_accepted = False if courier_acceptance_latency_min > 2.0 else True
        else:
            courier_acceptance_latency_min = 0.0
            courier_accepted = False

        # 4. Reassignment count
        reassignments = 0
        for ev in events:
            if ev.get("event_type") in ("RIDER_REASSIGNED", "ORDER_REASSIGNED"):
                reassignments += 1

        # 5. Simulated Transit Conditions
        congestion_factor = 1.0
        for ev in events:
            meta = ev.get("metadata", {}) or ev.get("event_metadata", {}) or {}
            if "traffic_factor" in meta:
                congestion_factor = float(meta["traffic_factor"])
                break
            elif "traffic_congestion" in meta:
                congestion_factor = float(meta["traffic_congestion"])
                break

        # 6. Formulate evidence & diagnosis
        if reassignments >= 2:
            operational_impact = f"Multiple courier reassignments ({reassignments} unassigned/re-allotted couriers). Severe first-mile pickup breach."
            suspected_cause = "Courier churn due to extreme pickup distance or merchant dispatch delay."
            confidence = "HIGH"
        elif not courier_assigned and is_allotment_delayed:
            operational_impact = f"Unassigned order. Allotment delayed by {allotment_latency_min:.1f}m without courier lock."
            suspected_cause = "Local fleet supply deficit in restaurant delivery zone."
            confidence = "HIGH"
        elif is_extreme_first_mile:
            operational_impact = f"Extreme first-mile distance ({first_mile:.1f} km). Courier transit to restaurant delayed."
            suspected_cause = "Sub-optimal allotment dispatch radius under elevated zone demand."
            confidence = "HIGH"
        elif congestion_factor > 1.3:
            operational_impact = f"Heavy route traffic congestion (traffic index: {congestion_factor:.2f}x). Transit speed degraded."
            suspected_cause = "Corridor congestion along restaurant-customer arterial route."
            confidence = "MEDIUM"
        else:
            operational_impact = "Courier assigned and proceeding on nominal transit schedule."
            suspected_cause = "Normal delivery fleet operations."
            confidence = "HIGH"

        delivery_evidence = DeliveryEvidence(
            courier_assigned=courier_assigned,
            courier_id=delivery_partner.get("id"),
            courier_name=delivery_partner.get("name"),
            allotment_latency_min=round(allotment_latency_min, 1),
            is_allotment_delayed=is_allotment_delayed,
            first_mile_km=round(first_mile, 2),
            is_extreme_first_mile=is_extreme_first_mile,
            courier_accepted=courier_accepted,
            courier_acceptance_latency_min=round(courier_acceptance_latency_min, 1),
            transit_congestion_factor=round(congestion_factor, 2),
            reassignment_count=reassignments,
            operational_impact=operational_impact,
            suspected_cause=suspected_cause,
            confidence=confidence,
        )

        existing_evidence = state.get("evidence_and_provenance", {})
        existing_evidence["delivery"] = delivery_evidence.model_dump()

        return {
            **state,
            "delivery_investigation": delivery_evidence.model_dump(),
            "evidence_and_provenance": existing_evidence,
        }
