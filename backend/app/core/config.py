from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str = "changeme"
    GEMINI_API_KEY: str | None = None
    REDIS_URL: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def require_gemini_api_key() -> str:
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is required for AI and knowledge-base operations")
    return settings.GEMINI_API_KEY


settings = Settings()
