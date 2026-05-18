from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from pydantic import BaseModel
import httpx

from ...core.auth import TokenData, require_admin
from ...services import keycloak_admin as kc

router = APIRouter(prefix="/api/v1/admin/kc", tags=["keycloak-admin"])


def _kc_error(exc: Exception) -> HTTPException:
    if isinstance(exc, httpx.HTTPStatusError):
        detail = exc.response.text or str(exc)
        return HTTPException(status_code=exc.response.status_code, detail=detail)
    return HTTPException(status_code=503, detail=f"Keycloak nicht erreichbar: {exc}")


# ── Schemas ───────────────────────────────────────────────────────────────────

class KcUserCreate(BaseModel):
    username: str
    email: str
    first_name: str = ""
    last_name: str = ""
    password: str
    temporary_password: bool = True


class KcUserUpdate(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    enabled: Optional[bool] = None


class KcPasswordReset(BaseModel):
    password: str
    temporary: bool = False


class KcRoleAssign(BaseModel):
    role_name: str


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(search: str = Query(""), _: TokenData = Depends(require_admin)):
    try:
        return kc.list_kc_users(search=search)
    except Exception as e:
        raise _kc_error(e)


@router.get("/users/{kc_id}")
def get_user(kc_id: str, _: TokenData = Depends(require_admin)):
    try:
        return kc.get_kc_user(kc_id)
    except Exception as e:
        raise _kc_error(e)


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(body: KcUserCreate, _: TokenData = Depends(require_admin)):
    try:
        kc_id = kc.create_kc_user(
            username=body.username,
            email=body.email,
            first_name=body.first_name,
            last_name=body.last_name,
            password=body.password,
            temporary_password=body.temporary_password,
        )
        return {"kc_id": kc_id, "username": body.username}
    except Exception as e:
        raise _kc_error(e)


@router.patch("/users/{kc_id}")
def update_user(kc_id: str, body: KcUserUpdate, _: TokenData = Depends(require_admin)):
    try:
        payload = body.model_dump(exclude_unset=True)
        if "first_name" in payload:
            payload["firstName"] = payload.pop("first_name")
        if "last_name" in payload:
            payload["lastName"] = payload.pop("last_name")
        kc.update_kc_user(kc_id, **payload)
        return {"ok": True}
    except Exception as e:
        raise _kc_error(e)


@router.post("/users/{kc_id}/reset-password")
def reset_password(kc_id: str, body: KcPasswordReset, _: TokenData = Depends(require_admin)):
    try:
        kc.set_kc_password(kc_id, body.password, body.temporary)
        return {"ok": True}
    except Exception as e:
        raise _kc_error(e)


@router.post("/users/{kc_id}/disable")
def disable_user(kc_id: str, _: TokenData = Depends(require_admin)):
    try:
        kc.disable_kc_user(kc_id)
        return {"ok": True}
    except Exception as e:
        raise _kc_error(e)


@router.post("/users/{kc_id}/enable")
def enable_user(kc_id: str, _: TokenData = Depends(require_admin)):
    try:
        kc.enable_kc_user(kc_id)
        return {"ok": True}
    except Exception as e:
        raise _kc_error(e)


@router.delete("/users/{kc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(kc_id: str, _: TokenData = Depends(require_admin)):
    try:
        kc.delete_kc_user(kc_id)
    except Exception as e:
        raise _kc_error(e)


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/users/{kc_id}/sessions")
def user_sessions(kc_id: str, _: TokenData = Depends(require_admin)):
    try:
        return kc.get_user_sessions(kc_id)
    except Exception as e:
        raise _kc_error(e)


@router.delete("/users/{kc_id}/sessions", status_code=status.HTTP_204_NO_CONTENT)
def logout_user(kc_id: str, _: TokenData = Depends(require_admin)):
    try:
        kc.logout_user_sessions(kc_id)
    except Exception as e:
        raise _kc_error(e)


# ── Roles ─────────────────────────────────────────────────────────────────────

@router.get("/roles")
def list_roles(_: TokenData = Depends(require_admin)):
    try:
        return kc.list_realm_roles()
    except Exception as e:
        raise _kc_error(e)


@router.get("/users/{kc_id}/roles")
def user_roles(kc_id: str, _: TokenData = Depends(require_admin)):
    try:
        return kc.get_user_realm_roles(kc_id)
    except Exception as e:
        raise _kc_error(e)


@router.post("/users/{kc_id}/roles")
def assign_role(kc_id: str, body: KcRoleAssign, _: TokenData = Depends(require_admin)):
    try:
        kc.assign_realm_role(kc_id, body.role_name)
        return {"ok": True}
    except Exception as e:
        raise _kc_error(e)


@router.delete("/users/{kc_id}/roles/{role_name}")
def remove_role(kc_id: str, role_name: str, _: TokenData = Depends(require_admin)):
    try:
        kc.remove_realm_role(kc_id, role_name)
        return {"ok": True}
    except Exception as e:
        raise _kc_error(e)
