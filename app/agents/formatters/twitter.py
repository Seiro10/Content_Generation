import logging
from app.agents.base_agent import BaseFormatter
from app.models.base import PlatformType
from app.models.content import PlatformContentConfig
from app.models.accounts import AccountConfig
from app.models.platforms import TwitterPostOutput
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class TwitterFormatter(BaseFormatter):
    """Formatter spécialisé pour Twitter"""

    def __init__(self):
        super().__init__(PlatformType.TWITTER)

    async def format_content(
            self,
            content: str,
            config: PlatformContentConfig,
            account: AccountConfig
    ) -> TwitterPostOutput:
        """Formate le contenu pour Twitter avec support d'image S3"""

        logger.info(f"🐦 Formatage Twitter pour compte: {account.account_name}")

        constraints = {
            "max_length": "280 caractères",
            "hashtags": config.hashtags,
            "mentions": config.mentions,
            "account": account.account_name
        }

        # Appel au LLM pour le formatage
        formatted_text = await llm_service.format_content_for_platform(
            content, "twitter", "post", constraints
        )

        # Créer l'objet de sortie avec image S3 si présente
        twitter_output = TwitterPostOutput(
            tweet=formatted_text,
            image_s3_url=config.image_s3_url
        )

        # Log pour debug
        if config.image_s3_url:
            logger.info(f"🖼️ Image S3 incluse: {config.image_s3_url}")

        logger.info(f"✅ Contenu Twitter formaté: {formatted_text[:50]}...")

        return twitter_output


# Instance globale
twitter_formatter = TwitterFormatter()