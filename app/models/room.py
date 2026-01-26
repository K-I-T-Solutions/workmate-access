from sqlalchemy import Column, String, Boolean, DateTime
from datetime import datetime
from .base import Base

class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(String, primary_key=True)  # "serverroom"
    name = Column(String, unique=True)  # "Server Room"
    description = Column(String, nullable=True)
    zigbee_lock_id = Column(String, nullable=True)  # Zigbee Lock Entity
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)