from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from ...db.database import get_db
from ...models import User, UserYubikey
from ...core.auth import TokenData, require_admin
from ...services.yubikey_service import extract_public_id, _is_modhex, OTP_LENGTH, PUBLIC_ID_LENGTH

router = APIRouter(prefix="/api/v1/users", tags=["yubikeys"])


class YubikeyCreate(BaseModel):
    # Entweder vollständiger OTP (44 Zeichen) oder direkt die Public-ID (12 Zeichen)
    otp_or_public_id: str
    label: Optional[str] = None

    def get_public_id(self) -> str:
        v = self.otp_or_public_id.strip().lower()
        if len(v) == OTP_LENGTH:
            return extract_public_id(v)
        if len(v) == PUBLIC_ID_LENGTH and _is_modhex(v):
            return v
        raise ValueError(f"Muss ein {OTP_LENGTH}-stelliger OTP oder eine {PUBLIC_ID_LENGTH}-stellige Public-ID sein")


class YubikeyResponse(BaseModel):
    id: int
    user_id: str
    public_id: str
    label: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/{user_id}/yubikeys", response_model=list[YubikeyResponse])
def list_user_yubikeys(
    user_id: str,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return db.query(UserYubikey).filter(
        UserYubikey.user_id == user_id,
        UserYubikey.is_active == True,
    ).all()


@router.post("/{user_id}/yubikeys", response_model=YubikeyResponse, status_code=status.HTTP_201_CREATED)
def add_yubikey(
    user_id: str,
    body: YubikeyCreate,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        public_id = body.get_public_id()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    existing = db.query(UserYubikey).filter(UserYubikey.public_id == public_id).first()
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=409, detail="YubiKey bereits registriert")
        existing.user_id = user_id
        existing.label = body.label
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing

    yk = UserYubikey(user_id=user_id, public_id=public_id, label=body.label)
    db.add(yk)
    db.commit()
    db.refresh(yk)
    return yk


@router.delete("/{user_id}/yubikeys/{yubikey_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_yubikey(
    user_id: str,
    yubikey_id: int,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_admin),
):
    yk = db.query(UserYubikey).filter(
        UserYubikey.id == yubikey_id,
        UserYubikey.user_id == user_id,
    ).first()
    if not yk:
        raise HTTPException(status_code=404, detail="YubiKey not found")
    yk.is_active = False
    db.commit()
    return None
