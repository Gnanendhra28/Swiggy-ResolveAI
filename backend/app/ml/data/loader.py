import os
import pandas as pd
from typing import Optional
from backend.app.ml.schemas.config import PipelineConfig


class RawDataLoader:
    """
    Safely loads raw CSV order telemetry.
    Ensures that raw data files are treated as read-only and never modified.
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()

    def load_raw_orders(self, path: Optional[str] = None) -> pd.DataFrame:
        file_path = path or self.config.raw_orders_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Raw orders dataset not found at: {file_path}")

        # Load CSV into pandas DataFrame
        df = pd.read_csv(file_path)
        return df.copy()
