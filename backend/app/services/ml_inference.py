import os
import json
import math
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from backend.app.core.logging import logger
from backend.app.ml.models.config import get_task_a_config, get_task_c2_config


class TaskAPrediction(BaseModel):
    eta_p10_min: float
    eta_p50_min: float
    eta_p90_min: float
    uncertainty_interval_min: Tuple[float, float]
    interval_width_min: float
    is_long_tail: bool
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    disclaimer: str
    crossing_corrected: bool = False
    model_version: str = "2.5.0"
    governance_status: str = "APPROVED_FOR_SIMULATION"


class TaskC2Prediction(BaseModel):
    is_eligible: bool
    eligibility_reason: str
    landmark_evaluated_at: Optional[str] = None
    allot_to_landmark_min: Optional[float] = None
    raw_probability: Optional[float] = None
    calibrated_probability: Optional[float] = None
    alert_budget_5_per_1000: bool = False
    alert_budget_10_per_1000: bool = False
    governance_status: str = "APPROVED_FOR_CONTROLLED_TRIAGE"
    is_operational_trigger: bool = True
    target_semantics: str = (
        "Eventual post-landmark cancellation within observed lifecycle (NOT imminent cancellation)"
    )
    operational_action: str = "NON_INTRUSIVE_MONITORING_ONLY"
    model_version: str = "2.5.0"


class ResearchModelPrediction(BaseModel):
    task_name: str
    score: float
    governance_status: str
    is_operational_trigger: bool = False
    notes: str


class MLInferenceResult(BaseModel):
    order_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    task_a_eta: TaskAPrediction
    task_c2_cancellation: TaskC2Prediction
    research_models: Optional[Dict[str, ResearchModelPrediction]] = None
    feature_provenance: Dict[str, Any]
    model_registry_version: str = "2.5.0"
    feature_schema_version: str = "1.0.0"
    inference_latency_ms: float = 0.0


class MLInferenceService:
    """
    Hardened Production ML Inference Service for Swiggy ResolveAI.
    Loads approved Phase 2.5 artifacts:
      - Task A ETA Quantiles (P10, P50, P90)
      - Task C2 Operational Landmark Cancellation (LightGBM + Isotonic Calibrator)
    Provides graceful fallback for missing artifacts, missing features, and invalid inputs.
    Isolates Tasks B & C1 as research-only.
    """

    _instance: Optional["MLInferenceService"] = None

    DEFAULT_ORDER_FEATURES: Dict[str, Any] = {
        "last_mile_distance": 2.67,
        "is_zero_last_mile": 0,
        "last_mile_distance_sq": 7.1289,
        "distance_bracket": "short",
        "order_hour": 19,
        "hour_sin": -0.965,
        "hour_cos": 0.258,
        "order_dayofweek": 4,
        "dow_sin": -0.433,
        "dow_cos": -0.900,
        "is_weekend": 0,
        "meal_period": "dinner",
        "is_peak_meal_window": 1,
        "rolling_order_volume_15m": 25.0,
        "rolling_order_volume_60m": 95.0,
        "demand_acceleration": 1.05,
    }

    DEFAULT_LANDMARK_FEATURES: Dict[str, Any] = {
        **DEFAULT_ORDER_FEATURES,
        "first_mile_distance": 1.85,
        "is_extreme_first_mile": 0,
        "first_to_last_mile_ratio": 0.69,
        "total_route_distance": 4.52,
        "courier_session_time_min": 145.0,
        "courier_fatigue_flag": 0,
        "is_delayed_allotment": 0,
        "allot_delay_min": 1.5,
        "has_accepted_by_landmark": 1,
        "accept_delay_at_landmark": 1.2,
    }

    def __init__(self, artifacts_dir: str = "data/artifacts/models/phase_2_5"):
        self.artifacts_dir = artifacts_dir
        self.task_a_cfg = get_task_a_config()
        self.task_c2_cfg = get_task_c2_config()
        self._load_artifacts()

    @classmethod
    def get_instance(cls, artifacts_dir: str = "data/artifacts/models/phase_2_5") -> "MLInferenceService":
        if cls._instance is None:
            cls._instance = MLInferenceService(artifacts_dir=artifacts_dir)
        return cls._instance

    def _load_artifacts(self) -> None:
        """Loads and verifies models, calibrator, and registry metadata with graceful fallback."""
        logger.info(f"Loading Phase 2.5 ML artifacts from {self.artifacts_dir}")
        try:
            self.model_task_a_p10 = self._safe_load("task_a_quantile_p10.joblib")
            self.model_task_a_p50 = self._safe_load("task_a_quantile_p50.joblib")
            self.model_task_a_p90 = self._safe_load("task_a_quantile_p90.joblib")

            self.model_task_c2 = self._safe_load("task_c2_improved_model.joblib")
            self.calibrator_task_c2 = self._safe_load("task_c2_calibrator.joblib")

            # Research models
            self.model_task_b = self._safe_load("task_b_improved_model.joblib")
            self.model_task_c1 = self._safe_load("task_c1_improved_model.joblib")

            reg_path = os.path.join(self.artifacts_dir, "registry.json")
            if os.path.exists(reg_path):
                with open(reg_path, "r", encoding="utf-8") as f:
                    self.registry = json.load(f)
            else:
                self.registry = {}
            logger.info("Phase 2.5 ML artifacts loaded successfully.")
        except Exception as exc:
            logger.error(f"Error loading Phase 2.5 ML artifacts: {exc}")
            raise

    def _safe_load(self, filename: str) -> Optional[Any]:
        path = os.path.join(self.artifacts_dir, filename)
        if os.path.exists(path):
            try:
                return joblib.load(path)
            except Exception as exc:
                logger.warning(f"Could not load artifact {path}: {exc}")
                return None
        return None

    # -------------------------------------------------------------------------
    # Feature Extraction Helpers
    # -------------------------------------------------------------------------
    @staticmethod
    def _compute_distance_bracket(distance: float) -> str:
        if distance < 1.0:
            return "very_short"
        elif distance < 3.0:
            return "short"
        elif distance < 6.0:
            return "medium"
        elif distance < 10.0:
            return "long"
        return "very_long"

    @staticmethod
    def _compute_meal_period(hour: int) -> str:
        if 0 <= hour < 6:
            return "late_night"
        elif 6 <= hour < 11:
            return "breakfast"
        elif 11 <= hour < 16:
            return "lunch"
        elif 16 <= hour < 19:
            return "afternoon"
        return "dinner"

    def extract_order_features(
        self,
        order: Any,
        events: List[Any],
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Extracts the 16 order-time features from order state and events.
        Applies strict training partition fitted values on missing features.
        """
        order_time = getattr(order, "created_at", None)
        if order_time is None:
            order_time = datetime.now(timezone.utc)
        elif isinstance(order_time, str):
            try:
                order_time = datetime.fromisoformat(order_time)
            except Exception:
                order_time = datetime.now(timezone.utc)
        if order_time.tzinfo is None:
            order_time = order_time.replace(tzinfo=timezone.utc)

        # Distance computation
        last_mile = 2.67  # Fitted training median from Phase 2.2.1
        for ev in events:
            meta = getattr(ev, "event_metadata", {}) or {}
            if "last_mile_distance" in meta and meta["last_mile_distance"] is not None:
                last_mile = float(meta["last_mile_distance"])
                break
            elif "distance_km" in meta and meta["distance_km"] is not None:
                last_mile = float(meta["distance_km"])
                break

        is_zero_last_mile = 1 if last_mile == 0.0 else 0
        if is_zero_last_mile:
            last_mile = 2.67  # Imputed median strictly from training partition

        last_mile_sq = float(last_mile ** 2)
        dist_bracket = self._compute_distance_bracket(last_mile)

        hour = order_time.hour
        hour_sin = math.sin(2 * math.pi * hour / 24.0)
        hour_cos = math.cos(2 * math.pi * hour / 24.0)

        dow = order_time.weekday()
        dow_sin = math.sin(2 * math.pi * dow / 7.0)
        dow_cos = math.cos(2 * math.pi * dow / 7.0)
        is_weekend = 1 if dow in (5, 6) else 0

        meal_period = self._compute_meal_period(hour)
        is_peak = 1 if meal_period in ("lunch", "dinner") else 0

        vol_15m = 25.0
        vol_60m = 95.0
        demand_accel = vol_15m / max(vol_60m / 4.0, 1.0)

        return {
            "last_mile_distance": float(last_mile),
            "is_zero_last_mile": int(is_zero_last_mile),
            "last_mile_distance_sq": float(last_mile_sq),
            "distance_bracket": dist_bracket,
            "order_hour": int(hour),
            "hour_sin": float(hour_sin),
            "hour_cos": float(hour_cos),
            "order_dayofweek": int(dow),
            "dow_sin": float(dow_sin),
            "dow_cos": float(dow_cos),
            "is_weekend": int(is_weekend),
            "meal_period": meal_period,
            "is_peak_meal_window": int(is_peak),
            "rolling_order_volume_15m": float(vol_15m),
            "rolling_order_volume_60m": float(vol_60m),
            "demand_acceleration": float(demand_accel),
        }

    def check_landmark_eligibility(
        self,
        order: Any,
        events: List[Any],
        now: Optional[datetime] = None,
    ) -> Tuple[bool, str, Optional[datetime], Optional[float]]:
        """
        Task C2 Landmark Eligibility Check:
        Must be at least 5 minutes post courier allotment (t >= t_allot + 5m),
        and order has not already finished (DELIVERED or CANCELLED).
        """
        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        current_status = getattr(order, "order_status", "PLACED")
        if current_status in ("DELIVERED", "CANCELLED"):
            return False, f"Order already concluded with status {current_status}", None, None

        allot_time: Optional[datetime] = None
        for ev in events:
            ev_type = getattr(ev, "event_type", "")
            if ev_type in ("RIDER_ASSIGNED", "COURIER_ALLOTTED", "RIDER_ALLOTTED"):
                ts = getattr(ev, "event_timestamp", None)
                if ts:
                    if isinstance(ts, str):
                        try:
                            ts = datetime.fromisoformat(ts)
                        except Exception:
                            continue
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    allot_time = ts
                    break

        if allot_time is None:
            return False, "Courier has not yet been allotted (allot_time missing)", None, None

        elapsed_since_allot = (now - allot_time).total_seconds() / 60.0
        if elapsed_since_allot < 5.0:
            return (
                False,
                f"Order has not reached landmark (elapsed: {elapsed_since_allot:.1f}m < 5.0m post-allotment)",
                allot_time,
                elapsed_since_allot,
            )

        return True, "Order is landmark eligible (t >= t_allot + 5m)", allot_time, elapsed_since_allot

    def extract_landmark_features(
        self,
        base_features: Dict[str, Any],
        order: Any,
        events: List[Any],
        allot_time: datetime,
        elapsed_min: float,
    ) -> Dict[str, Any]:
        """
        Constructs the 26 features required for Task C2 operational landmark model.
        """
        features = dict(base_features)

        first_mile = 1.85  # Default nominal first mile
        for ev in events:
            meta = getattr(ev, "event_metadata", {}) or {}
            if "first_mile_distance" in meta and meta["first_mile_distance"] is not None:
                first_mile = float(meta["first_mile_distance"])
                break

        is_extreme_fm = 1 if first_mile > 3.0 else 0
        ratio = first_mile / max(features["last_mile_distance"], 0.1)
        total_dist = first_mile + features["last_mile_distance"]

        # Allotment delay
        order_time = getattr(order, "created_at", allot_time)
        if isinstance(order_time, str):
            try:
                order_time = datetime.fromisoformat(order_time)
            except Exception:
                order_time = allot_time
        if order_time.tzinfo is None:
            order_time = order_time.replace(tzinfo=timezone.utc)
        if allot_time.tzinfo is None:
            allot_time = allot_time.replace(tzinfo=timezone.utc)
        allot_delay = max(0.0, (allot_time - order_time).total_seconds() / 60.0)
        is_delayed_allot = 1 if allot_delay > 3.0 else 0

        # Courier acceptance status at landmark
        accept_time: Optional[datetime] = None
        for ev in events:
            ev_type = getattr(ev, "event_type", "")
            if ev_type in ("RIDER_ACCEPTED", "COURIER_ACCEPTED"):
                ts = getattr(ev, "event_timestamp", None)
                if ts:
                    if isinstance(ts, str):
                        try:
                            ts = datetime.fromisoformat(ts)
                        except Exception:
                            continue
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    accept_time = ts
                    break

        if accept_time:
            accept_delay = max(0.0, (accept_time - allot_time).total_seconds() / 60.0)
            has_accepted = 1 if accept_delay <= 5.0 else 0
            accept_delay_landmark = min(5.0, accept_delay)
        else:
            has_accepted = 0
            accept_delay_landmark = 5.0

        features["first_mile_distance"] = float(first_mile)
        features["is_extreme_first_mile"] = int(is_extreme_fm)
        features["first_to_last_mile_ratio"] = float(ratio)
        features["total_route_distance"] = float(total_dist)
        features["courier_session_time_min"] = 145.0
        features["courier_fatigue_flag"] = 0
        features["is_delayed_allotment"] = int(is_delayed_allot)
        features["allot_delay_min"] = float(allot_delay)
        features["has_accepted_by_landmark"] = int(has_accepted)
        features["accept_delay_at_landmark"] = float(accept_delay_landmark)

        return features

    # -------------------------------------------------------------------------
    # Inference Methods
    # -------------------------------------------------------------------------
    def predict_task_a(self, features: Dict[str, Any]) -> TaskAPrediction:
        """
        Task A: Predicts ETA quantiles (P10, P50, P90).
        Enforces monotonic ordering: P10 <= P50 <= P90.
        Defensively validates schema and falls back gracefully if models are missing.
        """
        # Defensive feature schema validation
        safe_features = dict(self.DEFAULT_ORDER_FEATURES)
        safe_features.update(features or {})

        if not (self.model_task_a_p10 and self.model_task_a_p50 and self.model_task_a_p90):
            # Graceful fallback heuristic
            p50 = 28.5
            p10 = 20.0
            p90 = 42.0
            return TaskAPrediction(
                eta_p10_min=p10,
                eta_p50_min=p50,
                eta_p90_min=p90,
                uncertainty_interval_min=(p10, p90),
                interval_width_min=p90 - p10,
                is_long_tail=False,
                confidence="LOW",
                disclaimer="Fallback heuristic: model artifacts unavailable. P90 is an uncertainty interval upper bound, never a guaranteed delivery time.",
                crossing_corrected=False,
                model_version="FALLBACK_HEURISTIC",
                governance_status="APPROVED_FOR_SIMULATION",
            )

        df = pd.DataFrame([safe_features])[self.task_a_cfg.feature_columns]
        for cat_col in self.task_a_cfg.categorical_columns:
            df[cat_col] = df[cat_col].astype("category")

        pred_p10 = float(self.model_task_a_p10.predict(df)[0])
        pred_p50 = float(self.model_task_a_p50.predict(df)[0])
        pred_p90 = float(self.model_task_a_p90.predict(df)[0])

        crossing = False
        if not (pred_p10 <= pred_p50 <= pred_p90):
            crossing = True
            sorted_quantiles = sorted([pred_p10, pred_p50, pred_p90])
            pred_p10, pred_p50, pred_p90 = sorted_quantiles[0], sorted_quantiles[1], sorted_quantiles[2]

        width = pred_p90 - pred_p10
        is_long_tail = bool(pred_p50 > 40.0 or pred_p90 > 50.0)

        if is_long_tail:
            confidence = "LOW"
            disclaimer = (
                "Long-tail delivery duration (>50 min). Subject to high kitchen and traffic variability. "
                "P90 is an uncertainty quantile, not a guaranteed delivery time."
            )
        elif 20.0 <= pred_p50 <= 35.0:
            confidence = "HIGH"
            disclaimer = (
                "Core SLA regime (20-35 min). 80% coverage interval empirical reliability is ~95.8%. "
                "P90 is an uncertainty quantile, not a guaranteed delivery time."
            )
        else:
            confidence = "MEDIUM"
            disclaimer = (
                "Moderate duration regime. 80% coverage interval calibrated on historical benchmark. "
                "P90 is an uncertainty quantile, not a guaranteed delivery time."
            )

        return TaskAPrediction(
            eta_p10_min=round(pred_p10, 2),
            eta_p50_min=round(pred_p50, 2),
            eta_p90_min=round(pred_p90, 2),
            uncertainty_interval_min=(round(pred_p10, 2), round(pred_p90, 2)),
            interval_width_min=round(width, 2),
            is_long_tail=is_long_tail,
            confidence=confidence,
            disclaimer=disclaimer,
            crossing_corrected=crossing,
            model_version="2.5.0",
            governance_status="APPROVED_FOR_SIMULATION",
        )

    def predict_task_c2(
        self,
        features: Optional[Dict[str, Any]],
        is_eligible: bool,
        eligibility_reason: str,
        landmark_evaluated_at: Optional[str] = None,
        allot_to_landmark_min: Optional[float] = None,
    ) -> TaskC2Prediction:
        """
        Task C2: Predicts calibrated operational landmark cancellation risk.
        Requires landmark eligibility (t >= t_allot + 5m).
        Uses LightGBM + Isotonic Calibrator.
        Applies strict 5/1000 and 10/1000 operational budget thresholds.
        """
        if not is_eligible or features is None:
            return TaskC2Prediction(
                is_eligible=False,
                eligibility_reason=eligibility_reason,
                landmark_evaluated_at=landmark_evaluated_at,
                allot_to_landmark_min=allot_to_landmark_min,
                raw_probability=None,
                calibrated_probability=None,
                alert_budget_5_per_1000=False,
                alert_budget_10_per_1000=False,
                governance_status="APPROVED_FOR_CONTROLLED_TRIAGE",
                is_operational_trigger=True,
            )

        if not (self.model_task_c2 and self.calibrator_task_c2):
            return TaskC2Prediction(
                is_eligible=True,
                eligibility_reason="Artifact missing; fallback safe default applied.",
                landmark_evaluated_at=landmark_evaluated_at,
                allot_to_landmark_min=allot_to_landmark_min,
                raw_probability=0.01,
                calibrated_probability=0.01,
                alert_budget_5_per_1000=False,
                alert_budget_10_per_1000=False,
                governance_status="APPROVED_FOR_CONTROLLED_TRIAGE",
                is_operational_trigger=True,
            )

        safe_features = dict(self.DEFAULT_LANDMARK_FEATURES)
        safe_features.update(features or {})

        df = pd.DataFrame([safe_features])[self.task_c2_cfg.feature_columns]
        for cat_col in self.task_c2_cfg.categorical_columns:
            df[cat_col] = df[cat_col].astype("category")

        raw_prob = float(self.model_task_c2.predict_proba(df)[:, 1][0])
        calibrated_prob = float(self.calibrator_task_c2.transform([raw_prob])[0])

        threshold_5k = 0.6686
        threshold_10k = 0.5113

        alert_5k = raw_prob >= threshold_5k
        alert_10k = raw_prob >= threshold_10k

        return TaskC2Prediction(
            is_eligible=True,
            eligibility_reason=eligibility_reason,
            landmark_evaluated_at=landmark_evaluated_at,
            allot_to_landmark_min=allot_to_landmark_min,
            raw_probability=round(raw_prob, 4),
            calibrated_probability=round(calibrated_prob, 4),
            alert_budget_5_per_1000=alert_5k,
            alert_budget_10_per_1000=alert_10k,
            governance_status="APPROVED_FOR_CONTROLLED_TRIAGE",
            is_operational_trigger=True,
            target_semantics="Eventual post-landmark cancellation within observed lifecycle (NOT imminent cancellation)",
            operational_action="NON_INTRUSIVE_MONITORING_ONLY",
            model_version="2.5.0",
        )

    def predict_research_models(
        self,
        features_task_a: Dict[str, Any],
    ) -> Dict[str, ResearchModelPrediction]:
        """Provides research-only scores for Task B and Task C1."""
        safe_features = dict(self.DEFAULT_ORDER_FEATURES)
        safe_features.update(features_task_a or {})

        df_a = pd.DataFrame([safe_features])[self.task_a_cfg.feature_columns]
        for cat_col in self.task_a_cfg.categorical_columns:
            df_a[cat_col] = df_a[cat_col].astype("category")

        results: Dict[str, ResearchModelPrediction] = {}

        if self.model_task_b:
            score_b = float(self.model_task_b.predict_proba(df_a)[:, 1][0])
            results["task_b_allocation_delay"] = ResearchModelPrediction(
                task_name="task_b_allocation_delay",
                score=round(score_b, 4),
                governance_status="NOT_APPROVED",
                is_operational_trigger=False,
                notes="Not approved for operational alerting. High false positive rate.",
            )

        if self.model_task_c1:
            score_c1 = float(self.model_task_c1.predict_proba(df_a)[:, 1][0])
            results["task_c1_upfront_cancellation"] = ResearchModelPrediction(
                task_name="task_c1_upfront_cancellation",
                score=round(score_c1, 4),
                governance_status="RESEARCH_ONLY",
                is_operational_trigger=False,
                notes="Research only. Near-random separation over baseline prior (1.11%).",
            )

        return results

    def run_inference(
        self,
        order: Any,
        events: List[Any],
        now: Optional[datetime] = None,
        include_research_models: bool = True,
    ) -> MLInferenceResult:
        """
        Unified ML Inference execution for an order with timing and schema audit.
        """
        start_perf = time.perf_counter()
        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        order_id = getattr(order, "external_order_id", None) or getattr(order, "id", "UNKNOWN")

        # 1. Base order-time features
        base_features = self.extract_order_features(order, events, now=now)

        # 2. Task A ETA Prediction
        task_a_res = self.predict_task_a(base_features)

        # 3. Task C2 Landmark Eligibility and Feature Extraction
        is_eligible, reason, allot_time, elapsed_min = self.check_landmark_eligibility(order, events, now=now)
        if is_eligible and allot_time is not None and elapsed_min is not None:
            c2_features = self.extract_landmark_features(base_features, order, events, allot_time, elapsed_min)
            landmark_ts = allot_time + timedelta(minutes=5.0)
            task_c2_res = self.predict_task_c2(
                features=c2_features,
                is_eligible=True,
                eligibility_reason=reason,
                landmark_evaluated_at=landmark_ts.isoformat(),
                allot_to_landmark_min=round(elapsed_min, 1),
            )
            provenance_features = c2_features
        else:
            task_c2_res = self.predict_task_c2(
                features=None,
                is_eligible=False,
                eligibility_reason=reason,
                landmark_evaluated_at=None,
                allot_to_landmark_min=round(elapsed_min, 1) if elapsed_min is not None else None,
            )
            provenance_features = base_features

        # 4. Research models
        research_res = None
        if include_research_models:
            research_res = self.predict_research_models(base_features)

        latency_ms = round((time.perf_counter() - start_perf) * 1000.0, 2)

        return MLInferenceResult(
            order_id=str(order_id),
            timestamp=now,
            task_a_eta=task_a_res,
            task_c2_cancellation=task_c2_res,
            research_models=research_res,
            feature_provenance=provenance_features,
            model_registry_version="2.5.0",
            feature_schema_version="1.0.0",
            inference_latency_ms=latency_ms,
        )
