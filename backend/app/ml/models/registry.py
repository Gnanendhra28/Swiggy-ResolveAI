import os
import json
import joblib
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone


class ModelRegistry:
    """
    Manages persistence, serialization, and retrieval of trained model artifacts
    and their associated schemas, thresholds, and performance metadata.
    """

    def __init__(self, base_artifacts_dir: str = "data/artifacts/models"):
        self.base_artifacts_dir = base_artifacts_dir

    def save_model(
        self,
        task_name: str,
        model_name: str,
        model_artifact: Any,
        metadata: Dict[str, Any],
    ) -> Dict[str, str]:
        """Persists trained model artifact and metadata to disk."""
        task_dir = os.path.join(self.base_artifacts_dir, task_name)
        os.makedirs(task_dir, exist_ok=True)

        artifact_path = os.path.join(task_dir, f"{model_name}.joblib")
        metadata_path = os.path.join(task_dir, f"{model_name}_metadata.json")

        # Save model using joblib
        joblib.dump(model_artifact, artifact_path)

        # Enrich metadata
        enriched_meta = metadata.copy()
        enriched_meta["artifact_path"] = artifact_path
        enriched_meta["saved_at"] = datetime.now(timezone.utc).isoformat()

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(enriched_meta, f, indent=2)

        return {
            "artifact_path": artifact_path,
            "metadata_path": metadata_path,
        }

    def load_model(
        self, task_name: str, model_name: str
    ) -> Tuple[Any, Dict[str, Any]]:
        """Loads model artifact and its metadata schema from disk."""
        task_dir = os.path.join(self.base_artifacts_dir, task_name)
        artifact_path = os.path.join(task_dir, f"{model_name}.joblib")
        metadata_path = os.path.join(task_dir, f"{model_name}_metadata.json")

        if not os.path.exists(artifact_path):
            raise FileNotFoundError(f"Model artifact not found: {artifact_path}")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Model metadata not found: {metadata_path}")

        model = joblib.load(artifact_path)
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        return model, metadata
