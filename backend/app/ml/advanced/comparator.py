import json
from typing import Dict, Any, List


class ModelComparison:
    """
    Compiles baseline-versus-improved model comparisons across all four tasks
    and generates the Final Model Decision Matrix with operational governance classifications.
    """

    GOVERNANCE_STATUSES = [
        "RESEARCH_ONLY",
        "EXPERIMENTAL",
        "APPROVED_FOR_SIMULATION",
        "APPROVED_FOR_CONTROLLED_TRIAGE",
        "NOT_APPROVED",
    ]

    @classmethod
    def build_decision_matrix(
        cls,
        task_a_res: Dict[str, Any],
        task_b_res: Dict[str, Any],
        task_c1_res: Dict[str, Any],
        task_c2_res: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Builds decision matrix and governance recommendations for all 4 tasks."""

        decision_matrix = [
            {
                "task": "Task A: Delivery Duration (ETA)",
                "phase_2_3_baseline": "LightGBM Point Regressor (MAE: 9.38m, RMSE: 12.77m)",
                "phase_2_5_candidate": "LightGBM Quantile Regressors (P10, P50, P90)",
                "validation_performance": f"P50 Pinball: {task_a_res['pinball_loss']['pinball_p50']} | 80% Coverage: {task_a_res['uncertainty_intervals_80']['empirical_coverage_pct']}%",
                "test_performance": f"P50 MAE: {task_a_res['p50_vs_point_baseline']['p50_mae']}m | 80% Coverage: {task_a_res['uncertainty_intervals_80']['empirical_coverage_pct']}% | Mean Width: {task_a_res['uncertainty_intervals_80']['mean_interval_width_minutes']}m",
                "governance_classification": "APPROVED_FOR_SIMULATION",
                "operational_recommendation": (
                    "Deploy P10-P90 conditional intervals for operations simulation and customer communication. "
                    "Point predictions must not be presented without intervals. "
                    "Long-tail (>50 min) orders still suffer from unobserved kitchen delays; ETA + 15m rule remains unvalidated."
                ),
            },
            {
                "task": "Task B: Allocation Delay Risk (>3m)",
                "phase_2_3_baseline": "LightGBM Classifier (Val PR-AUC: 0.0698, Test PR-AUC: 0.0728, 581 alerts/1k)",
                "phase_2_5_candidate": f"LightGBM Optuna Tuned (Val PR-AUC: {task_b_res['best_val_pr_auc']}, Test PR-AUC: {task_b_res['test_pr_auc']})",
                "validation_performance": f"Val PR-AUC: {task_b_res['best_val_pr_auc']}",
                "test_performance": (
                    f"Test PR-AUC: {task_b_res['test_pr_auc']} | Budget 10/1k: Prec {task_b_res['budget_evaluation']['alert_budgets']['budget_10_per_1000']['test_performance']['precision']*100:.1f}%, "
                    f"Rec {task_b_res['budget_evaluation']['alert_budgets']['budget_10_per_1000']['test_performance']['recall']*100:.1f}%"
                ),
                "governance_classification": "NOT_APPROVED",
                "operational_recommendation": (
                    "NOT APPROVED for standalone alerts or operational alarms. At 10 alerts/1k budget, recall is only 3.9%. "
                    "At max F1, 58% of volume is flagged with 93% false alarms. "
                    "Downstream batching utility remains an untested experimental hypothesis requiring comparative simulation."
                ),
            },
            {
                "task": "Task C1: Upfront Cancellation Risk",
                "phase_2_3_baseline": "Logistic Regression / LightGBM (Val PR-AUC: 0.0134, Test PR-AUC: 0.0152 / 0.0207)",
                "phase_2_5_candidate": f"LightGBM Optuna Tuned (Val PR-AUC: {task_c1_res['best_val_pr_auc']}, Test PR-AUC: {task_c1_res['test_pr_auc']})",
                "validation_performance": f"Val PR-AUC: {task_c1_res['best_val_pr_auc']} (Prior: 1.10%)",
                "test_performance": f"Test PR-AUC: {task_c1_res['test_pr_auc']} (Prior: 1.11%)",
                "governance_classification": "RESEARCH_ONLY",
                "operational_recommendation": (
                    "RESEARCH ONLY. Static order-time coordinates and temporal features cannot predict cancellation prior to kitchen "
                    "prep and courier dispatch. Model provides zero actionable separation above the base rate prior. Retain baseline."
                ),
            },
            {
                "task": "Task C2: Landmark Cancellation Risk",
                "phase_2_3_baseline": "LightGBM (Val PR-AUC: 0.0550, Test PR-AUC: 0.0727, Prec: 24.32%, Rec: 11.54%)",
                "phase_2_5_candidate": f"LightGBM Tuned + Isotonic (Val PR-AUC: {task_c2_res['best_val_pr_auc']}, Test PR-AUC: {task_c2_res['test_pr_auc']})",
                "validation_performance": f"Val PR-AUC: {task_c2_res['best_val_pr_auc']} | Brier Reduction: {task_c2_res['calibration_evaluation']['brier_score_reduction_pct']}%",
                "test_performance": (
                    f"Test PR-AUC: {task_c2_res['test_pr_auc']} | Budget 5/1k: Prec {task_c2_res['budget_evaluation']['alert_budgets']['budget_5_per_1000']['test_performance']['precision']*100:.1f}%, "
                    f"Rec {task_c2_res['budget_evaluation']['alert_budgets']['budget_5_per_1000']['test_performance']['recall']*100:.1f}% | Budget 10/1k: Prec {task_c2_res['budget_evaluation']['alert_budgets']['budget_10_per_1000']['test_performance']['precision']*100:.1f}%, Rec {task_c2_res['budget_evaluation']['alert_budgets']['budget_10_per_1000']['test_performance']['recall']*100:.1f}%"
                ),
                "governance_classification": "APPROVED_FOR_CONTROLLED_TRIAGE",
                "operational_recommendation": (
                    "APPROVED FOR CONTROLLED TRIAGE under strict 5-to-10 alerts per 1,000 budget. "
                    "Intercepts 58 to 82 post-landmark cancellations with 17.5% - 27.1% precision (17x - 27x lift). "
                    "Interventions must be non-intrusive (monitoring only; no automated cancellation refunds). "
                    "Target is eventual post-landmark cancellation, not fixed-horizon or imminent cancellation."
                ),
            },
        ]

        return {
            "evaluation_protocol": (
                "Strict Chronological Evaluation: Training partition used for fitting; Validation partition used for "
                "Optuna hyperparameter selection, calibration fitting, and alert budget quantile thresholds. "
                "Test partition evaluated strictly once as iterative historical benchmark comparisons."
            ),
            "decision_matrix": decision_matrix,
        }
