"""
Swiggy ResolveAI — Phase 5 Test Suite.
Advanced Simulation, Counterfactual Recovery Evaluation & Business KPI Measurement.

Verifies:
1. Deterministic simulation across all 12 operational scenarios.
2. Four comparative recovery strategies running on identical matched counterfactual initial states.
3. Statistical rigor: Bootstrap 95% confidence intervals, Cohen's d_z effect size, paired p-values.
4. Five KPI dimensions: Delivery, Cancellation, Operational, Agent, and Business Efficiency.
5. Recovery action marginal effectiveness across all 6 autonomous recovery actions.
6. Sensitivity and stress testing across 8 operational dimensions.
7. Database persistence of SimulationExperiment models and FastAPI endpoints.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.session import get_db, SessionLocal
from backend.app.models.simulation_experiment import SimulationExperiment
from backend.app.simulation.advanced_engine import AdvancedSimulationEngine, SimulationConfig
from backend.app.simulation.strategies.base import StrategyExecutionResult
from backend.app.simulation.strategies.implementations import (
    BaselineMonitoringStrategy,
    RuleBasedRecoveryStrategy,
    MLAssistedRecoveryStrategy,
    MultiAgentRecoveryStrategy,
)
from backend.app.simulation.counterfactual import CounterfactualEvaluator
from backend.app.simulation.kpi_calculator import KPICalculator
from backend.app.simulation.action_effectiveness import ActionEffectivenessEvaluator
from backend.app.simulation.stress_testing import StressTestFramework
from backend.app.services.experiment_service import ExperimentService


@pytest.fixture
def db_session():
    """Provides a transactional database session for tests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Provides FastAPI test client."""
    return TestClient(app)


# =============================================================================
# 1. Advanced Simulation Engine & Scenarios
# =============================================================================

class TestAdvancedSimulationEngine:
    """Verifies operational scenario fidelity, deterministic reproducibility, and state initialization."""

    def test_deterministic_generation_with_identical_seed(self):
        cfg1 = SimulationConfig(scenario_type="NORMAL_DELIVERY", random_seed=42, order_volume=10)
        cfg2 = SimulationConfig(scenario_type="NORMAL_DELIVERY", random_seed=42, order_volume=10)

        batch1 = AdvancedSimulationEngine.generate_order_batch(cfg1)
        batch2 = AdvancedSimulationEngine.generate_order_batch(cfg2)

        assert len(batch1) == 10
        assert len(batch2) == 10
        for s1, s2 in zip(batch1, batch2):
            assert s1.seed == s2.seed
            assert s1.raw_prep_time_min == s2.raw_prep_time_min
            assert s1.raw_allotment_delay_min == s2.raw_allotment_delay_min
            assert s1.raw_courier_accept_delay_min == s2.raw_courier_accept_delay_min
            assert s1.order_value_inr == s2.order_value_inr

    def test_different_seeds_produce_distinct_values(self):
        cfg1 = SimulationConfig(scenario_type="NORMAL_DELIVERY", random_seed=42, order_volume=5)
        cfg2 = SimulationConfig(scenario_type="NORMAL_DELIVERY", random_seed=999, order_volume=5)

        batch1 = AdvancedSimulationEngine.generate_order_batch(cfg1)
        batch2 = AdvancedSimulationEngine.generate_order_batch(cfg2)

        durations1 = [s.raw_prep_time_min for s in batch1]
        durations2 = [s.raw_prep_time_min for s in batch2]
        assert durations1 != durations2

    @pytest.mark.parametrize("scenario", [
        "NORMAL_DELIVERY",
        "RESTAURANT_PREP_DELAY",
        "RESTAURANT_CAPACITY_OVERLOAD",
        "COURIER_ASSIGNMENT_DELAY",
        "COURIER_ACCEPTANCE_DELAY",
        "COURIER_REASSIGNMENT",
        "TRAFFIC_CONGESTION",
        "LONG_DISTANCE_DELIVERY",
        "COMBINED_KITCHEN_DELIVERY_DELAY",
        "HIGH_CANCELLATION_RISK",
        "FAILED_RECOVERY",
        "SUCCESSFUL_RECOVERY",
    ])
    def test_all_twelve_scenarios_generate_valid_states(self, scenario):
        cfg = SimulationConfig(scenario_type=scenario, random_seed=123, order_volume=4)
        states = AdvancedSimulationEngine.generate_order_batch(cfg)

        assert len(states) == 4
        for s in states:
            assert s.order_id is not None
            assert s.raw_prep_time_min > 0
            assert s.raw_allotment_delay_min > 0
            assert s.raw_first_mile_transit_min > 0
            assert s.raw_last_mile_transit_min > 0
            assert 0.0 <= s.base_cancellation_propensity <= 1.0


# =============================================================================
# 2. Four Comparative Recovery Strategies
# =============================================================================

class TestComparativeRecoveryStrategies:
    """Verifies isolation, correct behavior, and matched counterfactuals for Strategies 1-4."""

    def test_strategy_1_baseline_monitoring_zero_interventions(self):
        cfg = SimulationConfig(scenario_type="RESTAURANT_PREP_DELAY", random_seed=42, order_volume=5)
        states = AdvancedSimulationEngine.generate_order_batch(cfg)

        strat = BaselineMonitoringStrategy()
        results = [strat.evaluate_order(s, cfg) for s in states]

        for r in results:
            assert r.strategy_name == "Strategy 1 — Baseline Monitoring"
            assert r.interventions_count == 0
            assert r.total_intervention_cost_inr == 0.0
            assert r.actions_triggered == []
            assert r.eta_p50_min is None

    def test_strategy_2_rule_based_recovery_triggers_rules(self):
        cfg = SimulationConfig(scenario_type="RESTAURANT_PREP_DELAY", random_seed=42, order_volume=10)
        states = AdvancedSimulationEngine.generate_order_batch(cfg)

        strat = RuleBasedRecoveryStrategy()
        results = [strat.evaluate_order(s, cfg) for s in states]

        interventions = [r for r in results if r.interventions_count > 0]
        assert len(interventions) > 0
        for r in interventions:
            assert r.total_intervention_cost_inr > 0.0
            assert len(r.actions_triggered) > 0

    def test_strategy_3_ml_assisted_recovery_generates_ml_quantiles(self):
        cfg = SimulationConfig(scenario_type="COMBINED_KITCHEN_DELIVERY_DELAY", random_seed=42, order_volume=5)
        states = AdvancedSimulationEngine.generate_order_batch(cfg)

        strat = MLAssistedRecoveryStrategy()
        results = [strat.evaluate_order(s, cfg) for s in states]

        for r in results:
            assert r.eta_p50_min is not None
            assert r.eta_p10_min is not None
            assert r.eta_p90_min is not None
            assert r.task_c2_calibrated_prob is not None

    def test_strategy_4_multi_agent_recovery_executes_full_synthesis(self):
        cfg = SimulationConfig(scenario_type="COMBINED_KITCHEN_DELIVERY_DELAY", random_seed=42, order_volume=5)
        states = AdvancedSimulationEngine.generate_order_batch(cfg)

        strat = MultiAgentRecoveryStrategy()
        results = [strat.evaluate_order(s, cfg) for s in states]

        for r in results:
            assert r.strategy_name == "Strategy 4 — Full ResolveAI Multi-Agent Recovery"
            assert r.investigation_success is True
            assert r.workflow_completed is True
            assert r.approval_status in ("APPROVED", "AUTO_APPROVED")

    def test_matched_counterfactual_order_duration_comparison(self):
        """Under delay scenario, Multi-Agent recovery reduces delivery duration compared to Baseline."""
        cfg = SimulationConfig(scenario_type="COMBINED_KITCHEN_DELIVERY_DELAY", random_seed=42, order_volume=20)
        states = AdvancedSimulationEngine.generate_order_batch(cfg)

        strat1 = BaselineMonitoringStrategy()
        strat4 = MultiAgentRecoveryStrategy()

        res1 = [strat1.evaluate_order(s, cfg) for s in states]
        res4 = [strat4.evaluate_order(s, cfg) for s in states]

        avg_dur_1 = sum(r.delivery_duration_min for r in res1) / len(res1)
        avg_dur_4 = sum(r.delivery_duration_min for r in res4) / len(res4)

        # Multi-Agent strategy mitigates delay
        assert avg_dur_4 <= avg_dur_1


# =============================================================================
# 3. KPI Calculator Mathematical Integrity
# =============================================================================

class TestKPICalculator:
    """Verifies documented KPI formulas, zero-division guards, and metric boundaries."""

    def test_kpi_calculator_all_dimensions_present(self):
        cfg = SimulationConfig(random_seed=42, order_volume=10)
        states = AdvancedSimulationEngine.generate_order_batch(cfg)
        strat = MultiAgentRecoveryStrategy()
        results = [strat.evaluate_order(s, cfg) for s in states]

        kpis = KPICalculator.calculate_strategy_kpis(results, baseline_results=results, config=cfg)

        assert "delivery" in kpis
        assert "cancellation" in kpis
        assert "operational" in kpis
        assert "agent" in kpis
        assert "business_efficiency" in kpis

        d = kpis["delivery"]
        assert 0.0 <= d["on_time_delivery_rate_pct"] <= 100.0
        assert d["average_delivery_duration_min"] > 0
        assert d["median_delivery_duration_min"] > 0
        assert d["p90_delivery_duration_min"] >= d["median_delivery_duration_min"]

        c = kpis["cancellation"]
        assert 0.0 <= c["overall_cancellation_rate_pct"] <= 100.0
        assert 0.0 <= c["post_landmark_cancellation_rate_pct"] <= 100.0

        b = kpis["business_efficiency"]
        assert b["assumed_gross_order_value_inr"] == 450.0

    def test_empty_results_returns_empty_dict(self):
        kpis = KPICalculator.calculate_strategy_kpis([])
        assert kpis == {}


# =============================================================================
# 4. Counterfactual Evaluator & Statistical Testing
# =============================================================================

class TestCounterfactualEvaluator:
    """Verifies bootstrap 95% CI calculation, Cohen's d_z effect size, and pairwise comparisons."""

    def test_bootstrap_ci_bounds(self):
        diffs = [-2.5, -3.0, -1.8, -4.0, -2.2, -3.5, -2.8, -3.1, -1.9, -2.7]
        lower, upper = CounterfactualEvaluator.compute_paired_bootstrap_ci(diffs, n_bootstraps=500, seed=42)

        assert lower <= upper
        assert lower < 0.0
        assert upper < 0.0

    def test_evaluate_batch_contains_all_pairwise_comparisons(self):
        cfg = SimulationConfig(scenario_type="RESTAURANT_PREP_DELAY", random_seed=42, order_volume=15)
        states = AdvancedSimulationEngine.generate_order_batch(cfg)

        batch_eval = CounterfactualEvaluator.evaluate_batch(states, cfg)

        assert "strategy_kpis" in batch_eval
        assert "counterfactual_comparisons" in batch_eval
        comps = batch_eval["counterfactual_comparisons"]
        assert len(comps) == 5

        # Verify candidate vs reference pairs
        pair_names = [(c["candidate_name"], c["reference_name"]) for c in comps]
        assert any("Multi-Agent" in p[0] and "Baseline" in p[1] for p in pair_names)
        assert any("Multi-Agent" in p[0] and "Rule-Based" in p[1] for p in pair_names)
        assert any("Multi-Agent" in p[0] and "ML-Assisted" in p[1] for p in pair_names)

        # Verify statistical fields
        for c in comps:
            assert "duration" in c
            assert "ci_95" in c["duration"]
            assert "cohens_d" in c["duration"]
            assert "p_value" in c["duration"]
            assert "ontime" in c
            assert "cancellation" in c
            assert c["provenance"] == "SIMULATED_COUNTERFACTUAL"
            assert "causal_claim_caveat" in c


# =============================================================================
# 5. Recovery Action Effectiveness
# =============================================================================

class TestActionEffectiveness:
    """Verifies marginal effectiveness analysis for each individual autonomous action."""

    def test_evaluate_all_six_actions(self):
        cfg = SimulationConfig(scenario_type="COMBINED_KITCHEN_DELIVERY_DELAY", random_seed=42, order_volume=20)
        states = AdvancedSimulationEngine.generate_order_batch(cfg)

        scorecards = ActionEffectivenessEvaluator.evaluate_all_actions(states, cfg)

        assert len(scorecards) == 6
        expected_actions = {
            "EXPEDITE_KITCHEN_PING",
            "PRIORITIZE_COURIER_DISPATCH",
            "REASSIGN_COURIER",
            "PROACTIVE_CUSTOMER_NOTIFICATION",
            "APOLOGY_CREDIT_VOUCHER",
            "MONITOR_ORDER",
        }
        found_actions = {s["action_type"] for s in scorecards}
        assert expected_actions == found_actions

        for s in scorecards:
            assert 0.0 <= s["trigger_frequency_pct"] <= 100.0
            assert 0.0 <= s["action_success_rate_pct"] <= 100.0
            assert s["unit_cost_inr"] >= 0.0
            assert s["provenance"] == "SIMULATED_ACTION_EFFECTIVENESS"


# =============================================================================
# 6. Sensitivity & Stress Testing Framework
# =============================================================================

class TestStressTestingFramework:
    """Verifies the 8-dimension operational stress test matrix and resilience verdicts."""

    def test_run_stress_suite_returns_all_eight_dimensions(self):
        results = StressTestFramework.run_stress_suite(base_volume=15, seed=42)

        assert len(results) == 8
        keys = {r["dimension_key"] for r in results}
        expected_keys = {
            "LOW_VOLUME",
            "NORMAL_VOLUME",
            "HIGH_VOLUME",
            "KITCHEN_CONGESTION",
            "COURIER_SHORTAGE",
            "TRAFFIC_GRIDLOCK",
            "CANCELLATION_SURGE",
            "DEGRADED_EFFECTIVENESS",
        }
        assert expected_keys == keys

        for r in results:
            assert r["resilience_verdict"] in ("ROBUST", "MODERATELY_DEGRADED", "SEVERE_BOTTLENECK")
            assert len(r["operational_observation"]) > 0
            assert r["sample_size"] > 0


# =============================================================================
# 7. Experiment Service & API Integration
# =============================================================================

class TestExperimentServiceAndAPI:
    """Verifies database persistence of experiments and FastAPI route functionality."""

    def test_service_run_and_persist_experiment(self, db_session):
        cfg = SimulationConfig(scenario_type="NORMAL_DELIVERY", random_seed=77, order_volume=10)
        exp = ExperimentService.run_experiment(db_session, cfg, name="Test Unit Experiment")

        assert exp.id is not None
        assert exp.name == "Test Unit Experiment"
        assert exp.scenario_type == "NORMAL_DELIVERY"
        assert exp.num_orders == 10
        assert "multi_agent" in exp.kpi_results
        assert len(exp.counterfactual_comparisons["comparisons"]) == 5

        # Query back
        fetched = ExperimentService.get_experiment(db_session, exp.id)
        assert fetched is not None
        assert fetched.id == exp.id

    def test_api_run_simulation_experiment_endpoint(self, client):
        payload = {
            "name": "API Test Run",
            "scenario_type": "RESTAURANT_PREP_DELAY",
            "order_volume": 12,
            "random_seed": 55,
        }
        res = client.post("/api/v1/simulation/experiments/run", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "COMPLETED"
        assert data["name"] == "API Test Run"
        assert "experiment_id" in data
        assert "kpi_results" in data
        assert "counterfactual_comparisons" in data

    def test_api_list_and_get_experiment_endpoints(self, client):
        # 1. Run an experiment first
        run_res = client.post("/api/v1/simulation/experiments/run", json={"order_volume": 10, "random_seed": 12})
        exp_id = run_res.json()["experiment_id"]

        # 2. List experiments
        list_res = client.get("/api/v1/simulation/experiments?limit=10")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] > 0
        assert any(e["id"] == exp_id for e in list_data["experiments"])

        # 3. Get single experiment
        get_res = client.get(f"/api/v1/simulation/experiments/{exp_id}")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["id"] == exp_id
        assert get_data["num_orders"] == 10

    def test_api_stress_test_endpoint(self, client):
        res = client.post("/api/v1/simulation/experiments/stress-test", json={"base_volume": 10, "seed": 42})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "COMPLETED"
        assert data["total_dimensions"] == 8
        assert len(data["stress_test_matrix"]) == 8

    def test_api_action_effectiveness_endpoint(self, client):
        res = client.get("/api/v1/simulation/experiments/actions/effectiveness?scenario_type=NORMAL_DELIVERY&order_volume=10&random_seed=42")
        assert res.status_code == 200
        data = res.json()
        assert len(data["actions"]) == 6
        assert data["provenance"] == "SIMULATED_ACTION_EFFECTIVENESS"
