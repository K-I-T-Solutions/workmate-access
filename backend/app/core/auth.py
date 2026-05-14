from dataclasses import dataclass, field
from typing import Optional
import time

import httpx
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import settings

_jwks_cache: dict = {}
_jwks_fetched_at: float = 0.0
_JWKS_TTL = 3600  # 1 Stunde

_bearer = HTTPBearer()


@dataclass
class TokenData:
    sub: str
    username: str
    roles: list[str] = field(default_factory=list)
    email: Optional[str] = None


def _fetch_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    now = time.monotonic()
    if _jwks_cache and (now - _jwks_fetched_at) < _JWKS_TTL:
        return _jwks_cache
    url = f"{settings.keycloak_base_url}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    _jwks_cache = resp.json()
    _jwks_fetched_at = now
    return _jwks_cache


def _decode_token(token: str) -> dict:
    issuer = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
    options = {"verify_aud": bool(settings.KEYCLOAK_CLIENT_ID)}
    decode_kwargs = dict(
        algorithms=["RS256"],
        issuer=issuer,
        options=options,
    )
    if settings.KEYCLOAK_CLIENT_ID:
        decode_kwargs["audience"] = settings.KEYCLOAK_CLIENT_ID

    jwks = _fetch_jwks()
    try:
        return jwt.decode(token, jwks, **decode_kwargs)
    except JWTError:
        # Einmal JWKS-Cache leeren und erneut versuchen (Key-Rotation)
        _jwks_cache.clear()
        jwks = _fetch_jwks()
        return jwt.decode(token, jwks, **decode_kwargs)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> TokenData:
    try:
        payload = _decode_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token ungültig: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Keycloak nicht erreichbar: {exc}",
        )

    roles: list[str] = payload.get("realm_access", {}).get("roles", [])
    return TokenData(
        sub=payload["sub"],
        username=payload.get("preferred_username", ""),
        email=payload.get("email"),
        roles=roles,
    )


def require_admin(user: TokenData = Depends(get_current_user)) -> TokenData:
    if "admin" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin-Berechtigung erforderlich",
        )
    return user
