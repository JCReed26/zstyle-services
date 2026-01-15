"""
Core Configuration Module

Centralized configuration management using pydantic-settings.
Provides type-safe, validated environment variable access.
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Required variables:
        - GOOGLE_API_KEY: Google API key for Gemini models
        - TELEGRAM_BOT_TOKEN: Telegram bot token
        - SECRET_KEY: Secret key for encryption (must be 32+ characters)
    
    Optional variables with defaults:
        - PORT: Server port (default: 8000)
        - ENV: Environment (default: "development")
        - DATABASE_URL: Database connection string (default: None)
        - OPENMEMORY_URL: OpenMemory service URL (default: "http://openmemory:8080")
        - OPENMEMORY_API_KEY: OpenMemory API key (default: None)
        - TELEGRAM_WEBHOOK_URL: Telegram webhook URL (default: None)
        - TELEGRAM_WEBHOOK_SECRET: Telegram webhook secret (default: None)
        - TICKTICK_CLIENT_ID: TickTick OAuth client ID (default: None)
        - TICKTICK_CLIENT_SECRET: TickTick OAuth client secret (default: None)
    """
    
    # Required fields
    GOOGLE_API_KEY: str
    TELEGRAM_BOT_TOKEN: str
    SECRET_KEY: str
    
    # Optional fields with defaults
    PORT: int = 8000
    ENV: str = "development"
    DATABASE_URL: Optional[str] = None
    OPENMEMORY_URL: str = "http://openmemory:8080"
    OPENMEMORY_API_KEY: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = None
    TICKTICK_CLIENT_ID: Optional[str] = None
    TICKTICK_CLIENT_SECRET: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Ignore extra environment variables
    )
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate that SECRET_KEY is at least 32 characters long."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v


# Create singleton instance
settings = Settings()
