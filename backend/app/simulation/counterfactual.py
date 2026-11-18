"""
Swiggy ResolveAI — Counterfactual and Experimental Evaluation Module.

Evaluates comparative recovery strategies under matched-pair counterfactual conditions
where all strategies execute against identical initial operational order states.
Computes paired statistical differences, effect sizes (Cohen's d_z), paired test p-values,
and bootstrap 95% confidence intervals.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import scipy.stats as stats

from backend.app.simulation.advanced_engine import SimulatedOrderState, SimulationConfig
from backend.app.simulation.strategies.base import StrategyExecutionResult
from backend.app.simulation.strategies.implementations import (
    BaselineMonitoringStrategy,
    RuleBasedRecoveryStrategy,
    MLAssistedRecoveryStrategy,
    MultiAgentRecoveryStrategy,
)
from backend.app.simulation.kpi_calculator import KPICalculator


@dataclass
class PairedMetricComparison:
    """Statistical summary for a single metric across paired observations."""
    metric_name: str
    reference_mean: float
    candidate_mean: float
    mean_difference: float  # candidate - reference
    median_difference: float
    std_difference: float
    cohens_d: float
    ci_95_lower: float
    ci_95_upper: float
    p_value: float
    test_type: str  # 'paired_t_test' or 'wilcoxon'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "reference_mean": round(self.reference_mean, 2),
            "candidate_mean": round(self.candidate_mean, 2),
            "mean_difference": round(self.mean_difference, 2),
            "median_difference": round(self.median_difference, 2),
            "std_difference": round(self.std_difference, 2),
            "cohens_d": round(self.cohens_d, 3),
            "ci_95": [round(self.ci_95_lower, 2), round(self.ci_95_upper, 2)],
            "p_value": round(self.p_value, 5),
            "statistically_significant_0_05": bool(self.p_value < 0.05),
            "test_type": self.test_type,
        }


@dataclass
class StrategyComparisonReport:
    """Pairwise comparison between a candidate strategy and a reference strategy."""
    candidate_name: str
    reference_name: str
    sample_size: int
    duration_comparison: PairedMetricComparison
    ontime_rate_diff_pct: float
    ontime_ci_95: Tuple[float, float]
    ontime_p_value: float
    cancellation_rate_diff_pct: float
    cancellation_ci_95: Tuple[float, float]
    cancellation_p_value: float
    net_benefit_difference_inr: float
    provenance: str = "SIMULATED_COUNTERFACTUAL"
    causal_claim_caveat: str = (
        "Simulated counterfactual evaluation under model-based operational assumptions. "
        "Does not represent unadjusted observational correlation or verified real-world causal lift."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_name": self.candidate_name,
            "reference_name": self.reference_name,
            "sample_size": self.sample_size,
            "duration": self.duration_comparison.to_dict(),
            "ontime": {
                "difference_pct": round(self.ontime_rate_diff_pct, 2),
                "ci_95": [round(self.ontime_ci_95[0], 2), round(self.ontime_ci_95[1], 2)],
                "p_value": round(self.ontime_p_value, 5),
                "statistically_significant": bool(self.ontime_p_value < 0.05),
            },
            "cancellation": {
                "difference_pct": round(self.cancellation_rate_diff_pct, 2),
                "ci_95": [round(self.cancellation_ci_95[0], 2), round(self.cancellation_ci_95[1], 2)],
                "p_value": round(self.cancellation_p_value, 5),
                "statistically_significant": bool(self.cancellation_p_value < 0.05),
            },
            "net_benefit_difference_inr": round(self.net_benefit_difference_inr, 2),
            "provenance": self.provenance,
            "causal_claim_caveat": self.causal_claim_caveat,
        }


class CounterfactualEvaluator:
    """
    Executes multiple recovery strategies against identical simulated order states
    and computes paired counterfactual statistical differences.
    """

    @classmethod
    def compute_paired_bootstrap_ci(
        cls,
        diffs: List[float],
        n_bootstraps: int = 1000,
        alpha: float = 0.05,
        seed: int = 42,
    ) -> Tuple[float, float]:
        """Calculates two-sided (1 - alpha) bootstrap confidence interval on the mean difference."""
        if not diffs:
            return (0.0, 0.0)
        rng = np.random.RandomState(seed)
        arr = np.array(diffs, dtype=float)
        n = len(arr)
        if n == 1 or np.all(arr == arr[0]):
            return (float(arr[0]), float(arr[0]))

        indices = rng.randint(0, n, (n_bootstraps, n))
        bootstrap_means = np.mean(arr[indices], axis=1)
        lower = float(np.percentile(bootstrap_means, 100.0 * (alpha / 2.0)))
        upper = float(np.percentile(bootstrap_means, 100.0 * (1.0 - alpha / 2.0)))
        return (lower, upper)

    @classmethod
    def compute_paired_metric_comparison(
        cls,
        candidate_vals: List[float],
        reference_vals: List[float],
        metric_name: str,
        seed: int = 42,
    ) -> PairedMetricComparison:
        """Computes mean difference, Cohen's d_z, Wilcoxon or t-test p-value, and bootstrap CI."""
        c_arr = np.array(candidate_vals, dtype=float)
        r_arr = np.array(reference_vals, dtype=float)
        diffs = c_arr - r_arr

        mean_diff = float(np.mean(diffs))
        median_diff = float(np.median(diffs))
        std_diff = float(np.std(diffs, ddof=1)) if len(diffs) > 1 else 0.0

        # Cohen's d_z for paired samples: mean_diff / std_diff
        cohens_d = (mean_diff / std_diff) if std_diff > 1e-9 else 0.0

        # Bootstrap 95% CI
        ci_lower, ci_upper = cls.compute_paired_bootstrap_ci(diffs.tolist(), n_bootstraps=1000, seed=seed)

        # Statistical test
        p_val = 1.0
        test_type = "paired_t_test"
        if len(diffs) > 1 and not np.all(diffs == 0.0):
            try:
                # Prefer paired t-test for continuous latency differences
                t_res = stats.ttest_rel(c_arr, r_arr)
                p_val = float(t_res.pvalue) if not np.isnan(t_res.pvalue) else 1.0
            except Exception:
                p_val = 1.0

        return PairedMetricComparison(
            metric_name=metric_name,
            reference_mean=float(np.mean(r_arr)),
            candidate_mean=float(np.mean(c_arr)),
            mean_difference=mean_diff,
            median_difference=median_diff,
            std_difference=std_diff,
            cohens_d=cohens_d,
            ci_95_lower=ci_lower,
            ci_95_upper=ci_upper,
            p_value=p_val,
            test_type=test_type,
        )

    @classmethod
    def compare_strategies(
        cls,
        candidate_results: List[StrategyExecutionResult],
        reference_results: List[StrategyExecutionResult],
        candidate_name: str,
        reference_name: str,
        seed: int = 42,
    ) -> StrategyComparisonReport:
        """Computes matched counterfactual comparison between candidate and reference."""
        assert len(candidate_results) == len(reference_results), "Matched pair evaluation requires equal lengths"
        n = len(candidate_results)

        # 1. Delivery Durations
        c_dur = [r.delivery_duration_min for r in candidate_results]
        r_dur = [r.delivery_duration_min for r in reference_results]
        dur_comp = cls.compute_paired_metric_comparison(c_dur, r_dur, "delivery_duration_min", seed=seed)

        # 2. On-Time Delivery Rate
        c_ontime = [1.0 if r.is_on_time else 0.0 for r in candidate_results]
        r_ontime = [1.0 if r.is_on_time else 0.0 for r in reference_results]
        ontime_diffs = [(c - r) * 100.0 for c, r in zip(c_ontime, r_ontime)]
        ontime_rate_diff = float(np.mean(ontime_diffs))
        ontime_ci = cls.compute_paired_bootstrap_ci(ontime_diffs, n_bootstraps=1000, seed=seed)

        # McNemar / Paired sign test for binary on-time outcome
        ontime_p = 1.0
        try:
            # Contingency between candidate and reference on-time
            b = sum(1 for c, r in zip(c_ontime, r_ontime) if c == 1.0 and r == 0.0)
            c = sum(1 for c, r in zip(c_ontime, r_ontime) if c == 0.0 and r == 1.0)
            if (b + c) > 0:
                res = stats.binomtest(b, b + c, 0.5)
                ontime_p = float(res.pvalue)
        except Exception:
            ontime_p = 1.0

        # 3. Cancellation Rate
        c_cancel = [1.0 if r.is_cancelled else 0.0 for r in candidate_results]
        r_cancel = [1.0 if r.is_cancelled else 0.0 for r in reference_results]
        cancel_diffs = [(c - r) * 100.0 for c, r in zip(c_cancel, r_cancel)]
        cancel_rate_diff = float(np.mean(cancel_diffs))
        cancel_ci = cls.compute_paired_bootstrap_ci(cancel_diffs, n_bootstraps=1000, seed=seed)

        cancel_p = 1.0
        try:
            b_canc = sum(1 for c, r in zip(c_cancel, r_cancel) if c == 1.0 and r == 0.0)
            c_canc = sum(1 for c, r in zip(c_cancel, r_cancel) if c == 0.0 and r == 1.0)
            if (b_canc + c_canc) > 0:
                res = stats.binomtest(b_canc, b_canc + c_canc, 0.5)
                cancel_p = float(res.pvalue)
        except Exception:
            cancel_p = 1.0

        # 4. Net Benefit
        c_net = sum(r.net_operational_benefit_inr for r in candidate_results)
        r_net = sum(r.net_operational_benefit_inr for r in reference_results)

        return StrategyComparisonReport(
            candidate_name=candidate_name,
            reference_name=reference_name,
            sample_size=n,
            duration_comparison=dur_comp,
            ontime_rate_diff_pct=ontime_rate_diff,
            ontime_ci_95=ontime_ci,
            ontime_p_value=ontime_p,
            cancellation_rate_diff_pct=cancel_rate_diff,
            cancellation_ci_95=cancel_ci,
            cancellation_p_value=cancel_p,
            net_benefit_difference_inr=c_net - r_net,
        )

    @classmethod
    def evaluate_batch(
        cls,
        order_states: List[SimulatedOrderState],
        config: SimulationConfig,
    ) -> Dict[str, Any]:
        """
        Runs all four strategies over identical initial order states and generates
        individual KPI scorecards and pairwise counterfactual comparisons.
        """
        strategies = {
            "baseline": BaselineMonitoringStrategy(),
            "rule_based": RuleBasedRecoveryStrategy(),
            "ml_assisted": MLAssistedRecoveryStrategy(),
            "multi_agent": MultiAgentRecoveryStrategy(),
        }

        # 1. Execute each strategy independently
        execution_results: Dict[str, List[StrategyExecutionResult]] = {}
        for key, strat in strategies.items():
            results = [strat.evaluate_order(state, config) for state in order_states]
            execution_results[key] = results

        # 2. Compute individual strategy KPIs (using Strategy 1 as baseline for economic impact)
        baseline_res = execution_results["baseline"]
        strategy_kpis: Dict[str, Dict[str, Any]] = {}
        for key, results in execution_results.items():
            strategy_kpis[key] = KPICalculator.calculate_strategy_kpis(
                results,
                baseline_results=baseline_res,
                config=config,
            )

        # 3. Compute Counterfactual Pairwise Comparisons
        comparisons: List[Dict[str, Any]] = []

        # Strategy 4 vs Strategy 1 (Multi-Agent vs Baseline)
        comp_4_vs_1 = cls.compare_strategies(
            execution_results["multi_agent"],
            execution_results["baseline"],
            candidate_name="Strategy 4 — Multi-Agent",
            reference_name="Strategy 1 — Baseline Monitoring",
            seed=config.random_seed,
        )
        comparisons.append(comp_4_vs_1.to_dict())

        # Strategy 4 vs Strategy 2 (Multi-Agent vs Rules)
        comp_4_vs_2 = cls.compare_strategies(
            execution_results["multi_agent"],
            execution_results["rule_based"],
            candidate_name="Strategy 4 — Multi-Agent",
            reference_name="Strategy 2 — Rule-Based Recovery",
            seed=config.random_seed,
        )
        comparisons.append(comp_4_vs_2.to_dict())

        # Strategy 4 vs Strategy 3 (Multi-Agent vs ML-Assisted)
        comp_4_vs_3 = cls.compare_strategies(
            execution_results["multi_agent"],
            execution_results["ml_assisted"],
            candidate_name="Strategy 4 — Multi-Agent",
            reference_name="Strategy 3 — ML-Assisted Recovery",
            seed=config.random_seed,
        )
        comparisons.append(comp_4_vs_3.to_dict())

        # Strategy 3 vs Strategy 1 (ML-Assisted vs Baseline)
        comp_3_vs_1 = cls.compare_strategies(
            execution_results["ml_assisted"],
            execution_results["baseline"],
            candidate_name="Strategy 3 — ML-Assisted Recovery",
            reference_name="Strategy 1 — Baseline Monitoring",
            seed=config.random_seed,
        )
        comparisons.append(comp_3_vs_1.to_dict())

        # Strategy 2 vs Strategy 1 (Rules vs Baseline)
        comp_2_vs_1 = cls.compare_strategies(
            execution_results["rule_based"],
            execution_results["baseline"],
            candidate_name="Strategy 2 — Rule-Based Recovery",
            reference_name="Strategy 1 — Baseline Monitoring",
            seed=config.random_seed,
        )
        comparisons.append(comp_2_vs_1.to_dict())

        return {
            "scenario_type": config.scenario_type,
            "sample_size": len(order_states),
            "random_seed": config.random_seed,
            "strategy_kpis": strategy_kpis,
            "counterfactual_comparisons": comparisons,
            "execution_results": {
                k: [r.to_dict() for r in v] for k, v in execution_results.items()
            },
        }
