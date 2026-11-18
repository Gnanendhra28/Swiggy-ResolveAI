import os
import json
import optuna
import numpy as np
import pandas as pd
import lightgbm as lgb
from typing import Dict, Any, Tuple
from sklearn.metrics import precision_recall_curve, auc

from backend.app.ml.models.config import (
    get_task_b_config,
    get_task_c1_config,
    get_task_c2_config,
)
from backend.app.ml.advanced.threshold_optimizer import ThresholdOptimizer
from backend.app.ml.advanced.calibration import CalibrationEvaluator

optuna.logging.set_verbosity(optuna.logging.WARNING)


class ModelOptimizer:
    """
    Performs disciplined hyperparameter optimization using Optuna strictly on the VALIDATION partition.
    Never exposes the TEST partition to search, thresholding, or calibration.
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state

    @staticmethod
    def _compute_pr_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float:
        prec, rec, _ = precision_recall_curve(y_true, y_prob)
        return float(auc(rec, prec))

    # -------------------------------------------------------------
    # TASK B OPTIMIZATION
    # -------------------------------------------------------------
    def optimize_task_b(self, n_trials: int = 8) -> Dict[str, Any]:
        print("\n--- Optimizing Task B: Rider Allocation Delay Risk ---")
        cfg = get_task_b_config()

        train_df = pd.read_parquet(os.path.join(cfg.dataset_dir, "train.parquet"))
        val_df = pd.read_parquet(os.path.join(cfg.dataset_dir, "val.parquet"))
        test_df = pd.read_parquet(os.path.join(cfg.dataset_dir, "test.parquet"))

        X_tr, y_tr = train_df[cfg.feature_columns].copy(), train_df[cfg.target_column].values
        X_val, y_val = val_df[cfg.feature_columns].copy(), val_df[cfg.target_column].values
        X_te, y_te = test_df[cfg.feature_columns].copy(), test_df[cfg.target_column].values

        for c in cfg.categorical_columns:
            X_tr[c] = X_tr[c].astype("category")
            X_val[c] = X_val[c].astype("category")
            X_te[c] = X_te[c].astype("category")

        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 100, 200, step=50),
                "learning_rate": trial.suggest_float("learning_rate", 0.03, 0.08),
                "num_leaves": trial.suggest_int("num_leaves", 15, 35),
                "max_depth": trial.suggest_int("max_depth", 4, 8),
                "min_child_samples": trial.suggest_int("min_child_samples", 20, 60),
                "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, 15.0),
                "reg_alpha": trial.suggest_float("reg_alpha", 0.01, 1.0, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 5.0, log=True),
                "random_state": self.random_state,
                "n_jobs": -1,
                "verbose": -1,
            }
            m = lgb.LGBMClassifier(**params).fit(X_tr, y_tr)
            pv = m.predict_proba(X_val)[:, 1]
            return self._compute_pr_auc(y_val, pv)

        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=self.random_state),
        )
        study.optimize(objective, n_trials=n_trials)
        best_params = study.best_params
        best_params.update({"random_state": self.random_state, "n_jobs": -1, "verbose": -1})

        best_model = lgb.LGBMClassifier(**best_params).fit(X_tr, y_tr)
        p_val = best_model.predict_proba(X_val)[:, 1]
        p_test = best_model.predict_proba(X_te)[:, 1]

        budget_eval = ThresholdOptimizer.evaluate_alert_budgets(y_val, p_val, y_te, p_test)

        return {
            "task_name": "Task B: Allocation Delay",
            "model_type": "LightGBM Classifier (Optuna Tuned)",
            "best_hyperparameters": study.best_params,
            "best_val_pr_auc": round(study.best_value, 4),
            "test_pr_auc": round(self._compute_pr_auc(y_te, p_test), 4),
            "budget_evaluation": budget_eval,
            "model_artifact": best_model,
        }

    # -------------------------------------------------------------
    # TASK C1 OPTIMIZATION
    # -------------------------------------------------------------
    def optimize_task_c1(self, n_trials: int = 8) -> Dict[str, Any]:
        print("\n--- Optimizing Task C1: Upfront Cancellation Risk ---")
        cfg = get_task_c1_config()

        train_df = pd.read_parquet(os.path.join(cfg.dataset_dir, "train.parquet"))
        val_df = pd.read_parquet(os.path.join(cfg.dataset_dir, "val.parquet"))
        test_df = pd.read_parquet(os.path.join(cfg.dataset_dir, "test.parquet"))

        X_tr, y_tr = train_df[cfg.feature_columns].copy(), train_df[cfg.target_column].values
        X_val, y_val = val_df[cfg.feature_columns].copy(), val_df[cfg.target_column].values
        X_te, y_te = test_df[cfg.feature_columns].copy(), test_df[cfg.target_column].values

        for c in cfg.categorical_columns:
            X_tr[c] = X_tr[c].astype("category")
            X_val[c] = X_val[c].astype("category")
            X_te[c] = X_te[c].astype("category")

        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 80, 160, step=40),
                "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.06),
                "num_leaves": trial.suggest_int("num_leaves", 10, 25),
                "max_depth": trial.suggest_int("max_depth", 3, 6),
                "min_child_samples": trial.suggest_int("min_child_samples", 40, 100),
                "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, 50.0),
                "reg_alpha": trial.suggest_float("reg_alpha", 0.05, 2.0, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 10.0, log=True),
                "random_state": self.random_state,
                "n_jobs": -1,
                "verbose": -1,
            }
            m = lgb.LGBMClassifier(**params).fit(X_tr, y_tr)
            pv = m.predict_proba(X_val)[:, 1]
            return self._compute_pr_auc(y_val, pv)

        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=self.random_state),
        )
        study.optimize(objective, n_trials=n_trials)
        best_params = study.best_params
        best_params.update({"random_state": self.random_state, "n_jobs": -1, "verbose": -1})

        best_model = lgb.LGBMClassifier(**best_params).fit(X_tr, y_tr)
        p_val = best_model.predict_proba(X_val)[:, 1]
        p_test = best_model.predict_proba(X_te)[:, 1]

        budget_eval = ThresholdOptimizer.evaluate_alert_budgets(y_val, p_val, y_te, p_test)

        return {
            "task_name": "Task C1: Upfront Cancellation",
            "model_type": "LightGBM Classifier (Optuna Tuned)",
            "best_hyperparameters": study.best_params,
            "best_val_pr_auc": round(study.best_value, 4),
            "test_pr_auc": round(self._compute_pr_auc(y_te, p_test), 4),
            "budget_evaluation": budget_eval,
            "model_artifact": best_model,
        }

    # -------------------------------------------------------------
    # TASK C2 OPTIMIZATION (HIGH PRIORITY)
    # -------------------------------------------------------------
    def optimize_task_c2(self, n_trials: int = 12) -> Dict[str, Any]:
        print("\n--- Optimizing Task C2: Operational Landmark Cancellation (High Priority) ---")
        cfg = get_task_c2_config()

        train_df = pd.read_parquet(os.path.join(cfg.dataset_dir, "train.parquet"))
        val_df = pd.read_parquet(os.path.join(cfg.dataset_dir, "val.parquet"))
        test_df = pd.read_parquet(os.path.join(cfg.dataset_dir, "test.parquet"))

        X_tr, y_tr = train_df[cfg.feature_columns].copy(), train_df[cfg.target_column].values
        X_val, y_val = val_df[cfg.feature_columns].copy(), val_df[cfg.target_column].values
        X_te, y_te = test_df[cfg.feature_columns].copy(), test_df[cfg.target_column].values

        for c in cfg.categorical_columns:
            X_tr[c] = X_tr[c].astype("category")
            X_val[c] = X_val[c].astype("category")
            X_te[c] = X_te[c].astype("category")

        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 120, 220, step=50),
                "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.05),
                "num_leaves": trial.suggest_int("num_leaves", 15, 30),
                "max_depth": trial.suggest_int("max_depth", 4, 7),
                "min_child_samples": trial.suggest_int("min_child_samples", 30, 80),
                "scale_pos_weight": trial.suggest_float("scale_pos_weight", 15.0, 50.0),
                "reg_alpha": trial.suggest_float("reg_alpha", 0.05, 1.5, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 0.2, 5.0, log=True),
                "random_state": self.random_state,
                "n_jobs": -1,
                "verbose": -1,
            }
            m = lgb.LGBMClassifier(**params).fit(X_tr, y_tr)
            pv = m.predict_proba(X_val)[:, 1]
            return self._compute_pr_auc(y_val, pv)

        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=self.random_state),
        )
        study.optimize(objective, n_trials=n_trials)
        best_params = study.best_params
        best_params.update({"random_state": self.random_state, "n_jobs": -1, "verbose": -1})

        best_model = lgb.LGBMClassifier(**best_params).fit(X_tr, y_tr)
        p_val = best_model.predict_proba(X_val)[:, 1]
        p_test = best_model.predict_proba(X_te)[:, 1]

        # Budget evaluation
        budget_eval = ThresholdOptimizer.evaluate_alert_budgets(y_val, p_val, y_te, p_test)

        # Probability calibration
        calibrator = CalibrationEvaluator(method="isotonic")
        calib_eval = calibrator.evaluate(
            y_val=y_val,
            p_val_raw=p_val,
            y_test=y_te,
            p_test_raw=p_test,
            task_name="Task C2 Operational Landmark",
        )

        return {
            "task_name": "Task C2: Landmark Cancellation",
            "model_type": "LightGBM Classifier (Optuna Tuned + Isotonic Calibrated)",
            "best_hyperparameters": study.best_params,
            "best_val_pr_auc": round(study.best_value, 4),
            "test_pr_auc": round(self._compute_pr_auc(y_te, p_test), 4),
            "budget_evaluation": budget_eval,
            "calibration_evaluation": calib_eval,
            "model_artifact": best_model,
            "calibrator_artifact": calibrator.calibrator,
        }
