from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.app.core.logging import logger
from backend.app.agents.schemas import RestaurantEvidence
from backend.app.agents.state import MultiAgentInvestigationState


class RestaurantCoordinationAgent:
    """
    Restaurant Coordination Agent:
    - Investigates restaurant acceptance latency.
    - Inspects kitchen preparation timeline and backlog.
    - Clearly marks simulated current queue information vs historical evidence.
    - Generates evidence-grounded operational impact and suspected root causes.
    """

    def investigate(self, state: MultiAgentInvestigationState) -> MultiAgentInvestigationState:
        order_ctx = state.get("order_context", {})
        events = state.get("order_events", [])
        restaurant = order_ctx.get("restaurant", {})
        external_order_id = state.get("external_order_id", "UNKNOWN")

        logger.info(f"RestaurantCoordinationAgent investigating kitchen status for order {external_order_id}")

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

        # 1. Acceptance latency
        accepted_at: Optional[datetime] = None
        for ev in events:
            if ev.get("event_type") in ("ORDER_ACCEPTED", "RESTAURANT_ACCEPTED", "ORDER_CONFIRMED"):
                ts = ev.get("event_timestamp")
                if isinstance(ts, str):
                    try:
                        accepted_at = datetime.fromisoformat(ts)
                    except Exception:
                        pass
                elif isinstance(ts, datetime):
                    accepted_at = ts
                break

        if accepted_at:
            if accepted_at.tzinfo is None:
                accepted_at = accepted_at.replace(tzinfo=timezone.utc)
            acceptance_latency_min = max(0.0, (accepted_at - created_at).total_seconds() / 60.0)
        else:
            now_dt = datetime.now(timezone.utc)
            acceptance_latency_min = max(0.0, (now_dt - created_at).total_seconds() / 60.0)

        is_delayed_acceptance = acceptance_latency_min > 2.5

        # 2. Preparation status
        prep_started_at: Optional[datetime] = accepted_at or created_at
        food_ready_at: Optional[datetime] = None
        for ev in events:
            if ev.get("event_type") in ("FOOD_READY", "FOOD_PREPARED", "READY_FOR_PICKUP"):
                ts = ev.get("event_timestamp")
                if isinstance(ts, str):
                    try:
                        food_ready_at = datetime.fromisoformat(ts)
                    except Exception:
                        pass
                elif isinstance(ts, datetime):
                    food_ready_at = ts
                break

        estimated_prep_total = 16.0
        now_dt = datetime.now(timezone.utc)
        if food_ready_at:
            if food_ready_at.tzinfo is None:
                food_ready_at = food_ready_at.replace(tzinfo=timezone.utc)
            actual_prep_min = max(0.0, (food_ready_at - prep_started_at).total_seconds() / 60.0)
            prep_delay_min = max(0.0, actual_prep_min - estimated_prep_total)
            prep_elapsed_min = actual_prep_min
        else:
            prep_elapsed_min = max(0.0, (now_dt - prep_started_at).total_seconds() / 60.0)
            prep_delay_min = max(0.0, prep_elapsed_min - estimated_prep_total)

        # 3. Simulated Kitchen Backlog
        # Explicit distinction: mark as SIMULATED_TELEMETRY (historical orders do not have KDS data)
        simulated_backlog = 3
        for ev in events:
            meta = ev.get("metadata", {}) or ev.get("event_metadata", {}) or {}
            if "kitchen_queue_depth" in meta:
                simulated_backlog = int(meta["kitchen_queue_depth"])
                break
            elif "kitchen_backlog" in meta:
                simulated_backlog = int(meta["kitchen_backlog"])
                break

        # If prep delay is high, simulate queue backlog escalation
        if prep_delay_min > 10.0:
            simulated_backlog = max(simulated_backlog, 6)

        # 4. Formulate evidence & diagnosis
        if prep_delay_min > 12.0 or simulated_backlog >= 6:
            operational_impact = f"Severe kitchen backlog ({simulated_backlog} active orders). Prep running +{prep_delay_min:.1f}m late."
            suspected_cause = "Kitchen capacity exceeded during peak demand burst or bulk item preparation."
            confidence = "HIGH"
        elif prep_delay_min > 5.0:
            operational_impact = f"Moderate preparation delay (+{prep_delay_min:.1f}m above target). Kitchen queue: {simulated_backlog} orders."
            suspected_cause = "Preparation bottleneck or multi-station kitchen handoff delay."
            confidence = "HIGH"
        elif is_delayed_acceptance:
            operational_impact = f"Merchant acceptance delayed ({acceptance_latency_min:.1f}m latency). Order pending terminal confirmation."
            suspected_cause = "Merchant device muted, staff attending counter, or POS sync latency."
            confidence = "MEDIUM"
        else:
            operational_impact = "Preparation proceeding on target within standard 16-minute window."
            suspected_cause = "Normal kitchen throughput."
            confidence = "HIGH"

        restaurant_evidence = RestaurantEvidence(
            acceptance_latency_min=round(acceptance_latency_min, 1),
            is_delayed_acceptance=is_delayed_acceptance,
            prep_elapsed_min=round(prep_elapsed_min, 1),
            estimated_prep_total_min=round(estimated_prep_total, 1),
            prep_delay_min=round(prep_delay_min, 1),
            kitchen_backlog_orders=simulated_backlog,
            kitchen_backlog_source="SIMULATED_TELEMETRY",
            merchant_active=restaurant.get("is_active", True),
            operational_impact=operational_impact,
            suspected_cause=suspected_cause,
            confidence=confidence,
        )

        existing_evidence = state.get("evidence_and_provenance", {})
        existing_evidence["restaurant"] = restaurant_evidence.model_dump()

        return {
            **state,
            "restaurant_investigation": restaurant_evidence.model_dump(),
            "evidence_and_provenance": existing_evidence,
        }
