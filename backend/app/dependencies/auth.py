from typing import Any

import jwt
from jwt import PyJWKClient
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
    try:
        token_header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise _unauthorized("Invalid Supabase access token") from exc

    algorithm = token_header.get("alg")

    try:
        if algorithm == "HS256":
            if not settings.supabase_jwt_secret:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Supabase JWT secret is not configured",
                )

            # Legacy path: verify HS256 access tokens with project JWT secret.
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                options={"verify_exp": True, "verify_aud": False},
            )

        if algorithm in {"ES256", "RS256"}:
            if not settings.supabase_url:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Supabase URL is not configured",
                )

            supabase_base_url = settings.supabase_url.rstrip("/")
            expected_issuer = f"{supabase_base_url}/auth/v1"
            jwks_url = f"{expected_issuer}/.well-known/jwks.json"

            jwk_client = PyJWKClient(jwks_url)
            signing_key = jwk_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=[algorithm],
                options={"verify_exp": True, "verify_aud": False, "verify_iss": False},
            )

            token_issuer = claims.get("iss")
            if token_issuer and token_issuer != expected_issuer:
                raise _unauthorized("Invalid Supabase token issuer")

            # Supabase access tokens typically use aud='authenticated'. Enforce
            # this when audience data is present.
            token_aud = claims.get("aud")
            if token_aud is not None:
                if isinstance(token_aud, str) and token_aud != "authenticated":
                    raise _unauthorized("Invalid Supabase token audience")
                if isinstance(token_aud, list) and "authenticated" not in token_aud:
                    raise _unauthorized("Invalid Supabase token audience")

            return claims

        raise _unauthorized("Unsupported Supabase token algorithm")
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Supabase access token has expired") from exc
    except HTTPException:
        raise
    except jwt.InvalidTokenError as exc:
        raise _unauthorized("Invalid Supabase access token") from exc
    except Exception as exc:
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
