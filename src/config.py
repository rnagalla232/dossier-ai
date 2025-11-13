"""
Configuration management for Dossier AI application.
Handles environment variables and application settings.
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    snowflake_api_key: str = Field(default="", env="SNOWFLAKE_API_KEY")
    
    # Database Configuration
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        env="MONGODB_URI"
    )
    mongodb_database: str = Field(
        default="dossier_ai",
        env="MONGODB_DATABASE"
    )
    
    # Qdrant Configuration
    qdrant_url: str = Field(
        default="http://localhost:6333",
        env="QDRANT_URL"
    )
    qdrant_api_key: str = Field(default="", env="QDRANT_API_KEY")
    
    # Snowflake Configuration
    snowflake_base_url: str = Field(
        default="https://RQNIACH-ZF07937.snowflakecomputing.com/api/v2/cortex/v1",
        env="SNOWFLAKE_BASE_URL"
    )
    snowflake_model: str = Field(
        default="llama3.1-70b",
        env="SNOWFLAKE_MODEL"
    )
    
    # CORS Settings
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]
    
    # Application Settings
    app_name: str = "Dossier AI"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Worker Settings
    worker_poll_interval: int = Field(default=2, env="WORKER_POLL_INTERVAL")
    
    # LLM Settings
    max_completion_tokens: int = Field(default=2000, env="MAX_COMPLETION_TOKENS")
    temperature: float = Field(default=0.3, env="TEMPERATURE")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings

