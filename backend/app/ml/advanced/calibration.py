import os
import joblib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from typing import Dict, Any, Tuple
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.calibration import calibration_curve


class CalibrationEvaluator:
    """
    Evaluates probability calibration, fits Isotonic Regression on validation probabilities,
    and quantifies Brier score, ECE (Expected Calibration Error), and MCE (Maximum Calibration Error).
    """

    def __init__(self, method: str = "isotonic"):
        self.method = method
        self.calibrator = None

    def fit(self, val_probs: np.ndarray, y_val: np.ndarray):
        """Fits calibration curve strictly on validation partition."""
        if self.method == "isotonic":
            self.calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            self.calibrator.fit(val_probs, y_val)
        elif self.method == "sigmoid":
            # Platt scaling: logistic regression on log-odds
            eps = 1e-7
            clipped_probs = np.clip(val_probs, eps, 1.0 - eps)
            logits = np.log(clipped_probs / (1.0 - clipped_probs)).reshape(-1, 1)
            self.calibrator = LogisticRegression(solver="lbfgs")
            self.calibrator.fit(logits, y_val)
        return self

    def predict(self, raw_probs: np.ndarray) -> np.ndarray:
        """Transforms uncalibrated probabilities to calibrated posterior probabilities."""
        if self.calibrator is None:
            raise ValueError("Calibrator must be fitted before predict.")

        if self.method == "isotonic":
            cal_probs = self.calibrator.predict(raw_probs)
        elif self.method == "sigmoid":
            eps = 1e-7
            clipped_probs = np.clip(raw_probs, eps, 1.0 - eps)
            logits = np.log(clipped_probs / (1.0 - clipped_probs)).reshape(-1, 1)
            cal_probs = self.calibrator.predict_proba(logits)[:, 1]

        return np.clip(cal_probs, 0.0, 1.0)

    @staticmethod
    def compute_ece_mce(y_true: np.ndarray, probs: np.ndarray, n_bins: int = 10) -> Tuple[float, float, list]:
        """Calculates Expected Calibration Error (ECE) and Maximum Calibration Error (MCE)."""
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        ece = 0.0
        mce = 0.0
        bins_data = []

        n = len(y_true)
        for i in range(n_bins):
            b_min, b_max = bin_edges[i], bin_edges[i + 1]
            mask = (probs >= b_min) & (probs < b_max if i < n_bins - 1 else probs <= b_max)
            b_size = int(np.sum(mask))

            if b_size > 0:
                acc = float(np.mean(y_true[mask]))
                conf = float(np.mean(probs[mask]))
                err = abs(acc - conf)
                ece += (b_size / n) * err
                mce = max(mce, err)
                bins_data.append({
                    "bin_range": [round(b_min, 2), round(b_max, 2)],
                    "sample_size": b_size,
                    "mean_confidence": round(conf, 4),
                    "empirical_accuracy": round(acc, 4),
                    "calibration_error": round(err, 4),
                })

        return float(ece), float(mce), bins_data

    def evaluate(
        self,
        y_val: np.ndarray,
        p_val_raw: np.ndarray,
        y_test: np.ndarray,
        p_test_raw: np.ndarray,
        task_name: str = "Task C2",
        output_dir: str = "data/artifacts/diagnostics/phase_2_5",
        plots_dir: str = "data/artifacts/diagnostics/phase_2_5/plots",
    ) -> Dict[str, Any]:
        """Runs full calibration pipeline, saves artifact, and produces comparison plots."""
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(plots_dir, exist_ok=True)

        self.fit(p_val_raw, y_val)
        p_test_cal = self.predict(p_test_raw)

        # Compute Brier scores
        brier_uncal = float(brier_score_loss(y_test, p_test_raw))
        brier_cal = float(brier_score_loss(y_test, p_test_cal))

        # Compute ECE and MCE
        ece_uncal, mce_uncal, bins_uncal = self.compute_ece_mce(y_test, p_test_raw)
        ece_cal, mce_cal, bins_cal = self.compute_ece_mce(y_test, p_test_cal)

        # Plot calibration curve comparison
        pt_u, pp_u = calibration_curve(y_test, p_test_raw, n_bins=10, strategy="quantile")
        pt_c, pp_c = calibration_curve(y_test, p_test_cal, n_bins=10, strategy="quantile")

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(pp_u, pt_u, marker="o", color="#E23744", label=f"Uncalibrated (Brier={brier_uncal:.4f}, ECE={ece_uncal:.4f})")
        ax.plot(pp_c, pt_c, marker="s", color="#2ECC71", label=f"Isotonic Calibrated (Brier={brier_cal:.4f}, ECE={ece_cal:.4f})")
        ax.plot([0, 0.25], [0, 0.25], color="black", linestyle="--", label="Perfect Calibration")
        ax.set_title(f"{task_name}: Probability Calibration Comparison (Test Partition)")
        ax.set_xlabel("Mean Predicted Probability")
        ax.set_ylabel("Empirical Fraction of Cancellations")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = os.path.join(plots_dir, "task_c2_calibration_comparison.png")
        plt.savefig(plot_path, dpi=150)
        plt.close()

        results = {
            "task_name": task_name,
            "calibration_method": self.method,
            "brier_score_uncalibrated": round(brier_uncal, 6),
            "brier_score_calibrated": round(brier_cal, 6),
            "brier_score_reduction_pct": round(float((brier_uncal - brier_cal) / brier_uncal * 100), 2),
            "ece_uncalibrated": round(ece_uncal, 4),
            "ece_calibrated": round(ece_cal, 4),
            "mce_uncalibrated": round(mce_uncal, 4),
            "mce_calibrated": round(mce_cal, 4),
            "mean_prob_uncalibrated": round(float(np.mean(p_test_raw)), 4),
            "mean_prob_calibrated": round(float(np.mean(p_test_cal)), 4),
            "true_test_prevalence": round(float(np.mean(y_test)), 4),
            "quantile_calibration_bins_calibrated": bins_cal,
        }

        return results
