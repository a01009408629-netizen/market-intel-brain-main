from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AppConfig:
    ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = ENV == "development"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///brain.db")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


config = AppConfig()
