from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json

class Settings(BaseSettings):
    # App
    PROJEKT_NAME: str = "Workmate Access"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql://workmate:password@localhost:5432/workmate_access"

    # Zitadel
    ZITADEL_URL: str = "http://localhost:8080"
    ZITADEL_CLIENT_ID: str = ""
    ZITADEL_CLIENT_SECRET: str = ""
    ZITADEL_REALM: str = "master"

    # API
    API_V1_STR: str = "/api/v1"

    # CORS
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:8000"]'

    # Access Control
    DEFAULT_LOCK_TIMEOUT: int = 5
    MAX_FAILED_ATTEMPTS: int = 3
    LOCKOUT_DURATION: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string to list"""
        return json.loads(self.CORS_ORIGINS)

settings = Settings()