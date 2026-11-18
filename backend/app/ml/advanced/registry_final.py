import os
import json
import joblib
import lightgbm
import sklearn
import optuna
import pandas
import numpy
from typing import Dict, Any
from datetime import datetime, timezone


class FinalModelRegistry:
    """
    Manages final Phase 2.5 model artifact persistence, schemas, calibration parameters,
    and governance metadata in data/artifacts/models/phase_2_5/registry.json.
    """

    def __init__(self, registry_dir: str = "data/artifacts/models/phase_2_5"):
        self.registry_dir = registry_dir
        os.makedirs(self.registry_dir, exist_ok=True)

    def persist_registry(
        self,
        task_a_results: Dict[str, Any],
        task_b_results: Dict[str, Any],
        task_c1_results: Dict[str, Any],
        task_c2_results: Dict[str, Any],
        decision_matrix_res: Dict[str, Any],
    ) -> str:
        """Persists all improved artifacts and writes master registry.json."""

        # 1. Save Task B model
        task_b_model_path = os.path.join(self.registry_dir, "task_b_improved_model.joblib")
        joblib.dump(task_b_results["model_artifact"], task_b_model_path)

        # 2. Save Task C1 model
        task_c1_model_path = os.path.join(self.registry_dir, "task_c1_improved_model.joblib")
        joblib.dump(task_c1_results["model_artifact"], task_c1_model_path)

        # 3. Save Task C2 model and calibrator
        task_c2_model_path = os.path.join(self.registry_dir, "task_c2_improved_model.joblib")
        joblib.dump(task_c2_results["model_artifact"], task_c2_model_path)

        task_c2_calib_path = os.path.join(self.registry_dir, "task_c2_calibrator.joblib")
        joblib.dump(task_c2_results["calibrator_artifact"], task_c2_calib_path)

        # 4. Compile master registry.json
        registry_data = {
            "model_version": "2.5.0",
            "phase": "2.5 — Advanced Model Optimization, ETA Uncertainty & Cancellation Intelligence",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "library_versions": {
                "lightgbm": lightgbm.__version__,
                "scikit_learn": sklearn.__version__,
                "optuna": optuna.__version__,
                "joblib": joblib.__version__,
                "pandas": pandas.__version__,
                "numpy": numpy.__version__,
            },
            "split_boundaries": {
                "train": "2021-01-26 to 2021-02-02 (70.2%)",
                "validation": "2021-02-03 to 2021-02-04 (18.0%)",
                "test": "2021-02-05 to 2021-02-06 (11.8%)",
            },
            "evaluation_protocol": decision_matrix_res["evaluation_protocol"],
            "tasks": {
                "task_a_delivery_duration_quantiles": {
                    "task_type": "QUANTILE_REGRESSION",
                    "target": "target_delivery_duration_min",
                    "quantiles": [0.10, 0.50, 0.90],
                    "artifacts": {
                        "p10": "task_a_quantile_p10.joblib",
                        "p50": "task_a_quantile_p50.joblib",
                        "p90": "task_a_quantile_p90.joblib",
                    },
                    "features": task_a_results["prediction_schema"]["inputs"],
                    "evaluation": {
                        "pinball_loss": task_a_results["pinball_loss"],
                        "uncertainty_intervals_80": task_a_results["uncertainty_intervals_80"],
                        "bucket_level_calibration": task_a_results["bucket_level_calibration"],
                    },
                    "governance_classification": "APPROVED_FOR_SIMULATION",
                    "operational_approval": False,
                    "approval_notes": "Approved for operations simulation. Requires quantile intervals for customer display. Point predictions alone prohibited.",
                },
                "task_b_allocation_delay": {
                    "task_type": "BINARY_CLASSIFICATION",
                    "target": "target_is_allocation_delayed",
                    "artifact": "task_b_improved_model.joblib",
                    "hyperparameters": task_b_results["best_hyperparameters"],
                    "validation_selection_criterion": "validation_pr_auc",
                    "validation_pr_auc": task_b_results["best_val_pr_auc"],
                    "test_pr_auc": task_b_results["test_pr_auc"],
                    "alert_budgets": task_b_results["budget_evaluation"]["alert_budgets"],
                    "governance_classification": "NOT_APPROVED",
                    "operational_approval": False,
                    "approval_notes": "Not approved for standalone alerts. High false-positive rate. Batching integration is an untested hypothesis.",
                },
                "task_c1_upfront_cancellation": {
                    "task_type": "BINARY_CLASSIFICATION",
                    "target": "target_is_cancelled",
                    "artifact": "task_c1_improved_model.joblib",
                    "hyperparameters": task_c1_results["best_hyperparameters"],
                    "validation_selection_criterion": "validation_pr_auc",
                    "validation_pr_auc": task_c1_results["best_val_pr_auc"],
                    "test_pr_auc": task_c1_results["test_pr_auc"],
                    "alert_budgets": task_c1_results["budget_evaluation"]["alert_budgets"],
                    "governance_classification": "RESEARCH_ONLY",
                    "operational_approval": False,
                    "approval_notes": "Research only. Near-random separation over baseline prior (1.11%). Cannot predict upfront cancellation.",
                },
                "task_c2_landmark_cancellation": {
                    "task_type": "BINARY_CLASSIFICATION",
                    "target": "target_cancelled_post_landmark",
                    "target_semantics": "eventual post-landmark cancellation within the observed lifecycle (NOT a fixed-horizon prediction)",
                    "artifacts": {
                        "model": "task_c2_improved_model.joblib",
                        "calibrator": "task_c2_calibrator.joblib",
                    },
                    "hyperparameters": task_c2_results["best_hyperparameters"],
                    "validation_selection_criterion": "validation_pr_auc",
                    "validation_pr_auc": task_c2_results["best_val_pr_auc"],
                    "test_pr_auc": task_c2_results["test_pr_auc"],
                    "alert_budgets": task_c2_results["budget_evaluation"]["alert_budgets"],
                    "calibration_evaluation": task_c2_results["calibration_evaluation"],
                    "governance_classification": "APPROVED_FOR_CONTROLLED_TRIAGE",
                    "operational_approval": True,
                    "approval_notes": (
                        "Approved for controlled triage queue under 5-to-10 alerts per 1,000 budget. "
                        "Non-intrusive monitoring only. Does not imply imminent cancellation."
                    ),
                },
            },
            "decision_matrix": decision_matrix_res["decision_matrix"],
        }

        registry_path = os.path.join(self.registry_dir, "registry.json")
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry_data, f, indent=2)

        print(f"Phase 2.5 Final Model Registry saved -> {registry_path}")
        return registry_path
