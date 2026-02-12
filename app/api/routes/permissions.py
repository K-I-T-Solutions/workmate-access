from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...db.database import get_db
from ...models import Permission, User, Room
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/permissions", tags=["permissions"])

class PermissionCreate(BaseModel):
    user_id: str
    room_id: str
    access_level: str = "read"

class PermissionResponse(BaseModel):
    id: int
    user_id: str
    room_id: str
    access_level: str
    is_active: bool
    
    class Config:
        from_attributes = True

@router.get("/", response_model=list[PermissionResponse])
def list_permissions(db: Session = Depends(get_db)):
    """Liste alle aktiven Berechtigungen auf"""
    return db.query(Permission).filter(Permission.is_active == True).all()

@router.post("/", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
def create_permission(perm: PermissionCreate, db: Session = Depends(get_db)):
    """Vergebe eine Permission (User zu Room)"""
    # Prüfe ob User und Room existieren
    user = db.query(User).filter(User.id == perm.user_id).first()
    room = db.query(Room).filter(Room.id == perm.room_id).first()
    
    if not user or not room:
        raise HTTPException(status_code=404, detail="User or Room not found")
    
    db_perm = Permission(**perm.dict())
    db.add(db_perm)
    db.commit()
    db.refresh(db_perm)
    return db_perm

@router.get("/{user_id}", response_model=list[PermissionResponse])
def get_user_permissions(user_id: str, db: Session = Depends(get_db)):
    """Hole alle Permissions für einen User"""
    return db.query(Permission).filter(
        Permission.user_id == user_id,
        Permission.is_active == True
    ).all()

@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission(permission_id: int, db: Session = Depends(get_db)):
    """Lösche eine Permission"""
    perm = db.query(Permission).filter(Permission.id == permission_id).first()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    perm.is_active = False
    db.commit()
    return None