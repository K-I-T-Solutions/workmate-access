from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
import re

class AccessVerifyRequest(BaseModel):
    user_id: str  # KIT-0001
    room_id: str  # serverroom
    nfc_chip_id: Optional[str] = None
    device_id: Optional[str] = None

class AccessVerifyResponse(BaseModel):
    granted: bool
    reason: Optional[str] = None
    user_id: str
    room_id: str
    timestamp: datetime

class AccessLogResponse(BaseModel):
    id: int
    user_id: Optional[str] = None
    room_id: Optional[str] = None
    granted: bool
    reason: Optional[str] = None
    device_id: Optional[str] = None
    nfc_chip_id: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class CardVerifyRequest(BaseModel):
    """Request vom ESP32 NFC Reader"""
    card_uid: str  # NFC Karten UID z.B. "74AFF106"
    device_id: str  # ESP32 Kennung z.B. "esp32_entrance_01"
    room_id: str  # Zielraum z.B. "office_main"

    @field_validator("card_uid")
    @classmethod
    def validate_card_uid(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.fullmatch(r"[0-9A-F]{8,14}", v):
            raise ValueError("card_uid muss 8-14 Hex-Zeichen sein")
        return v


class CardVerifyResponse(BaseModel):
    """Response für ESP32 NFC Reader"""
    access: bool
    message: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    timestamp: datetime


class OtpSendRequest(BaseModel):
    phone_number: str  # E.164: +4915712345678
    room_id: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"\+[1-9]\d{6,14}", v):
            raise ValueError("phone_number muss im E.164-Format sein (z.B. +4915712345678)")
        return v


class OtpSendResponse(BaseModel):
    success: bool
    message: str
    channel: str  # "whatsapp" oder "sms"


class OtpVerifyRequest(BaseModel):
    phone_number: str
    code: str
    room_id: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"\+[1-9]\d{6,14}", v):
            raise ValueError("phone_number muss im E.164-Format sein (z.B. +4915712345678)")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"\d{6}", v):
            raise ValueError("code muss genau 6 Ziffern haben")
        return v


class OtpVerifyResponse(BaseModel):
    access: bool
    message: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    timestamp: datetime