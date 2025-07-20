from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuration de l'application"""

    # API Configuration
    api_title: str = "Social Media Publisher"
    api_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8090
    debug: bool = False

    # LLM Configuration (Claude)
    anthropic_api_key: str
    claude_model: str = "claude-3-sonnet-20240229"

    # Celery Configuration - DB 1 pour éviter conflits
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Social Media APIs
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_token_secret: Optional[str] = None

    facebook_app_id: Optional[str] = None
    facebook_app_secret: Optional[str] = None
    facebook_access_token: Optional[str] = None

    linkedin_client_id: Optional[str] = None
    linkedin_client_secret: Optional[str] = None
    linkedin_access_token: Optional[str] = None

    instagram_access_token: Optional[str] = None
    instagram_business_account_id: Optional[str] = None

    # Task Configuration
    max_retry_attempts: int = 3
    task_timeout: int = 300  # 5 minutes

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instance globale des settings
settings = Settings()