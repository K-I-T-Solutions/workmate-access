import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...db.database import get_db
from ...models import GuestToken, Room, AccessLog
from ...core.auth import TokenData, require_admin

router = APIRouter(prefix="/api/v1/access/guest", tags=["guest"])


class GuestTokenCreate(BaseModel):
    room_id:   str
    label:     Optional[str] = None
    hours:     int = 24       # Gültigkeitsdauer in Stunden


class GuestTokenResponse(BaseModel):
    id:         str
    room_id:    str
    label:      Optional[str]
    created_by: Optional[str]
    expires_at: datetime
    is_used:    bool
    used_at:    Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/generate", response_model=GuestTokenResponse, status_code=status.HTTP_201_CREATED)
def generate_guest_token(
    body: GuestTokenCreate,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_admin),
):
    room = db.query(Room).filter(Room.id == body.room_id, Room.is_active == True).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    token = GuestToken(
        id=str(uuid.uuid4()),
        room_id=body.room_id,
        label=body.label,
        created_by=user.username,
        expires_at=datetime.utcnow() + timedelta(hours=body.hours),
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


@router.get("/list", response_model=list[GuestTokenResponse])
def list_guest_tokens(db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    return db.query(GuestToken).order_by(GuestToken.created_at.desc()).limit(100).all()


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_guest_token(token_id: str, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    token = db.query(GuestToken).filter(GuestToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    db.delete(token)
    db.commit()


@router.post("/use/{token_id}")
def use_guest_token(token_id: str, db: Session = Depends(get_db)):
    """Öffentlicher Endpunkt — kein Auth erforderlich."""
    token = db.query(GuestToken).filter(GuestToken.id == token_id).first()
    now = datetime.utcnow()

    if not token:
        _log_guest(db, None, "unknown", False, "Token nicht gefunden", now)
        raise HTTPException(status_code=404, detail="Token ungültig")

    if token.is_used:
        _log_guest(db, token.room_id, token_id, False, "Token bereits verwendet", now)
        raise HTTPException(status_code=410, detail="Token bereits verwendet")

    if now > token.expires_at:
        _log_guest(db, token.room_id, token_id, False, "Token abgelaufen", now)
        raise HTTPException(status_code=410, detail="Token abgelaufen")

    token.is_used = True
    token.used_at = now
    _log_guest(db, token.room_id, token_id, True, f"Gast-Zugang: {token.label or token_id}", now)
    db.commit()

    return {
        "access":   True,
        "room_id":  token.room_id,
        "message":  "Zugang gewährt",
        "expires_at": token.expires_at.isoformat(),
    }


def _log_guest(db, room_id, device_id, granted, reason, timestamp):
    db.add(AccessLog(
        user_id=None,
        room_id=room_id,
        granted=granted,
        reason=reason,
        device_id=device_id,
        timestamp=timestamp,
    ))
    db.commit()
