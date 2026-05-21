from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path
import json

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"

class Settings(BaseSettings):
    # App
    PROJEKT_NAME: str = "Workmate Access"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql://workmate:password@localhost:5432/workmate_access"

    # Keycloak
    KEYCLOAK_URL: str = "https://login.intern.phudevelopement.xyz"
    KEYCLOAK_INTERNAL_URL: str = ""  # Docker-interner Hostname, z.B. http://keycloak:8080
    KEYCLOAK_CLIENT_ID: str = ""
    KEYCLOAK_CLIENT_SECRET: str = ""
    KEYCLOAK_REALM: str = "kit"
    # Keycloak Admin Service Account (client_credentials)
    KEYCLOAK_ADMIN_CLIENT_ID: str = "workmate-admin"
    KEYCLOAK_ADMIN_CLIENT_SECRET: str = ""

    @property
    def keycloak_base_url(self) -> str:
        return self.KEYCLOAK_INTERNAL_URL or self.KEYCLOAK_URL

    # API
    API_V1_STR: str = "/api/v1"

    # CORS
    CORS_ORIGINS: str = '["*"]'

    # Device Authentication (ESP32 / NFC Reader)
    DEVICE_API_KEY: str = ""  # Leer = deaktiviert; sonst X-Device-Token Header prüfen

    # Access Control
    DEFAULT_LOCK_TIMEOUT: int = 5
    MAX_FAILED_ATTEMPTS: int = 3
    LOCKOUT_DURATION: int = 300

    # Zigbee2MQTT (optional — leer lassen wenn nicht genutzt)
    ZIGBEE2MQTT_HOST: str = ""      # z.B. "192.168.178.50"
    ZIGBEE2MQTT_PORT: int = 1883
    ZIGBEE2MQTT_USER: str = ""
    ZIGBEE2MQTT_PASSWORD: str = ""
    ZIGBEE_UNLOCK_PAYLOAD: str = '{"state":"UNLOCK"}'
    ZIGBEE_LOCK_PAYLOAD:   str = '{"state":"LOCK"}'
    ZIGBEE_RELOCK_DELAY:   int = 5  # Sekunden bis automatisches Zurückschließen

    # sent.dm OTP
    SENT_DM_API_KEY: str = ""
    SENT_DM_CUSTOMER_ID: str = ""
    SENT_DM_OTP_TEMPLATE_ID: str = "otp"
    SENT_DM_SANDBOX: bool = False

    # OTP Rate-Limiting
    OTP_SEND_MAX_PER_HOUR: int = 5
    OTP_VERIFY_MAX_ATTEMPTS: int = 10
    OTP_VERIFY_WINDOW_MINUTES: int = 15

    # Yubico OTP (YubiCloud)
    YUBICO_CLIENT_ID: str = ""
    YUBICO_SECRET_KEY: str = ""  # Base64-kodierter HMAC-Schlüssel von https://upgrade.yubico.com/getapikey/

    # Telegram-Benachrichtigungen (optional)
    TELEGRAM_BOT_TOKEN: str = ""   # @BotFather → /newbot
    TELEGRAM_CHAT_ID: str = ""     # Chat-ID des Admins oder einer Gruppe

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string to list — handles both '*' and '["*"]' formats"""
        raw = self.CORS_ORIGINS.strip()
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else [str(parsed)]
        except json.JSONDecodeError:
            return [raw]

settings = Settings()
