from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import datetime
from ...db.database import get_db
from ...models import Permission, User, Room
from ...core.auth import TokenData, require_admin
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/permissions", tags=["permissions"])


class PermissionCreate(BaseModel):
    user_id: str
    room_id: str
    access_level: str = "read"
    valid_from:  Optional[datetime.date] = None
    valid_until: Optional[datetime.date] = None
    time_from:   Optional[datetime.time] = None
    time_until:  Optional[datetime.time] = None
    weekdays:    Optional[str] = None  # "0,1,2,3,4" = Mo–Fr


class PermissionUpdate(BaseModel):
    access_level: Optional[str] = None
    valid_from:  Optional[datetime.date] = None
    valid_until: Optional[datetime.date] = None
    time_from:   Optional[datetime.time] = None
    time_until:  Optional[datetime.time] = None
    weekdays:    Optional[str] = None


class PermissionResponse(BaseModel):
    id: int
    user_id: str
    room_id: str
    access_level: str
    is_active: bool
    valid_from:  Optional[datetime.date] = None
    valid_until: Optional[datetime.date] = None
    time_from:   Optional[datetime.time] = None
    time_until:  Optional[datetime.time] = None
    weekdays:    Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=list[PermissionResponse])
def list_permissions(db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    return db.query(Permission).filter(Permission.is_active == True).all()


@router.post("/", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
def create_permission(perm: PermissionCreate, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    user = db.query(User).filter(User.id == perm.user_id).first()
    room = db.query(Room).filter(Room.id == perm.room_id).first()
    if not user or not room:
        raise HTTPException(status_code=404, detail="User or Room not found")

    db_perm = Permission(**perm.model_dump())
    db.add(db_perm)
    db.commit()
    db.refresh(db_perm)
    return db_perm


@router.patch("/{permission_id}", response_model=PermissionResponse)
def update_permission(permission_id: int, update: PermissionUpdate, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    perm = db.query(Permission).filter(Permission.id == permission_id, Permission.is_active == True).first()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(perm, field, value)
    db.commit()
    db.refresh(perm)
    return perm


@router.get("/{user_id}", response_model=list[PermissionResponse])
def get_user_permissions(user_id: str, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    return db.query(Permission).filter(
        Permission.user_id == user_id,
        Permission.is_active == True
    ).all()


@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission(permission_id: int, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    perm = db.query(Permission).filter(Permission.id == permission_id).first()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    perm.is_active = False
    db.commit()
    return None
