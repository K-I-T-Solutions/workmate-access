import threading
import time
import json
from ..core.config import settings

_client = None


def _get_client():
    global _client
    if not settings.ZIGBEE2MQTT_HOST:
        return None
    if _client and _client.is_connected():
        return _client
    try:
        import paho.mqtt.client as mqtt
        c = mqtt.Client()
        if settings.ZIGBEE2MQTT_USER:
            c.username_pw_set(settings.ZIGBEE2MQTT_USER, settings.ZIGBEE2MQTT_PASSWORD)
        c.connect(settings.ZIGBEE2MQTT_HOST, settings.ZIGBEE2MQTT_PORT, keepalive=30)
        c.loop_start()
        _client = c
        return c
    except Exception as e:
        print(f"[Zigbee] MQTT Verbindung fehlgeschlagen: {e}")
        return None


def unlock(zigbee_lock_id: str) -> bool:
    """Sendet UNLOCK-Befehl und nach ZIGBEE_RELOCK_DELAY Sekunden LOCK."""
    c = _get_client()
    if not c:
        return False
    topic = f"zigbee2mqtt/{zigbee_lock_id}/set"
    try:
        c.publish(topic, settings.ZIGBEE_UNLOCK_PAYLOAD)
        if settings.ZIGBEE_RELOCK_DELAY > 0:
            threading.Timer(
                settings.ZIGBEE_RELOCK_DELAY,
                lambda: c.publish(topic, settings.ZIGBEE_LOCK_PAYLOAD)
            ).start()
        return True
    except Exception as e:
        print(f"[Zigbee] Publish fehlgeschlagen: {e}")
        return False
