import logging
import json
from app.agents.base_agent import BaseFormatter
from app.models.base import PlatformType, ContentType
from app.models.content import PlatformContentConfig, generate_images
from app.models.accounts import AccountConfig
from app.models.platforms import InstagramPostOutput, InstagramStoryOutput, InstagramCarouselOutput
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class InstagramFormatter(BaseFormatter):
    """Formatter spécialisé pour Instagram (post, story, carousel)"""

    def __init__(self):
        super().__init__(PlatformType.INSTAGRAM)

    async def format_content(
            self,
            content: str,
            config: PlatformContentConfig,
            account: AccountConfig
    ) -> any:
        """Formate le contenu pour Instagram selon le type"""

        logger.info(f"📸 Formatage Instagram {config.content_type} pour compte: {account.account_name}")

        if config.content_type == ContentType.POST:
            return await self._format_post(content, config, account)
        elif config.content_type == ContentType.STORY:
            return await self._format_story(content, config, account)
        elif config.content_type == ContentType.CAROUSEL:
            return await self._format_carousel(content, config, account)
        else:
            raise ValueError(f"Type de contenu Instagram non supporté: {config.content_type}")

    async def _format_post(
            self,
            content: str,
            config: PlatformContentConfig,
            account: AccountConfig
    ) -> InstagramPostOutput:
        """Formate un post Instagram classique"""

        constraints = {
            "tone": "décontracté avec émojis",
            "hashtags": config.hashtags,
            "mention": config.mentions[0] if config.mentions else None,
            "account": account.account_name
        }

        formatted_text = await llm_service.format_content_for_platform(
            content, "instagram", "post", constraints
        )

        result = InstagramPostOutput(
            legende=formatted_text,
            hashtags=config.hashtags
        )

        logger.info(f"✅ Post Instagram formaté: {formatted_text[:50]}...")
        return result

    async def _format_story(
            self,
            content: str,
            config: PlatformContentConfig,
            account: AccountConfig
    ) -> InstagramStoryOutput:
        """Formate une story Instagram"""

        constraints = {
            "max_length": "50 caractères maximum",
            "style": "très court et percutant",
            "lien_sticker": config.lien_sticker,
            "account": account.account_name
        }

        formatted_text = await llm_service.format_content_for_platform(
            content, "instagram", "story", constraints
        )

        result = InstagramStoryOutput(
            texte_story=formatted_text[:50]  # Sécurité longueur
        )

        logger.info(f"✅ Story Instagram formatée: {formatted_text}")
        return result

    async def _format_carousel(
            self,
            content: str,
            config: PlatformContentConfig,
            account: AccountConfig
    ) -> InstagramCarouselOutput:
        """Formate un carrousel Instagram avec gestion des images"""

        # Gestion des images
        images_urls = config.images_urls
        images_generated = False

        if not images_urls:
            # Pas d'images fournies -> génération automatique
            nb_slides = config.nb_slides or 5
            images_urls = generate_images(nb_slides, content[:100])
            images_generated = True
            logger.info(f"Images générées automatiquement: {len(images_urls)} images")
        else:
            logger.info(f"Utilisation des images fournies: {len(images_urls)} images")

        constraints = {
            "nb_slides": config.nb_slides or len(images_urls),
            "titre_carousel": config.titre_carousel,
            "hashtags": config.hashtags,
            "style": "découper en points clés",
            "account": account.account_name,
            "images_provided": not images_generated
        }

        # Prompt spécifique pour carrousel
        system_prompt = f"""Tu es un expert en carrousels Instagram pour le compte {account.account_name}. 
        Découpe le contenu en {constraints['nb_slides']} slides maximum.

        IMPORTANT: Réponds UNIQUEMENT avec un JSON valide contenant:
        {{
            "slides": ["Texte slide 1", "Texte slide 2", ...],
            "legende": "Légende pour le carrousel avec émojis et hashtags"
        }}

        Chaque slide doit être courte et impactante (1-2 phrases max).
        La légende doit inciter à swiper et inclure les hashtags.
        {"Images fournies par l'utilisateur." if not images_generated else "Images générées automatiquement."}
        """

        formatted_json = await llm_service.generate_content(content, system_prompt)

        try:
            parsed = json.loads(formatted_json)
            result = InstagramCarouselOutput(
                slides=parsed["slides"][:config.nb_slides or 5],
                legende=parsed["legende"],
                hashtags=config.hashtags,
                images_urls=images_urls,
                images_generated=images_generated
            )

            logger.info(f"✅ Carrousel Instagram formaté: {len(result.slides)} slides")
            return result

        except Exception as e:
            logger.warning(f"Erreur parsing JSON carrousel: {e}. Utilisation du fallback.")
            # Fallback si le JSON n'est pas valide
            slides = [f"Point {i + 1}: {content[:100]}..." for i in range(config.nb_slides or 3)]
            result = InstagramCarouselOutput(
                slides=slides,
                legende=f"📱 Swipe pour découvrir → {' '.join(config.hashtags or [])}",
                hashtags=config.hashtags,
                images_urls=images_urls,
                images_generated=images_generated
            )

            logger.info(f"✅ Carrousel Instagram formaté (fallback): {len(result.slides)} slides")
            return result


# Instance globale
instagram_formatter = InstagramFormatter()