from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import sys


class Settings(BaseSettings):
    DATABASE_URL: str
    # Safe-ish dev fallback so local startup and tests do not crash when the
    # secret is omitted. Override this in any real deployment.
    JWT_SECRET: str = "dev-only-jwt-secret-change-me-32chars"
    GEMINI_API_KEY: str | None = None
    REDIS_URL: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("JWT_SECRET")
    def jwt_must_be_strong(cls, v: str):
        if not v or len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return v

    @field_validator("DATABASE_URL")
    def db_url_must_be_valid(cls, v: str):
        if not v.startswith(("postgresql", "sqlite", "mysql")):
            raise ValueError("DATABASE_URL must be a valid DB url (postgresql|sqlite|mysql)")
        return v


def require_gemini_api_key() -> str:
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is required for AI and knowledge-base operations")
    return settings.GEMINI_API_KEY


try:
    settings = Settings()
except Exception as e:
    # During inspection or build, environment variables might be missing.
    # Log the error but don't exit, allowing the app instance to be inspected if possible.
    print(f"Configuration warning: {e}")
    # Provide a dummy settings object for inspection time
    class DummySettings:
        DATABASE_URL = "sqlite+aiosqlite:///:memory:"
        JWT_SECRET = "dev-only-jwt-secret-change-me-32chars"
        GEMINI_API_KEY = None
        REDIS_URL = None
    settings = DummySettings() # type: ignore
