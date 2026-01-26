from sqlalchemy.orm import Session
from datetime import datetime
from ..models import User, Room, Permission, AccessLog
from ..schemas.access import AccessVerifyRequest, AccessVerifyResponse

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
