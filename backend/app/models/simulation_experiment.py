import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import String, Integer, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base


class SimulationExperiment(Base):
    __tablename__ = "simulation_experiments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    scenario_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    random_seed: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    num_orders: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    config_parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    strategies_evaluated: Mapped[List[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    kpi_results: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    counterfactual_comparisons: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    action_effectiveness: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<SimulationExperiment {self.id} '{self.name}' ({self.scenario_type}, N={self.num_orders})>"
