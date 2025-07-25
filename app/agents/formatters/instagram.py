# app/agents/formatters/instagram.py - Updated with S3 support

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
    """Formatter spécialisé pour Instagram avec support S3"""

    def __init__(self):
        super().__init__(PlatformType.INSTAGRAM)

    def _is_s3_url(self, url: str) -> bool:
        """Vérifie si l'URL est une URL S3"""
        return url.startswith('s3://') if url else False

    def _separate_s3_and_regular_urls(self, urls_list):
        """Sépare les URLs S3 des URLs normales"""
        s3_urls = []
        regular_urls = []

        for url in urls_list or []:
            if self._is_s3_url(url):
                s3_urls.append(url)
            else:
                regular_urls.append(url)

        return s3_urls, regular_urls

    async def format_content(
            self,
            content: str,
            config: PlatformContentConfig,
            account: AccountConfig
    ) -> any:
        """Formate le contenu pour Instagram selon le type avec support S3"""

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
        """Formate un post Instagram avec support S3"""

        constraints = {
            "tone": "décontracté avec émojis",
            "hashtags": config.hashtags,
            "mention": config.mentions[0] if config.mentions else None,
            "account": account.account_name
        }

        formatted_text = await llm_service.format_content_for_platform(
            content, "instagram", "post", constraints
        )

        # Gérer l'image S3 ou normale
        image_s3_url = None
        if config.image_s3_url and self._is_s3_url(config.image_s3_url):
            image_s3_url = config.image_s3_url
            logger.info(f"🖼️ Image S3 détectée pour le post: {config.image_s3_url}")

        result = InstagramPostOutput(
            legende=formatted_text,
            hashtags=config.hashtags,
            image_s3_url=image_s3_url
        )

        logger.info(f"✅ Post Instagram formaté: {formatted_text[:50]}...")
        return result

    async def _format_story(
            self,
            content: str,
            config: PlatformContentConfig,
            account: AccountConfig
    ) -> InstagramStoryOutput:
        """Formate une story Instagram avec support S3"""

        constraints = {
            "max_length": "50 caractères maximum",
            "style": "très court et percutant",
            "lien_sticker": config.lien_sticker,
            "account": account.account_name
        }

        formatted_text = await llm_service.format_content_for_platform(
            content, "instagram", "story", constraints
        )

        # Gérer l'image S3 pour la story
        image_s3_url = None
        if config.image_s3_url and self._is_s3_url(config.image_s3_url):
            image_s3_url = config.image_s3_url
            logger.info(f"🖼️ Image S3 détectée pour la story: {config.image_s3_url}")

        result = InstagramStoryOutput(
            texte_story=formatted_text[:50],  # Sécurité longueur
            image_s3_url=image_s3_url
        )

        logger.info(f"✅ Story Instagram formatée: {formatted_text}")
        return result

    async def _format_carousel(
            self,
            content: str,
            config: PlatformContentConfig,
            account: AccountConfig
    ) -> InstagramCarouselOutput:
        """Formate un carrousel Instagram avec gestion S3 et URLs normales"""

        # Séparer les URLs S3 des URLs normales
        s3_urls, regular_urls = self._separate_s3_and_regular_urls(config.images_urls)

        # Déterminer la source des images
        images_urls = None
        images_s3_urls = None
        images_generated = False

        if s3_urls:
            # Priorité aux URLs S3
            images_s3_urls = s3_urls
            logger.info(f"🖼️ Images S3 détectées: {len(s3_urls)} images")
        elif regular_urls:
            # Utiliser les URLs normales
            images_urls = regular_urls
            logger.info(f"🔗 URLs normales détectées: {len(regular_urls)} images")
        else:
            # Pas d'images fournies -> génération automatique
            nb_slides = config.nb_slides or 5
            images_urls = generate_images(nb_slides, content[:100])
            images_generated = True
            logger.info(f"🎨 Images générées automatiquement: {len(images_urls)} images")

        constraints = {
            "nb_slides": config.nb_slides or len(images_s3_urls or images_urls or []),
            "titre_carousel": config.titre_carousel,
            "hashtags": config.hashtags,
            "style": "découper en points clés",
            "account": account.account_name,
            "images_provided": not images_generated,
            "images_source": "s3" if images_s3_urls else "urls" if images_urls else "generated"
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
        Source des images: {constraints['images_source']}
        """

        formatted_json = await llm_service.generate_content(content, system_prompt)

        try:
            parsed = json.loads(formatted_json)
            result = InstagramCarouselOutput(
                slides=parsed["slides"][:config.nb_slides or 5],
                legende=parsed["legende"],
                hashtags=config.hashtags,
                images_urls=images_urls,
                images_s3_urls=images_s3_urls,
                images_generated=images_generated
            )

            logger.info(f"✅ Carrousel Instagram formaté: {len(result.slides)} slides")
            if images_s3_urls:
                logger.info(f"📦 URLs S3: {len(images_s3_urls)} images")

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
                images_s3_urls=images_s3_urls,
                images_generated=images_generated
            )

            logger.info(f"✅ Carrousel Instagram formaté (fallback): {len(result.slides)} slides")
            return result


# Instance globale
instagram_formatter = InstagramFormatter()