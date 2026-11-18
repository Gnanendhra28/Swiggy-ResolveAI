from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number starting from 1")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    total_pages: int


class ApplicationHealth(BaseModel):
    name: str
    status: str
    version: str
    environment: str


class InfrastructureHealth(BaseModel):
    database_status: str
    database_engine: str
    database_latency_ms: float
    connection_pooling: Dict[str, Any]


class AIProviderHealth(BaseModel):
    provider_name: str
    status: str  # "live", "fallback_ready", "degraded"
    model_name: str
    fallback_engine_available: bool
    details: str


class MLArtifactHealth(BaseModel):
    status: str  # "ready", "degraded", "missing"
    model_version: str
    task_a_quantiles: bool
    task_c2_calibrated: bool
    registry_loaded: bool
    artifacts_dir: str


class HealthResponse(BaseModel):
    status: str  # "healthy", "degraded", "unhealthy"
    database: str  # Preserved for backward compatibility
    version: str
    environment: str = "development"
    timestamp: str
    application: Optional[ApplicationHealth] = None
    infrastructure: Optional[InfrastructureHealth] = None
    ai_provider: Optional[AIProviderHealth] = None
    ml_artifacts: Optional[MLArtifactHealth] = None


class LivenessResponse(BaseModel):
    status: str = "alive"
    timestamp: str


class ReadinessResponse(BaseModel):
    status: str = "ready"
    timestamp: str
    database: str
    ml_artifacts: str
