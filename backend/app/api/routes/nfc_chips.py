from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from ...db.database import get_db
from ...models import NfcChip, User
from ...core.auth import TokenData, require_admin
from pydantic import BaseModel, field_validator
from datetime import datetime
import re

router = APIRouter(prefix="/api/v1/users", tags=["nfc-chips"])


class NfcChipCreate(BaseModel):
    chip_uid: str
    label: Optional[str] = None

    @field_validator("chip_uid")
    @classmethod
    def validate_chip_uid(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.fullmatch(r"[0-9A-F]{8,14}", v):
            raise ValueError("chip_uid muss 8-14 Hex-Zeichen sein (z.B. 'A395E806')")
        return v


class NfcChipResponse(BaseModel):
    id: int
    user_id: str
    chip_uid: str
    label: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/{user_id}/chips", response_model=list[NfcChipResponse])
def list_user_chips(user_id: str, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    """Liste alle NFC Chips eines Users auf"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return db.query(NfcChip).filter(
        NfcChip.user_id == user_id,
        NfcChip.is_active == True,
    ).all()


@router.post("/{user_id}/chips", response_model=NfcChipResponse, status_code=status.HTTP_201_CREATED)
def add_chip(user_id: str, chip: NfcChipCreate, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    """Füge einem User einen NFC Chip hinzu"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(NfcChip).filter(NfcChip.chip_uid == chip.chip_uid).first()
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=409, detail="Chip UID bereits registriert")
        # Deaktivierten Chip reaktivieren und neuem User zuweisen
        existing.user_id = user_id
        existing.label = chip.label
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing

    db_chip = NfcChip(user_id=user_id, chip_uid=chip.chip_uid, label=chip.label)
    db.add(db_chip)
    db.commit()
    db.refresh(db_chip)
    return db_chip


@router.delete("/{user_id}/chips/{chip_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_chip(user_id: str, chip_id: int, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    """Deaktiviere einen NFC Chip"""
    chip = db.query(NfcChip).filter(
        NfcChip.id == chip_id,
        NfcChip.user_id == user_id,
    ).first()
    if not chip:
        raise HTTPException(status_code=404, detail="Chip not found")
    chip.is_active = False
    db.commit()
    return None
