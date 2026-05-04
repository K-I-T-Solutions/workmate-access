from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from .base import Base


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String, nullable=False, index=True)
    code = Column(String(6), nullable=False)
    room_id = Column(String, nullable=True)
    channel = Column(String, default="sms")  # "whatsapp" oder "sms"
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
