from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END

from backend.app.core.logging import logger
from backend.app.agents.state import MultiAgentInvestigationState
from backend.app.agents.schemas import InvestigationStatus, RiskTier
from backend.app.agents.order_intelligence import OrderIntelligenceAgent
from backend.app.agents.restaurant_coordination import RestaurantCoordinationAgent
from backend.app.agents.delivery_intelligence import DeliveryIntelligenceAgent
from backend.app.agents.customer_resolution import CustomerResolutionAgent
from backend.app.services.policy_engine import PolicyEngine


# Resilient Node Implementations with Error Handling & Telemetry
def order_intelligence_node(state: MultiAgentInvestigationState) -> MultiAgentInvestigationState:
    try:
        agent = OrderIntelligenceAgent()
        return agent.evaluate_order(state)
    except Exception as exc:
        logger.error(f"OrderIntelligenceAgent error: {exc}")
        errors = list(state.get("errors", []))
        errors.append(f"OrderIntelligenceAgent degraded: {exc}")
        return {
            **state,
            "risk_tier": RiskTier.NOMINAL,
            "workflow_status": InvestigationStatus.FAILED,
            "errors": errors,
        }


def route_after_order_intel(state: MultiAgentInvestigationState):
    status = state.get("workflow_status")
    # If completed early (terminal order) or unrecoverable error, terminate graph
    if status in (InvestigationStatus.COMPLETED, InvestigationStatus.FAILED) or state.get("errors"):
        return END
    return "restaurant_node"


def restaurant_node(state: MultiAgentInvestigationState) -> MultiAgentInvestigationState:
    try:
        agent = RestaurantCoordinationAgent()
        return agent.investigate(state)
    except Exception as exc:
        logger.error(f"RestaurantCoordinationAgent degraded: {exc}")
        # Do NOT fabricate evidence on failure
        degraded_evidence = {
            "is_available": False,
            "confidence": "UNAVAILABLE",
            "operational_impact": "Restaurant telemetry unavailable due to partner gateway latency.",
            "suspected_cause": "Merchant integration offline or timeout.",
            "kitchen_backlog_source": "TELEMETRY_UNAVAILABLE",
            "prep_delay_min": 0.0,
        }
        existing_evidence = dict(state.get("evidence_and_provenance", {}))
        existing_evidence["restaurant"] = degraded_evidence
        return {
            **state,
            "restaurant_investigation": degraded_evidence,
            "evidence_and_provenance": existing_evidence,
        }


def delivery_node(state: MultiAgentInvestigationState) -> MultiAgentInvestigationState:
    try:
        agent = DeliveryIntelligenceAgent()
        return agent.investigate(state)
    except Exception as exc:
        logger.error(f"DeliveryIntelligenceAgent degraded: {exc}")
        # Do NOT fabricate evidence on failure
        degraded_evidence = {
            "is_available": False,
            "confidence": "UNAVAILABLE",
            "operational_impact": "Delivery fleet telemetry unavailable due to dispatch gateway timeout.",
            "suspected_cause": "Courier GPS or network connectivity deficit.",
            "courier_assigned": False,
            "first_mile_km": 0.0,
            "reassignment_count": 0,
        }
        existing_evidence = dict(state.get("evidence_and_provenance", {}))
        existing_evidence["delivery"] = degraded_evidence
        return {
            **state,
            "delivery_investigation": degraded_evidence,
            "evidence_and_provenance": existing_evidence,
        }


def customer_resolution_node(state: MultiAgentInvestigationState) -> MultiAgentInvestigationState:
    try:
        agent = CustomerResolutionAgent()
        return agent.synthesize(state)
    except Exception as exc:
        logger.error(f"CustomerResolutionAgent fallback: {exc}")
        # Fallback to conservative monitoring
        agent = CustomerResolutionAgent(use_llm=False)
        return agent._synthesize_deterministic(state)


def policy_engine_node(state: MultiAgentInvestigationState) -> MultiAgentInvestigationState:
    recs = state.get("recovery_recommendations", [])
    order_ctx = state.get("order_context", {})
    order_status = order_ctx.get("order_status", "PLACED")
    existing_actions = state.get("order_events", [])

    validated_recs, summary = PolicyEngine.evaluate_recommendations(
        recommendations=recs,
        order_status=order_status,
        existing_actions=existing_actions,
        order_context=order_ctx,
    )

    return {
        **state,
        "recovery_recommendations": validated_recs,
        "policy_validation": summary,
        "workflow_status": InvestigationStatus.COMPLETED,
    }


def build_intelligence_graph():
    """
    Constructs and compiles the LangGraph StateGraph orchestrating
    the four specialized agents with deterministic policy validation.
    """
    graph = StateGraph(MultiAgentInvestigationState)

    # 1. Add nodes
    graph.add_node("order_intelligence_node", order_intelligence_node)
    graph.add_node("restaurant_node", restaurant_node)
    graph.add_node("delivery_node", delivery_node)
    graph.add_node("customer_resolution_node", customer_resolution_node)
    graph.add_node("policy_engine_node", policy_engine_node)

    # 2. Add edges
    graph.add_edge(START, "order_intelligence_node")
    graph.add_conditional_edges(
        "order_intelligence_node",
        route_after_order_intel,
        {
            "restaurant_node": "restaurant_node",
            END: END,
        },
    )
    # Pipeline investigation flow
    graph.add_edge("restaurant_node", "delivery_node")
    graph.add_edge("delivery_node", "customer_resolution_node")
    graph.add_edge("customer_resolution_node", "policy_engine_node")
    graph.add_edge("policy_engine_node", END)

    compiled_graph = graph.compile()
    return compiled_graph


# Pre-compiled global workflow
intelligence_workflow = build_intelligence_graph()
