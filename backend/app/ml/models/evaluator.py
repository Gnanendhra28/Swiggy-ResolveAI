import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional


class ModelEvaluator:
    """
    Evaluates regression and classification models with production-grade rigor.
    Calculates operational metrics, error percentiles, duration bucket breakdowns,
    calibration (Brier score), and precision/recall trade-off sweeps.
    """

    @staticmethod
    def evaluate_regression(
        y_true: np.ndarray, y_pred: np.ndarray
    ) -> Dict[str, Any]:
        """Calculates regression metrics (MAE, RMSE, R2, percentiles, range breakdown)."""
        errors = y_pred - y_true
        abs_errors = np.abs(errors)

        mae = float(np.mean(abs_errors))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        ss_res = np.sum(errors ** 2)
        r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

        percentiles = {
            "p10": float(np.percentile(abs_errors, 10)),
            "p25": float(np.percentile(abs_errors, 25)),
            "p50_median": float(np.percentile(abs_errors, 50)),
            "p75": float(np.percentile(abs_errors, 75)),
            "p90": float(np.percentile(abs_errors, 90)),
            "p95": float(np.percentile(abs_errors, 95)),
            "p99": float(np.percentile(abs_errors, 99)),
        }

        # Performance by delivery duration range
        range_bins = [
            ("under_20min", (y_true < 20)),
            ("20_to_35min", (y_true >= 20) & (y_true < 35)),
            ("35_to_50min", (y_true >= 35) & (y_true < 50)),
            ("over_50min", (y_true >= 50)),
        ]

        range_performance = {}
        for label, mask in range_bins:
            if np.sum(mask) > 0:
                range_performance[label] = {
                    "count": int(np.sum(mask)),
                    "pct_of_total": round(float(np.mean(mask) * 100), 2),
                    "mae": round(float(np.mean(abs_errors[mask])), 2),
                    "rmse": round(float(np.sqrt(np.mean(errors[mask] ** 2))), 2),
                }

        return {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "r2": round(r2, 4),
            "sample_size": len(y_true),
            "absolute_error_percentiles": percentiles,
            "performance_by_duration_range": range_performance,
        }

    @staticmethod
    def evaluate_classification(
        y_true: np.ndarray,
        y_prob: np.ndarray,
        threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Calculates classification metrics: PR-AUC, ROC-AUC, Brier score,
        and thresholded precision, recall, F1, and confusion matrix.
        """
        from sklearn.metrics import (
            average_precision_score,
            roc_auc_score,
            brier_score_loss,
            confusion_matrix,
            precision_score,
            recall_score,
            f1_score,
        )

        y_true_int = y_true.astype(int)
        y_pred = (y_prob >= threshold).astype(int)

        pr_auc = float(average_precision_score(y_true_int, y_prob))
        try:
            roc_auc = float(roc_auc_score(y_true_int, y_prob))
        except ValueError:
            roc_auc = 0.5

        brier = float(brier_score_loss(y_true_int, y_prob))

        cm = confusion_matrix(y_true_int, y_pred, labels=[0, 1])
        tn, fp, fn, tp = [int(v) for v in cm.ravel()]

        precision = float(precision_score(y_true_int, y_pred, zero_division=0))
        recall = float(recall_score(y_true_int, y_pred, zero_division=0))
        f1 = float(f1_score(y_true_int, y_pred, zero_division=0))

        positive_prevalence = float(np.mean(y_true_int))

        return {
            "pr_auc": round(pr_auc, 4),
            "roc_auc": round(roc_auc, 4),
            "brier_score": round(brier, 6),
            "positive_class_prevalence": round(positive_prevalence, 4),
            "threshold": round(threshold, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "confusion_matrix": {
                "true_negative": tn,
                "false_positive": fp,
                "false_negative": fn,
                "true_positive": tp,
            },
            "sample_size": len(y_true),
        }

    @staticmethod
    def find_optimal_threshold(
        y_true: np.ndarray,
        y_prob: np.ndarray,
        metric: str = "f1",
        min_precision: Optional[float] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Sweeps candidate decision thresholds on validation data.
        Selects threshold maximizing F1 or satisfying a minimum precision constraint.
        """
        from sklearn.metrics import precision_recall_curve

        precisions, recalls, thresholds = precision_recall_curve(y_true, y_prob)

        best_thresh = 0.5
        best_f1 = -1.0
        best_eval = {}

        # Evaluate across grid of thresholds
        eval_grid = np.linspace(0.01, 0.99, 99)
        for t in eval_grid:
            ev = ModelEvaluator.evaluate_classification(y_true, y_prob, threshold=t)
            p = ev["precision"]
            f1 = ev["f1"]

            if min_precision is not None:
                # Constrained optimization: target precision threshold
                if p >= min_precision and f1 > best_f1:
                    best_f1 = f1
                    best_thresh = float(t)
                    best_eval = ev
            else:
                if f1 > best_f1:
                    best_f1 = f1
                    best_thresh = float(t)
                    best_eval = ev

        if not best_eval:
            best_eval = ModelEvaluator.evaluate_classification(
                y_true, y_prob, threshold=best_thresh
            )

        return best_thresh, best_eval
