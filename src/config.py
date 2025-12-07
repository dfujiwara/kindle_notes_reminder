"""
Application configuration management using Pydantic Settings.

This module provides centralized configuration for the entire application,
loading values from environment variables and .env files with validation.
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file.

    Required Settings:
        openai_api_key: OpenAI API key for LLM and embedding generation

    Optional Settings (with defaults):
        database_url: PostgreSQL connection string
        db_echo: Whether to echo SQL queries (useful for debugging)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        cors_allow_origin: Production CORS origin (if None, uses dev defaults)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # API key - optional for testing, required for production use
    # Runtime validation happens in OpenAI client to allow test imports
    openai_api_key: SecretStr | None = None

    # Optional settings with sensible defaults
    database_url: str = "postgresql://postgres:postgres@localhost:5432/fastapi"
    db_echo: bool = True  # Set to False in production via DB_ECHO=false
    log_level: str = "INFO"
    cors_allow_origin: str | None = None


# Create global settings instance
# This will validate and fail-fast on import if required config is missing
settings = Settings()  # type: ignore[call-arg]
