from pydantic import BaseModel
from datetime import datetime
from typing import Optional

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
    user_id: str
    room_id: str
    granted: bool
    reason: Optional[str] = None
    timestamp: datetime
    
    class Config:
        from_attributes = True