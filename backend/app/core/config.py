"""Application configuration using pydantic-settings."""
from dotenv import load_dotenv

load_dotenv()

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import ClassVar


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # API Keys
    DEEPSEEK_API_KEY: str = ""
    EXCHANGE_RATE_API_KEY: str = ""

    # Database
    DATABASE_URL: str = "data/africa_zero.db"

    # Security
    JWT_SECRET: str = ""

    # CORS
    # In production, set CORS_ORIGINS env var to:
    # https://africa.zxqconsulting.com,https://zxqconsulting.com,https://www.zxqconsulting.com
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8000,https://africa.zxqconsulting.com,https://zxqconsulting.com"

    # Admin
    ADMIN_EMAIL: str = "hello@africa-zero.com"

    # Debug
    DEBUG: bool = False

    # Exchange rates
    EXCHANGE_RATE_FALLBACK: float = 7.25

    # Required secrets for production
    REQUIRED_SECRETS: ClassVar[list[str]] = ["JWT_SECRET"]

    @property
    def cors_origins_list(self) -> list[str]:
        """Split CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def validate_secrets(self) -> None:
        """Validate that required secrets are set. Only enforced in production."""
        if self.DEBUG:
            return

        missing = [key for key in self.REQUIRED_SECRETS if not getattr(self, key, "")]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Set these in your .env file or environment."
            )


# Global settings instance
settings = Settings()
