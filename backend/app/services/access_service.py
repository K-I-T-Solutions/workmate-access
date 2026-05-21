from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from ..models import User, Room, Permission, AccessLog, NfcChip, Presence
from . import zigbee_service
from .event_bus import publish as bus_publish
from . import notification_service
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
            AccessService._update_presence(db, user.id, request.room_id, timestamp)
            if room.zigbee_lock_id:
                zigbee_service.unlock(room.zigbee_lock_id)
        else:
            bus_publish({
                "type": "access_denied",
                "user_id":   user.id,
                "user_name": user.display_name,
                "room_id":   request.room_id,
                "reason":    reason,
                "timestamp": timestamp.isoformat(),
            })
            notification_service.notify_denial(
                user_id=user.id,
                user_name=user.display_name,
                room_id=request.room_id,
                reason=reason,
                timestamp=timestamp.strftime("%d.%m.%Y %H:%M:%S"),
            )

        return CardVerifyResponse(
            access=has_access,
            message="Zugang gewährt" if has_access else "Keine Berechtigung für diesen Raum",
            user_id=user.id if has_access else None,
            user_name=user.display_name if has_access else None,
            timestamp=timestamp
        )

    @staticmethod
    def check_room_access(db: Session, user: User, room_id: str) -> tuple[bool, str]:
        """
        Prüfe ob User Zugang zu einem Raum hat.
        Returns: (has_access: bool, reason: str)
        """
        if user.role == "admin":
            return True, "Admin-Zugang"

        permission = db.query(Permission).filter(
            Permission.user_id == user.id,
            Permission.room_id == room_id,
            Permission.is_active == True
        ).first()

        if not permission:
            return False, "Keine Berechtigung"

        denied = AccessService._check_time_constraints(permission)
        if denied:
            return False, denied

        return True, f"Berechtigung: {permission.access_level}"

    @staticmethod
    def _check_time_constraints(permission) -> str | None:
        """Gibt einen Ablehnungsgrund zurück oder None wenn alles passt."""
        now = datetime.now()
        today = now.date()
        current_time = now.time()
        current_weekday = now.weekday()  # 0=Mo … 6=So

        if permission.valid_from and today < permission.valid_from:
            return f"Berechtigung gilt erst ab {permission.valid_from}"

        if permission.valid_until and today > permission.valid_until:
            return f"Berechtigung abgelaufen am {permission.valid_until}"

        if permission.weekdays:
            allowed = {int(d) for d in permission.weekdays.split(",") if d.strip()}
            if current_weekday not in allowed:
                names = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
                allowed_names = ", ".join(names[d] for d in sorted(allowed))
                return f"Zugang nur erlaubt an: {allowed_names}"

        if permission.time_from and permission.time_until:
            if not (permission.time_from <= current_time <= permission.time_until):
                return (f"Zugang nur zwischen {permission.time_from.strftime('%H:%M')}"
                        f" und {permission.time_until.strftime('%H:%M')} Uhr")

        return None

    @staticmethod
    def _update_presence(db: Session, user_id: str, room_id: str, timestamp: datetime) -> None:
        """Toggle-Logik: erster Scan = betreten, zweiter Scan = verlassen."""
        open_entry = db.query(Presence).filter(
            Presence.user_id == user_id,
            Presence.room_id == room_id,
            Presence.left_at == None,
        ).first()
        if open_entry:
            open_entry.left_at = timestamp
        else:
            db.add(Presence(user_id=user_id, room_id=room_id, entered_at=timestamp))
        db.commit()

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
