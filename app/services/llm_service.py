from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage
from typing import Optional, Dict, Any
import logging
from app.config.settings import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service pour interagir avec Claude LLM"""

    def __init__(self):
        self.llm = ChatAnthropic(
            anthropic_api_key=settings.anthropic_api_key,
            model=settings.claude_model,
            temperature=0.7,
            max_tokens=1000
        )

    async def generate_content(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Génère du contenu avec Claude"""
        try:
            messages = []

            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))

            messages.append(HumanMessage(content=prompt))

            response = await self.llm.ainvoke(messages)
            return response.content.strip()

        except Exception as e:
            logger.error(f"Erreur lors de la génération de contenu: {e}")
            raise

    async def format_content_for_platform(
            self,
            content: str,
            platform: str,
            content_type: str = "post",
            constraints: Optional[Dict[str, Any]] = None
    ) -> str:
        """Formate le contenu pour une plateforme spécifique"""

        # Prompts système par plateforme
        platform_prompts = {
            "twitter": {
                "post": """Tu es un expert en communication Twitter. Reformule le contenu donné en un tweet percutant de 280 caractères maximum. 
                Utilise un ton direct et engageant. Inclus des hashtags pertinents si approprié."""
            },
            "facebook": {
                "post": """Tu es un expert en communication Facebook. Reformule le contenu en un post Facebook engageant et convivial.
                Le ton doit être chaleureux et inciter à l'interaction. Quelques phrases maximum."""
            },
            "linkedin": {
                "post": """Tu es un expert en communication LinkedIn. Reformule le contenu en un post professionnel et informatif.
                Utilise un ton expert et inclus des insights pertinents. Structure le texte clairement."""
            },
            "instagram": {
                "post": """Tu es un expert en communication Instagram. Crée une légende accrocheuse avec émojis et hashtags pertinents.
                Ton décontracté et visuel. Commence par une phrase qui accroche l'attention.""",
                "story": """Tu es un expert en stories Instagram. Crée un texte très court (50 caractères max) pour une story.
                Sois percutant et direct. Utilise des émojis si approprié.""",
                "carousel": """Tu es un expert en carrousels Instagram. Découpe le contenu en points clés pour un carrousel.
                Crée des textes courts et impactants pour chaque slide."""
            }
        }

        system_prompt = platform_prompts.get(platform, {}).get(content_type, "")

        if not system_prompt:
            raise ValueError(f"Pas de prompt défini pour {platform}/{content_type}")

        # Ajouter les contraintes au prompt si fournies
        if constraints:
            constraint_text = "\n".join([f"- {k}: {v}" for k, v in constraints.items()])
            system_prompt += f"\n\nContraintes spécifiques:\n{constraint_text}"

        return await self.generate_content(content, system_prompt)


# Instance globale du service LLM
llm_service = LLMService()