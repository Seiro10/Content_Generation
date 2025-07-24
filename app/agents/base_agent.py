from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from app.models.base import PlatformType
from app.models.accounts import SiteWeb, AccountConfig
from app.models.content import PlatformContentConfig

logger = logging.getLogger(__name__)


class BaseFormatter(ABC):
    """Classe de base pour tous les formatters"""

    def __init__(self, platform: PlatformType):
        self.platform = platform

    @abstractmethod
    async def format_content(
            self,
            content: str,
            config: PlatformContentConfig,
            account: AccountConfig
    ) -> Any:
        """Formate le contenu pour la plateforme"""
        pass


class BasePublisher(ABC):
    """Classe de base pour tous les publishers"""

    def __init__(self, platform: PlatformType):
        self.platform = platform

    @abstractmethod
    async def publish_content(
            self,
            formatted_content: Any,
            site_web: SiteWeb,
            account: AccountConfig
    ) -> Dict[str, Any]:
        """Publie le contenu formaté"""
        pass

    def _create_success_result(
            self,
            post_id: str,
            post_url: str,
            additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Crée un résultat de publication réussi"""
        from datetime import datetime

        result = {
            "status": "success",
            "post_id": post_id,
            "post_url": post_url,
            "platform": self.platform.value,
            "published_at": datetime.now().isoformat()
        }

        if additional_data:
            result.update(additional_data)

        return result

    def _create_error_result(self, error: str) -> Dict[str, Any]:
        """Crée un résultat d'erreur"""
        return {
            "status": "failed",
            "platform": self.platform.value,
            "error": error
        }