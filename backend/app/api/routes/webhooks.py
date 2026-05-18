from fastapi import APIRouter, Request, Header, HTTPException
from sqlalchemy.orm import Session
from fastapi import Depends
from datetime import datetime
from ...db.database import get_db
from ...models import AccessLog
from ...core.config import settings

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

# Optionaler shared Secret-Header (in .env als WEBHOOK_SECRET konfigurieren)


@router.post("/keycloak")
async def keycloak_event(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_secret: str = Header(default=""),
):
    """
    Keycloak Event-Listener Webhook.
    Konfigurieren: Keycloak Admin → Events → Event Listener → HTTP (via Plugin)
    Unterstützte Events: LOGIN, LOGIN_ERROR, LOGOUT
    """
    secret = getattr(settings, "WEBHOOK_SECRET", "")
    if secret and x_webhook_secret != secret:
        raise HTTPException(status_code=403, detail="Ungültiges Webhook-Secret")

    body = await request.json()
    event_type = body.get("type", "")
    user_id    = body.get("userId") or body.get("details", {}).get("username", "")
    realm      = body.get("realmId", "")
    ip         = body.get("ipAddress", "")
    timestamp  = datetime.utcnow()

    if event_type in ("LOGIN", "LOGIN_ERROR", "LOGOUT"):
        granted = event_type == "LOGIN"
        reason  = {
            "LOGIN":       "SSO Login",
            "LOGIN_ERROR": f"SSO Login fehlgeschlagen ({ip})",
            "LOGOUT":      "SSO Logout",
        }.get(event_type, event_type)

        db.add(AccessLog(
            user_id=user_id or None,
            room_id="__sso__",
            granted=granted,
            reason=reason,
            device_id=f"keycloak/{realm}",
            timestamp=timestamp,
        ))
        db.commit()

    return {"ok": True}
