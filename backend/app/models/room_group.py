from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .base import Base

class RoomGroup(Base):
    __tablename__ = "room_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    color = Column(String, default="#6366f1", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
