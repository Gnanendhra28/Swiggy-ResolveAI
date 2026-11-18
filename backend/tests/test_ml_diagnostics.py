import os
import json
import pytest
import numpy as np

from backend.app.ml.diagnostics.analyzer_a import TaskADiagnostics
from backend.app.ml.diagnostics.analyzer_b import TaskBDiagnostics
from backend.app.ml.diagnostics.analyzer_c import TaskCDiagnostics
from backend.app.ml.diagnostics.explainability import ExplainabilityDiagnostics


class TestTaskADiagnostics:
    """Verifies Task A Delivery Duration error analysis and diagnostics."""

    @pytest.fixture(scope="class")
    def task_a_results(self, tmp_path_factory):
        out_dir = str(tmp_path_factory.mktemp("diag_a"))
        diag = TaskADiagnostics()
        return diag.run(output_dir=out_dir)

    def test_overall_metrics_validity(self, task_a_results):
        assert "overall_evaluation" in task_a_results
        lgb_eval = task_a_results["overall_evaluation"]["lightgbm"]
        assert lgb_eval["mae"] > 0
        assert lgb_eval["rmse"] > lgb_eval["mae"]
        assert task_a_results["test_sample_size"] > 50000

    def test_subgroup_range_breakdown(self, task_a_results):
        subgroups = task_a_results["subgroup_comparison"]
        assert "under_20min" in subgroups
        assert "20_to_35min" in subgroups
        assert "35_to_50min" in subgroups
        assert "over_50min" in subgroups

        total_pct = sum(sg["pct_of_total"] for sg in subgroups.values())
        assert pytest.approx(total_pct, abs=0.2) == 100.0

        for name, sg in subgroups.items():
            assert sg["lightgbm"]["mae"] > 0
            assert sg["lightgbm"]["p95_abs_err"] >= sg["lightgbm"]["p50_abs_err"]

    def test_directional_bias_partition(self, task_a_results):
        bias = task_a_results["bias_analysis"]
        total_orders = bias["overpredicted_orders"]["count"] + bias["underpredicted_orders"]["count"] + bias["exact_predictions"]
        assert total_orders == task_a_results["test_sample_size"]
        assert bias["overpredicted_orders"]["mean_overprediction_minutes"] > 0
        assert bias["underpredicted_orders"]["mean_underprediction_minutes"] > 0


class TestTaskBDiagnostics:
    """Verifies Task B Allocation Delay diagnostics and validation-only threshold analysis."""

    @pytest.fixture(scope="class")
    def task_b_results(self, tmp_path_factory):
        out_dir = str(tmp_path_factory.mktemp("diag_b"))
        diag = TaskBDiagnostics()
        return diag.run(output_dir=out_dir)

    def test_metrics_schema_and_ranges(self, task_b_results):
        m = task_b_results["test_metrics_at_selected_threshold"]
        assert 0.0 <= m["precision"] <= 1.0
        assert 0.0 <= m["recall"] <= 1.0
        assert 0.0 <= m["specificity"] <= 1.0
        assert 0.0 <= m["false_positive_rate"] <= 1.0
        assert pytest.approx(m["specificity"] + m["false_positive_rate"], abs=1e-3) == 1.0
        assert m["alerts_per_1000_orders"] > 0

    def test_validation_tradeoff_sweep(self, task_b_results):
        tradeoffs = task_b_results["validation_threshold_tradeoffs"]
        assert len(tradeoffs) >= 5

        # As threshold increases, recall should generally decrease and specificity should increase
        recalls = [t["recall"] for t in tradeoffs]
        specificities = [t["specificity"] for t in tradeoffs]
        assert recalls[0] >= recalls[-1]
        assert specificities[0] <= specificities[-1]


class TestTaskCDiagnostics:
    """Verifies Task C1 and C2 Cancellation diagnostics, calibration, and population comparison."""

    @pytest.fixture(scope="class")
    def task_c_results(self, tmp_path_factory):
        out_dir = str(tmp_path_factory.mktemp("diag_c"))
        diag = TaskCDiagnostics()
        return diag.run(output_dir=out_dir)

    def test_exact_c2_test_confusion_counts(self, task_c_results):
        c2 = task_c_results["task_c2_landmark"]
        cm_exact = c2["exact_test_confusion_at_selected_threshold"]

        # Exact positive count must equal TP + FN
        assert cm_exact["true_positives"] + cm_exact["false_negatives"] == cm_exact["total_cancellations"]
        assert cm_exact["true_negatives"] + cm_exact["false_positives"] == cm_exact["total_survived"]
        assert cm_exact["total_cancellations"] + cm_exact["total_survived"] == c2["test_sample_size"]

    def test_population_difference_documented(self, task_c_results):
        comp = task_c_results["comparison_c1_vs_c2"]["population_difference"]
        assert comp["c1_test_orders"] > comp["c2_test_orders"]
        assert comp["excluded_from_c2_in_test"] == comp["c1_test_orders"] - comp["c2_test_orders"]
        assert len(comp["exclusion_reason"]) > 10

    def test_calibration_curve_structure(self, task_c_results):
        c2 = task_c_results["task_c2_landmark"]
        bins = c2["calibration"]["quantile_bins"]
        assert len(bins) == 10
        # Quantile bin predicted probabilities should be non-decreasing
        probs = [b["mean_predicted_prob"] for b in bins]
        assert all(probs[i] <= probs[i+1] for i in range(len(probs)-1))


class TestExplainabilityDiagnostics:
    """Verifies SHAP analysis, feature importance, and linear model explanations."""

    @pytest.fixture(scope="class")
    def exp_results(self, tmp_path_factory):
        out_dir = str(tmp_path_factory.mktemp("diag_exp"))
        diag = ExplainabilityDiagnostics()
        return diag.run(output_dir=out_dir, sample_size=100)

    def test_disclaimer_present(self, exp_results):
        assert "MUST NOT be interpreted as causal intervention effects" in exp_results["disclaimer"]

    def test_global_feature_importance_ranking(self, exp_results):
        for task_key in ["task_a_delivery_duration", "task_b_allocation_delay", "task_c2_cancellation_landmark"]:
            fi = exp_results[task_key]["global_feature_importance_mean_abs_shap"]
            assert len(fi) > 5
            # Verify values are non-negative and ranked descending
            vals = [list(item.values())[1] for item in fi]
            assert all(v >= 0 for v in vals)
            assert all(vals[i] >= vals[i+1] for i in range(len(vals)-1))

    def test_case_studies_exist(self, exp_results):
        task_a = exp_results["task_a_delivery_duration"]
        assert "case_study_accurate_prediction" in task_a
        assert "case_study_extreme_underprediction" in task_a

        task_b = exp_results["task_b_allocation_delay"]
        assert "case_study_true_positive" in task_b
        assert "case_study_false_positive" in task_b

        task_c2 = exp_results["task_c2_cancellation_landmark"]
        assert "case_study_true_positive" in task_c2
        assert "case_study_false_positive" in task_c2
        assert "case_study_false_negative" in task_c2

    def test_linear_coefficients_extracted(self, exp_results):
        coefs_b = exp_results["task_b_allocation_delay"]["linear_baseline_coefficients_logistic"]
        assert len(coefs_b) == 10
        for entry in coefs_b:
            assert "feature" in entry
            assert "coefficient" in entry
            assert "odds_ratio" in entry
            assert entry["odds_ratio"] > 0


class TestPhase241ReconciliationAndClaimsAudit:
    """Regression tests for Phase 2.4.1 diagnostic reconciliation and operational claims."""

    def test_task_a_model_is_point_predictor_and_intervals_marked_future_work(self):
        from backend.app.ml.models.registry import ModelRegistry
        registry = ModelRegistry("data/artifacts/models")
        model, meta = registry.load_model("delivery_duration", "selected_model")

        # Verify model produces 1D point predictions, not conditional quantiles
        dummy_input = np.zeros((3, 16))
        preds = model.predict(dummy_input)
        assert len(preds.shape) == 1
        assert preds.shape[0] == 3

        # Verify registry metadata
        assert meta["selection_criterion"] == "validation_mae"
        assert meta["selection_partition"] == "validation"
        assert meta["model_capability"]["conditional_quantiles_supported"] is False
        assert meta["model_capability"]["prediction_intervals"] == "FUTURE_WORK"
        assert any("unvalidated" in p.lower() for p in meta["model_capability"]["unvalidated_policies"])

    def test_task_b_not_approved_for_standalone_alerts(self):
        with open("data/artifacts/diagnostics/task_b_allocation_diagnostics.json", "r", encoding="utf-8") as f:
            diag_b = json.load(f)

        op_status = diag_b["operational_status"]
        assert op_status["approved_for_standalone_alerts"] is False
        assert op_status["alert_rate_per_1000"] > 500
        assert "HYPOTHESIS" in op_status["downstream_batching_usage"]

    def test_task_c1_model_selection_metadata_and_reconciliation(self):
        from backend.app.ml.models.registry import ModelRegistry
        registry = ModelRegistry("data/artifacts/models")

        # Load persisted selected model metadata
        _, meta_c1 = registry.load_model("cancellation_upfront", "selected_model")
        assert meta_c1["selection_criterion"] == "validation_pr_auc"
        assert meta_c1["selection_partition"] == "validation"

        audit = meta_c1["selection_audit"]
        assert audit["declared_primary_metric"] == "pr_auc"
        assert audit["evaluation_partition"] == "validation"
        assert audit["validation_best_model"] == "logistic_regression"
        assert audit["validation_results"]["logistic_regression"] > audit["validation_results"]["lightgbm"]
        assert audit["operational_approval"] is False

        # Verify both artifacts exist on disk and can be loaded
        lgb_model, _ = registry.load_model("cancellation_upfront", "selected_model")
        log_model, _ = registry.load_model("cancellation_upfront", "baseline_logistic")
        assert lgb_model is not None
        assert log_model is not None

    def test_task_c2_cohort_reconciliation_and_exact_denominators(self):
        import pandas as pd
        df_c1_test = pd.read_parquet("data/processed/cancellation/test.parquet")
        df_c2_test = pd.read_parquet("data/processed/cancellation/operational_landmark/test.parquet")

        # 1. Cohort sizes
        n_c1 = len(df_c1_test)
        n_c2 = len(df_c2_test)
        assert n_c1 == 54221
        assert n_c2 == 54150
        assert n_c1 - n_c2 == 71

        # 2. Excluded orders breakdown
        excluded_ids = set(df_c1_test["order_id"]) - set(df_c2_test["order_id"])
        assert len(excluded_ids) == 71
        df_ex = df_c1_test[df_c1_test["order_id"].isin(excluded_ids)]
        assert (df_ex["target_is_cancelled"] == 1).sum() == 57
        assert (df_ex["target_is_cancelled"] == 0).sum() == 14

        # 3. Scored population labels
        positives = int(df_c2_test["target_cancelled_post_landmark"].sum())
        negatives = int((df_c2_test["target_cancelled_post_landmark"] == 0).sum())
        assert positives == 546
        assert negatives == 53604
        assert positives + negatives == 54150

        # 4. Confusion matrix denominator matches eligible population exactly
        with open("data/artifacts/diagnostics/task_c_cancellation_diagnostics.json", "r", encoding="utf-8") as f:
            diag_c = json.load(f)
        c2 = diag_c["task_c2_landmark"]
        cm = c2["exact_test_confusion_at_selected_threshold"]
        total_denom = cm["true_positives"] + cm["false_positives"] + cm["false_negatives"] + cm["true_negatives"]
        assert total_denom == 54150

        # 5. Recomputed metrics verification
        prec = cm["true_positives"] / (cm["true_positives"] + cm["false_positives"])
        rec = cm["true_positives"] / (cm["true_positives"] + cm["false_negatives"])
        alerts_per_1000 = (cm["true_positives"] + cm["false_positives"]) / 54150 * 1000
        assert pytest.approx(prec, abs=1e-4) == 0.2432
        assert pytest.approx(rec, abs=1e-4) == 0.1154
        assert pytest.approx(alerts_per_1000, abs=1e-2) == 4.78

    def test_task_c2_operational_language_and_recall_caveat(self):
        with open("data/artifacts/diagnostics/task_c_cancellation_diagnostics.json", "r", encoding="utf-8") as f:
            diag_c = json.load(f)
        c2 = diag_c["task_c2_landmark"]
        assert "eventual post-landmark cancellation" in c2["target_semantics"]
        assert "NOT a fixed-horizon prediction" in c2["target_semantics"]

        lang_audit = c2["operational_language_audit"]
        assert lang_audit["detection_recall_pct"] == 11.54
        assert lang_audit["undetected_cancellations_pct"] == 88.46
        assert lang_audit["imminent_cancellation_claim"] is False

