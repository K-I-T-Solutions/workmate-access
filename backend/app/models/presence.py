from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime
from .base import Base

class Presence(Base):
    __tablename__ = "presence"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(String, ForeignKey("users.id"), nullable=False)
    room_id    = Column(String, ForeignKey("rooms.id"), nullable=False)
    entered_at = Column(DateTime, default=datetime.utcnow)
    left_at    = Column(DateTime, nullable=True)
