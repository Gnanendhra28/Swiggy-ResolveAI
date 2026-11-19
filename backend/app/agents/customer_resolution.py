import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.agents.schemas import (
    RiskTier,
    ActionType,
    SensitivityLevel,
    ApprovalStatus,
    RecoveryActionRecommendation,
    CustomerResolutionSynthesis,
)
from backend.app.agents.state import MultiAgentInvestigationState


class CustomerResolutionAgent:
    """
    Customer Resolution Agent:
    - Consumes investigation evidence from Restaurant and Delivery agents.
    - Synthesizes the primary bottleneck and root cause.
    - Generates evidence-grounded, ranked recovery recommendations.
    - Supports Gemini structured output when available, with a deterministic fallback engine.
    """

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self.api_key = os.getenv("GEMINI_API_KEY", getattr(settings, "GEMINI_API_KEY", "") or "")

    def synthesize(self, state: MultiAgentInvestigationState) -> MultiAgentInvestigationState:
        order_ctx = state.get("order_context", {})
        ml_preds = state.get("ml_predictions", {}) or {}
        risk_tier = state.get("risk_tier", RiskTier.NOMINAL)
        rest_inv = state.get("restaurant_investigation", {}) or {}
        deliv_inv = state.get("delivery_investigation", {}) or {}
        external_order_id = state.get("external_order_id", "UNKNOWN")

        logger.info(f"CustomerResolutionAgent synthesizing recovery plan for order {external_order_id} [{risk_tier}]")

        # Try LLM synthesis if key exists and use_llm is True; otherwise run deterministic synthesis
        synthesis: Optional[CustomerResolutionSynthesis] = None
        if self.use_llm and self.api_key and not self.api_key.startswith("mock"):
            try:
                synthesis = self._synthesize_with_llm(state)
            except Exception as exc:
                logger.warning(f"LLM synthesis failed or timed out ({exc}). Falling back to deterministic synthesis.")
                synthesis = None

        if synthesis is None:
            synthesis = self._synthesize_deterministic(state)

        # Upgrade nominal risk tier if investigation revealed significant kitchen or dispatch delay
        final_risk = state.get("risk_tier", RiskTier.NOMINAL)
        if final_risk == RiskTier.NOMINAL:
            prep_delay = (state.get("restaurant_investigation") or {}).get("prep_delay_min", 0.0)
            reassignments = (state.get("delivery_investigation") or {}).get("reassignment_count", 0)
            allot_delayed = (state.get("delivery_investigation") or {}).get("is_allotment_delayed", False)
            if prep_delay >= 12.0 or reassignments >= 2:
                final_risk = RiskTier.HIGH_RISK
            elif prep_delay > 4.0 or allot_delayed or reassignments >= 1:
                final_risk = RiskTier.MONITORED

        # Update state
        rec_dicts = [r.model_dump() for r in synthesis.recommendations]
        return {
            **state,
            "risk_tier": final_risk,
            "resolution_synthesis": synthesis.model_dump(),
            "recovery_recommendations": rec_dicts,
            "evidence_and_provenance": {
                **state.get("evidence_and_provenance", {}),
                "customer_resolution": synthesis.model_dump(),
            },
        }

    def _synthesize_deterministic(self, state: MultiAgentInvestigationState) -> CustomerResolutionSynthesis:
        """
        Deterministic, rule-grounded synthesis guaranteeing 100% test reliability
        and adherence to Swiggy ResolveAI operational policies.
        """
        risk_tier = state.get("risk_tier", RiskTier.NOMINAL)
        ml_preds = state.get("ml_predictions", {}) or {}
        task_a = ml_preds.get("task_a_eta", {})
        task_c2 = ml_preds.get("task_c2_cancellation", {})
        rest_inv = state.get("restaurant_investigation", {}) or {}
        deliv_inv = state.get("delivery_investigation", {}) or {}

        prep_delay = rest_inv.get("prep_delay_min", 0.0)
        kitchen_backlog = rest_inv.get("kitchen_backlog_orders", 0)
        reassignments = deliv_inv.get("reassignment_count", 0)
        allot_delayed = deliv_inv.get("is_allotment_delayed", False)
        courier_assigned = deliv_inv.get("courier_assigned", True)
        first_mile = deliv_inv.get("first_mile_km", 1.8)
        c2_alert_10k = task_c2.get("alert_budget_10_per_1000", False)
        c2_alert_5k = task_c2.get("alert_budget_5_per_1000", False)

        if risk_tier == RiskTier.NOMINAL:
            if prep_delay >= 12.0 or reassignments >= 2:
                risk_tier = RiskTier.HIGH_RISK
            elif prep_delay > 4.0 or allot_delayed or reassignments >= 1:
                risk_tier = RiskTier.MONITORED

        recommendations: List[RecoveryActionRecommendation] = []
        rank_counter = 1

        # Determine Primary Bottleneck
        if prep_delay > 8.0 or kitchen_backlog >= 6:
            primary_bottleneck = "RESTAURANT_KITCHEN"
            root_cause = f"Kitchen preparation delay of +{prep_delay:.1f}m due to simulated queue backlog ({kitchen_backlog} orders)."
        elif reassignments >= 2 or (not courier_assigned and allot_delayed):
            primary_bottleneck = "COURIER_DISPATCH"
            root_cause = f"Courier dispatch failure: {reassignments} reassignments or unassigned courier with allotment delay."
        elif deliv_inv.get("transit_congestion_factor", 1.0) > 1.3 or first_mile > 3.0:
            primary_bottleneck = "TRANSIT_TRAFFIC"
            root_cause = f"First-mile transit congestion ({first_mile:.1f} km pickup route under elevated traffic factor)."
        else:
            primary_bottleneck = "NOMINAL"
            root_cause = "Operations proceeding within standard delivery tolerance."

        # Severity
        if risk_tier in (RiskTier.CRITICAL, RiskTier.HIGH_RISK):
            severity = "SEVERE" if risk_tier == RiskTier.CRITICAL else "MODERATE"
        elif risk_tier == RiskTier.MONITORED:
            severity = "MODERATE"
        else:
            severity = "LOW"

        # Formulate grounded recommendations based on bottleneck and risk tier
        if risk_tier == RiskTier.CRITICAL:
            # 1. Proactive Customer Notification (Medium Sensitivity)
            recommendations.append(
                RecoveryActionRecommendation(
                    action_type=ActionType.PROACTIVE_CUSTOMER_NOTIFICATION,
                    title="Proactive Customer Delay Notification",
                    rationale=f"Order risk is CRITICAL. Proactively notify customer with revised ETA interval [{task_a.get('eta_p10_min')}m - {task_a.get('eta_p90_min')}m] to eliminate customer inquiry anxiety.",
                    sensitivity_level=SensitivityLevel.MEDIUM,
                    estimated_impact="Eliminates WISMO (Where Is My Order) ticket with 92% satisfaction retention.",
                    requires_approval=False,
                    approval_status=ApprovalStatus.AUTO_APPROVED,
                    rank=rank_counter,
                    execution_payload={"revised_eta_p50": task_a.get("eta_p50_min")},
                )
            )
            rank_counter += 1

            # 2. Courier Reassignment or Priority Dispatch
            if reassignments >= 1 or not courier_assigned:
                recommendations.append(
                    RecoveryActionRecommendation(
                        action_type=ActionType.REASSIGN_COURIER,
                        title="Express Courier Reassignment",
                        rationale="Active courier has stalled or order has experienced multiple reassignments. Reassign to nearby high-velocity courier.",
                        sensitivity_level=SensitivityLevel.HIGH,
                        estimated_impact="Reduces first-mile transit delay by 8 to 12 minutes.",
                        requires_approval=True,
                        approval_status=ApprovalStatus.PENDING_APPROVAL,
                        rank=rank_counter,
                        execution_payload={"target_radius_km": 2.0},
                    )
                )
                rank_counter += 1

            # 3. Apology Voucher (Sensitive)
            if c2_alert_5k or prep_delay > 15.0:
                recommendations.append(
                    RecoveryActionRecommendation(
                        action_type=ActionType.APOLOGY_CREDIT_VOUCHER,
                        title="Autonomous Apology Wallet Credit (₹50)",
                        rationale="Order is at severe risk of cancellation post-landmark. Issue courtesy appeasement credit before customer cancellation.",
                        sensitivity_level=SensitivityLevel.HIGH,
                        estimated_impact="Retains customer lifetime value and prevents order churn.",
                        requires_approval=True,
                        approval_status=ApprovalStatus.PENDING_APPROVAL,
                        rank=rank_counter,
                        execution_payload={"credit_amount_inr": 50.0},
                    )
                )
                rank_counter += 1

        elif risk_tier == RiskTier.HIGH_RISK:
            # 1. Kitchen Ping if prep delay, else Courier Prioritization
            if prep_delay > 5.0:
                recommendations.append(
                    RecoveryActionRecommendation(
                        action_type=ActionType.EXPEDITE_KITCHEN_PING,
                        title="Expedite Kitchen KDS Ping",
                        rationale=f"Kitchen prep running +{prep_delay:.1f}m late. Send automated gentle alert to merchant POS to expedite packaging.",
                        sensitivity_level=SensitivityLevel.LOW,
                        estimated_impact="Prompts kitchen staff to prioritize packaging, recovering ~4-6 minutes.",
                        requires_approval=False,
                        approval_status=ApprovalStatus.AUTO_APPROVED,
                        rank=rank_counter,
                        execution_payload={"prep_delay_min": prep_delay},
                    )
                )
                rank_counter += 1

            # 2. Proactive Customer Notification
            recommendations.append(
                RecoveryActionRecommendation(
                    action_type=ActionType.PROACTIVE_CUSTOMER_NOTIFICATION,
                    title="Transparent ETA Adjustment Update",
                    rationale=f"Inform customer of revised arrival window [{task_a.get('eta_p10_min')}m - {task_a.get('eta_p90_min')}m] to prevent inbound support contact.",
                    sensitivity_level=SensitivityLevel.MEDIUM,
                    estimated_impact="Maintains customer trust with proactive operational transparency.",
                    requires_approval=False,
                    approval_status=ApprovalStatus.AUTO_APPROVED,
                    rank=rank_counter,
                    execution_payload={"revised_eta_p50": task_a.get("eta_p50_min")},
                )
            )
            rank_counter += 1

            # 3. Prioritize courier dispatch if courier pending
            if not courier_assigned or allot_delayed:
                recommendations.append(
                    RecoveryActionRecommendation(
                        action_type=ActionType.PRIORITIZE_COURIER_DISPATCH,
                        title="Elevate Courier Allocation Priority",
                        rationale="Order allotment is delayed. Elevate dispatch queue rank in delivery partner allotment algorithm.",
                        sensitivity_level=SensitivityLevel.LOW,
                        estimated_impact="Locks nearest courier within next 90 seconds.",
                        requires_approval=False,
                        approval_status=ApprovalStatus.AUTO_APPROVED,
                        rank=rank_counter,
                        execution_payload={"priority_boost": True},
                    )
                )
                rank_counter += 1

        elif risk_tier == RiskTier.MONITORED:
            recommendations.append(
                RecoveryActionRecommendation(
                    action_type=ActionType.MONITOR_ORDER,
                    title="Active Lifecycle Telemetry Monitoring",
                    rationale="Order is slightly delayed but within recoverable margin. Continue automated telemetry polling without intrusive intervention.",
                    sensitivity_level=SensitivityLevel.LOW,
                    estimated_impact="Maintains system visibility without merchant or customer friction.",
                    requires_approval=False,
                    approval_status=ApprovalStatus.AUTO_APPROVED,
                    rank=rank_counter,
                    execution_payload={"poll_interval_sec": 30},
                )
            )
            rank_counter += 1
            if prep_delay > 4.0:
                recommendations.append(
                    RecoveryActionRecommendation(
                        action_type=ActionType.EXPEDITE_KITCHEN_PING,
                        title="Expedite Kitchen KDS Ping",
                        rationale="Gentle reminder to kitchen staff to mark order as prepared.",
                        sensitivity_level=SensitivityLevel.LOW,
                        estimated_impact="Saves ~2-3 minutes handoff delay.",
                        requires_approval=False,
                        approval_status=ApprovalStatus.AUTO_APPROVED,
                        rank=rank_counter,
                        execution_payload={"prep_delay_min": prep_delay},
                    )
                )
                rank_counter += 1

        else:  # NOMINAL
            recommendations.append(
                RecoveryActionRecommendation(
                    action_type=ActionType.MONITOR_ORDER,
                    title="Standard Operational Monitoring",
                    rationale="All lifecycle milestones (prep, allocation, transit) are on schedule.",
                    sensitivity_level=SensitivityLevel.LOW,
                    estimated_impact="Nominal on-time delivery expected.",
                    requires_approval=False,
                    approval_status=ApprovalStatus.AUTO_APPROVED,
                    rank=1,
                    execution_payload={},
                )
            )

        op_summary = (
            f"Risk Tier: {risk_tier.value} | Primary Bottleneck: {primary_bottleneck} | "
            f"Task A ETA: {task_a.get('eta_p50_min')}m (P10-P90: [{task_a.get('eta_p10_min')}m - {task_a.get('eta_p90_min')}m]) | "
            f"Task C2 Calibrated Prob: {task_c2.get('calibrated_probability')} | Actions Proposed: {len(recommendations)}"
        )

        return CustomerResolutionSynthesis(
            root_cause_summary=root_cause,
            primary_bottleneck=primary_bottleneck,
            customer_impact_severity=severity,
            recommendations=recommendations,
            operational_risk_summary=op_summary,
        )

    def _synthesize_with_llm(self, state: MultiAgentInvestigationState) -> CustomerResolutionSynthesis:
        """Invokes Gemini model using langchain-google-genai to synthesize recommendations."""
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import SystemMessage, HumanMessage

        model_name = os.getenv("GEMINI_MODEL_NAME", getattr(settings, "GEMINI_MODEL_NAME", "gemini-3.5-flash"))
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self.api_key,
            temperature=0.1,
            timeout=getattr(settings, "GEMINI_TIMEOUT_SECONDS", 10.0),
        )
        structured_llm = llm.with_structured_output(CustomerResolutionSynthesis)

        prompt_text = f"""
You are the Swiggy ResolveAI Customer Resolution Agent.
Review the following multi-agent operational telemetry and synthesize root cause and recovery recommendations.

Order ID: {state.get('external_order_id')}
Order Context: {state.get('order_context')}
Risk Tier: {state.get('risk_tier')}
ML Predictions: {state.get('ml_predictions')}
Restaurant Investigation: {state.get('restaurant_investigation')}
Delivery Investigation: {state.get('delivery_investigation')}

Rules:
1. Ground every recommendation in verified evidence.
2. Low sensitivity actions (e.g., MONITOR_ORDER, EXPEDITE_KITCHEN_PING, PRIORITIZE_COURIER_DISPATCH) can be auto-approved.
3. Sensitive actions (e.g., REASSIGN_COURIER, APOLOGY_CREDIT_VOUCHER) MUST require approval (requires_approval=True).
4. Rank recommendations in order of urgency and feasibility.
"""
        messages = [
            SystemMessage(content="You are an autonomous food delivery operations resolver for Swiggy ResolveAI."),
            HumanMessage(content=prompt_text),
        ]
        result = structured_llm.invoke(messages)
        return result
