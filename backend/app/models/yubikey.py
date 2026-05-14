from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from .base import Base


class UserYubikey(Base):
    __tablename__ = "user_yubikeys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    public_id = Column(String(12), nullable=False, unique=True, index=True)  # erste 12 Modhex-Zeichen
    label = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
