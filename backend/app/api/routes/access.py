import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ...db.database import get_db
from ...core.auth import TokenData, require_admin
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
from ...services.yubikey_service import verify_yubikey_access
from ...models import AccessLog
from pydantic import BaseModel
from typing import Optional

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
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_admin),
):
    """Hole Access Logs (optional gefiltert)"""
    query = db.query(AccessLog)
    
    if user_id:
        query = query.filter(AccessLog.user_id == user_id)
    if room_id:
        query = query.filter(AccessLog.room_id == room_id)
    
    return query.order_by(AccessLog.timestamp.desc()).limit(limit).all()

@router.get("/logs/export")
def export_logs_csv(
    user_id: str = None,
    room_id: str = None,
    limit: int = 10000,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_admin),
):
    """Zugangsprotokoll als CSV exportieren"""
    query = db.query(AccessLog)
    if user_id:
        query = query.filter(AccessLog.user_id == user_id)
    if room_id:
        query = query.filter(AccessLog.room_id == room_id)
    logs = query.order_by(AccessLog.timestamp.desc()).limit(limit).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "timestamp", "user_id", "room_id", "granted", "reason", "device_id", "nfc_chip_id"])
    for l in logs:
        writer.writerow([
            l.id,
            l.timestamp.isoformat() if l.timestamp else "",
            l.user_id or "",
            l.room_id or "",
            "ja" if l.granted else "nein",
            l.reason or "",
            l.device_id or "",
            l.nfc_chip_id or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=zugangsprotokoll.csv"},
    )

@router.get("/logs/{user_id}", response_model=list[AccessLogResponse])
def get_user_logs(
    user_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_admin),
):
    """Hole alle Access Logs für einen spezifischen User"""
    return (
        db.query(AccessLog)
        .filter(AccessLog.user_id == user_id)
        .order_by(AccessLog.timestamp.desc())
        .limit(limit)
        .all()
    )


class YubikeyVerifyRequest(BaseModel):
    yubikey_otp: str
    room_id: str
    device_id: Optional[str] = None


@router.post("/yubikey/verify", response_model=CardVerifyResponse)
def verify_yubikey(request: YubikeyVerifyRequest, db: Session = Depends(get_db)):
    """
    Verifiziere Yubico OTP und prüfe Raum-Berechtigung.
    Wird vom ESP32 aufgerufen nachdem der YubiKey NFC-OTP via NDEF gelesen wurde.
    """
    return verify_yubikey_access(db, request.yubikey_otp, request.room_id, request.device_id or "")


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