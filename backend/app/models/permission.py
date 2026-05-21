from sqlalchemy import Column, Index, Integer, String, ForeignKey, Boolean, DateTime, Date, Time, UniqueConstraint
from datetime import datetime
from .base import Base

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    room_id = Column(String, ForeignKey("rooms.id"), index=True)
    access_level = Column(String, default="read")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Zeitbasierte Einschränkungen (alle nullable = keine Einschränkung)
    valid_from  = Column(Date, nullable=True)   # ab diesem Datum gültig
    valid_until = Column(Date, nullable=True)   # bis zu diesem Datum gültig
    time_from   = Column(Time, nullable=True)   # Tagesbeginn (z. B. 08:00)
    time_until  = Column(Time, nullable=True)   # Tagesende   (z. B. 18:00)
    # Wochentage als kommaseparierte Ints: 0=Mo,1=Di,...,6=So — null = alle
    weekdays    = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "room_id", name="uq_permission_user_room"),
    )