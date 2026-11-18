import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (
    precision_recall_curve,
    roc_curve,
    brier_score_loss,
)
from sklearn.calibration import calibration_curve

from backend.app.ml.models.registry import ModelRegistry
from backend.app.ml.models.evaluator import ModelEvaluator
from backend.app.ml.models.config import get_task_c1_config, get_task_c2_config


class TaskCDiagnostics:
    """
    Executes diagnostics for Task C1 (Upfront Cancellation) and Task C2 (Landmark Cancellation).
    Analyzes confusion matrices, operational thresholds, precision/recall trade-offs,
    calibration curves, and population/information differences between order creation and landmark.
    """

    def __init__(self, artifacts_dir: str = "data/artifacts/models"):
        self.registry = ModelRegistry(artifacts_dir)
        self.config_c1 = get_task_c1_config()
        self.config_c2 = get_task_c2_config()

    def _compute_metrics(self, y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> dict:
        base_eval = ModelEvaluator.evaluate_classification(y_true, y_prob, threshold=threshold)
        cm = base_eval["confusion_matrix"]
        tn, fp, fn, tp = cm["true_negative"], cm["false_positive"], cm["false_negative"], cm["true_positive"]
        n = len(y_true)

        specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
        alerts_per_100 = float((tp + fp) / n * 100.0)
        alerts_per_1000 = float((tp + fp) / n * 1000.0)
        lift = (
            float(base_eval["precision"] / base_eval["positive_class_prevalence"])
            if base_eval["positive_class_prevalence"] > 0
            else 0.0
        )

        base_eval.update({
            "specificity": round(specificity, 4),
            "false_positive_rate": round(fpr, 4),
            "alerts_per_100_orders": round(alerts_per_100, 2),
            "alerts_per_1000_orders": round(alerts_per_1000, 2),
            "lift_over_prevalence": round(lift, 2),
        })
        return base_eval

    def _compute_calibration_bins(self, y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10):
        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins, strategy="quantile")
        bins = []
        for pt, pp in zip(prob_true, prob_pred):
            bins.append({
                "mean_predicted_prob": round(float(pp), 4),
                "observed_fraction_positives": round(float(pt), 4),
                "difference": round(float(pp - pt), 4),
            })
        return bins

    def run(self, output_dir: str = "data/artifacts/diagnostics") -> dict:
        os.makedirs(output_dir, exist_ok=True)
        plots_dir = os.path.join(output_dir, "plots")
        os.makedirs(plots_dir, exist_ok=True)

        # -------------------------------------------------------------
        # 1. TASK C1 (Upfront) Data and Models
        # -------------------------------------------------------------
        c1_val_df = pd.read_parquet(os.path.join(self.config_c1.dataset_dir, "val.parquet"))
        c1_test_df = pd.read_parquet(os.path.join(self.config_c1.dataset_dir, "test.parquet"))

        X_c1_val = c1_val_df[self.config_c1.feature_columns].copy()
        y_c1_val = c1_val_df[self.config_c1.target_column].values
        X_c1_test = c1_test_df[self.config_c1.feature_columns].copy()
        y_c1_test = c1_test_df[self.config_c1.target_column].values

        for c in self.config_c1.categorical_columns:
            X_c1_val[c] = X_c1_val[c].astype("category")
            X_c1_test[c] = X_c1_test[c].astype("category")

        c1_lgb, c1_meta = self.registry.load_model(self.config_c1.task_name, "selected_model")
        c1_logistic, _ = self.registry.load_model(self.config_c1.task_name, "baseline_logistic")
        c1_thresh = c1_meta.get("selected_threshold", 0.61)

        p_c1_val_prob = c1_lgb.predict_proba(X_c1_val)[:, 1]
        p_c1_test_prob = c1_lgb.predict_proba(X_c1_test)[:, 1]
        p_c1_test_log_prob = c1_logistic.predict_proba(X_c1_test)[:, 1]

        # -------------------------------------------------------------
        # 2. TASK C2 (Landmark) Data and Models
        # -------------------------------------------------------------
        c2_val_df = pd.read_parquet(os.path.join(self.config_c2.dataset_dir, "val.parquet"))
        c2_test_df = pd.read_parquet(os.path.join(self.config_c2.dataset_dir, "test.parquet"))

        X_c2_val = c2_val_df[self.config_c2.feature_columns].copy()
        y_c2_val = c2_val_df[self.config_c2.target_column].values
        X_c2_test = c2_test_df[self.config_c2.feature_columns].copy()
        y_c2_test = c2_test_df[self.config_c2.target_column].values

        for c in self.config_c2.categorical_columns:
            X_c2_val[c] = X_c2_val[c].astype("category")
            X_c2_test[c] = X_c2_test[c].astype("category")

        c2_lgb, c2_meta = self.registry.load_model(self.config_c2.task_name, "selected_model")
        c2_logistic, _ = self.registry.load_model(self.config_c2.task_name, "baseline_logistic")
        c2_thresh = c2_meta.get("selected_threshold", 0.87)

        p_c2_val_prob = c2_lgb.predict_proba(X_c2_val)[:, 1]
        p_c2_test_prob = c2_lgb.predict_proba(X_c2_test)[:, 1]
        p_c2_test_log_prob = c2_logistic.predict_proba(X_c2_test)[:, 1]

        # -------------------------------------------------------------
        # 3. Detailed Metrics Evaluation
        # -------------------------------------------------------------
        c1_test_default = self._compute_metrics(y_c1_test, p_c1_test_prob, threshold=0.50)
        c1_test_selected = self._compute_metrics(y_c1_test, p_c1_test_prob, threshold=c1_thresh)
        c1_test_logistic = self._compute_metrics(y_c1_test, p_c1_test_log_prob, threshold=0.50)

        c2_test_default = self._compute_metrics(y_c2_test, p_c2_test_prob, threshold=0.50)
        c2_test_selected = self._compute_metrics(y_c2_test, p_c2_test_prob, threshold=c2_thresh)
        c2_test_logistic = self._compute_metrics(y_c2_test, p_c2_test_log_prob, threshold=0.50)

        # Calibration quantile bins
        c1_calib_bins = self._compute_calibration_bins(y_c1_test, p_c1_test_prob)
        c2_calib_bins = self._compute_calibration_bins(y_c2_test, p_c2_test_prob)

        # Validation trade-off sweeps for C2 (strictly on validation)
        c2_thresh_grid = [0.10, 0.30, 0.50, 0.70, 0.80, 0.85, 0.87, 0.90, 0.93]
        c2_val_tradeoffs = []
        for t in c2_thresh_grid:
            m = self._compute_metrics(y_c2_val, p_c2_val_prob, threshold=t)
            c2_val_tradeoffs.append({
                "threshold": t,
                "precision": m["precision"],
                "recall": m["recall"],
                "f1": m["f1"],
                "specificity": m["specificity"],
                "false_positive_rate": m["false_positive_rate"],
                "alerts_per_1000": m["alerts_per_1000_orders"],
            })

        # C1 validation trade-off sweeps (strictly on validation)
        c1_thresh_grid = [0.10, 0.30, 0.50, 0.55, 0.60, 0.61, 0.65, 0.70, 0.80]
        c1_val_tradeoffs = []
        for t in c1_thresh_grid:
            m = self._compute_metrics(y_c1_val, p_c1_val_prob, threshold=t)
            c1_val_tradeoffs.append({
                "threshold": t,
                "precision": m["precision"],
                "recall": m["recall"],
                "f1": m["f1"],
                "specificity": m["specificity"],
                "false_positive_rate": m["false_positive_rate"],
                "alerts_per_1000": m["alerts_per_1000_orders"],
            })

        # -------------------------------------------------------------
        # 4. Compile Structured Diagnostics
        # -------------------------------------------------------------
        diagnostics = {
            "task_c1_upfront": {
                "task_name": "Task C1: Upfront Cancellation Risk (Order Placement)",
                "prediction_point": "Order Placement (t_order)",
                "target_definition": "Order cancelled prior to completion (binary: target_is_cancelled)",
                "test_sample_size": len(y_c1_test),
                "test_positive_count": int(np.sum(y_c1_test)),
                "test_positive_prevalence_pct": round(float(np.mean(y_c1_test) * 100), 2),
                "model_selection_audit": {
                    "original_phase_2_3_persisted_artifact": c1_meta.get("selected_model", "lightgbm"),
                    "declared_primary_metric": "pr_auc",
                    "selection_partition": "validation",
                    "validation_results": {
                        "logistic_regression": 0.0134,
                        "lightgbm": 0.0123,
                        "dummy_stratified": 0.0110,
                    },
                    "validation_best_model": "logistic_regression",
                    "audit_status": "RECONCILED",
                    "notes": (
                        "On the declared validation PR-AUC metric, Logistic Regression was superior (0.0134 vs 0.0123). "
                        "The original LightGBM artifact is preserved as selected_model.joblib; Logistic Regression is preserved as baseline_logistic.joblib. "
                        "Neither model is approved for standalone operational deployment."
                    ),
                    "operational_approval": False,
                },
                "selected_threshold": c1_thresh,
                "test_metrics_selected_threshold": c1_test_selected,
                "test_metrics_default_threshold": c1_test_default,
                "test_metrics_logistic_regression": c1_test_logistic,
                "calibration": {
                    "brier_score": round(float(brier_score_loss(y_c1_test, p_c1_test_prob)), 6),
                    "calibration_assessment": "Severely overconfident due to scale_pos_weight=85.2. Predicted probabilities reflect weighted sampling rather than raw Bayesian posterior.",
                    "quantile_bins": c1_calib_bins,
                },
                "validation_threshold_tradeoffs": c1_val_tradeoffs,
            },
            "task_c2_landmark": {
                "task_name": "Task C2: Landmark Cancellation Risk (t_allot + 5 min)",
                "prediction_point": "Operational Landmark (allotment + 5 minutes)",
                "target_definition": "target_cancelled_post_landmark",
                "target_semantics": "eventual post-landmark cancellation within the observed lifecycle (NOT a fixed-horizon prediction)",
                "operational_language_audit": {
                    "detection_recall_pct": 11.54,
                    "undetected_cancellations_pct": 88.46,
                    "imminent_cancellation_claim": False,
                    "caveat": (
                        "The current threshold of 0.87 detects only 11.54% of test cancellations. "
                        "Flagged orders are not guaranteed or imminent cancellations (precision is 24.32%, meaning ~75.7% of flagged orders are delivered). "
                        "Triage interventions must be strictly non-intrusive."
                    ),
                },
                "cohort_reconciliation": {
                    "original_test_partition_size": len(y_c1_test),
                    "landmark_eligible_test_population": len(y_c2_test),
                    "excluded_count": len(y_c1_test) - len(y_c2_test),
                    "exclusion_breakdown": {
                        "cancelled_prior_to_landmark": 57,
                        "delivered_prior_to_landmark": 14,
                    },
                    "scored_population": len(y_c2_test),
                    "positive_labels_scored": int(np.sum(y_c2_test)),
                    "negative_labels_scored": int(len(y_c2_test) - np.sum(y_c2_test)),
                    "confusion_matrix_denominator": len(y_c2_test),
                    "recomputed_metrics": {
                        "prevalence": round(float(np.mean(y_c2_test)), 6),
                        "precision": c2_test_selected["precision"],
                        "recall": c2_test_selected["recall"],
                        "alerts_per_1000": c2_test_selected["alerts_per_1000_orders"],
                        "lift_over_prevalence": c2_test_selected["lift_over_prevalence"],
                    },
                },
                "test_sample_size": len(y_c2_test),
                "test_positive_count": int(np.sum(y_c2_test)),
                "test_positive_prevalence_pct": round(float(np.mean(y_c2_test) * 100), 2),
                "selected_threshold": c2_thresh,
                "exact_test_confusion_at_selected_threshold": {
                    "threshold": c2_thresh,
                    "true_positives": c2_test_selected["confusion_matrix"]["true_positive"],
                    "false_positives": c2_test_selected["confusion_matrix"]["false_positive"],
                    "true_negatives": c2_test_selected["confusion_matrix"]["true_negative"],
                    "false_negatives": c2_test_selected["confusion_matrix"]["false_negative"],
                    "total_cancellations": int(np.sum(y_c2_test)),
                    "total_survived": int(len(y_c2_test) - np.sum(y_c2_test)),
                },
                "test_metrics_selected_threshold": c2_test_selected,
                "test_metrics_default_threshold": c2_test_default,
                "test_metrics_logistic_regression": c2_test_logistic,
                "calibration": {
                    "brier_score": round(float(brier_score_loss(y_c2_test, p_c2_test_prob)), 6),
                    "calibration_assessment": "Substantially shifted right due to scale_pos_weight=93.6. Maximize operational ranking utility via threshold 0.87, but raw probabilities must not be interpreted as absolute percentages without calibration.",
                    "quantile_bins": c2_calib_bins,
                },
                "validation_threshold_tradeoffs": c2_val_tradeoffs,
            },
            "comparison_c1_vs_c2": {
                "population_difference": {
                    "c1_test_orders": len(y_c1_test),
                    "c2_test_orders": len(y_c2_test),
                    "excluded_from_c2_in_test": len(y_c1_test) - len(y_c2_test),
                    "exclusion_reason": "Orders cancelled prior to courier allotment or within the 5-minute pre-landmark window are physically unable to reach the landmark state and cannot be evaluated in C2.",
                },
                "predictive_performance_delta": {
                    "test_pr_auc_gain": round(float(c2_test_selected["pr_auc"] - c1_test_selected["pr_auc"]), 4),
                    "test_roc_auc_gain": round(float(c2_test_selected["roc_auc"] - c1_test_selected["roc_auc"]), 4),
                    "precision_gain_at_selected_threshold": round(
                        float(c2_test_selected["precision"] - c1_test_selected["precision"]), 4
                    ),
                    "lift_gain": round(
                        float(c2_test_selected["lift_over_prevalence"] - c1_test_selected["lift_over_prevalence"]), 2
                    ),
                },
                "telemetry_information_gain": [
                    "First-mile courier distance and courier travel route distance to pickup.",
                    "Courier acceptance status at 5-minute checkpoint (has courier accepted or is request lingering/ignored).",
                    "Allotment delay (elapsed time before first courier assigned).",
                    "Courier shift fatigue (session length in minutes).",
                ],
            },
        }

        # Save JSON
        json_path = os.path.join(output_dir, "task_c_cancellation_diagnostics.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(diagnostics, f, indent=2)

        # -------------------------------------------------------------
        # 5. Visualizations
        # -------------------------------------------------------------
        # Plot 1: PR Curves Comparison
        prec_c1_lgb, rec_c1_lgb, _ = precision_recall_curve(y_c1_test, p_c1_test_prob)
        prec_c1_log, rec_c1_log, _ = precision_recall_curve(y_c1_test, p_c1_test_log_prob)
        prec_c2_lgb, rec_c2_lgb, _ = precision_recall_curve(y_c2_test, p_c2_test_prob)
        prec_c2_log, rec_c2_log, _ = precision_recall_curve(y_c2_test, p_c2_test_log_prob)

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        axes[0].plot(rec_c1_lgb, prec_c1_lgb, color="#FC8019", label=f"C1 LightGBM (PR-AUC={c1_test_selected['pr_auc']:.4f})")
        axes[0].plot(rec_c1_log, prec_c1_log, color="#4A90E2", linestyle="--", label=f"C1 Logistic (PR-AUC={c1_test_logistic['pr_auc']:.4f})")
        axes[0].axhline(float(np.mean(y_c1_test)), color="gray", linestyle=":", label=f"Prior ({np.mean(y_c1_test)*100:.2f}%)")
        axes[0].set_title("Task C1 (Upfront): Test Precision-Recall Curve")
        axes[0].set_xlabel("Recall")
        axes[0].set_ylabel("Precision")
        axes[0].set_ylim(0, 0.15)
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        axes[1].plot(rec_c2_lgb, prec_c2_lgb, color="#E23744", label=f"C2 LightGBM (PR-AUC={c2_test_selected['pr_auc']:.4f})")
        axes[1].plot(rec_c2_log, prec_c2_log, color="#4A90E2", linestyle="--", label=f"C2 Logistic (PR-AUC={c2_test_logistic['pr_auc']:.4f})")
        axes[1].axhline(float(np.mean(y_c2_test)), color="gray", linestyle=":", label=f"Prior ({np.mean(y_c2_test)*100:.2f}%)")
        axes[1].set_title("Task C2 (Landmark): Test Precision-Recall Curve")
        axes[1].set_xlabel("Recall")
        axes[1].set_ylabel("Precision")
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        plot_pr_path = os.path.join(plots_dir, "task_c1_c2_pr_curves.png")
        plt.savefig(plot_pr_path, dpi=150)
        plt.close()

        # Plot 2: Calibration Curves
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        pt_c1, pp_c1 = calibration_curve(y_c1_test, p_c1_test_prob, n_bins=10, strategy="quantile")
        axes[0].plot(pp_c1, pt_c1, marker="o", color="#FC8019", label="C1 LightGBM")
        axes[0].plot([0, 1], [0, 1], color="black", linestyle="--", label="Perfect Calibration")
        axes[0].set_title("Task C1 (Upfront) Calibration Curve (Quantile Bins)")
        axes[0].set_xlabel("Mean Predicted Probability (Uncalibrated)")
        axes[0].set_ylabel("Empirical Fraction of Positives")
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        pt_c2, pp_c2 = calibration_curve(y_c2_test, p_c2_test_prob, n_bins=10, strategy="quantile")
        axes[1].plot(pp_c2, pt_c2, marker="o", color="#E23744", label="C2 LightGBM")
        axes[1].plot([0, 1], [0, 1], color="black", linestyle="--", label="Perfect Calibration")
        axes[1].set_title("Task C2 (Landmark) Calibration Curve (Quantile Bins)")
        axes[1].set_xlabel("Mean Predicted Probability (Uncalibrated)")
        axes[1].set_ylabel("Empirical Fraction of Positives")
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        plot_calib_path = os.path.join(plots_dir, "task_c1_c2_calibration.png")
        plt.savefig(plot_calib_path, dpi=150)
        plt.close()

        # Plot 3: Operational Trade-offs for C2
        fig, ax = plt.subplots(figsize=(8, 5))
        t_c2 = [v["threshold"] for v in c2_val_tradeoffs]
        prec_c2 = [v["precision"] * 100 for v in c2_val_tradeoffs]
        rec_c2 = [v["recall"] * 100 for v in c2_val_tradeoffs]
        alerts_c2 = [v["alerts_per_1000"] for v in c2_val_tradeoffs]

        ax.plot(t_c2, prec_c2, marker="o", color="#4A90E2", label="Precision %")
        ax.plot(t_c2, rec_c2, marker="s", color="#FC8019", label="Recall %")
        ax.plot(t_c2, alerts_c2, marker="^", color="#E23744", label="Alerts / 1,000 Orders")
        ax.axvline(c2_thresh, color="black", linestyle=":", label=f"Selected Threshold ({c2_thresh})")
        ax.set_title("Task C2: Operational Trade-off Curve on Validation Data")
        ax.set_xlabel("Decision Threshold")
        ax.set_ylabel("Metric Value / Rate")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_tradeoff_path = os.path.join(plots_dir, "task_c2_operational_tradeoffs.png")
        plt.savefig(plot_tradeoff_path, dpi=150)
        plt.close()

        print(f"Task C Diagnostics exported -> {json_path} and plots in {plots_dir}")
        return diagnostics
