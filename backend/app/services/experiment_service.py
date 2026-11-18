"""
Swiggy ResolveAI — Simulation Experiment Service.

Coordinates counterfactual experiment execution, action effectiveness evaluation,
stress testing, and database persistence for Phase 5 governance and reporting.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.models.simulation_experiment import SimulationExperiment
from backend.app.simulation.advanced_engine import AdvancedSimulationEngine, SimulationConfig
from backend.app.simulation.counterfactual import CounterfactualEvaluator
from backend.app.simulation.action_effectiveness import ActionEffectivenessEvaluator
from backend.app.simulation.stress_testing import StressTestFramework


class ExperimentService:
    """Service layer managing reproducible simulation experiments."""

    @classmethod
    def run_experiment(
        cls,
        db: Session,
        config: SimulationConfig,
        name: Optional[str] = None,
    ) -> SimulationExperiment:
        """
        Executes a complete counterfactual experiment across all 4 strategies,
        evaluates action effectiveness, and persists the record to the database.
        """
        # 1. Generate matched baseline order states
        states = AdvancedSimulationEngine.generate_order_batch(config)

        # 2. Evaluate all 4 recovery strategies counterfactually
        batch_eval = CounterfactualEvaluator.evaluate_batch(states, config)

        # 3. Evaluate individual recovery action effectiveness
        action_eval = ActionEffectivenessEvaluator.evaluate_all_actions(states, config)

        # 4. Generate experiment title if none provided
        experiment_name = name or (
            f"Exp-{config.scenario_type}-N{config.order_volume}-Seed{config.random_seed}"
        )

        # 5. Persist to database
        experiment = SimulationExperiment(
            id=str(uuid.uuid4()),
            name=experiment_name,
            scenario_type=config.scenario_type,
            random_seed=config.random_seed,
            num_orders=config.order_volume,
            config_parameters=config.to_dict(),
            strategies_evaluated=["baseline", "rule_based", "ml_assisted", "multi_agent"],
            kpi_results=batch_eval["strategy_kpis"],
            counterfactual_comparisons={"comparisons": batch_eval["counterfactual_comparisons"]},
            action_effectiveness={"actions": action_eval},
            created_at=datetime.now(timezone.utc),
        )

        db.add(experiment)
        db.commit()
        db.refresh(experiment)

        return experiment

    @classmethod
    def get_experiment(
        cls,
        db: Session,
        experiment_id: str,
    ) -> Optional[SimulationExperiment]:
        """Retrieves a single experiment by ID."""
        return db.query(SimulationExperiment).filter(SimulationExperiment.id == experiment_id).first()

    @classmethod
    def list_experiments(
        cls,
        db: Session,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SimulationExperiment]:
        """Lists historical simulation experiments ordered by creation time descending."""
        return (
            db.query(SimulationExperiment)
            .order_by(SimulationExperiment.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @classmethod
    def run_stress_test(
        cls,
        base_volume: int = 40,
        seed: int = 101,
    ) -> List[Dict[str, Any]]:
        """Runs the complete 8-dimension stress test suite."""
        return StressTestFramework.run_stress_suite(base_volume=base_volume, seed=seed)

    @classmethod
    def evaluate_action_effectiveness(
        cls,
        config: SimulationConfig,
    ) -> List[Dict[str, Any]]:
        """Generates order batch and evaluates action effectiveness directly."""
        states = AdvancedSimulationEngine.generate_order_batch(config)
        return ActionEffectivenessEvaluator.evaluate_all_actions(states, config)
