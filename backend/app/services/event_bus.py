import asyncio
import json
from typing import AsyncGenerator

_subscribers: list[asyncio.Queue] = []


def publish(event: dict) -> None:
    """Wird aus synchronem Code aufgerufen (z.B. access_service)."""
    data = json.dumps(event)
    for q in list(_subscribers):
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            pass


async def subscribe() -> AsyncGenerator[str, None]:
    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    _subscribers.append(q)
    try:
        while True:
            data = await q.get()
            yield data
    finally:
        _subscribers.remove(q)
