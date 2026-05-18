import httpx
from ..core.config import settings


def notify_denial(user_id: str, user_name: str, room_id: str, reason: str, timestamp: str) -> None:
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return
    text = (
        f"🚫 *Zugang verweigert*\n"
        f"👤 {user_name} (`{user_id}`)\n"
        f"🚪 Raum: `{room_id}`\n"
        f"❌ Grund: {reason}\n"
        f"🕐 {timestamp}"
    )
    try:
        httpx.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            timeout=5,
        )
    except Exception:
        pass
