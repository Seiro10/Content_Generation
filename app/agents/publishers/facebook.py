# app/agents/formatters/facebook.py
import logging
from app.agents.base_agent import BaseFormatter
from app.models.base import PlatformType
from app.models.content import PlatformContentConfig
from app.models.accounts import AccountConfig
from app.models.platforms import FacebookPostOutput
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class FacebookFormatter(BaseFormatter):
    def __init__(self):
        super().__init__(PlatformType.FACEBOOK)

    async def format_content(self, content: str, config: PlatformContentConfig,
                             account: AccountConfig) -> FacebookPostOutput:
        logger.info(f"📘 Formatage Facebook pour compte: {account.account_name}")

        constraints = {
            "lien_source": config.lien_source,
            "hashtags": config.hashtags,
            "account": account.account_name
        }

        formatted_text = await llm_service.format_content_for_platform(
            content, "facebook", "post", constraints
        )

        return FacebookPostOutput(message=formatted_text)


facebook_formatter = FacebookFormatter()

# app/agents/formatters/linkedin.py
import logging
from app.agents.base_agent import BaseFormatter
from app.models.base import PlatformType
from app.models.content import PlatformContentConfig
from app.models.accounts import AccountConfig
from app.models.platforms import LinkedInPostOutput
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class LinkedInFormatter(BaseFormatter):
    def __init__(self):
        super().__init__(PlatformType.LINKEDIN)

    async def format_content(self, content: str, config: PlatformContentConfig,
                             account: AccountConfig) -> LinkedInPostOutput:
        logger.info(f"💼 Formatage LinkedIn pour compte: {account.account_name}")

        constraints = {
            "tone": "professionnel",
            "lien_source": config.lien_source,
            "hashtags": config.hashtags,
            "account": account.account_name
        }

        formatted_text = await llm_service.format_content_for_platform(
            content, "linkedin", "post", constraints
        )

        return LinkedInPostOutput(contenu=formatted_text)


linkedin_formatter = LinkedInFormatter()