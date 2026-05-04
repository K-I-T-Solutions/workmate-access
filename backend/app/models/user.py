from sqlalchemy import Column, String, Boolean, DateTime
from datetime import datetime
from .base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    keycloak_id = Column(String, unique=True)
    username = Column(String, unique=True)
    display_name = Column(String)
    phone_number = Column(String, unique=True, nullable=True, index=True)  # E.164: +4915712345678
    role = Column(String, default="user")  # "admin" für vollen Zugang
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)