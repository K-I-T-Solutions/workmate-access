from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from datetime import datetime
from .base import Base

class Room(Base):
    __tablename__ = "rooms"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True)
    description = Column(String, nullable=True)
    zigbee_lock_id = Column(String, nullable=True)
    group_id = Column(Integer, ForeignKey("room_groups.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)