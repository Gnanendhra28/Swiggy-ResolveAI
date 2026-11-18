import os
import json
import time
import joblib
import shap
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve, auc

from backend.app.ml.advanced.quantile_trainer import ETAQuantileTrainer
from backend.app.ml.advanced.optimizer import ModelOptimizer
from backend.app.ml.advanced.comparator import ModelComparison
from backend.app.ml.advanced.registry_final import FinalModelRegistry
from backend.app.ml.models.config import get_task_c2_config


def run_phase_2_5():
    start_time = time.time()
    models_dir = "data/artifacts/models/phase_2_5"
    diag_dir = "data/artifacts/diagnostics/phase_2_5"
    plots_dir = os.path.join(diag_dir, "plots")
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)

    print("=" * 80)
    print("SWIGGY RESOLVEAI — PHASE 2.5 ADVANCED MODEL OPTIMIZATION & UNCERTAINTY SUITE")
    print("=" * 80)

    # 1. TASK A: ETA Quantile Regression (P10, P50, P90)
    print("\n[STEP 1/5] Training Task A ETA Quantile Regressors (P10, P50, P90)...")
    q_trainer = ETAQuantileTrainer(random_state=42)
    q_trainer.train()
    task_a_res = q_trainer.evaluate(artifacts_models_dir=models_dir, diagnostics_dir=diag_dir)

    # 2. TASK B, C1, C2: Optimization with Optuna on Validation Partition
    print("\n[STEP 2/5] Running Hyperparameter Optimization strictly on Validation Data...")
    optimizer = ModelOptimizer(random_state=42)
    task_b_res = optimizer.optimize_task_b(n_trials=8)
    task_c1_res = optimizer.optimize_task_c1(n_trials=8)
    task_c2_res = optimizer.optimize_task_c2(n_trials=12)

    # 3. Decision Matrix & Baseline Comparisons
    print("\n[STEP 3/5] Building Final Model Decision Matrix...")
    comp_res = ModelComparison.build_decision_matrix(
        task_a_res=task_a_res,
        task_b_res=task_b_res,
        task_c1_res=task_c1_res,
        task_c2_res=task_c2_res,
    )

    # 4. Generate Additional Phase 2.5 Plots
    print("\n[STEP 4/5] Generating Diagnostic & Comparative Plots...")
    # Plot: Task C2 Alert Budget Trade-off Curve
    c2_budgets = task_c2_res["budget_evaluation"]["alert_budgets"]
    budget_nums = [5, 10, 25, 50]
    c2_precs = [c2_budgets[f"budget_{b}_per_1000"]["test_performance"]["precision"] * 100 for b in budget_nums]
    c2_recs = [c2_budgets[f"budget_{b}_per_1000"]["test_performance"]["recall"] * 100 for b in budget_nums]
    c2_f1s = [c2_budgets[f"budget_{b}_per_1000"]["test_performance"]["f1"] * 100 for b in budget_nums]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(budget_nums, c2_precs, marker="o", color="#4A90E2", linewidth=2, label="Precision (%)")
    ax.plot(budget_nums, c2_recs, marker="s", color="#FC8019", linewidth=2, label="Recall (%)")
    ax.plot(budget_nums, c2_f1s, marker="^", color="#2ECC71", linewidth=2, linestyle="--", label="F1 Score (x100)")
    ax.set_title("Task C2: Precision & Recall across Operational Alert Budgets (Test Partition)")
    ax.set_xlabel("Alert Budget (Alerts per 1,000 Orders)")
    ax.set_ylabel("Metric (%)")
    ax.set_xticks(budget_nums)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    c2_budget_plot = os.path.join(plots_dir, "task_c2_alert_budgets.png")
    plt.savefig(c2_budget_plot, dpi=150)
    plt.close()

    # Plot: PR Curve Comparison (Baseline vs Improved C2)
    c2_cfg = get_task_c2_config()
    test_df_c2 = pd.read_parquet(os.path.join(c2_cfg.dataset_dir, "test.parquet"))
    X_te_c2 = test_df_c2[c2_cfg.feature_columns].copy()
    y_te_c2 = test_df_c2[c2_cfg.target_column].values
    for c in c2_cfg.categorical_columns:
        X_te_c2[c] = X_te_c2[c].astype("category")

    # Load Phase 2.3 baseline
    base_c2_model = joblib.load("data/artifacts/models/cancellation_landmark/selected_model.joblib")
    p_te_base_c2 = base_c2_model.predict_proba(X_te_c2)[:, 1]
    p_te_opt_c2 = task_c2_res["model_artifact"].predict_proba(X_te_c2)[:, 1]

    pr_b, rc_b, _ = precision_recall_curve(y_te_c2, p_te_base_c2)
    pr_o, rc_o, _ = precision_recall_curve(y_te_c2, p_te_opt_c2)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(rc_b, pr_b, color="#A0A0A0", linestyle="--", label=f"Phase 2.3 Baseline (PR-AUC={auc(rc_b, pr_b):.4f})")
    ax.plot(rc_o, pr_o, color="#E23744", linewidth=2, label=f"Phase 2.5 Optuna Tuned (PR-AUC={auc(rc_o, pr_o):.4f})")
    ax.axhline(float(np.mean(y_te_c2)), color="gray", linestyle=":", label=f"Prior Prevalence ({np.mean(y_te_c2)*100:.2f}%)")
    ax.set_title("Task C2: Precision-Recall Curve Comparison on Test Partition")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    c2_pr_plot = os.path.join(plots_dir, "task_c2_pr_comparison.png")
    plt.savefig(c2_pr_plot, dpi=150)
    plt.close()

    # SHAP Summary Plot for Improved Task C2 Model
    print("Computing SHAP values for improved Task C2 model...")
    sample_idx = np.random.RandomState(42).choice(len(X_te_c2), size=1000, replace=False)
    X_sample = X_te_c2.iloc[sample_idx]
    explainer = shap.TreeExplainer(task_c2_res["model_artifact"])
    shap_vals = explainer(X_sample)
    sv = shap_vals.values if len(shap_vals.values.shape) == 2 else shap_vals.values[:, :, 1]

    plt.figure(figsize=(10, 8))
    shap.summary_plot(sv, X_sample, show=False)
    plt.title("Task C2 Improved Model: SHAP Summary Plot (Test Sample)")
    plt.tight_layout()
    shap_plot_c2 = os.path.join(plots_dir, "shap_summary_task_c2_improved.png")
    plt.savefig(shap_plot_c2, dpi=150)
    plt.close()

    # 5. Save Final Model Registry and Master Summary
    print("\n[STEP 5/5] Persisting Model Artifacts and Final Registry...")
    registry = FinalModelRegistry(registry_dir=models_dir)
    reg_path = registry.persist_registry(
        task_a_results=task_a_res,
        task_b_results=task_b_res,
        task_c1_results=task_c1_res,
        task_c2_results=task_c2_res,
        decision_matrix_res=comp_res,
    )

    # Master diagnostics compilation
    master_diagnostics = {
        "execution_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "total_runtime_seconds": round(time.time() - start_time, 2),
        "task_a_quantiles": task_a_res,
        "task_b_optimization": {
            "best_hyperparameters": task_b_res["best_hyperparameters"],
            "best_val_pr_auc": task_b_res["best_val_pr_auc"],
            "test_pr_auc": task_b_res["test_pr_auc"],
            "budget_evaluation": task_b_res["budget_evaluation"],
        },
        "task_c1_optimization": {
            "best_hyperparameters": task_c1_res["best_hyperparameters"],
            "best_val_pr_auc": task_c1_res["best_val_pr_auc"],
            "test_pr_auc": task_c1_res["test_pr_auc"],
            "budget_evaluation": task_c1_res["budget_evaluation"],
        },
        "task_c2_optimization": {
            "best_hyperparameters": task_c2_res["best_hyperparameters"],
            "best_val_pr_auc": task_c2_res["best_val_pr_auc"],
            "test_pr_auc": task_c2_res["test_pr_auc"],
            "budget_evaluation": task_c2_res["budget_evaluation"],
            "calibration_evaluation": task_c2_res["calibration_evaluation"],
        },
        "decision_matrix": comp_res["decision_matrix"],
    }

    diag_summary_path = os.path.join(diag_dir, "diagnostics_summary.json")
    with open(diag_summary_path, "w", encoding="utf-8") as f:
        json.dump(master_diagnostics, f, indent=2)

    total_time = round(time.time() - start_time, 2)
    print("\n" + "=" * 80)
    print(f"PHASE 2.5 COMPLETE in {total_time} seconds!")
    print(f"Final Model Registry: {reg_path}")
    print(f"Diagnostics Summary:  {diag_summary_path}")
    print("=" * 80)

    return master_diagnostics


if __name__ == "__main__":
    run_phase_2_5()
