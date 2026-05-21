from sqlalchemy import Column, Index, Integer, String, Boolean, DateTime
from datetime import datetime
from .base import Base

class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=True, index=True)
    room_id = Column(String, nullable=True, index=True)
    granted = Column(Boolean)
    reason = Column(String, nullable=True)
    device_id = Column(String, nullable=True)
    nfc_chip_id = Column(String, nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_access_logs_timestamp_granted", "timestamp", "granted"),
        Index("ix_access_logs_nfc_timestamp", "nfc_chip_id", "timestamp"),
    )