from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from ...db.database import get_db
from ...models import RoomGroup, Room
from ...core.auth import TokenData, require_admin, get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/room-groups", tags=["room-groups"])


class RoomGroupCreate(BaseModel):
    name: str
    color: str = "#6366f1"


class RoomGroupUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class RoomGroupResponse(BaseModel):
    id: int
    name: str
    color: str

    class Config:
        from_attributes = True


@router.get("/", response_model=list[RoomGroupResponse])
def list_groups(db: Session = Depends(get_db), _: TokenData = Depends(get_current_user)):
    return db.query(RoomGroup).order_by(RoomGroup.name).all()


@router.post("/", response_model=RoomGroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(group: RoomGroupCreate, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    db_group = RoomGroup(**group.model_dump())
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


@router.patch("/{group_id}", response_model=RoomGroupResponse)
def update_group(group_id: int, update: RoomGroupUpdate, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    group = db.query(RoomGroup).filter(RoomGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    group = db.query(RoomGroup).filter(RoomGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    # Räume aus der Gruppe entfernen
    db.query(Room).filter(Room.group_id == group_id).update({"group_id": None})
    db.delete(group)
    db.commit()
    return None
