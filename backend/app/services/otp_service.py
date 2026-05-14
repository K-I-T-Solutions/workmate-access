import secrets
import string
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta

import sent_dm
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import User, OtpCode
from ..schemas.access import (
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
)

OTP_TTL_MINUTES = 5

_verify_attempts: dict[str, list[float]] = defaultdict(list)
_verify_lock = threading.Lock()


def _check_send_rate_limit(db: Session, phone_number: str) -> None:
    since = datetime.utcnow() - timedelta(hours=1)
    count = (
        db.query(OtpCode)
        .filter(OtpCode.phone_number == phone_number, OtpCode.created_at >= since)
        .count()
    )
    if count >= settings.OTP_SEND_MAX_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Zu viele OTP-Anfragen. Maximal {settings.OTP_SEND_MAX_PER_HOUR} pro Stunde erlaubt.",
        )


def _check_verify_rate_limit(phone_number: str) -> None:
    now = time.monotonic()
    window = settings.OTP_VERIFY_WINDOW_MINUTES * 60
    with _verify_lock:
        recent = [t for t in _verify_attempts[phone_number] if now - t < window]
        if len(recent) >= settings.OTP_VERIFY_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=429,
                detail=f"Zu viele Versuche. Bitte {settings.OTP_VERIFY_WINDOW_MINUTES} Minuten warten.",
            )
        recent.append(now)
        _verify_attempts[phone_number] = recent


class OtpService:
    @staticmethod
    def _generate_code() -> str:
        return "".join(secrets.choice(string.digits) for _ in range(6))

    @staticmethod
    def _get_client() -> sent_dm.Sent:
        return sent_dm.Sent(api_key=settings.SENT_DM_API_KEY)

    @staticmethod
    def _profile_id() -> str | None:
        return settings.SENT_DM_CUSTOMER_ID or None

    @staticmethod
    def _detect_channel(client: sent_dm.Sent, phone_number: str) -> str:
        """WhatsApp prüfen via Contacts API, SMS als Fallback."""
        try:
            kwargs = {"id": phone_number}
            if OtpService._profile_id():
                kwargs["x_profile_id"] = OtpService._profile_id()
            response = client.contacts.retrieve(**kwargs)
            channels = (response.data.available_channels or "") if response.data else ""
            if "whatsapp" in channels.lower():
                return "whatsapp"
        except Exception:
            pass
        return "sms"

    @staticmethod
    def _deliver(client: sent_dm.Sent, phone_number: str, code: str, channel: str) -> None:
        kwargs = {
            "to": [phone_number],
            "channel": [channel],
            "sandbox": settings.SENT_DM_SANDBOX,
            "template": {
                "id": settings.SENT_DM_OTP_TEMPLATE_ID,
                "parameters": {"otp": code},
            },
        }
        if OtpService._profile_id():
            kwargs["x_profile_id"] = OtpService._profile_id()
        client.messages.send(**kwargs)

    @staticmethod
    def send_otp(db: Session, request: OtpSendRequest) -> OtpSendResponse:
        _check_send_rate_limit(db, request.phone_number)
        client = OtpService._get_client()
        channel = OtpService._detect_channel(client, request.phone_number)
        code = OtpService._generate_code()
        expires_at = datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES)

        # Alle noch aktiven OTPs für diese Nummer invalidieren
        db.query(OtpCode).filter(
            OtpCode.phone_number == request.phone_number,
            OtpCode.is_used == False,
        ).update({"is_used": True})

        otp = OtpCode(
            phone_number=request.phone_number,
            code=code,
            room_id=request.room_id,
            channel=channel,
            expires_at=expires_at,
        )
        db.add(otp)
        db.commit()

        try:
            OtpService._deliver(client, request.phone_number, code, channel)
        except Exception as e:
            # Versand fehlgeschlagen → OTP sofort ungültig machen
            otp.is_used = True
            db.commit()
            raise HTTPException(status_code=502, detail=f"Nachricht konnte nicht gesendet werden: {e}")

        return OtpSendResponse(
            success=True,
            message=f"OTP gesendet via {channel.upper()}",
            channel=channel,
        )

    @staticmethod
    def verify_otp(db: Session, request: OtpVerifyRequest) -> OtpVerifyResponse:
        _check_verify_rate_limit(request.phone_number)
        timestamp = datetime.utcnow()

        otp = db.query(OtpCode).filter(
            OtpCode.phone_number == request.phone_number,
            OtpCode.code == request.code,
            OtpCode.room_id == request.room_id,
            OtpCode.is_used == False,
            OtpCode.expires_at >= timestamp,
        ).first()

        if not otp:
            return OtpVerifyResponse(
                access=False,
                message="OTP ungültig oder abgelaufen",
                timestamp=timestamp,
            )

        otp.is_used = True
        otp.verified_at = timestamp
        db.commit()

        user = db.query(User).filter(
            User.phone_number == request.phone_number,
            User.is_active == True,
        ).first()

        if not user:
            return OtpVerifyResponse(
                access=False,
                message="Kein aktiver User für diese Nummer registriert",
                timestamp=timestamp,
            )

        from .access_service import AccessService
        has_access, reason = AccessService.check_room_access(db, user, request.room_id)

        return OtpVerifyResponse(
            access=has_access,
            message="Zugang gewährt" if has_access else reason,
            user_id=user.id,
            user_name=user.display_name,
            timestamp=timestamp,
        )
