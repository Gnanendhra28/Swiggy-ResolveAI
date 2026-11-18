import numpy as np
from typing import Dict, Any, List
from sklearn.metrics import precision_recall_curve, auc, confusion_matrix, f1_score


class ThresholdOptimizer:
    """
    Computes and evaluates decision thresholds under explicit operational alert budgets:
    - 5 alerts per 1,000 orders (0.50% volume)
    - 10 alerts per 1,000 orders (1.00% volume)
    - 25 alerts per 1,000 orders (2.50% volume)
    - 50 alerts per 1,000 orders (5.00% volume)
    Thresholds are strictly calibrated on the VALIDATION partition and evaluated out-of-sample on TEST.
    """

    ALERT_BUDGETS: List[int] = [5, 10, 25, 50]

    @staticmethod
    def compute_pr_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float:
        prec, rec, _ = precision_recall_curve(y_true, y_prob)
        return float(auc(rec, prec))

    @classmethod
    def evaluate_at_threshold(
        cls, y_true: np.ndarray, y_prob: np.ndarray, threshold: float
    ) -> Dict[str, Any]:
        """Calculates confusion matrix and performance at a specific threshold."""
        pred = (y_prob >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
        n = len(y_true)

        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
        alerts_per_1000 = float((tp + fp) / n * 1000.0)

        return {
            "threshold": round(float(threshold), 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "specificity": round(specificity, 4),
            "false_positive_rate": round(fpr, 4),
            "confusion_matrix": {
                "true_positive": int(tp),
                "false_positive": int(fp),
                "false_negative": int(fn),
                "true_negative": int(tn),
            },
            "alerts_per_1000": round(alerts_per_1000, 2),
            "total_samples": int(n),
        }

    @classmethod
    def evaluate_alert_budgets(
        cls,
        y_val: np.ndarray,
        p_val: np.ndarray,
        y_test: np.ndarray,
        p_test: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Derives threshold for each alert budget on validation data,
        then evaluates performance on both validation and test partitions.
        """
        pr_auc_val = cls.compute_pr_auc(y_val, p_val)
        pr_auc_test = cls.compute_pr_auc(y_test, p_test)

        budget_results = {}
        for budget in cls.ALERT_BUDGETS:
            rate = budget / 1000.0
            # Target alert rate alpha: threshold is the (1 - alpha) quantile of validation probabilities
            thresh = float(np.quantile(p_val, 1.0 - rate))

            val_perf = cls.evaluate_at_threshold(y_val, p_val, thresh)
            test_perf = cls.evaluate_at_threshold(y_test, p_test, thresh)

            budget_results[f"budget_{budget}_per_1000"] = {
                "target_budget_per_1000": budget,
                "selected_threshold": round(thresh, 4),
                "validation_performance": val_perf,
                "test_performance": test_perf,
            }

        # Also find validation optimal F1 threshold
        prec_v, rec_v, thresh_v = precision_recall_curve(y_val, p_val)
        f1_scores = np.zeros_like(thresh_v)
        for i, t in enumerate(thresh_v):
            p = prec_v[i]
            r = rec_v[i]
            f1_scores[i] = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0

        best_idx = int(np.argmax(f1_scores)) if len(f1_scores) > 0 else 0
        opt_thresh = float(thresh_v[best_idx]) if len(thresh_v) > 0 else 0.50

        return {
            "pr_auc_val": round(pr_auc_val, 4),
            "pr_auc_test": round(pr_auc_test, 4),
            "optimal_f1_threshold": round(opt_thresh, 4),
            "optimal_f1_val_performance": cls.evaluate_at_threshold(y_val, p_val, opt_thresh),
            "optimal_f1_test_performance": cls.evaluate_at_threshold(y_test, p_test, opt_thresh),
            "alert_budgets": budget_results,
        }
