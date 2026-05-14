from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from ...db.database import get_db
from ...models import Room
from ...core.auth import TokenData, get_current_user, require_admin
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])

class RoomCreate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    zigbee_lock_id: Optional[str] = None

class RoomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    zigbee_lock_id: Optional[str] = None

class RoomResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    zigbee_lock_id: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True

@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(room: RoomCreate, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    """Erstelle einen neuen Room"""
    db_room = Room(**room.model_dump())
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room

@router.get("/", response_model=list[RoomResponse])
def list_rooms(db: Session = Depends(get_db), _: TokenData = Depends(get_current_user)):
    """Liste alle Rooms auf"""
    return db.query(Room).filter(Room.is_active == True).all()

@router.get("/{room_id}", response_model=RoomResponse)
def get_room(room_id: str, db: Session = Depends(get_db), _: TokenData = Depends(get_current_user)):
    """Hole einen spezifischen Room"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room

@router.patch("/{room_id}", response_model=RoomResponse)
def update_room(room_id: str, update: RoomUpdate, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    """Aktualisiere einen Raum"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(room, field, value)
    db.commit()
    db.refresh(room)
    return room

@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: str, db: Session = Depends(get_db), _: TokenData = Depends(require_admin)):
    """Lösche einen Room (deactivate)"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    room.is_active = False
    db.commit()
    return None