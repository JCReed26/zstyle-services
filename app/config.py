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
        - DATABASE_URL: PostgreSQL connection string (required, no SQLite support)
    
    Optional variables with defaults:
        - PORT: Server port (default: 8000)
        - ENV: Environment (default: "development")
        - OPENMEMORY_URL: OpenMemory service URL (default: "http://openmemory:8080")
        - OPENMEMORY_API_KEY: OpenMemory API key (default: None)
        - TELEGRAM_WEBHOOK_URL: Telegram webhook URL (default: None)
        - TELEGRAM_WEBHOOK_SECRET: Telegram webhook secret (default: None)
        - TICKTICK_CLIENT_ID: TickTick OAuth client ID (default: None)
        - TICKTICK_CLIENT_SECRET: TickTick OAuth client secret (default: None)
        - GOOGLE_CLIENT_ID: Google OAuth client ID (default: None)
        - GOOGLE_CLIENT_SECRET: Google OAuth client secret (default: None)
        - OAUTH_BASE_URL: Base URL for OAuth redirects (default: None)
    """
    
    # Required fields
    GOOGLE_API_KEY: str
    TELEGRAM_BOT_TOKEN: str
    SECRET_KEY: str
    DATABASE_URL: str  # PostgreSQL connection string (required)
                       # Format: postgresql://user:password@host:port/database
                       # Example: postgresql://postgres:password@db:5432/zstyle_db
    
    # Optional fields with defaults
    PORT: int = 8000
    ENV: str = "development"
    OPENMEMORY_URL: str = "http://openmemory:8080"
    OPENMEMORY_API_KEY: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = None
    TICKTICK_CLIENT_ID: Optional[str] = None
    TICKTICK_CLIENT_SECRET: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    OAUTH_BASE_URL: Optional[str] = None  # Base URL for OAuth redirects (e.g., "https://api.example.com")
    
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
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate that DATABASE_URL is a PostgreSQL connection string."""
        if not v:
            raise ValueError("DATABASE_URL is required")
        if not v.startswith("postgresql://"):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL connection string. "
                "SQLite is not supported. Format: postgresql://user:password@host:port/database"
            )
        return v
    
    @field_validator("OAUTH_BASE_URL")
    @classmethod
    def validate_oauth_base_url(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate that OAUTH_BASE_URL is HTTPS if provided.
        
        Telegram Mini Apps require HTTPS. For development, use ngrok.
        """
        if v:
            v = v.strip().rstrip('/')
            if not v.startswith("https://"):
                raise ValueError(
                    "OAUTH_BASE_URL must be HTTPS. "
                    "For development, use ngrok: https://your-domain.ngrok.io"
                )
        return v
    
    def has_database(self) -> bool:
        """
        Check if database configuration is present and valid.
        
        Returns:
            True if DATABASE_URL is set and valid, False otherwise
        """
        try:
            return bool(self.DATABASE_URL)
        except Exception:
            return False


# Create singleton instance (lazy-loaded for testability)
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the singleton Settings instance.
    
    Lazy-loads the instance on first access to allow tests to set
    environment variables before the singleton is created.
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def reset_settings() -> None:
    """
    Reset the singleton Settings instance.
    
    This is useful for testing when you need to reload settings
    with different environment variables.
    """
    global _settings_instance
    _settings_instance = None


# Create singleton instance for backward compatibility
settings = get_settings()
