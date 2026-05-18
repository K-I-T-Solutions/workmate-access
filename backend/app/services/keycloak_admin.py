import time
import httpx
from typing import Optional
from ..core.config import settings

_admin_token: str = ""
_admin_token_exp: float = 0.0


def _get_admin_token() -> str:
    global _admin_token, _admin_token_exp
    if _admin_token and time.monotonic() < _admin_token_exp - 30:
        return _admin_token
    url = f"{settings.keycloak_base_url}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token"
    resp = httpx.post(url, data={
        "grant_type": "client_credentials",
        "client_id": settings.KEYCLOAK_ADMIN_CLIENT_ID,
        "client_secret": settings.KEYCLOAK_ADMIN_CLIENT_SECRET,
    }, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    _admin_token = data["access_token"]
    _admin_token_exp = time.monotonic() + data.get("expires_in", 60)
    return _admin_token


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_admin_token()}"}


def _admin_url(path: str) -> str:
    base = settings.keycloak_base_url
    realm = settings.KEYCLOAK_REALM
    return f"{base}/admin/realms/{realm}{path}"


# ── Users ──────────────────────────────────────────────────────────────────

def list_kc_users(search: str = "", limit: int = 100) -> list[dict]:
    params = {"max": limit}
    if search:
        params["search"] = search
    resp = httpx.get(_admin_url("/users"), headers=_headers(), params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_kc_user(kc_id: str) -> dict:
    resp = httpx.get(_admin_url(f"/users/{kc_id}"), headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def create_kc_user(username: str, email: str, first_name: str, last_name: str,
                   password: str, temporary_password: bool = True) -> str:
    payload = {
        "username": username,
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "enabled": True,
        "credentials": [{
            "type": "password",
            "value": password,
            "temporary": temporary_password,
        }],
    }
    resp = httpx.post(_admin_url("/users"), headers=_headers(), json=payload, timeout=10)
    resp.raise_for_status()
    location = resp.headers.get("Location", "")
    return location.rstrip("/").split("/")[-1]


def update_kc_user(kc_id: str, **kwargs) -> None:
    resp = httpx.put(_admin_url(f"/users/{kc_id}"), headers=_headers(), json=kwargs, timeout=10)
    resp.raise_for_status()


def set_kc_password(kc_id: str, password: str, temporary: bool = False) -> None:
    resp = httpx.put(
        _admin_url(f"/users/{kc_id}/reset-password"),
        headers=_headers(),
        json={"type": "password", "value": password, "temporary": temporary},
        timeout=10,
    )
    resp.raise_for_status()


def disable_kc_user(kc_id: str) -> None:
    resp = httpx.put(_admin_url(f"/users/{kc_id}"), headers=_headers(),
                     json={"enabled": False}, timeout=10)
    resp.raise_for_status()


def enable_kc_user(kc_id: str) -> None:
    resp = httpx.put(_admin_url(f"/users/{kc_id}"), headers=_headers(),
                     json={"enabled": True}, timeout=10)
    resp.raise_for_status()


def delete_kc_user(kc_id: str) -> None:
    resp = httpx.delete(_admin_url(f"/users/{kc_id}"), headers=_headers(), timeout=10)
    resp.raise_for_status()


# ── Sessions ────────────────────────────────────────────────────────────────

def get_user_sessions(kc_id: str) -> list[dict]:
    resp = httpx.get(_admin_url(f"/users/{kc_id}/sessions"), headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def logout_user_sessions(kc_id: str) -> None:
    resp = httpx.delete(_admin_url(f"/users/{kc_id}/sessions"), headers=_headers(), timeout=10)
    resp.raise_for_status()


def get_realm_sessions(limit: int = 100) -> list[dict]:
    resp = httpx.get(_admin_url("/sessions/stats"), headers=_headers(), timeout=10)
    # Fallback: list clients and their sessions — use active-sessions per realm
    if not resp.is_success:
        return []
    return resp.json() if isinstance(resp.json(), list) else []


# ── Roles ────────────────────────────────────────────────────────────────────

def get_user_realm_roles(kc_id: str) -> list[dict]:
    resp = httpx.get(_admin_url(f"/users/{kc_id}/role-mappings/realm"), headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def list_realm_roles() -> list[dict]:
    resp = httpx.get(_admin_url("/roles"), headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def assign_realm_role(kc_id: str, role_name: str) -> None:
    roles = list_realm_roles()
    role = next((r for r in roles if r["name"] == role_name), None)
    if not role:
        raise ValueError(f"Role '{role_name}' not found")
    resp = httpx.post(
        _admin_url(f"/users/{kc_id}/role-mappings/realm"),
        headers=_headers(), json=[role], timeout=10,
    )
    resp.raise_for_status()


def remove_realm_role(kc_id: str, role_name: str) -> None:
    roles = list_realm_roles()
    role = next((r for r in roles if r["name"] == role_name), None)
    if not role:
        return
    resp = httpx.request(
        "DELETE", _admin_url(f"/users/{kc_id}/role-mappings/realm"),
        headers=_headers(), json=[role], timeout=10,
    )
    resp.raise_for_status()
