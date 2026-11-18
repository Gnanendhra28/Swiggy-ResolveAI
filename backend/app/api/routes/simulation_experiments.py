"""
Swiggy ResolveAI — Simulation Experiments API Router.

Endpoints for running counterfactual recovery experiments, querying experiment history,
retrieving action effectiveness, and running sensitivity stress tests.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.simulation.advanced_engine import SimulationConfig
from backend.app.services.experiment_service import ExperimentService


router = APIRouter(prefix="/simulation/experiments", tags=["Simulation Experiments"])


class RunExperimentRequest(BaseModel):
    name: Optional[str] = None
    scenario_type: str = Field(default="NORMAL_DELIVERY")
    order_volume: int = Field(default=50, ge=5, le=500)
    random_seed: int = Field(default=42)
    prep_time_base_min: float = Field(default=16.0, ge=5.0, le=90.0)
    kitchen_queue_length: int = Field(default=3, ge=0, le=50)
    restaurant_capacity: int = Field(default=20, ge=1, le=100)
    courier_availability_ratio: float = Field(default=0.85, ge=0.1, le=1.0)
    courier_acceptance_delay_min: float = Field(default=2.0, ge=0.1, le=30.0)
    first_mile_distance_km: float = Field(default=2.0, ge=0.1, le=25.0)
    last_mile_distance_km: float = Field(default=3.8, ge=0.5, le=35.0)
    traffic_congestion_factor: float = Field(default=1.2, ge=1.0, le=4.0)
    recovery_action_effectiveness: float = Field(default=0.80, ge=0.1, le=1.0)
    recovery_action_delay_min: float = Field(default=2.0, ge=0.1, le=15.0)
    gross_order_value_inr: float = Field(default=450.0, ge=50.0, le=5000.0)


class StressTestRequest(BaseModel):
    base_volume: int = Field(default=40, ge=10, le=200)
    seed: int = Field(default=101)


@router.post("/run", status_code=status.HTTP_201_CREATED)
def run_simulation_experiment(
    req: RunExperimentRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Executes a matched counterfactual experiment comparing all 4 recovery strategies,
    measures individual action effectiveness, and persists results.
    """
    config = SimulationConfig(
        scenario_type=req.scenario_type,
        random_seed=req.random_seed,
        order_volume=req.order_volume,
        prep_time_base_min=req.prep_time_base_min,
        kitchen_queue_length=req.kitchen_queue_length,
        restaurant_capacity=req.restaurant_capacity,
        courier_availability_ratio=req.courier_availability_ratio,
        courier_acceptance_delay_min=req.courier_acceptance_delay_min,
        first_mile_distance_km=req.first_mile_distance_km,
        last_mile_distance_km=req.last_mile_distance_km,
        traffic_congestion_factor=req.traffic_congestion_factor,
        recovery_action_effectiveness=req.recovery_action_effectiveness,
        recovery_action_delay_min=req.recovery_action_delay_min,
        gross_order_value_inr=req.gross_order_value_inr,
    )

    exp = ExperimentService.run_experiment(db, config, name=req.name)
    return {
        "status": "COMPLETED",
        "id": exp.id,
        "experiment_id": exp.id,
        "name": exp.name,
        "scenario_type": exp.scenario_type,
        "random_seed": exp.random_seed,
        "num_orders": exp.num_orders,
        "config_parameters": exp.config_parameters,
        "strategies_evaluated": exp.strategies_evaluated,
        "kpi_results": exp.kpi_results,
        "counterfactual_comparisons": exp.counterfactual_comparisons,
        "action_effectiveness": exp.action_effectiveness,
        "created_at": exp.created_at.isoformat(),
        "provenance": "SIMULATED_EXPERIMENT",
    }


@router.get("")
def list_simulation_experiments(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Lists persisted simulation experiments."""
    exps = ExperimentService.list_experiments(db, limit=limit, offset=offset)
    return {
        "total": len(exps),
        "experiments": [
            {
                "id": e.id,
                "name": e.name,
                "scenario_type": e.scenario_type,
                "random_seed": e.random_seed,
                "num_orders": e.num_orders,
                "created_at": e.created_at.isoformat(),
                "kpi_summary": {
                    strat: {
                        "on_time_rate_pct": e.kpi_results.get(strat, {}).get("delivery", {}).get("on_time_delivery_rate_pct"),
                        "cancellation_rate_pct": e.kpi_results.get(strat, {}).get("cancellation", {}).get("overall_cancellation_rate_pct"),
                        "avg_duration_min": e.kpi_results.get(strat, {}).get("delivery", {}).get("average_delivery_duration_min"),
                        "net_benefit_inr": e.kpi_results.get(strat, {}).get("business_efficiency", {}).get("net_simulated_operational_benefit_inr"),
                    }
                    for strat in e.strategies_evaluated
                },
            }
            for e in exps
        ],
    }


@router.get("/{experiment_id}")
def get_simulation_experiment(
    experiment_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves full experiment details by ID."""
    exp = ExperimentService.get_experiment(db, experiment_id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{experiment_id}' not found",
        )
    return {
        "id": exp.id,
        "name": exp.name,
        "scenario_type": exp.scenario_type,
        "random_seed": exp.random_seed,
        "num_orders": exp.num_orders,
        "config_parameters": exp.config_parameters,
        "strategies_evaluated": exp.strategies_evaluated,
        "kpi_results": exp.kpi_results,
        "counterfactual_comparisons": exp.counterfactual_comparisons,
        "action_effectiveness": exp.action_effectiveness,
        "created_at": exp.created_at.isoformat(),
    }


@router.post("/stress-test")
def run_stress_test(req: StressTestRequest) -> Dict[str, Any]:
    """Runs the 8-dimension operational stress test suite."""
    results = ExperimentService.run_stress_test(base_volume=req.base_volume, seed=req.seed)
    return {
        "status": "COMPLETED",
        "base_volume": req.base_volume,
        "seed": req.seed,
        "total_dimensions": len(results),
        "stress_test_matrix": results,
        "provenance": "SIMULATED_STRESS_TEST",
    }


@router.get("/actions/effectiveness")
def get_action_effectiveness(
    scenario_type: str = Query(default="NORMAL_DELIVERY"),
    order_volume: int = Query(default=50, ge=5, le=500),
    random_seed: int = Query(default=42),
) -> Dict[str, Any]:
    """Evaluates action effectiveness across the 6 autonomous actions."""
    cfg = SimulationConfig(
        scenario_type=scenario_type,
        order_volume=order_volume,
        random_seed=random_seed,
    )
    scorecards = ExperimentService.evaluate_action_effectiveness(cfg)
    return {
        "scenario_type": scenario_type,
        "order_volume": order_volume,
        "random_seed": random_seed,
        "actions": scorecards,
        "provenance": "SIMULATED_ACTION_EFFECTIVENESS",
    }
