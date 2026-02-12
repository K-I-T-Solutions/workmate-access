from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from datetime import datetime
from .base import Base

class Permission(Base):
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    room_id = Column(String, ForeignKey("rooms.id"))
    access_level = Column(String, default="read")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)