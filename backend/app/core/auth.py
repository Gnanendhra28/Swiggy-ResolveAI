import base64
import hmac
import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.core.logging import logger

# HTTP Bearer scheme
bearer_scheme = HTTPBearer(auto_error=False)


class TokenData(BaseModel):
    sub: str
    role: str
    exp: int
    iss: Optional[str] = None
    aud: Optional[str] = None


def _b64url_encode(data: bytes) -> str:
    """Base64URL encode without padding as per RFC 7515."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    """Base64URL decode with restored padding."""
    padding = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + padding).encode("utf-8"))


def create_access_token(
    identity: str,
    role: str,
    expires_in_seconds: Optional[int] = None,
    secret_key: Optional[str] = None,
    issuer: Optional[str] = None,
    audience: Optional[str] = None,
) -> str:
    """
    Creates a signed HMAC-SHA256 Bearer Token (RFC 7519 JWT compatible format).
    """
    secret = (secret_key or settings.AUTH_SECRET_KEY).encode("utf-8")
    now = int(time.time())
    ttl = expires_in_seconds or (settings.AUTH_TOKEN_EXPIRE_MINUTES * 60)
    exp = now + ttl

    header = {"alg": settings.AUTH_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": identity,
        "role": role,
        "iat": now,
        "exp": exp,
        "iss": issuer or settings.AUTH_ISSUER,
        "aud": audience or settings.AUTH_AUDIENCE,
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_access_token(
    token: str,
    secret_key: Optional[str] = None,
    verify_issuer: bool = True,
    verify_audience: bool = True,
) -> TokenData:
    """
    Cryptographically verifies an HMAC-SHA256 signed bearer token.
    Enforces signature validity, expiration, issuer, and audience claims.
    """
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: empty or malformed token",
        )

    parts = token.strip().split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: invalid token format (must contain 3 segments)",
        )

    header_b64, payload_b64, sig_b64 = parts
    secret = (secret_key or settings.AUTH_SECRET_KEY).encode("utf-8")
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    expected_sig = _b64url_encode(hmac.new(secret, signing_input, hashlib.sha256).digest())
    if not hmac.compare_digest(sig_b64, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: cryptographic signature mismatch or token tampering detected",
        )

    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: malformed token payload ({exc})",
        )

    # Validate Expiration
    now = int(time.time())
    exp = payload.get("exp")
    if exp is None or now > exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: token has expired",
        )

    # Validate Issuer
    if verify_issuer and settings.AUTH_ISSUER:
        if payload.get("iss") != settings.AUTH_ISSUER:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: token issuer mismatch (expected: {settings.AUTH_ISSUER})",
            )

    # Validate Audience
    if verify_audience and settings.AUTH_AUDIENCE:
        if payload.get("aud") != settings.AUTH_AUDIENCE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: token audience mismatch (expected: {settings.AUTH_AUDIENCE})",
            )

    sub = payload.get("sub")
    role = payload.get("role")
    if not sub or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: token missing required 'sub' or 'role' claim",
        )

    return TokenData(
        sub=str(sub),
        role=str(role),
        exp=int(exp),
        iss=payload.get("iss"),
        aud=payload.get("aud"),
    )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> TokenData:
    """
    FastAPI security dependency resolving authenticated operator identity and role.
    If credentials provided, validates token cryptographically.
    If credentials omitted in development/testing, falls back to unprivileged guest identity
    so that elevated privileges (OPS_LEAD, ADMIN) can NEVER be obtained without a signed token.
    In staging/production, unauthenticated requests are strictly rejected with 401.
    """
    if credentials and credentials.credentials:
        return verify_access_token(credentials.credentials)

    # In production or staging, token is strictly required
    if settings.ENVIRONMENT in ("staging", "production"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials missing: Bearer token required in Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In development or testing, unauthenticated callers receive unprivileged GUEST identity
    # (Cannot approve sensitive actions or execute elevated recovery operations without explicit token)
    return TokenData(
        sub="dev_unauthenticated_operator",
        role="OPERATOR",
        exp=int(time.time()) + 3600,
        iss=settings.AUTH_ISSUER,
        aud=settings.AUTH_AUDIENCE,
    )


def require_roles(allowed_roles: List[str]):
    """
    FastAPI authorization factory enforcing verified operator role membership.
    Rejects unauthorized roles with HTTP 403 Forbidden.
    """
    normalized_allowed = {r.upper().strip() for r in allowed_roles}

    def role_dependency(user: TokenData = Depends(get_current_user)) -> TokenData:
        user_role_norm = user.role.upper().strip()
        if user_role_norm not in normalized_allowed:
            logger.warning(
                f"RBAC authorization denied for operator '{user.sub}' with role '{user.role}'. "
                f"Required one of: {sorted(list(normalized_allowed))}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Authorization denied: role '{user.role}' lacks required privileges. Permitted roles: {sorted(list(normalized_allowed))}",
            )
        return user

    return role_dependency
