import base64
import hashlib
import hmac
import secrets
from datetime import datetime

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import User, AccessLog, UserYubikey
from ..services.access_service import AccessService
from ..schemas.access import CardVerifyResponse

YUBICO_API_URL = "https://api.yubico.com/wsapi/2.0/verify"
MODHEX = "cbdefghijklnrtuv"
OTP_LENGTH = 44
PUBLIC_ID_LENGTH = 12


def extract_public_id(otp: str) -> str:
    return otp[:PUBLIC_ID_LENGTH]


def _is_modhex(s: str) -> bool:
    return all(c in MODHEX for c in s)


def validate_otp_format(otp: str) -> None:
    if len(otp) != OTP_LENGTH:
        raise HTTPException(status_code=422, detail=f"Yubico OTP muss {OTP_LENGTH} Zeichen lang sein")
    if not _is_modhex(otp):
        raise HTTPException(status_code=422, detail="Yubico OTP enthält ungültige Zeichen (Modhex erwartet)")


def _build_signed_params(otp: str, nonce: str) -> dict:
    params = {
        "id": settings.YUBICO_CLIENT_ID,
        "nonce": nonce,
        "otp": otp,
        "sl": "secure",
        "timestamp": "1",
    }
    if settings.YUBICO_SECRET_KEY:
        sorted_str = "&".join(f"{k}={params[k]}" for k in sorted(params))
        key = base64.b64decode(settings.YUBICO_SECRET_KEY)
        sig = base64.b64encode(hmac.new(key, sorted_str.encode(), hashlib.sha1).digest()).decode()
        params["h"] = sig
    return params


def _parse_response(text: str) -> dict:
    result = {}
    for line in text.strip().split("\r\n"):
        if "=" in line:
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def _verify_response_hmac(result: dict) -> bool:
    if not settings.YUBICO_SECRET_KEY:
        return True
    sig = result.pop("h", None)
    if not sig:
        return False
    sorted_str = "&".join(f"{k}={result[k]}" for k in sorted(result))
    key = base64.b64decode(settings.YUBICO_SECRET_KEY)
    expected = base64.b64encode(hmac.new(key, sorted_str.encode(), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(sig, expected)


def validate_with_yubico(otp: str) -> None:
    if not settings.YUBICO_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Yubico Client-ID nicht konfiguriert (YUBICO_CLIENT_ID)")

    nonce = secrets.token_hex(16)
    params = _build_signed_params(otp, nonce)

    try:
        resp = httpx.get(YUBICO_API_URL, params=params, timeout=10)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"YubiCloud nicht erreichbar: {e}")

    result = _parse_response(resp.text)

    if not _verify_response_hmac(result):
        raise HTTPException(status_code=502, detail="YubiCloud Antwort-Signatur ungültig")

    if result.get("nonce") != nonce:
        raise HTTPException(status_code=502, detail="YubiCloud Nonce-Mismatch")

    status = result.get("status")
    if status == "OK":
        return
    if status == "REPLAYED_OTP":
        raise HTTPException(status_code=409, detail="OTP bereits verwendet (Replay erkannt)")
    if status == "BAD_OTP":
        raise HTTPException(status_code=422, detail="Ungültiger OTP")
    raise HTTPException(status_code=401, detail=f"YubiCloud Fehler: {status}")


def verify_yubikey_access(db: Session, otp: str, room_id: str, device_id: str = "") -> CardVerifyResponse:
    validate_otp_format(otp)
    timestamp = datetime.utcnow()
    public_id = extract_public_id(otp)

    yubikey = db.query(UserYubikey).filter(
        UserYubikey.public_id == public_id,
        UserYubikey.is_active == True,
    ).first()

    def _log(user_id, granted, reason):
        db.add(AccessLog(
            user_id=user_id,
            room_id=room_id,
            granted=granted,
            reason=reason,
            device_id=device_id or None,
            nfc_chip_id=f"yubikey:{public_id}",
            timestamp=timestamp,
        ))
        db.commit()

    if not yubikey:
        _log(None, False, "Unbekannte YubiKey Public-ID")
        return CardVerifyResponse(access=False, message="YubiKey nicht registriert", timestamp=timestamp)

    user = db.query(User).filter(User.id == yubikey.user_id, User.is_active == True).first()
    if not user:
        _log(None, False, "User inaktiv oder nicht gefunden")
        return CardVerifyResponse(access=False, message="Benutzer nicht gefunden", timestamp=timestamp)

    # OTP gegen YubiCloud validieren — erst nach User-Lookup, um unnötige API-Calls zu vermeiden
    try:
        validate_with_yubico(otp)
    except HTTPException as e:
        _log(user.id, False, f"YubiCloud: {e.detail}")
        raise

    has_access, reason = AccessService.check_room_access(db, user, room_id)
    _log(user.id, has_access, reason)

    return CardVerifyResponse(
        access=has_access,
        message="Zugang gewährt" if has_access else reason,
        user_id=user.id,
        user_name=user.display_name,
        timestamp=timestamp,
    )
