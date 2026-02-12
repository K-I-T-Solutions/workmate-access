from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from ..models import User, Room, Permission, AccessLog, NfcChip
from ..core.config import settings
from ..schemas.access import (
    AccessVerifyRequest,
    AccessVerifyResponse,
    CardVerifyRequest,
    CardVerifyResponse,
)

class AccessService:
    @staticmethod
    def verify_access(db: Session, request: AccessVerifyRequest) -> AccessVerifyResponse:
        """
        Verifiziere Zugang für einen User zu einem Room
        """
        # Prüfe ob User existiert
        user = db.query(User).filter(User.id == request.user_id, User.is_active == True).first()
        if not user:
            return AccessService._log_access(
                db, request, granted=False, reason="User not found or inactive"
            )

        # Prüfe ob Room existiert
        room = db.query(Room).filter(Room.id == request.room_id, Room.is_active == True).first()
        if not room:
            return AccessService._log_access(
                db, request, granted=False, reason="Room not found or inactive"
            )

        # Prüfe Permission
        permission = db.query(Permission).filter(
            Permission.user_id == request.user_id,
            Permission.room_id == request.room_id,
            Permission.is_active == True
        ).first()

        if not permission:
            return AccessService._log_access(
                db, request, granted=False, reason="No permission granted"
            )

        # Zugang gewährt
        return AccessService._log_access(
            db, request, granted=True, reason=f"Access granted with level: {permission.access_level}"
        )

    @staticmethod
    def _log_access(
        db: Session,
        request: AccessVerifyRequest,
        granted: bool,
        reason: str
    ) -> AccessVerifyResponse:
        """
        Logge den Access Versuch und gib Response zurück
        """
        timestamp = datetime.utcnow()

        # Log in DB
        log = AccessLog(
            user_id=request.user_id,
            room_id=request.room_id,
            granted=granted,
            reason=reason,
            device_id=request.device_id,
            nfc_chip_id=request.nfc_chip_id,
            timestamp=timestamp
        )
        db.add(log)
        db.commit()

        return AccessVerifyResponse(
            granted=granted,
            reason=reason,
            user_id=request.user_id,
            room_id=request.room_id,
            timestamp=timestamp
        )

    @staticmethod
    def _is_locked_out(db: Session, card_uid: str) -> bool:
        """
        Prüfe ob eine card_uid wegen zu vieler Fehlversuche gesperrt ist.
        Zählt fehlgeschlagene Versuche in den letzten LOCKOUT_DURATION Sekunden.
        """
        cutoff = datetime.utcnow() - timedelta(seconds=settings.LOCKOUT_DURATION)
        failed_count = db.query(func.count(AccessLog.id)).filter(
            AccessLog.nfc_chip_id == card_uid,
            AccessLog.granted == False,
            AccessLog.timestamp >= cutoff,
        ).scalar()
        return failed_count >= settings.MAX_FAILED_ATTEMPTS

    @staticmethod
    def verify_card_access(db: Session, request: CardVerifyRequest) -> CardVerifyResponse:
        """
        Verifiziere Zugang anhand NFC Karten UID (für ESP32 Geräte)
        """
        timestamp = datetime.utcnow()

        # Rate-Limiting: Lockout bei zu vielen Fehlversuchen
        if AccessService._is_locked_out(db, request.card_uid):
            AccessService._log_card_access(
                db,
                request=request,
                user_id=None,
                granted=False,
                reason="Karte gesperrt (zu viele Fehlversuche)",
                timestamp=timestamp,
            )
            return CardVerifyResponse(
                access=False,
                message="Karte gesperrt (zu viele Fehlversuche)",
                timestamp=timestamp,
            )

        # Chip anhand UID suchen, dann User laden
        chip = db.query(NfcChip).filter(
            NfcChip.chip_uid == request.card_uid,
            NfcChip.is_active == True,
        ).first()
        user = None
        if chip:
            user = db.query(User).filter(
                User.id == chip.user_id,
                User.is_active == True,
            ).first()

        if not user:
            # Unbekannte Karte - loggen und ablehnen
            AccessService._log_card_access(
                db,
                request=request,
                user_id=None,
                granted=False,
                reason="Unbekannte Karten UID",
                timestamp=timestamp
            )
            return CardVerifyResponse(
                access=False,
                message="Karte nicht registriert",
                timestamp=timestamp
            )

        # Prüfe ob Room existiert
        room = db.query(Room).filter(
            Room.id == request.room_id,
            Room.is_active == True
        ).first()

        if not room:
            AccessService._log_card_access(
                db,
                request=request,
                user_id=user.id,
                granted=False,
                reason="Raum nicht gefunden",
                timestamp=timestamp
            )
            return CardVerifyResponse(
                access=False,
                message="Raum nicht gefunden",
                user_id=user.id,
                user_name=user.display_name,
                timestamp=timestamp
            )

        # Prüfe Raum-Berechtigung
        has_access, reason = AccessService.check_room_access(db, user, request.room_id)

        AccessService._log_card_access(
            db,
            request=request,
            user_id=user.id,
            granted=has_access,
            reason=reason,
            timestamp=timestamp
        )

        if has_access:
            return CardVerifyResponse(
                access=True,
                message="Zugang gewährt",
                user_id=user.id,
                user_name=user.display_name,
                timestamp=timestamp
            )
        else:
            return CardVerifyResponse(
                access=False,
                message="Keine Berechtigung für diesen Raum",
                user_id=user.id,
                user_name=user.display_name,
                timestamp=timestamp
            )

    @staticmethod
    def check_room_access(db: Session, user: User, room_id: str) -> tuple[bool, str]:
        """
        Prüfe ob User Zugang zu einem Raum hat.
        Returns: (has_access: bool, reason: str)
        """
        # Admins haben vollen Zugang
        if user.role == "admin":
            return True, "Admin-Zugang"

        # Prüfe spezifische Berechtigung
        permission = db.query(Permission).filter(
            Permission.user_id == user.id,
            Permission.room_id == room_id,
            Permission.is_active == True
        ).first()

        if permission:
            return True, f"Berechtigung: {permission.access_level}"

        return False, "Keine Berechtigung"

    @staticmethod
    def _log_card_access(
        db: Session,
        request: CardVerifyRequest,
        user_id: str | None,
        granted: bool,
        reason: str,
        timestamp: datetime
    ) -> None:
        """
        Logge Card Access Versuch in DB
        """
        log = AccessLog(
            user_id=user_id,
            room_id=request.room_id,
            granted=granted,
            reason=reason,
            device_id=request.device_id,
            nfc_chip_id=request.card_uid,
            timestamp=timestamp
        )
        db.add(log)
        db.commit()
