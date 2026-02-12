from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from ...db.database import get_db
from ...models import NfcChip, User
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/v1/users", tags=["nfc-chips"])


class NfcChipCreate(BaseModel):
    chip_uid: str
    label: Optional[str] = None


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
def list_user_chips(user_id: str, db: Session = Depends(get_db)):
    """Liste alle NFC Chips eines Users auf"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return db.query(NfcChip).filter(
        NfcChip.user_id == user_id,
        NfcChip.is_active == True,
    ).all()


@router.post("/{user_id}/chips", response_model=NfcChipResponse, status_code=status.HTTP_201_CREATED)
def add_chip(user_id: str, chip: NfcChipCreate, db: Session = Depends(get_db)):
    """Füge einem User einen NFC Chip hinzu"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(NfcChip).filter(NfcChip.chip_uid == chip.chip_uid, NfcChip.is_active == True).first()
    if existing:
        raise HTTPException(status_code=409, detail="Chip UID bereits registriert")

    db_chip = NfcChip(user_id=user_id, chip_uid=chip.chip_uid, label=chip.label)
    db.add(db_chip)
    db.commit()
    db.refresh(db_chip)
    return db_chip


@router.delete("/{user_id}/chips/{chip_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_chip(user_id: str, chip_id: int, db: Session = Depends(get_db)):
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
