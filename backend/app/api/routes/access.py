from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...db.database import get_db
from ...schemas.access import (
    AccessVerifyRequest,
    AccessVerifyResponse,
    AccessLogResponse,
    CardVerifyRequest,
    CardVerifyResponse,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
)
from ...services.access_service import AccessService
from ...services.otp_service import OtpService
from ...models import AccessLog

router = APIRouter(prefix="/api/v1/access", tags=["access"])

@router.post("/verify", response_model=AccessVerifyResponse)
def verify_access(
    request: AccessVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Prüfe Zugang für einen User zu einem Room

    Request Body:
```json
    {
        "user_id": "KIT-0001",
        "room_id": "serverroom",
        "nfc_chip_id": "abc123",
        "device_id": "esp-serverroom-01"
    }
```
    """
    return AccessService.verify_access(db, request)


@router.post("/verify-card", response_model=CardVerifyResponse)
def verify_card(
    request: CardVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Verifiziere NFC-Karten Zugang (für ESP32 Geräte)

    Sucht User anhand card_uid und prüft Raum-Berechtigung.
    Alle Zugriffsversuche werden geloggt.

    Request Body:
```json
    {
        "card_uid": "74AFF106",
        "device_id": "esp32_entrance_01",
        "room_id": "office_main"
    }
```

    Response:
```json
    {
        "access": true,
        "message": "Zugang gewährt",
        "user_id": "KIT-0001",
        "user_name": "Joshua",
        "timestamp": "2025-02-05T14:30:00"
    }
```
    """
    return AccessService.verify_card_access(db, request)

@router.get("/logs", response_model=list[AccessLogResponse])
def get_access_logs(
    user_id: str = None,
    room_id: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Hole Access Logs (optional gefiltert)"""
    query = db.query(AccessLog)
    
    if user_id:
        query = query.filter(AccessLog.user_id == user_id)
    if room_id:
        query = query.filter(AccessLog.room_id == room_id)
    
    return query.order_by(AccessLog.timestamp.desc()).limit(limit).all()

@router.get("/logs/{user_id}", response_model=list[AccessLogResponse])
def get_user_logs(
    user_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Hole alle Access Logs für einen spezifischen User"""
    return (
        db.query(AccessLog)
        .filter(AccessLog.user_id == user_id)
        .order_by(AccessLog.timestamp.desc())
        .limit(limit)
        .all()
    )


@router.post("/otp/send", response_model=OtpSendResponse)
def send_otp(request: OtpSendRequest, db: Session = Depends(get_db)):
    """
    Sende einen 6-stelligen OTP per WhatsApp (bevorzugt) oder SMS.

    Request Body:
```json
    {
        "phone_number": "+4915712345678",
        "room_id": "office_main"
    }
```
    """
    return OtpService.send_otp(db, request)


@router.post("/otp/verify", response_model=OtpVerifyResponse)
def verify_otp(request: OtpVerifyRequest, db: Session = Depends(get_db)):
    """
    Verifiziere OTP und gewähre temporären Zugang.

    Request Body:
```json
    {
        "phone_number": "+4915712345678",
        "code": "123456",
        "room_id": "office_main"
    }
```
    """
    return OtpService.verify_otp(db, request)