import os
import json
import pandas as pd
from typing import Dict, Any
from backend.app.ml.schemas.metadata import DatasetMetadata


class DatasetExporter:
    """
    Exports processed datasets to Parquet and metadata to JSON.
    Never overwrites or modifies raw source datasets.
    """

    def __init__(self, base_output_dir: str = "data/processed"):
        self.base_output_dir = base_output_dir

    def export_task_dataset(
        self,
        task_name: str,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
        metadata: DatasetMetadata,
    ) -> Dict[str, str]:
        task_dir = os.path.join(self.base_output_dir, task_name)
        os.makedirs(task_dir, exist_ok=True)

        train_path = os.path.join(task_dir, "train.parquet")
        val_path = os.path.join(task_dir, "val.parquet")
        test_path = os.path.join(task_dir, "test.parquet")
        metadata_path = os.path.join(task_dir, "metadata.json")

        # Export to Parquet using pyarrow
        train_df.to_parquet(train_path, index=False, engine="pyarrow")
        val_df.to_parquet(val_path, index=False, engine="pyarrow")
        test_df.to_parquet(test_path, index=False, engine="pyarrow")

        # Export metadata to JSON
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        # Verification: Read back 1 row from each partition to ensure file validity
        t_verify = pd.read_parquet(train_path, engine="pyarrow")
        v_verify = pd.read_parquet(val_path, engine="pyarrow")
        te_verify = pd.read_parquet(test_path, engine="pyarrow")

        assert len(t_verify) == len(train_df), "Train partition size mismatch on re-import!"
        assert len(v_verify) == len(val_df), "Validation partition size mismatch on re-import!"
        assert len(te_verify) == len(test_df), "Test partition size mismatch on re-import!"

        return {
            "task_dir": task_dir,
            "train_path": train_path,
            "val_path": val_path,
            "test_path": test_path,
            "metadata_path": metadata_path,
        }
