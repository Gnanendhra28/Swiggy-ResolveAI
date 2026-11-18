from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.auth import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication & Security"])


class DevTokenRequest(BaseModel):
    operator_profile: str = Field(
        default="ops_lead",
        description="Predefined demonstration profile: 'ops_lead', 'admin', 'operator', 'intern'",
    )


class DevTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    operator_identity: str
    operator_role: str
    expires_in_seconds: int
    environment: str
    warning: str


PREDEFINED_DEV_PROFILES = {
    "ops_lead": {"identity": "dev_ops_lead_console", "role": "OPS_LEAD"},
    "admin": {"identity": "dev_admin_console", "role": "ADMIN"},
    "operator": {"identity": "dev_field_operator", "role": "OPERATOR"},
    "supervisor": {"identity": "dev_ops_supervisor", "role": "SUPERVISOR"},
    "intern": {"identity": "dev_unauthorized_intern", "role": "INTERN"},
}


@router.post(
    "/dev-token",
    response_model=DevTokenResponse,
    summary="Issue Demonstration Token (Development Environment Only)",
)
def issue_dev_token(payload: DevTokenRequest = DevTokenRequest()) -> DevTokenResponse:
    """
    Issues a cryptographically signed HMAC-SHA256 Bearer Token for local demonstration.
    STRICT SECURITY CONTROLS:
    - Strictly disabled in 'staging' and 'production' (returns HTTP 403 Forbidden).
    - Accepts ONLY predefined operator profiles to prevent arbitrary role claims.
    - Explicitly marked as non-production in token metadata.
    """
    if settings.ENVIRONMENT != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Development token generator is strictly disabled in '{settings.ENVIRONMENT}' environment.",
        )

    profile_key = payload.operator_profile.lower().strip()
    if profile_key not in PREDEFINED_DEV_PROFILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown profile '{payload.operator_profile}'. Allowed predefined profiles: {list(PREDEFINED_DEV_PROFILES.keys())}",
        )

    prof = PREDEFINED_DEV_PROFILES[profile_key]
    token = create_access_token(
        identity=prof["identity"],
        role=prof["role"],
        expires_in_seconds=settings.AUTH_TOKEN_EXPIRE_MINUTES * 60,
    )

    return DevTokenResponse(
        access_token=token,
        token_type="bearer",
        operator_identity=prof["identity"],
        operator_role=prof["role"],
        expires_in_seconds=settings.AUTH_TOKEN_EXPIRE_MINUTES * 60,
        environment=settings.ENVIRONMENT,
        warning="DEVELOPMENT ONLY: This token generator is strictly disabled in staging and production.",
    )
