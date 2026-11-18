import os
import json
import joblib
import pytest
import numpy as np
import pandas as pd

from backend.app.ml.advanced.quantile_trainer import ETAQuantileTrainer
from backend.app.ml.advanced.threshold_optimizer import ThresholdOptimizer
from backend.app.ml.advanced.calibration import CalibrationEvaluator
from backend.app.ml.advanced.optimizer import ModelOptimizer
from backend.app.ml.advanced.comparator import ModelComparison
from backend.app.ml.advanced.registry_final import FinalModelRegistry


class TestPhase25QuantileRegression:
    """Verifies Task A Quantile Regression implementation and evaluation metrics."""

    def test_pinball_loss_symmetry_and_values(self):
        y_true = np.array([20.0, 30.0, 40.0])
        # Exact predictions -> zero loss
        loss_exact = ETAQuantileTrainer.pinball_loss(y_true, y_true, quantile=0.5)
        assert loss_exact == 0.0

        # Overprediction vs underprediction
        loss_under = ETAQuantileTrainer.pinball_loss(y_true, y_true - 10.0, quantile=0.9)
        loss_over = ETAQuantileTrainer.pinball_loss(y_true, y_true + 10.0, quantile=0.9)
        assert loss_under > 0
        assert loss_over > 0
        # For q=0.9, underprediction error is penalized with slope q=0.9, overprediction with 1-q=0.1
        assert pytest.approx(loss_under / loss_over, abs=1e-2) == 9.0

    def test_quantile_ordering_and_monotonic_sorting(self):
        # Create un-ordered / crossed predictions
        p10 = np.array([25.0, 15.0, 30.0])
        p50 = np.array([20.0, 20.0, 35.0])  # sample 0 crossed (p10 > p50)
        p90 = np.array([30.0, 25.0, 32.0])  # sample 2 crossed (p50 > p90)

        s10, s50, s90, crossed = ETAQuantileTrainer.enforce_quantile_ordering(p10, p50, p90)
        assert crossed == 2
        # Verify strictly sorted
        assert np.all(s10 <= s50)
        assert np.all(s50 <= s90)
        assert s10[0] == 20.0
        assert s50[0] == 25.0
        assert s90[0] == 30.0

    def test_quantile_artifacts_exist_and_predict(self):
        reg_dir = "data/artifacts/models/phase_2_5"
        for q in ["p10", "p50", "p90"]:
            p = os.path.join(reg_dir, f"task_a_quantile_{q}.joblib")
            assert os.path.exists(p)
            m = joblib.load(p)
            dummy_x = np.zeros((2, 16))
            preds = m.predict(dummy_x)
            assert preds.shape == (2,)

    def test_prediction_interval_coverage_and_schema(self):
        eval_path = "data/artifacts/diagnostics/phase_2_5/task_a_quantile_evaluation.json"
        assert os.path.exists(eval_path)
        with open(eval_path, "r", encoding="utf-8") as f:
            res = json.load(f)

        assert "prediction_schema" in res
        assert res["prediction_schema"]["outputs"] == ["eta_p10_min", "eta_p50_min", "eta_p90_min"]

        cov = res["uncertainty_intervals_80"]["empirical_coverage_pct"]
        assert 70.0 <= cov <= 85.0  # nominal 80% coverage
        assert res["uncertainty_intervals_80"]["mean_interval_width_minutes"] > 15.0

        buckets = res["bucket_level_calibration"]
        assert "under_20min" in buckets
        assert "20_to_35min" in buckets
        assert "35_to_50min" in buckets
        assert "over_50min" in buckets


class TestPhase25ThresholdOptimizerAndBudgets:
    """Verifies alert-budget evaluation and threshold selection."""

    def test_alert_budget_quantile_derivation(self):
        # 1,000 samples with uniform probs
        y_val = np.random.binomial(1, 0.05, 1000)
        p_val = np.linspace(0.01, 0.99, 1000)
        y_test = y_val.copy()
        p_test = p_val.copy()

        budgets = ThresholdOptimizer.evaluate_alert_budgets(y_val, p_val, y_test, p_test)
        b_res = budgets["alert_budgets"]
        assert "budget_5_per_1000" in b_res
        assert "budget_10_per_1000" in b_res
        assert "budget_25_per_1000" in b_res
        assert "budget_50_per_1000" in b_res

        # As budget increases (more alerts allowed), threshold must decrease monotonically
        t5 = b_res["budget_5_per_1000"]["selected_threshold"]
        t10 = b_res["budget_10_per_1000"]["selected_threshold"]
        t25 = b_res["budget_25_per_1000"]["selected_threshold"]
        t50 = b_res["budget_50_per_1000"]["selected_threshold"]
        assert t5 > t10 > t25 > t50

    def test_alert_budget_confusion_matrix_accounting(self):
        with open("data/artifacts/models/phase_2_5/registry.json", "r", encoding="utf-8") as f:
            reg = json.load(f)

        c2_budgets = reg["tasks"]["task_c2_landmark_cancellation"]["alert_budgets"]
        for b_key in ["budget_5_per_1000", "budget_10_per_1000", "budget_25_per_1000", "budget_50_per_1000"]:
            cm = c2_budgets[b_key]["test_performance"]["confusion_matrix"]
            total = cm["true_positive"] + cm["false_positive"] + cm["false_negative"] + cm["true_negative"]
            assert total == 54150
            assert cm["true_positive"] + cm["false_negative"] == 546
            assert cm["true_negative"] + cm["false_positive"] == 53604


class TestPhase25CalibrationEvaluator:
    """Verifies probability calibration and Brier score improvements."""

    def test_isotonic_calibration_fit_and_brier_reduction(self):
        # Synthesize skewed raw probs (overconfident)
        np.random.seed(42)
        y_val = np.random.binomial(1, 0.02, 5000)
        p_val_raw = np.clip(y_val * 0.4 + np.random.beta(2, 5, 5000) * 0.3, 0.01, 0.99)

        cal = CalibrationEvaluator(method="isotonic")
        cal.fit(p_val_raw, y_val)

        p_test_cal = cal.predict(p_val_raw)
        # Mean calibrated prob should be close to true base rate
        assert pytest.approx(np.mean(p_test_cal), abs=0.01) == np.mean(y_val)

    def test_c2_calibrator_artifact_and_metrics(self):
        cal_path = "data/artifacts/models/phase_2_5/task_c2_calibrator.joblib"
        assert os.path.exists(cal_path)
        cal = joblib.load(cal_path)

        with open("data/artifacts/models/phase_2_5/registry.json", "r", encoding="utf-8") as f:
            reg = json.load(f)

        cal_eval = reg["tasks"]["task_c2_landmark_cancellation"]["calibration_evaluation"]
        assert cal_eval["brier_score_calibrated"] < cal_eval["brier_score_uncalibrated"]
        assert cal_eval["brier_score_reduction_pct"] > 50.0
        assert cal_eval["ece_calibrated"] < 0.01


class TestPhase25ModelRegistryAndGovernance:
    """Verifies registry schema completeness, split boundaries, and governance classifications."""

    @pytest.fixture(scope="class")
    def registry_data(self):
        with open("data/artifacts/models/phase_2_5/registry.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def test_registry_metadata_and_library_versions(self, registry_data):
        assert registry_data["model_version"] == "2.5.0"
        libs = registry_data["library_versions"]
        assert "lightgbm" in libs
        assert "scikit_learn" in libs
        assert "optuna" in libs
        assert "joblib" in libs

    def test_governance_decision_matrix_classifications(self, registry_data):
        tasks = registry_data["tasks"]
        # Task A: Approved for simulation
        assert tasks["task_a_delivery_duration_quantiles"]["governance_classification"] == "APPROVED_FOR_SIMULATION"
        assert tasks["task_a_delivery_duration_quantiles"]["operational_approval"] is False

        # Task B: Not approved
        assert tasks["task_b_allocation_delay"]["governance_classification"] == "NOT_APPROVED"
        assert tasks["task_b_allocation_delay"]["operational_approval"] is False

        # Task C1: Research only
        assert tasks["task_c1_upfront_cancellation"]["governance_classification"] == "RESEARCH_ONLY"
        assert tasks["task_c1_upfront_cancellation"]["operational_approval"] is False

        # Task C2: Approved for controlled triage
        assert tasks["task_c2_landmark_cancellation"]["governance_classification"] == "APPROVED_FOR_CONTROLLED_TRIAGE"
        assert tasks["task_c2_landmark_cancellation"]["operational_approval"] is True

    def test_no_test_set_leakage_in_hyperparameters(self, registry_data):
        for t_key in ["task_b_allocation_delay", "task_c1_upfront_cancellation", "task_c2_landmark_cancellation"]:
            t_obj = registry_data["tasks"][t_key]
            assert t_obj["validation_selection_criterion"] == "validation_pr_auc"
            assert "validation_pr_auc" in t_obj
