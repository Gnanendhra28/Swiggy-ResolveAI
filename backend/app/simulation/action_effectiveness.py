"""
Swiggy ResolveAI — Recovery Action Effectiveness Module.

Evaluates the marginal effectiveness of individual autonomous recovery actions:
- EXPEDITE_KITCHEN_PING
- PRIORITIZE_COURIER_DISPATCH
- REASSIGN_COURIER
- PROACTIVE_CUSTOMER_NOTIFICATION
- APOLOGY_CREDIT_VOUCHER
- MONITOR_ORDER

Evaluates each action under matched-pair counterfactual conditions against an identical
no-action control to compute trigger frequency, delay reduction, cancellation reduction,
unit cost, cost per successful recovery, and net simulated ROI.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from backend.app.simulation.advanced_engine import SimulatedOrderState, SimulationConfig
from backend.app.simulation.strategies.base import StrategyExecutionResult


@dataclass
class ActionEffectivenessScorecard:
    """Quantitative performance scorecard for a specific recovery action."""
    action_type: str
    description: str
    sample_evaluated: int
    triggered_count: int
    trigger_frequency_pct: float
    successful_recoveries_count: int
    action_success_rate_pct: float
    average_delay_reduction_min: float
    median_delay_reduction_min: float
    cancellation_reduction_pct: float
    unit_cost_inr: float
    total_cost_inr: float
    cost_per_successful_recovery_inr: float
    estimated_losses_avoided_inr: float
    net_simulated_benefit_inr: float
    simulated_roi_ratio: float
    provenance: str = "SIMULATED_ACTION_EFFECTIVENESS"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "description": self.description,
            "sample_evaluated": self.sample_evaluated,
            "triggered_count": self.triggered_count,
            "trigger_frequency_pct": round(self.trigger_frequency_pct, 2),
            "successful_recoveries_count": self.successful_recoveries_count,
            "action_success_rate_pct": round(self.action_success_rate_pct, 2),
            "average_delay_reduction_min": round(self.average_delay_reduction_min, 2),
            "median_delay_reduction_min": round(self.median_delay_reduction_min, 2),
            "cancellation_reduction_pct": round(self.cancellation_reduction_pct, 2),
            "unit_cost_inr": round(self.unit_cost_inr, 2),
            "total_cost_inr": round(self.total_cost_inr, 2),
            "cost_per_successful_recovery_inr": round(self.cost_per_successful_recovery_inr, 2),
            "estimated_losses_avoided_inr": round(self.estimated_losses_avoided_inr, 2),
            "net_simulated_benefit_inr": round(self.net_simulated_benefit_inr, 2),
            "simulated_roi_ratio": round(self.simulated_roi_ratio, 2),
            "provenance": self.provenance,
        }


class ActionEffectivenessEvaluator:
    """Evaluates individual recovery actions against matched controls."""

    ACTIONS_CONFIG = {
        "EXPEDITE_KITCHEN_PING": {
            "description": "Automated priority alert to kitchen display system to prioritize food prep",
            "unit_cost": 5.0,
            "delay_reduction_range": (3.5, 7.5),
            "cancellation_mitigation_factor": 0.25,
            "applicable_scenarios": ["RESTAURANT_PREP_DELAY", "RESTAURANT_CAPACITY_OVERLOAD", "COMBINED_KITCHEN_DELIVERY_DELAY"],
        },
        "PRIORITIZE_COURIER_DISPATCH": {
            "description": "Elevates courier search radius and dispatch queue priority for stalled assignment",
            "unit_cost": 15.0,
            "delay_reduction_range": (4.5, 9.0),
            "cancellation_mitigation_factor": 0.35,
            "applicable_scenarios": ["COURIER_ASSIGNMENT_DELAY", "COURIER_ACCEPTANCE_DELAY", "COMBINED_KITCHEN_DELIVERY_DELAY"],
        },
        "REASSIGN_COURIER": {
            "description": "Reassigns order to an alternate active courier in the same dispatch zone",
            "unit_cost": 35.0,
            "delay_reduction_range": (6.0, 12.0),
            "cancellation_mitigation_factor": 0.50,
            "applicable_scenarios": ["COURIER_REASSIGNMENT", "COURIER_ACCEPTANCE_DELAY"],
        },
        "PROACTIVE_CUSTOMER_NOTIFICATION": {
            "description": "Transparent SMS/push update setting customer expectations and resetting arrival ETA",
            "unit_cost": 2.0,
            "delay_reduction_range": (0.0, 0.0),  # Informs customer; does not speed up logistics
            "cancellation_mitigation_factor": 0.45,
            "applicable_scenarios": ["ALL"],
        },
        "APOLOGY_CREDIT_VOUCHER": {
            "description": "Simulated ₹50 customer concession voucher for high delay risk orders",
            "unit_cost": 50.0,
            "delay_reduction_range": (0.0, 0.0),
            "cancellation_mitigation_factor": 0.70,
            "applicable_scenarios": ["HIGH_CANCELLATION_RISK", "COMBINED_KITCHEN_DELIVERY_DELAY"],
        },
        "MONITOR_ORDER": {
            "description": "Continuous telemetry observation without direct operational modification",
            "unit_cost": 0.0,
            "delay_reduction_range": (0.0, 0.0),
            "cancellation_mitigation_factor": 0.0,
            "applicable_scenarios": ["NORMAL_DELIVERY"],
        },
    }

    @classmethod
    def evaluate_single_action(
        cls,
        action_type: str,
        states: List[SimulatedOrderState],
        config: SimulationConfig,
    ) -> ActionEffectivenessScorecard:
        """
        Executes a matched counterfactual experiment isolating the specific action
        against an identical no-action control across the supplied orders.
        """
        action_meta = cls.ACTIONS_CONFIG.get(action_type, cls.ACTIONS_CONFIG["MONITOR_ORDER"])
        unit_cost = action_meta["unit_cost"]
        del_range = action_meta["delay_reduction_range"]
        cancel_mitigation = action_meta["cancellation_mitigation_factor"]

        n = len(states)
        triggered_count = 0
        successful_recoveries = 0
        delay_reductions = []
        control_cancellations = 0
        action_cancellations = 0

        for state in states:
            rng = random.Random(state.seed + 777 + hash(action_type) % 1000)

            # Determine if order triggers this action
            applicable = (
                "ALL" in action_meta["applicable_scenarios"]
                or state.scenario_type in action_meta["applicable_scenarios"]
            )
            # If scenario is generic, trigger on risk/delay threshold
            if not applicable and action_type in ("PROACTIVE_CUSTOMER_NOTIFICATION", "EXPEDITE_KITCHEN_PING"):
                applicable = (state.raw_prep_time_min > 20.0 or state.base_cancellation_propensity > 0.15)
            elif not applicable and action_type in ("PRIORITIZE_COURIER_DISPATCH", "REASSIGN_COURIER"):
                applicable = (state.raw_allotment_delay_min > 5.0 or state.raw_courier_accept_delay_min > 4.0)

            # Control outcome (Zero intervention)
            ctrl_prep = state.raw_prep_time_min
            ctrl_courier = state.raw_allotment_delay_min + state.raw_courier_accept_delay_min + state.raw_first_mile_transit_min
            ctrl_duration = max(ctrl_prep, ctrl_courier) + state.raw_last_mile_transit_min
            ctrl_cancelled = False
            if state.critical_disruption:
                ctrl_cancelled = (rng.random() < 0.90)
            else:
                delay_beyond = max(0.0, ctrl_duration - state.promised_duration_min)
                p_cancel = state.base_cancellation_propensity + (min(0.5, delay_beyond * 0.03) if delay_beyond > 15.0 else 0.0)
                ctrl_cancelled = (rng.random() < p_cancel)

            if ctrl_cancelled:
                control_cancellations += 1

            if not applicable:
                # Action not triggered; outcomes match control
                if ctrl_cancelled:
                    action_cancellations += 1
                delay_reductions.append(0.0)
                continue

            # Action was triggered!
            triggered_count += 1

            # Simulate action effectiveness
            is_effective = rng.random() < config.recovery_action_effectiveness
            act_delay_reduction = rng.uniform(*del_range) if is_effective else 0.0
            delay_reductions.append(act_delay_reduction)

            # Action treated logistics
            act_prep = ctrl_prep
            act_courier = ctrl_courier

            if action_type == "EXPEDITE_KITCHEN_PING":
                act_prep = max(10.0, ctrl_prep - act_delay_reduction)
            elif action_type in ("PRIORITIZE_COURIER_DISPATCH", "REASSIGN_COURIER"):
                act_courier = max(5.0, ctrl_courier - act_delay_reduction)

            act_duration = max(act_prep, act_courier) + state.raw_last_mile_transit_min

            # Action treated cancellation
            act_cancelled = False
            effective_mitigation = cancel_mitigation * config.recovery_action_effectiveness if is_effective else 0.0

            if state.critical_disruption:
                act_p = 0.90 * (1.0 - effective_mitigation)
                act_cancelled = (rng.random() < act_p)
            else:
                delay_beyond = max(0.0, act_duration - state.promised_duration_min)
                base_p = state.base_cancellation_propensity * (1.0 - effective_mitigation)
                act_p = base_p + (min(0.4, delay_beyond * 0.02) if delay_beyond > 15.0 else 0.0)
                act_cancelled = (rng.random() < act_p)

            if act_cancelled:
                action_cancellations += 1

            # Check if recovery was successful (on-time and uncancelled)
            if not act_cancelled and (act_duration <= state.promised_duration_min or not ctrl_cancelled):
                successful_recoveries += 1

        trigger_freq = (triggered_count / n * 100.0) if n > 0 else 0.0
        success_rate = (successful_recoveries / triggered_count * 100.0) if triggered_count > 0 else 0.0
        avg_delay_red = float(np.mean(delay_reductions)) if delay_reductions else 0.0
        med_delay_red = float(np.median(delay_reductions)) if delay_reductions else 0.0

        # Cancellation reduction
        ctrl_cancel_rate = (control_cancellations / n * 100.0) if n > 0 else 0.0
        act_cancel_rate = (action_cancellations / n * 100.0) if n > 0 else 0.0
        cancel_reduction = max(0.0, ctrl_cancel_rate - act_cancel_rate)

        total_cost = triggered_count * unit_cost
        cost_per_recovery = (total_cost / successful_recoveries) if successful_recoveries > 0 else 0.0

        cancellations_avoided = max(0, control_cancellations - action_cancellations)
        losses_avoided = cancellations_avoided * config.gross_order_value_inr
        net_benefit = losses_avoided - total_cost
        roi_ratio = (losses_avoided / total_cost) if total_cost > 0 else 1.0

        return ActionEffectivenessScorecard(
            action_type=action_type,
            description=action_meta["description"],
            sample_evaluated=n,
            triggered_count=triggered_count,
            trigger_frequency_pct=trigger_freq,
            successful_recoveries_count=successful_recoveries,
            action_success_rate_pct=success_rate,
            average_delay_reduction_min=avg_delay_red,
            median_delay_reduction_min=med_delay_red,
            cancellation_reduction_pct=cancel_reduction,
            unit_cost_inr=unit_cost,
            total_cost_inr=total_cost,
            cost_per_successful_recovery_inr=cost_per_recovery,
            estimated_losses_avoided_inr=losses_avoided,
            net_simulated_benefit_inr=net_benefit,
            simulated_roi_ratio=roi_ratio,
        )

    @classmethod
    def evaluate_all_actions(
        cls,
        states: List[SimulatedOrderState],
        config: SimulationConfig,
    ) -> List[Dict[str, Any]]:
        """Evaluates all 6 recovery actions and returns a formatted list of scorecards."""
        scorecards = []
        for action_type in cls.ACTIONS_CONFIG.keys():
            sc = cls.evaluate_single_action(action_type, states, config)
            scorecards.append(sc.to_dict())
        return scorecards
