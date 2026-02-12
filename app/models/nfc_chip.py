from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from .base import Base


class NfcChip(Base):
    __tablename__ = "nfc_chips"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    chip_uid = Column(String, unique=True, nullable=False, index=True)
    label = Column(String, nullable=True)  # z.B. "Schlüsselanhänger", "Karte"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
