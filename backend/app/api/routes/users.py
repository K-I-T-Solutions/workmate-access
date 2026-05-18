from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from ...db.database import get_db
from ...models import User, NfcChip, Permission, AccessLog, UserYubikey, Presence
from ...models.nfc_chip import NfcChip
from ...core.auth import TokenData, get_current_user, require_admin
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/v1/users", tags=["users"])

class UserCreate(BaseModel):
    id: str
    workmate_id: Optional[str] = None
    keycloak_id: str
    username: str
    display_name: str
    phone_number: Optional[str] = None
    role: str = "user"

class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    workmate_id: Optional[str] = None
    keycloak_id: Optional[str] = None
    username: Optional[str] = None
    phone_number: Optional[str] = None

class RenameIdBody(BaseModel):
    new_id: str

class UserResponse(BaseModel):
    id: str
    workmate_id: Optional[str] = None
    username: str
    display_name: str
    role: str = "user"
    keycloak_id: str
    phone_number: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    """Erstelle einen neuen User"""
    db_user = User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), _: TokenData = Depends(get_current_user)):
    """Liste alle Users auf"""
    return db.query(User).filter(User.is_active == True).all()

@router.get("/wm/{workmate_id}", response_model=UserResponse)
def get_user_by_workmate_id(workmate_id: str, db: Session = Depends(get_db), _: TokenData = Depends(get_current_user)):
    """Benutzer anhand der plattformübergreifenden Workmate-ID abrufen (z.B. WM-100)"""
    user = db.query(User).filter(User.workmate_id == workmate_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db), _: TokenData = Depends(get_current_user)):
    """Hole einen spezifischen User"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, update: UserUpdate, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    """Aktualisiere einen User"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    """Deaktiviere einen User"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.query(NfcChip).filter(NfcChip.user_id == user_id).update({"is_active": False})
    db.commit()
    return None


@router.post("/{user_id}/rename-id", response_model=UserResponse)
def rename_user_id(user_id: str, body: RenameIdBody, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    """Interne Benutzer-ID umbenennen und alle FK-Referenzen migrieren."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if db.query(User).filter(User.id == body.new_id).first():
        raise HTTPException(status_code=400, detail="ID bereits vergeben")

    new_id = body.new_id
    for model in [Permission, AccessLog, NfcChip, UserYubikey, Presence]:
        db.query(model).filter(model.user_id == user_id).update({"user_id": new_id}, synchronize_session=False)
    user.id = new_id
    db.commit()
    db.refresh(user)
    return user