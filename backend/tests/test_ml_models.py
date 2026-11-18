import os
import shutil
import tempfile
import numpy as np
import pandas as pd
import pytest

from sklearn.dummy import DummyRegressor, DummyClassifier
from sklearn.linear_model import Ridge, LogisticRegression
from lightgbm import LGBMRegressor, LGBMClassifier

from backend.app.ml.models.config import (
    TrainingTaskConfig,
    get_task_a_config,
    get_task_b_config,
    get_task_c1_config,
    get_task_c2_config,
)
from backend.app.ml.models.evaluator import ModelEvaluator
from backend.app.ml.models.registry import ModelRegistry
from backend.app.ml.models.trainer import ModelTrainer


@pytest.fixture
def synthetic_regression_data():
    np.random.seed(42)
    n = 200
    X = pd.DataFrame({
        "last_mile_distance": np.random.uniform(0.5, 10.0, n),
        "is_zero_last_mile": np.zeros(n, dtype=int),
        "last_mile_distance_sq": np.random.uniform(0.25, 100.0, n),
        "distance_bracket": pd.Series(np.random.choice(["short", "medium", "long"], n)).astype("category"),
        "order_hour": np.random.randint(0, 24, n),
        "hour_sin": np.random.uniform(-1, 1, n),
        "hour_cos": np.random.uniform(-1, 1, n),
        "order_dayofweek": np.random.randint(0, 7, n),
        "dow_sin": np.random.uniform(-1, 1, n),
        "dow_cos": np.random.uniform(-1, 1, n),
        "is_weekend": np.random.choice([0, 1], n),
        "meal_period": pd.Series(np.random.choice(["LUNCH_PEAK", "DINNER_PEAK", "LATE_NIGHT"], n)).astype("category"),
        "is_peak_meal_window": np.random.choice([0, 1], n),
        "rolling_order_volume_15m": np.random.uniform(10, 200, n),
        "rolling_order_volume_60m": np.random.uniform(50, 800, n),
        "demand_acceleration": np.random.uniform(0.5, 2.0, n),
    })
    y = 15.0 + 3.0 * X["last_mile_distance"] + np.random.normal(0, 2.0, n)
    return X, y.values


@pytest.fixture
def synthetic_classification_data():
    np.random.seed(42)
    n = 200
    X = pd.DataFrame({
        "last_mile_distance": np.random.uniform(0.5, 10.0, n),
        "is_zero_last_mile": np.zeros(n, dtype=int),
        "last_mile_distance_sq": np.random.uniform(0.25, 100.0, n),
        "distance_bracket": pd.Series(np.random.choice(["short", "medium", "long"], n)).astype("category"),
        "order_hour": np.random.randint(0, 24, n),
        "hour_sin": np.random.uniform(-1, 1, n),
        "hour_cos": np.random.uniform(-1, 1, n),
        "order_dayofweek": np.random.randint(0, 7, n),
        "dow_sin": np.random.uniform(-1, 1, n),
        "dow_cos": np.random.uniform(-1, 1, n),
        "is_weekend": np.random.choice([0, 1], n),
        "meal_period": pd.Series(np.random.choice(["LUNCH_PEAK", "DINNER_PEAK", "LATE_NIGHT"], n)).astype("category"),
        "is_peak_meal_window": np.random.choice([0, 1], n),
        "rolling_order_volume_15m": np.random.uniform(10, 200, n),
        "rolling_order_volume_60m": np.random.uniform(50, 800, n),
        "demand_acceleration": np.random.uniform(0.5, 2.0, n),
    })
    logits = -3.0 + 0.3 * X["last_mile_distance"] + 0.01 * X["rolling_order_volume_15m"]
    probs = 1.0 / (1.0 + np.exp(-logits))
    y = (np.random.uniform(0, 1, n) < probs).astype(int)
    return X, y


def test_task_to_dataset_mapping_and_schema():
    """Verifies that all 4 task configs map to valid processed parquet datasets."""
    configs = [
        get_task_a_config(),
        get_task_b_config(),
        get_task_c1_config(),
        get_task_c2_config(),
    ]
    for cfg in configs:
        train_path = os.path.join(cfg.dataset_dir, "train.parquet")
        assert os.path.exists(train_path), f"Missing dataset for task {cfg.task_name}: {train_path}"

        df = pd.read_parquet(train_path)
        assert cfg.target_column in df.columns, f"Target {cfg.target_column} missing in {cfg.task_name}"
        for feat in cfg.feature_columns:
            assert feat in df.columns, f"Feature {feat} missing in {cfg.task_name}"


def test_no_quarantined_features_in_model_configs():
    """Verifies that none of the quarantined/leaked fields exist in any model configuration."""
    quarantined = [
        "pickup_time", "delivered_time", "allot_time", "accept_time",
        "rider_id", "order_id", "reassigned_order", "reassignment_method",
        "reassignment_reason", "alloted_orders", "delivered_orders",
        "undelivered_orders", "lifetime_order_count", "cancelled_time",
    ]
    configs = [
        get_task_a_config(),
        get_task_b_config(),
        get_task_c1_config(),
        get_task_c2_config(),
    ]
    for cfg in configs:
        for q in quarantined:
            assert q not in cfg.feature_columns, f"Leaked feature '{q}' found in config for {cfg.task_name}!"


def test_feature_target_separation(synthetic_regression_data):
    """Verifies that prepare_features cleanly separates X from y without data mutation."""
    X_syn, y_syn = synthetic_regression_data
    df = X_syn.copy()
    df["order_id"] = 12345
    df["order_time"] = "2021-01-26 12:00:00"
    df["target_delivery_duration_min"] = y_syn

    cfg = get_task_a_config()
    trainer = ModelTrainer(cfg)
    X, y = trainer.prepare_features(df)

    assert "target_delivery_duration_min" not in X.columns
    assert "order_id" not in X.columns
    assert "order_time" not in X.columns
    assert len(X) == len(y)
    assert np.allclose(y, y_syn)


def test_reproducible_training(synthetic_regression_data):
    """Verifies that model training with set seed produces byte-identical predictions."""
    X, y = synthetic_regression_data
    m1 = LGBMRegressor(n_estimators=30, learning_rate=0.1, random_state=42, n_jobs=1, verbosity=-1)
    m2 = LGBMRegressor(n_estimators=30, learning_rate=0.1, random_state=42, n_jobs=1, verbosity=-1)

    m1.fit(X, y)
    m2.fit(X, y)

    p1 = m1.predict(X)
    p2 = m2.predict(X)
    np.testing.assert_allclose(p1, p2)


def test_model_serialization_and_reloading(synthetic_regression_data):
    """Verifies that ModelRegistry saves and reloads models with intact inference."""
    temp_dir = tempfile.mkdtemp()
    try:
        X, y = synthetic_regression_data
        model = LGBMRegressor(n_estimators=20, random_state=42, n_jobs=1, verbosity=-1)
        model.fit(X, y)
        preds_before = model.predict(X)

        registry = ModelRegistry(base_artifacts_dir=temp_dir)
        meta = {"task_name": "test_task", "feature_names": list(X.columns)}
        registry.save_model("test_task", "lgb_test", model, meta)

        loaded_model, loaded_meta = registry.load_model("test_task", "lgb_test")
        preds_after = loaded_model.predict(X)

        np.testing.assert_allclose(preds_before, preds_after)
        assert loaded_meta["task_name"] == "test_task"
    finally:
        shutil.rmtree(temp_dir)


def test_metric_calculations_regression():
    """Verifies regression metric calculations and error range breakdown."""
    y_true = np.array([10.0, 25.0, 40.0, 60.0])
    y_pred = np.array([12.0, 23.0, 45.0, 55.0])  # errors: +2, -2, +5, -5

    eval_res = ModelEvaluator.evaluate_regression(y_true, y_pred)
    assert eval_res["mae"] == pytest.approx(3.5, abs=1e-4)
    assert eval_res["rmse"] == pytest.approx(np.sqrt((4 + 4 + 25 + 25) / 4), abs=1e-4)
    assert "absolute_error_percentiles" in eval_res
    assert "performance_by_duration_range" in eval_res
    assert eval_res["performance_by_duration_range"]["under_20min"]["count"] == 1
    assert eval_res["performance_by_duration_range"]["20_to_35min"]["count"] == 1


def test_metric_calculations_classification():
    """Verifies classification metric calculations, PR-AUC, Brier score, and confusion matrix."""
    y_true = np.array([0, 0, 0, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.3, 0.8, 0.9])

    eval_res = ModelEvaluator.evaluate_classification(y_true, y_prob, threshold=0.5)
    assert eval_res["pr_auc"] == pytest.approx(1.0)
    assert eval_res["roc_auc"] == pytest.approx(1.0)
    assert eval_res["precision"] == pytest.approx(1.0)
    assert eval_res["recall"] == pytest.approx(1.0)
    assert eval_res["f1"] == pytest.approx(1.0)
    assert eval_res["confusion_matrix"]["true_positive"] == 2
    assert eval_res["confusion_matrix"]["true_negative"] == 3


def test_threshold_optimization_on_validation():
    """Verifies that find_optimal_threshold tunes threshold on validation probabilities."""
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    # Imbalanced probabilities
    y_prob = np.array([0.05, 0.1, 0.15, 0.2, 0.3, 0.35, 0.4, 0.45])

    thresh, opt_eval = ModelEvaluator.find_optimal_threshold(y_true, y_prob, metric="f1")
    # Default 0.50 yields 0 recall, but optimal threshold should find a split
    assert thresh < 0.50
    assert opt_eval["f1"] > 0.0


def test_linear_preprocessor_training_only_fit(synthetic_classification_data):
    """Verifies that linear model preprocessor fits OneHotEncoder strictly on train."""
    X, y = synthetic_classification_data
    cfg = get_task_b_config()
    trainer = ModelTrainer(cfg)

    preprocessor = trainer.build_linear_preprocessor()
    X_train_trans = preprocessor.fit_transform(X)

    # Check that transform works on new data without refitting
    X_val_trans = preprocessor.transform(X)
    assert X_train_trans.shape == X_val_trans.shape
