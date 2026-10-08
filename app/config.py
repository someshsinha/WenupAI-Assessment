from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Document Intake Assistant"
    app_env: Literal["development", "test", "production"] = "development"
    port: int = 8000
    host: str = "0.0.0.0"

    # LLM Settings
    llm_provider: Literal["mock", "gemini"] = "mock"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash"

    @property
    def is_llm_configured(self) -> bool:
        if self.llm_provider == "mock":
            return True
        if self.llm_provider == "gemini":
            return bool(self.gemini_api_key)
        return False


settings = Settings()
