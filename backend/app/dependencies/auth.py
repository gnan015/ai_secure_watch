from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import settings


bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """Authenticated Supabase user details from a verified access token."""

    id: str
    email: str | None = None
    role: str | None = None
    aud: str | list[str] | None = None


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode_supabase_token(token: str) -> dict[str, Any]:
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase JWT secret is not configured",
        )

    try:
        # The frontend receives a Supabase access_token after login. Future V2
        # protected APIs will pass that token as Authorization: Bearer <token>,
        # and this backend dependency verifies it with SUPABASE_JWT_SECRET.
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_exp": True, "verify_aud": False},
        )
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Supabase access token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise _unauthorized("Invalid Supabase access token") from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Verify a Supabase Bearer token and return current user info."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Missing Authorization Bearer token")

    claims = _decode_supabase_token(credentials.credentials)
    user_id = claims.get("sub")

    if not user_id:
        raise _unauthorized("Supabase access token is missing subject")

    return CurrentUser(
        id=user_id,
        email=claims.get("email"),
        role=claims.get("role"),
        aud=claims.get("aud"),
    )
