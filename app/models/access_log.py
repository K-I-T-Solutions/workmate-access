from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from datetime import datetime
from .base import Base

class AccessLog(Base):
    __tablename__ = "access_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    room_id = Column(String, ForeignKey("rooms.id"))
    granted = Column(Boolean)
    reason = Column(String, nullable=True)
    device_id = Column(String, nullable=True)
    nfc_chip_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)