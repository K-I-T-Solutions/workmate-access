from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from ...db.database import get_db
from ...models import Presence, User, Room
from ...core.auth import TokenData, get_current_user

router = APIRouter(prefix="/api/v1/presence", tags=["presence"])


class PresenceEntry(BaseModel):
    user_id:    str
    room_id:    str
    entered_at: datetime
    left_at:    Optional[datetime]
    display_name: Optional[str]
    room_name:    Optional[str]

    class Config:
        from_attributes = True


@router.get("/current", response_model=list[PresenceEntry])
def current_presence(db: Session = Depends(get_db), _: TokenData = Depends(get_current_user)):
    """Alle Benutzer die aktuell in einem Raum sind (kein left_at)."""
    entries = db.query(Presence).filter(Presence.left_at == None).all()
    result = []
    for e in entries:
        user = db.query(User).filter(User.id == e.user_id).first()
        room = db.query(Room).filter(Room.id == e.room_id).first()
        result.append(PresenceEntry(
            user_id=e.user_id,
            room_id=e.room_id,
            entered_at=e.entered_at,
            left_at=e.left_at,
            display_name=user.display_name if user else e.user_id,
            room_name=room.name if room else e.room_id,
        ))
    return result


@router.get("/history", response_model=list[PresenceEntry])
def presence_history(limit: int = 50, db: Session = Depends(get_db), _: TokenData = Depends(get_current_user)):
    """Letzte Anwesenheits-Einträge."""
    entries = db.query(Presence).order_by(Presence.entered_at.desc()).limit(limit).all()
    result = []
    for e in entries:
        user = db.query(User).filter(User.id == e.user_id).first()
        room = db.query(Room).filter(Room.id == e.room_id).first()
        result.append(PresenceEntry(
            user_id=e.user_id,
            room_id=e.room_id,
            entered_at=e.entered_at,
            left_at=e.left_at,
            display_name=user.display_name if user else e.user_id,
            room_name=room.name if room else e.room_id,
        ))
    return result
