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
    KEYCLOAK_CLIENT_ID: str = ""
    KEYCLOAK_CLIENT_SECRET: str = ""
    KEYCLOAK_REALM: str = "kit"

    # API
    API_V1_STR: str = "/api/v1"

    # CORS
    CORS_ORIGINS: str = '*'

    # Access Control
    DEFAULT_LOCK_TIMEOUT: int = 5
    MAX_FAILED_ATTEMPTS: int = 3
    LOCKOUT_DURATION: int = 300

    # sent.dm OTP
    SENT_DM_API_KEY: str = ""
    SENT_DM_CUSTOMER_ID: str = ""
    SENT_DM_OTP_TEMPLATE_ID: str = "otp"
    SENT_DM_SANDBOX: bool = False

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string to list"""
        return json.loads(self.CORS_ORIGINS)

settings = Settings()
