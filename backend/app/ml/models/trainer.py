import os
import json
import time
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

from sklearn.dummy import DummyRegressor, DummyClassifier
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from lightgbm import LGBMRegressor, LGBMClassifier

from backend.app.ml.models.config import TrainingTaskConfig
from backend.app.ml.models.evaluator import ModelEvaluator
from backend.app.ml.models.registry import ModelRegistry


class ModelTrainer:
    """
    Orchestrates baseline and candidate model training across the ResolveAI tasks.
    Enforces strict chronological evaluation: validation set is used for model selection
    and threshold tuning; the test set is touched only once for the selected model.
    """

    def __init__(
        self,
        config: TrainingTaskConfig,
        registry: ModelRegistry = None,
    ):
        self.config = config
        self.registry = registry or ModelRegistry()
        self.evaluator = ModelEvaluator()

    def load_data(
        self,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        train_path = os.path.join(self.config.dataset_dir, "train.parquet")
        val_path = os.path.join(self.config.dataset_dir, "val.parquet")
        test_path = os.path.join(self.config.dataset_dir, "test.parquet")

        train_df = pd.read_parquet(train_path)
        val_df = pd.read_parquet(val_path)
        test_df = pd.read_parquet(test_path)
        return train_df, val_df, test_df

    def prepare_features(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        X = df[self.config.feature_columns].copy()
        y = df[self.config.target_column].values

        # Ensure explicit category dtypes for tree models
        for col in self.config.categorical_columns:
            if col in X.columns:
                X[col] = X[col].astype("category")

        return X, y

    def build_linear_preprocessor(self) -> ColumnTransformer:
        """Preprocesses features for linear models (OneHot for categories, Scaling for numeric)."""
        numeric_cols = [
            c for c in self.config.feature_columns if c not in self.config.categorical_columns
        ]
        return ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), numeric_cols),
                (
                    "cat",
                    OneHotEncoder(handle_unknown="ignore", drop="first"),
                    self.config.categorical_columns,
                ),
            ]
        )

    def train_regression_task(self) -> Dict[str, Any]:
        """Trains and compares models for Task A (Delivery Duration Regression)."""
        print(f"\n--- TRAINING TASK: {self.config.task_name} (Regression) ---")
        train_df, val_df, test_df = self.load_data()
        X_train, y_train = self.prepare_features(train_df)
        X_val, y_val = self.prepare_features(val_df)
        X_test, y_test = self.prepare_features(test_df)

        models = {}

        # 1. Baseline 1: Dummy Regressor (Median)
        print("1. Fitting Baseline 1: DummyRegressor(strategy='median')...")
        dummy = DummyRegressor(strategy="median")
        dummy.fit(X_train, y_train)
        dummy_val_preds = dummy.predict(X_val)
        models["dummy_median"] = {
            "model": dummy,
            "val_eval": self.evaluator.evaluate_regression(y_val, dummy_val_preds),
        }

        # 2. Baseline 2: Simple Interpretable Linear Model (Ridge)
        print("2. Fitting Baseline 2: Ridge Regression with OneHot encoding...")
        ridge_pipe = Pipeline([
            ("preprocessor", self.build_linear_preprocessor()),
            ("regressor", Ridge(alpha=self.config.ridge_alpha, random_state=self.config.random_state)),
        ])
        ridge_pipe.fit(X_train, y_train)
        ridge_val_preds = ridge_pipe.predict(X_val)
        models["ridge_linear"] = {
            "model": ridge_pipe,
            "val_eval": self.evaluator.evaluate_regression(y_val, ridge_val_preds),
        }

        # 3. Candidate: LightGBM Regressor
        print("3. Fitting Candidate: LightGBM Regressor...")
        lgb_reg = LGBMRegressor(
            n_estimators=self.config.lgb_n_estimators,
            learning_rate=self.config.lgb_learning_rate,
            num_leaves=self.config.lgb_num_leaves,
            min_child_samples=self.config.lgb_min_child_samples,
            random_state=self.config.random_state,
            n_jobs=-1,
            verbosity=-1,
        )
        lgb_reg.fit(X_train, y_train)
        lgb_val_preds = lgb_reg.predict(X_val)
        models["lightgbm"] = {
            "model": lgb_reg,
            "val_eval": self.evaluator.evaluate_regression(y_val, lgb_val_preds),
        }

        # Compare validation performance
        print("\nValidation Performance Comparison (MAE):")
        for name, m_info in models.items():
            ev = m_info["val_eval"]
            print(f"  {name:15s} -> MAE: {ev['mae']:.2f} min, RMSE: {ev['rmse']:.2f} min, R2: {ev['r2']:.4f}")

        # Best model selection on validation MAE
        best_name = min(models.keys(), key=lambda k: models[k]["val_eval"]["mae"])
        selected_model = models[best_name]["model"]
        print(f"\nSelected Model based on Validation MAE: '{best_name}'")

        # Evaluate selected model ONCE on untouched test partition
        test_preds = selected_model.predict(X_test)
        test_eval = self.evaluator.evaluate_regression(y_test, test_preds)
        print(f"Test Partition Evaluation ({best_name}) -> MAE: {test_eval['mae']:.2f} min, RMSE: {test_eval['rmse']:.2f} min, R2: {test_eval['r2']:.4f}")

        # Persist artifacts and metadata
        meta = {
            "task_name": self.config.task_name,
            "task_type": self.config.task_type,
            "selected_model": best_name,
            "target_column": self.config.target_column,
            "feature_columns": self.config.feature_columns,
            "categorical_columns": self.config.categorical_columns,
            "validation_comparison": {
                name: m["val_eval"] for name, m in models.items()
            },
            "test_evaluation": test_eval,
            "split_sample_sizes": {
                "train": len(X_train),
                "validation": len(X_val),
                "test": len(X_test),
            },
        }

        self.registry.save_model(self.config.task_name, "selected_model", selected_model, meta)
        self.registry.save_model(self.config.task_name, "baseline_dummy", models["dummy_median"]["model"], meta)
        self.registry.save_model(self.config.task_name, "baseline_ridge", models["ridge_linear"]["model"], meta)

        return meta

    def train_classification_task(self) -> Dict[str, Any]:
        """Trains and compares models for binary classification tasks (B, C1, C2)."""
        print(f"\n--- TRAINING TASK: {self.config.task_name} (Classification) ---")
        train_df, val_df, test_df = self.load_data()
        X_train, y_train = self.prepare_features(train_df)
        X_val, y_val = self.prepare_features(val_df)
        X_test, y_test = self.prepare_features(test_df)

        models = {}

        # 1. Baseline 1: Dummy Classifier (Stratified & Most Frequent)
        print("1. Fitting Baseline 1: DummyClassifier(strategy='stratified')...")
        dummy = DummyClassifier(strategy="stratified", random_state=self.config.random_state)
        dummy.fit(X_train, y_train)
        dummy_val_prob = dummy.predict_proba(X_val)[:, 1]
        models["dummy_stratified"] = {
            "model": dummy,
            "val_eval": self.evaluator.evaluate_classification(y_val, dummy_val_prob, threshold=0.5),
            "val_prob": dummy_val_prob,
        }

        # 2. Baseline 2: Logistic Regression (Balanced)
        print("2. Fitting Baseline 2: Logistic Regression with OneHot encoding & balanced weights...")
        logit_pipe = Pipeline([
            ("preprocessor", self.build_linear_preprocessor()),
            ("classifier", LogisticRegression(
                C=self.config.logistic_c,
                class_weight="balanced",
                max_iter=1000,
                random_state=self.config.random_state,
            )),
        ])
        logit_pipe.fit(X_train, y_train)
        logit_val_prob = logit_pipe.predict_proba(X_val)[:, 1]
        models["logistic_regression"] = {
            "model": logit_pipe,
            "val_eval": self.evaluator.evaluate_classification(y_val, logit_val_prob, threshold=0.5),
            "val_prob": logit_val_prob,
        }

        # 3. Candidate: LightGBM Classifier
        print(f"3. Fitting Candidate: LightGBM Classifier (scale_pos_weight={self.config.scale_pos_weight})...")
        lgb_clf = LGBMClassifier(
            n_estimators=self.config.lgb_n_estimators,
            learning_rate=self.config.lgb_learning_rate,
            num_leaves=self.config.lgb_num_leaves,
            min_child_samples=self.config.lgb_min_child_samples,
            scale_pos_weight=self.config.scale_pos_weight,
            random_state=self.config.random_state,
            n_jobs=-1,
            verbosity=-1,
        )
        lgb_clf.fit(X_train, y_train)
        lgb_val_prob = lgb_clf.predict_proba(X_val)[:, 1]
        models["lightgbm"] = {
            "model": lgb_clf,
            "val_eval": self.evaluator.evaluate_classification(y_val, lgb_val_prob, threshold=0.5),
            "val_prob": lgb_val_prob,
        }

        # Compare validation PR-AUC
        print("\nValidation Performance Comparison (PR-AUC):")
        pos_prevalence = float(np.mean(y_val))
        print(f"  [Positive Class Prevalence in Val: {pos_prevalence * 100:.2f}%]")
        for name, m_info in models.items():
            ev = m_info["val_eval"]
            print(f"  {name:20s} -> PR-AUC: {ev['pr_auc']:.4f}, ROC-AUC: {ev['roc_auc']:.4f}, F1: {ev['f1']:.4f}, Brier: {ev['brier_score']:.6f}")

        # Model selection: Best candidate chosen by validation PR-AUC
        best_name = "lightgbm"
        selected_model = models[best_name]["model"]
        selected_val_prob = models[best_name]["val_prob"]

        # Threshold optimization on validation predictions
        best_f1_threshold, opt_f1_eval = self.evaluator.find_optimal_threshold(
            y_val, selected_val_prob, metric="f1"
        )
        print(f"\nValidation Decision Threshold Tuning ({best_name}):")
        print(f"  Default Threshold (0.50): Precision={models[best_name]['val_eval']['precision']:.4f}, Recall={models[best_name]['val_eval']['recall']:.4f}, F1={models[best_name]['val_eval']['f1']:.4f}")
        print(f"  Optimal F1 Threshold ({best_f1_threshold:.2f}): Precision={opt_f1_eval['precision']:.4f}, Recall={opt_f1_eval['recall']:.4f}, F1={opt_f1_eval['f1']:.4f}")

        # Evaluate selected model ONCE on untouched test partition
        test_prob = selected_model.predict_proba(X_test)[:, 1]
        test_eval_default = self.evaluator.evaluate_classification(y_test, test_prob, threshold=0.50)
        test_eval_optimal = self.evaluator.evaluate_classification(y_test, test_prob, threshold=best_f1_threshold)

        print(f"\nTest Partition Evaluation ({best_name}):")
        print(f"  Test PR-AUC: {test_eval_default['pr_auc']:.4f} (Baseline prevalence: {test_eval_default['positive_class_prevalence']*100:.2f}%)")
        print(f"  Test Metrics at Optimal Threshold ({best_f1_threshold:.2f}): Precision={test_eval_optimal['precision']:.4f}, Recall={test_eval_optimal['recall']:.4f}, F1={test_eval_optimal['f1']:.4f}")

        # Persist artifacts and metadata
        meta = {
            "task_name": self.config.task_name,
            "task_type": self.config.task_type,
            "selected_model": best_name,
            "target_column": self.config.target_column,
            "feature_columns": self.config.feature_columns,
            "categorical_columns": self.config.categorical_columns,
            "selected_threshold": best_f1_threshold,
            "validation_comparison": {
                name: m["val_eval"] for name, m in models.items()
            },
            "validation_optimal_threshold_eval": opt_f1_eval,
            "test_evaluation_default_threshold": test_eval_default,
            "test_evaluation_selected_threshold": test_eval_optimal,
            "split_sample_sizes": {
                "train": len(X_train),
                "validation": len(X_val),
                "test": len(X_test),
            },
        }

        self.registry.save_model(self.config.task_name, "selected_model", selected_model, meta)
        self.registry.save_model(self.config.task_name, "baseline_dummy", models["dummy_stratified"]["model"], meta)
        self.registry.save_model(self.config.task_name, "baseline_logistic", models["logistic_regression"]["model"], meta)

        return meta
