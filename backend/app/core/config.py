import os
from typing import List, Union, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Production-ready application settings validated by Pydantic.
    Supports development, testing, staging, and production environments.
    """
    PROJECT_NAME: str = "Swiggy ResolveAI"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./resolveai.db"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800  # Recycle connections every 30 minutes

    # Execution Mode (SIMULATION, SHADOW, LIVE)
    EXECUTION_MODE: str = "SIMULATION"

    # Authentication & Security
    AUTH_SECRET_KEY: str = os.getenv(
        "AUTH_SECRET_KEY",
        "resolveai-insecure-dev-secret-key-change-in-production-12345678"
    )
    AUTH_ALGORITHM: str = "HS256"
    AUTH_ISSUER: str = "swiggy-resolveai"
    AUTH_AUDIENCE: str = "resolveai-ops"
    AUTH_TOKEN_EXPIRE_MINUTES: int = 120

    # Request & Timeout Controls
    REQUEST_TIMEOUT_SECONDS: float = 30.0

    # CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # AI & Gemini API Integration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: str = "gemini-1.5-flash"
    GEMINI_TIMEOUT_SECONDS: float = 10.0

    # ML Artifacts Configuration
    ML_ARTIFACTS_DIR: str = "data/artifacts/models/phase_2_5"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid_envs = {"development", "testing", "staging", "production"}
        norm = v.lower().strip()
        if norm not in valid_envs:
            raise ValueError(f"Invalid ENVIRONMENT '{v}'. Must be one of {valid_envs}")
        return norm

    @field_validator("EXECUTION_MODE")
    @classmethod
    def validate_execution_mode(cls, v: str) -> str:
        valid_modes = {"SIMULATION", "SHADOW", "LIVE"}
        norm = v.upper().strip()
        if norm not in valid_modes:
            raise ValueError(f"Invalid EXECUTION_MODE '{v}'. Must be one of {valid_modes}")
        if norm == "LIVE":
            raise ValueError("LIVE execution mode is strictly disabled by safety governance policy.")
        return norm

    @model_validator(mode="after")
    def validate_cross_field_governance(self) -> "Settings":
        if self.ENVIRONMENT == "production" and self.EXECUTION_MODE == "SIMULATION":
            raise ValueError(
                "SIMULATION execution mode is strictly prohibited in production environment."
            )
        if self.ENVIRONMENT in ("staging", "production"):
            default_dev_key = "resolveai-insecure-dev-secret-key-change-in-production-12345678"
            if self.AUTH_SECRET_KEY == default_dev_key or len(self.AUTH_SECRET_KEY) < 32:
                raise ValueError(
                    f"Production/staging requires a strong, non-default AUTH_SECRET_KEY with minimum 32 characters (got length {len(self.AUTH_SECRET_KEY)})."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
