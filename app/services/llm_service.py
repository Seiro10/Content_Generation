from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Optional, Dict, Any
import logging
from app.config.settings import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service pour interagir avec Claude LLM"""

    def __init__(self):
        if not settings.anthropic_api_key:
            logger.warning("ANTHROPIC_API_KEY not provided - LLM service will be disabled")
            self.llm = None
        else:
            try:
                self.llm = ChatAnthropic(
                    anthropic_api_key=settings.anthropic_api_key,
                    model=settings.claude_model,
                    temperature=0.7,
                    max_tokens=1000
                )
                logger.info("LLM service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize LLM service: {e}")
                self.llm = None

    async def generate_content(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Génère du contenu avec Claude"""
        if not self.llm:
            logger.warning("LLM service not available - returning placeholder content")
            return f"[PLACEHOLDER CONTENT] {prompt[:100]}..."

        try:
            messages = []

            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))

            messages.append(HumanMessage(content=prompt))

            response = await self.llm.ainvoke(messages)
            return response.content.strip()

        except Exception as e:
            logger.error(f"Erreur lors de la génération de contenu: {e}")
            # Retourner un contenu de fallback au lieu de lever une exception
            return f"[ERROR - Using fallback] {prompt[:200]}..."

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
            logger.warning(f"Pas de prompt défini pour {platform}/{content_type} - using generic formatting")
            # Fallback générique
            if platform == "twitter":
                return content[:270] + "..." if len(content) > 270 else content
            elif platform == "instagram" and content_type == "story":
                return content[:45] + "..." if len(content) > 45 else content
            else:
                return content

        # Ajouter les contraintes au prompt si fournies
        if constraints:
            constraint_text = "\n".join([f"- {k}: {v}" for k, v in constraints.items()])
            system_prompt += f"\n\nContraintes spécifiques:\n{constraint_text}"

        return await self.generate_content(content, system_prompt)


# Instance globale du service LLM
llm_service = LLMService()