import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from backend.app.ml.models.registry import ModelRegistry
from backend.app.ml.models.evaluator import ModelEvaluator
from backend.app.ml.models.config import get_task_a_config


class TaskADiagnostics:
    """
    Executes deep diagnostics for Task A: Delivery Duration Regression (ETA).
    Analyzes error distributions, duration range breakdowns, systematic bias,
    and feature associations with extreme errors.
    """

    def __init__(self, artifacts_dir: str = "data/artifacts/models"):
        self.registry = ModelRegistry(artifacts_dir)
        self.config = get_task_a_config()

    def run(self, output_dir: str = "data/artifacts/diagnostics") -> dict:
        os.makedirs(output_dir, exist_ok=True)
        plots_dir = os.path.join(output_dir, "plots")
        os.makedirs(plots_dir, exist_ok=True)

        # 1. Load test data
        test_path = os.path.join(self.config.dataset_dir, "test.parquet")
        test_df = pd.read_parquet(test_path)
        X_test = test_df[self.config.feature_columns].copy()
        y_test = test_df[self.config.target_column].values

        for c in self.config.categorical_columns:
            X_test[c] = X_test[c].astype("category")

        # 2. Load models
        lgb_model, _ = self.registry.load_model(self.config.task_name, "selected_model")
        ridge_model, _ = self.registry.load_model(self.config.task_name, "baseline_ridge")
        dummy_model, _ = self.registry.load_model(self.config.task_name, "baseline_dummy")

        # 3. Generate predictions
        p_lgb = lgb_model.predict(X_test)
        p_ridge = ridge_model.predict(X_test)
        p_dummy = dummy_model.predict(X_test)

        # 4. Overall metrics
        eval_lgb = ModelEvaluator.evaluate_regression(y_test, p_lgb)
        eval_ridge = ModelEvaluator.evaluate_regression(y_test, p_ridge)
        eval_dummy = ModelEvaluator.evaluate_regression(y_test, p_dummy)

        # 5. Range breakdown across all 3 models on identical test subgroups
        range_bins = [
            ("under_20min", (y_test < 20)),
            ("20_to_35min", (y_test >= 20) & (y_test < 35)),
            ("35_to_50min", (y_test >= 35) & (y_test < 50)),
            ("over_50min", (y_test >= 50)),
        ]

        subgroup_comparison = {}
        for label, mask in range_bins:
            subgroup_comparison[label] = {
                "sample_size": int(np.sum(mask)),
                "pct_of_total": round(float(np.mean(mask) * 100), 2),
                "lightgbm": {
                    "mae": round(float(np.mean(np.abs(p_lgb[mask] - y_test[mask]))), 2),
                    "rmse": round(float(np.sqrt(np.mean((p_lgb[mask] - y_test[mask]) ** 2))), 2),
                    "p50_abs_err": round(float(np.percentile(np.abs(p_lgb[mask] - y_test[mask]), 50)), 2),
                    "p75_abs_err": round(float(np.percentile(np.abs(p_lgb[mask] - y_test[mask]), 75)), 2),
                    "p90_abs_err": round(float(np.percentile(np.abs(p_lgb[mask] - y_test[mask]), 90)), 2),
                    "p95_abs_err": round(float(np.percentile(np.abs(p_lgb[mask] - y_test[mask]), 95)), 2),
                },
                "ridge": {
                    "mae": round(float(np.mean(np.abs(p_ridge[mask] - y_test[mask]))), 2),
                    "rmse": round(float(np.sqrt(np.mean((p_ridge[mask] - y_test[mask]) ** 2))), 2),
                },
                "dummy": {
                    "mae": round(float(np.mean(np.abs(p_dummy[mask] - y_test[mask]))), 2),
                    "rmse": round(float(np.sqrt(np.mean((p_dummy[mask] - y_test[mask]) ** 2))), 2),
                },
            }

        # 6. Directional Bias Analysis (Overprediction vs Underprediction)
        errors = p_lgb - y_test  # positive = predicted longer than actual (overprediction)
        over_mask = errors > 0
        under_mask = errors < 0
        exact_mask = errors == 0

        bias_analysis = {
            "overpredicted_orders": {
                "count": int(np.sum(over_mask)),
                "pct": round(float(np.mean(over_mask) * 100), 2),
                "mean_overprediction_minutes": round(float(np.mean(errors[over_mask])), 2),
            },
            "underpredicted_orders": {
                "count": int(np.sum(under_mask)),
                "pct": round(float(np.mean(under_mask) * 100), 2),
                "mean_underprediction_minutes": round(float(np.abs(np.mean(errors[under_mask]))), 2),
            },
            "exact_predictions": int(np.sum(exact_mask)),
        }

        # 7. Extreme Error Profile (Top 10% worst absolute errors)
        abs_err = np.abs(errors)
        err_threshold_90 = np.percentile(abs_err, 90)
        high_err_mask = abs_err >= err_threshold_90

        high_err_features = {
            "threshold_minutes": round(float(err_threshold_90), 2),
            "high_error_count": int(np.sum(high_err_mask)),
            "high_error_mean_last_mile_km": round(float(X_test.loc[high_err_mask, "last_mile_distance"].mean()), 2),
            "normal_error_mean_last_mile_km": round(float(X_test.loc[~high_err_mask, "last_mile_distance"].mean()), 2),
            "high_error_peak_meal_pct": round(float(X_test.loc[high_err_mask, "is_peak_meal_window"].mean() * 100), 2),
            "normal_error_peak_meal_pct": round(float(X_test.loc[~high_err_mask, "is_peak_meal_window"].mean() * 100), 2),
            "high_error_mean_actual_duration": round(float(np.mean(y_test[high_err_mask])), 2),
            "normal_error_mean_actual_duration": round(float(np.mean(y_test[~high_err_mask])), 2),
        }

        diagnostics = {
            "task_name": "Task A: Delivery Duration Regression (ETA)",
            "test_sample_size": len(y_test),
            "model_capability": {
                "output_type": "point_prediction",
                "conditional_quantiles_supported": False,
                "prediction_intervals": "FUTURE_WORK",
                "unvalidated_policies": [
                    "ETA + 15-minute operational intervention rule (unvalidated policy; requires retrospective simulation validation)"
                ],
            },
            "overall_evaluation": {
                "lightgbm": eval_lgb,
                "ridge": eval_ridge,
                "dummy": eval_dummy,
            },
            "subgroup_comparison": subgroup_comparison,
            "bias_analysis": bias_analysis,
            "high_error_profile": high_err_features,
        }

        # Save JSON
        json_path = os.path.join(output_dir, "task_a_eta_diagnostics.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(diagnostics, f, indent=2)

        # Plot 1: Error distribution and Range Comparison
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        # Histogram of errors
        axes[0].hist(errors, bins=60, range=(-40, 40), color="#FC8019", edgecolor="white", alpha=0.8)
        axes[0].axvline(0, color="black", linestyle="--", linewidth=1.2)
        axes[0].set_title("Task A: Delivery Duration Prediction Error (Pred - Actual)")
        axes[0].set_xlabel("Error (Minutes)")
        axes[0].set_ylabel("Order Count")
        axes[0].grid(True, alpha=0.3)

        # Bar chart of MAE by duration bucket
        ranges = list(subgroup_comparison.keys())
        lgb_maes = [subgroup_comparison[r]["lightgbm"]["mae"] for r in ranges]
        ridge_maes = [subgroup_comparison[r]["ridge"]["mae"] for r in ranges]
        dummy_maes = [subgroup_comparison[r]["dummy"]["mae"] for r in ranges]

        x_pos = np.arange(len(ranges))
        width = 0.25
        axes[1].bar(x_pos - width, dummy_maes, width, label="Dummy Median", color="#A0A0A0")
        axes[1].bar(x_pos, ridge_maes, width, label="Ridge Linear", color="#4A90E2")
        axes[1].bar(x_pos + width, lgb_maes, width, label="LightGBM", color="#FC8019")
        axes[1].set_xticks(x_pos)
        axes[1].set_xticklabels(["< 20 min", "20-35 min", "35-50 min", "> 50 min"])
        axes[1].set_title("Test MAE by Actual Delivery Duration Bucket")
        axes[1].set_xlabel("Delivery Duration Subgroup")
        axes[1].set_ylabel("MAE (Minutes)")
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = os.path.join(plots_dir, "task_a_eta_error_analysis.png")
        plt.savefig(plot_path, dpi=150)
        plt.close()

        print(f"Task A Diagnostics exported -> {json_path} and {plot_path}")
        return diagnostics
