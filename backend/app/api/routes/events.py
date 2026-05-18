from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse
from ...core.auth import get_current_user, TokenData
from ...services.event_bus import subscribe

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("/access")
async def access_events(_: TokenData = Depends(get_current_user)):
    """Server-Sent Events — liefert Echtzeit-Zugangsereignisse."""
    async def generator():
        async for data in subscribe():
            yield {"data": data}
    return EventSourceResponse(generator())
