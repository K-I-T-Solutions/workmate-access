from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...db.database import get_db
from ...models import User
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/users", tags=["users"])

class UserCreate(BaseModel):
    id: str  # KIT-0001
    zitadel_id: str
    username: str
    display_name: str

class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str
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