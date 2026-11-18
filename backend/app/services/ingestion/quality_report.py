import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class DataQualityReport(BaseModel):
    dataset_name: str
    source_file_or_id: str
    provenance: str = "PUBLIC_HISTORICAL"
    total_rows_read: int = 0
    valid_rows: int = 0
    duplicate_rows: int = 0
    inserted_count: int = 0
    skipped_count: int = 0
    missing_values_per_column: Dict[str, int] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def record_null(self, column: str) -> None:
        self.missing_values_per_column[column] = (
            self.missing_values_per_column.get(column, 0) + 1
        )

    def record_error(self, message: str) -> None:
        if len(self.errors) < 50:  # Keep top 50 sample errors to avoid ballooning
            self.errors.append(message)

    def summary(self) -> Dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "source": self.source_file_or_id,
            "provenance": self.provenance,
            "total_rows_read": self.total_rows_read,
            "valid_rows": self.valid_rows,
            "inserted_count": self.inserted_count,
            "duplicate_or_skipped": self.skipped_count,
            "missing_values": self.missing_values_per_column,
            "duration_seconds": round(self.duration_seconds, 2),
            "ingested_at": self.ingested_at.isoformat(),
            "error_sample_count": len(self.errors),
        }
