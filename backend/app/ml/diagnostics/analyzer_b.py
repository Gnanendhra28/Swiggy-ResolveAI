import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve

from backend.app.ml.models.registry import ModelRegistry
from backend.app.ml.models.evaluator import ModelEvaluator
from backend.app.ml.models.config import get_task_b_config


class TaskBDiagnostics:
    """
    Executes diagnostics for Task B: Rider Allocation Delay Risk (>3 min).
    Analyzes confusion matrix, alert frequency, false-positive rates, specificity,
    and operational trade-offs across decision thresholds.
    """

    def __init__(self, artifacts_dir: str = "data/artifacts/models"):
        self.registry = ModelRegistry(artifacts_dir)
        self.config = get_task_b_config()

    def run(self, output_dir: str = "data/artifacts/diagnostics") -> dict:
        os.makedirs(output_dir, exist_ok=True)
        plots_dir = os.path.join(output_dir, "plots")
        os.makedirs(plots_dir, exist_ok=True)

        # 1. Load data
        val_path = os.path.join(self.config.dataset_dir, "val.parquet")
        test_path = os.path.join(self.config.dataset_dir, "test.parquet")
        val_df = pd.read_parquet(val_path)
        test_df = pd.read_parquet(test_path)

        X_val = val_df[self.config.feature_columns].copy()
        y_val = val_df[self.config.target_column].values
        X_test = test_df[self.config.feature_columns].copy()
        y_test = test_df[self.config.target_column].values

        for c in self.config.categorical_columns:
            X_val[c] = X_val[c].astype("category")
            X_test[c] = X_test[c].astype("category")

        # 2. Load selected model & metadata
        model, meta = self.registry.load_model(self.config.task_name, "selected_model")
        selected_thresh = meta.get("selected_threshold", 0.47)

        # 3. Model predictions
        p_val_prob = model.predict_proba(X_val)[:, 1]
        p_test_prob = model.predict_proba(X_test)[:, 1]

        def compute_detailed_classification_metrics(y_true, y_prob, threshold):
            base_eval = ModelEvaluator.evaluate_classification(y_true, y_prob, threshold=threshold)
            cm = base_eval["confusion_matrix"]
            tn, fp, fn, tp = cm["true_negative"], cm["false_positive"], cm["false_negative"], cm["true_positive"]
            n = len(y_true)

            specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
            fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
            alerts_per_100 = float((tp + fp) / n * 100.0)
            alerts_per_1000 = float((tp + fp) / n * 1000.0)
            lift_over_prevalence = (
                float(base_eval["precision"] / base_eval["positive_class_prevalence"])
                if base_eval["positive_class_prevalence"] > 0
                else 0.0
            )

            base_eval.update({
                "specificity": round(specificity, 4),
                "false_positive_rate": round(fpr, 4),
                "alerts_per_100_orders": round(alerts_per_100, 2),
                "alerts_per_1000_orders": round(alerts_per_1000, 2),
                "lift_over_prevalence": round(lift_over_prevalence, 2),
            })
            return base_eval

        # 4. Evaluate at default (0.50) and selected threshold (0.47) on Test
        test_eval_default = compute_detailed_classification_metrics(y_test, p_test_prob, threshold=0.50)
        test_eval_selected = compute_detailed_classification_metrics(y_test, p_test_prob, threshold=selected_thresh)

        # 5. Threshold trade-off curve evaluated strictly on VALIDATION data
        thresh_grid = [0.10, 0.20, 0.30, 0.40, 0.47, 0.50, 0.60, 0.70, 0.80]
        val_tradeoffs = []
        for t in thresh_grid:
            m = compute_detailed_classification_metrics(y_val, p_val_prob, threshold=t)
            val_tradeoffs.append({
                "threshold": t,
                "precision": m["precision"],
                "recall": m["recall"],
                "f1": m["f1"],
                "specificity": m["specificity"],
                "false_positive_rate": m["false_positive_rate"],
                "alerts_per_1000": m["alerts_per_1000_orders"],
            })

        diagnostics = {
            "task_name": "Task B: Rider Allocation Delay Risk (>3 min)",
            "target_definition": "allot_time - order_time > 3.0 minutes",
            "telemetry_note": "allot_time represents recorded final courier allotment, which for reassigned orders logs the second courier allotment after repushing to auto-allocation pool.",
            "operational_status": {
                "approved_for_standalone_alerts": False,
                "selected_threshold": selected_thresh,
                "alert_rate_per_1000": test_eval_selected["alerts_per_1000_orders"],
                "downstream_batching_usage": "HYPOTHESIS_REQUIRING_EVALUATION",
                "warning": "High alert volume (58.1% of orders flagged) prevents use as standalone alerting without overwhelming operators.",
            },
            "test_sample_size": len(y_test),
            "test_positive_prevalence": round(float(np.mean(y_test) * 100), 2),
            "test_metrics_at_selected_threshold": test_eval_selected,
            "test_metrics_at_default_threshold": test_eval_default,
            "validation_threshold_tradeoffs": val_tradeoffs,
        }

        # Save JSON
        json_path = os.path.join(output_dir, "task_b_allocation_diagnostics.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(diagnostics, f, indent=2)

        # Plot: PR curve and Alert rate vs Recall on Validation
        precisions, recalls, thresholds = precision_recall_curve(y_val, p_val_prob)
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        axes[0].plot(recalls, precisions, color="#FC8019", linewidth=2, label=f"LightGBM (PR-AUC={meta['validation_comparison']['lightgbm']['pr_auc']:.4f})")
        axes[0].axhline(float(np.mean(y_val)), color="gray", linestyle="--", label=f"Random Prior ({np.mean(y_val)*100:.2f}%)")
        axes[0].set_title("Task B: Validation Precision-Recall Curve")
        axes[0].set_xlabel("Recall")
        axes[0].set_ylabel("Precision")
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Alert burden vs recall
        t_arr = [v["threshold"] for v in val_tradeoffs]
        alerts_arr = [v["alerts_per_1000"] for v in val_tradeoffs]
        recalls_arr = [v["recall"] * 100 for v in val_tradeoffs]

        axes[1].plot(t_arr, alerts_arr, marker="o", color="#E23744", label="Alerts per 1,000 Orders")
        axes[1].plot(t_arr, recalls_arr, marker="s", color="#FC8019", label="Recall %")
        axes[1].axvline(selected_thresh, color="black", linestyle=":", label=f"Selected Threshold ({selected_thresh})")
        axes[1].set_title("Task B: Operational Trade-off (Alert Rate vs Recall)")
        axes[1].set_xlabel("Decision Threshold")
        axes[1].set_ylabel("Rate")
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = os.path.join(plots_dir, "task_b_allocation_tradeoff.png")
        plt.savefig(plot_path, dpi=150)
        plt.close()

        print(f"Task B Diagnostics exported -> {json_path} and {plot_path}")
        return diagnostics
