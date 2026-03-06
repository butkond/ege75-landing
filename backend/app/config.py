from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os


class Settings(BaseSettings):
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str

    # Security
    API_SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:80"
    RATE_LIMIT_PER_MINUTE: int = 5
    RATE_LIMIT_PER_HOUR: int = 20

    # App
    APP_ENV: str = "production"
    APP_DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
