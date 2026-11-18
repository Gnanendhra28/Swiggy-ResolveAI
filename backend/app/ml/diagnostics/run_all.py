import os
import json
import time

from backend.app.ml.diagnostics.analyzer_a import TaskADiagnostics
from backend.app.ml.diagnostics.analyzer_b import TaskBDiagnostics
from backend.app.ml.diagnostics.analyzer_c import TaskCDiagnostics
from backend.app.ml.diagnostics.explainability import ExplainabilityDiagnostics


def run_all_diagnostics(output_dir: str = "data/artifacts/diagnostics"):
    start_time = time.time()
    os.makedirs(output_dir, exist_ok=True)
    plots_dir = os.path.join(output_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)

    print("================================================================================")
    print("SWIGGY RESOLVEAI — PHASE 2.4 MODEL DIAGNOSTICS & EXPLAINABILITY SUITE")
    print("================================================================================")

    print("\n[1/4] Running Task A: Delivery Duration (ETA) Error Analysis...")
    diag_a = TaskADiagnostics()
    results_a = diag_a.run(output_dir)

    print("\n[2/4] Running Task B: Rider Allocation Delay Risk Diagnostics...")
    diag_b = TaskBDiagnostics()
    results_b = diag_b.run(output_dir)

    print("\n[3/4] Running Task C1 & C2: Cancellation Risk Diagnostics & Calibration...")
    diag_c = TaskCDiagnostics()
    results_c = diag_c.run(output_dir)

    print("\n[4/4] Running TreeExplainer SHAP & Linear Model Explainability...")
    diag_exp = ExplainabilityDiagnostics()
    results_exp = diag_exp.run(output_dir, sample_size=1500)

    # Master summary compilation
    master_summary = {
        "execution_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "total_runtime_seconds": round(time.time() - start_time, 2),
        "task_a_eta": {
            "test_sample_size": results_a["test_sample_size"],
            "overall_lightgbm_mae": results_a["overall_evaluation"]["lightgbm"]["mae"],
            "overall_lightgbm_rmse": results_a["overall_evaluation"]["lightgbm"]["rmse"],
            "core_sla_20_35m_mae": results_a["subgroup_comparison"]["20_to_35min"]["lightgbm"]["mae"],
            "long_tail_over_50m_mae": results_a["subgroup_comparison"]["over_50min"]["lightgbm"]["mae"],
        },
        "task_b_allocation_delay": {
            "test_sample_size": results_b["test_sample_size"],
            "prevalence_pct": results_b["test_positive_prevalence"],
            "selected_threshold": results_b["test_metrics_at_selected_threshold"]["threshold"],
            "precision": results_b["test_metrics_at_selected_threshold"]["precision"],
            "recall": results_b["test_metrics_at_selected_threshold"]["recall"],
            "f1": results_b["test_metrics_at_selected_threshold"]["f1"],
            "alerts_per_1000": results_b["test_metrics_at_selected_threshold"]["alerts_per_1000_orders"],
            "lift_over_prevalence": results_b["test_metrics_at_selected_threshold"]["lift_over_prevalence"],
        },
        "task_c1_upfront_cancellation": {
            "test_sample_size": results_c["task_c1_upfront"]["test_sample_size"],
            "prevalence_pct": results_c["task_c1_upfront"]["test_positive_prevalence_pct"],
            "selected_threshold": results_c["task_c1_upfront"]["selected_threshold"],
            "pr_auc": results_c["task_c1_upfront"]["test_metrics_selected_threshold"]["pr_auc"],
            "precision": results_c["task_c1_upfront"]["test_metrics_selected_threshold"]["precision"],
            "recall": results_c["task_c1_upfront"]["test_metrics_selected_threshold"]["recall"],
            "lift_over_prevalence": results_c["task_c1_upfront"]["test_metrics_selected_threshold"]["lift_over_prevalence"],
        },
        "task_c2_landmark_cancellation": {
            "test_sample_size": results_c["task_c2_landmark"]["test_sample_size"],
            "total_cancellations": results_c["task_c2_landmark"]["exact_test_confusion_at_selected_threshold"]["total_cancellations"],
            "prevalence_pct": results_c["task_c2_landmark"]["test_positive_prevalence_pct"],
            "selected_threshold": results_c["task_c2_landmark"]["selected_threshold"],
            "pr_auc": results_c["task_c2_landmark"]["test_metrics_selected_threshold"]["pr_auc"],
            "precision": results_c["task_c2_landmark"]["test_metrics_selected_threshold"]["precision"],
            "recall": results_c["task_c2_landmark"]["test_metrics_selected_threshold"]["recall"],
            "f1": results_c["task_c2_landmark"]["test_metrics_selected_threshold"]["f1"],
            "alerts_per_1000": results_c["task_c2_landmark"]["test_metrics_selected_threshold"]["alerts_per_1000_orders"],
            "lift_over_prevalence": results_c["task_c2_landmark"]["test_metrics_selected_threshold"]["lift_over_prevalence"],
        },
        "comparison_c1_vs_c2": results_c["comparison_c1_vs_c2"],
        "artifacts_generated": [
            "data/artifacts/diagnostics/task_a_eta_diagnostics.json",
            "data/artifacts/diagnostics/task_b_allocation_diagnostics.json",
            "data/artifacts/diagnostics/task_c_cancellation_diagnostics.json",
            "data/artifacts/diagnostics/explainability_summary.json",
            "data/artifacts/diagnostics/plots/task_a_eta_error_analysis.png",
            "data/artifacts/diagnostics/plots/task_b_allocation_tradeoff.png",
            "data/artifacts/diagnostics/plots/task_c1_c2_pr_curves.png",
            "data/artifacts/diagnostics/plots/task_c1_c2_calibration.png",
            "data/artifacts/diagnostics/plots/task_c2_operational_tradeoffs.png",
            "data/artifacts/diagnostics/plots/shap_summary_task_a.png",
            "data/artifacts/diagnostics/plots/shap_summary_task_b.png",
            "data/artifacts/diagnostics/plots/shap_summary_task_c2.png",
        ],
    }

    summary_path = os.path.join(output_dir, "diagnostics_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(master_summary, f, indent=2)

    print("\n================================================================================")
    print(f"DIAGNOSTICS COMPLETE in {master_summary['total_runtime_seconds']} seconds.")
    print(f"Master Summary -> {summary_path}")
    print("================================================================================")
    return master_summary


if __name__ == "__main__":
    run_all_diagnostics()
