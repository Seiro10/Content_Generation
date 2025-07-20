from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class PlatformType(str, Enum):
    """Types de plateformes supportées"""
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"


class ContentType(str, Enum):
    """Types de contenu"""
    POST = "post"
    STORY = "story"
    CAROUSEL = "carousel"


class TaskStatus(str, Enum):
    """Statuts des tâches"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseContentRequest(BaseModel):
    """Modèle de base pour les demandes de contenu"""
    texte_source: str = Field(..., description="Texte source à traiter")
    plateformes: List[PlatformType] = Field(..., description="Plateformes ciblées")
    hashtags: Optional[List[str]] = Field(default=None, description="Hashtags suggérés")
    mentions: Optional[List[str]] = Field(default=None, description="Mentions à inclure")
    lien_source: Optional[str] = Field(default=None, description="Lien vers la source")


class PublicationRequest(BaseContentRequest):
    """Demande de publication complète"""
    task_id: Optional[str] = Field(default=None, description="ID de la tâche")
    created_at: datetime = Field(default_factory=datetime.now)


class TaskResult(BaseModel):
    """Résultat d'une tâche"""
    task_id: str
    status: TaskStatus
    platform: PlatformType
    content_type: ContentType
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class PublicationResult(BaseModel):
    """Résultat global d'une publication multi-plateformes"""
    request_id: str
    status: TaskStatus
    platforms_results: List[TaskResult]
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None