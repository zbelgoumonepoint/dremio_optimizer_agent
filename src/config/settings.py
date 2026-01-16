"""Application settings and configuration."""
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    cors_origins: str = "*"

    # Dremio
    dremio_url: str = "http://localhost:9047"
    dremio_username: str = "admin"
    dremio_password: str = ""
    dremio_token: str = ""  # Optional: Use pre-generated personal access token instead of username/password
    dremio_project_id: str = ""  # Required for Dremio Cloud
    dremio_verify_ssl: bool = True  # Set to False to disable SSL verification (not recommended for production)

    # Database
    database_url: str = "postgresql://localhost/dremio_optimizer"

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.1

    # Observability
    log_level: str = "INFO"
    tempo_endpoint: str = "http://localhost:4317"
    loki_endpoint: str = "http://localhost:3100"

    # Collection
    collection_interval_minutes: int = 30
    collection_lookback_hours: int = 24

    # Analysis
    baseline_lookback_days: int = 30
    min_baseline_samples: int = 5
    regression_threshold_pct: float = 50.0

    # Recommendations
    min_estimated_improvement_pct: float = 20.0

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
