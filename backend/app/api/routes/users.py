from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from ...db.database import get_db
from ...models import User, NfcChip
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/users", tags=["users"])

class UserCreate(BaseModel):
    id: str  # KIT-0001
    zitadel_id: str
    username: str
    display_name: str
    role: str = "user"

class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    role: str = "user"
    zitadel_id: str
    is_active: bool

    class Config:
        from_attributes = True

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Erstelle einen neuen User"""
    db_user = User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    """Liste alle Users auf"""
    return db.query(User).filter(User.is_active == True).all()

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    """Hole einen spezifischen User"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, update: UserUpdate, db: Session = Depends(get_db)):
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
def delete_user(user_id: str, db: Session = Depends(get_db)):
    """Deaktiviere einen User"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.query(NfcChip).filter(NfcChip.user_id == user_id).update({"is_active": False})
    db.commit()
    return None