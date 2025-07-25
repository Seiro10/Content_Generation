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

    # LLM Configuration (Claude) - Optionnel pour permettre à Flower de démarrer
    anthropic_api_key: Optional[str] = None
    claude_model: str = "claude-3-5-sonnet-20241022"

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

    # AWS S3 Configuration
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_default_region: str = "eu-west-3"
    s3_bucket_name: str = "matrix-reloaded-rss-img-bucket"

    # SAM (Segment Anything Model) Configuration
    sam_enabled: bool = True
    sam_model_type: str = "vit_b"  # vit_b, vit_l, vit_h
    sam_checkpoint_path: Optional[str] = None  # Chemin vers le checkpoint SAM
    sam_device: str = "cpu"  # cpu ou cuda
    sam_fallback_to_opencv: bool = True  # Utiliser OpenCV si SAM échoue

    # Image Processing Configuration
    crop_method: str = "intelligent"  # "intelligent", "simple", "opencv_only"
    image_quality: int = 90  # Qualité JPEG (1-100)
    max_image_size: int = 5 * 1024 * 1024  # 5MB max

    # Timeouts pour le processing d'images
    sam_timeout: int = 30  # Timeout SAM en secondes
    opencv_timeout: int = 15  # Timeout OpenCV en secondes

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instance globale des settings
settings = Settings()