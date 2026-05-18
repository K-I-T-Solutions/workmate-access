from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime
from .base import Base

class GuestToken(Base):
    __tablename__ = "guest_tokens"

    id         = Column(String, primary_key=True)   # UUID
    room_id    = Column(String, ForeignKey("rooms.id"), nullable=False)
    label      = Column(String, nullable=True)       # optionale Beschreibung
    created_by = Column(String, nullable=True)       # Keycloak-Username des Admins
    expires_at = Column(DateTime, nullable=False)
    is_used    = Column(Boolean, default=False)
    used_at    = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
