from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...db.database import get_db
from ...schemas.access import AccessVerifyRequest, AccessVerifyResponse, AccessLogResponse
from ...services.access_service import AccessService
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