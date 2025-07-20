from celery import current_task
from app.services.celery_app import celery_app
from app.services.llm_service import llm_service
from app.models.content import PlatformContentConfig
from app.models.accounts import SiteWeb
from app.models.base import PlatformType
from app.models.platforms import *
import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='content_formatting.format_for_platform')
def format_for_platform_task(
        self,
        content: str,
        site_web: str,
        platform: str,
        content_type: str,
        config_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Tâche Celery pour formater du contenu pour une plateforme spécifique
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': f'Starting formatting for {platform}_{content_type}'})

        logger.info(f"Formatting content for {platform}_{content_type} - Task {self.request.id}")

        # Reconstituer la configuration
        config = PlatformContentConfig.parse_obj(config_data)

        # Formater selon la plateforme (synchrone)
        if platform == 'twitter':
            result = _format_twitter_content_sync(content, config)
        elif platform == 'facebook':
            result = _format_facebook_content_sync(content, config)
        elif platform == 'linkedin':
            result = _format_linkedin_content_sync(content, config)
        elif platform == 'instagram':
            if content_type == 'post':
                result = _format_instagram_post_sync(content, config)
            elif content_type == 'story':
                result = _format_instagram_story_sync(content, config)
            elif content_type == 'carousel':
                result = _format_instagram_carousel_sync(content, config)
            else:
                raise ValueError(f"Unsupported Instagram content type: {content_type}")
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        logger.info(f"Content formatting completed for {platform}_{content_type} - Task {self.request.id}")

        return {
            'task_id': self.request.id,
            'platform': platform,
            'content_type': content_type,
            'site_web': site_web,
            'status': 'completed',
            'formatted_content': result.dict() if hasattr(result, 'dict') else result
        }

    except Exception as e:
        logger.error(f"Error in formatting task {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': f'{platform}_{content_type} formatting failed'}
        )
        raise


def _format_twitter_content_sync(content: str, config: PlatformContentConfig) -> TwitterPostOutput:
    """Format content for Twitter (synchronous)"""
    constraints = {
        "max_length": "280 caractères",
        "hashtags": config.hashtags,
        "mentions": config.mentions
    }

    # Utiliser asyncio.run pour exécuter la fonction async de manière synchrone
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        formatted = loop.run_until_complete(
            llm_service.format_content_for_platform(content, "twitter", "post", constraints)
        )
    finally:
        loop.close()

    return TwitterPostOutput(tweet=formatted)


def _format_facebook_content_sync(content: str, config: PlatformContentConfig) -> FacebookPostOutput:
    """Format content for Facebook (synchronous)"""
    constraints = {
        "lien_source": config.lien_source,
        "hashtags": config.hashtags
    }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        formatted = loop.run_until_complete(
            llm_service.format_content_for_platform(content, "facebook", "post", constraints)
        )
    finally:
        loop.close()

    return FacebookPostOutput(message=formatted)


def _format_linkedin_content_sync(content: str, config: PlatformContentConfig) -> LinkedInPostOutput:
    """Format content for LinkedIn (synchronous)"""
    constraints = {
        "tone": "professionnel",
        "lien_source": config.lien_source,
        "hashtags": config.hashtags
    }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        formatted = loop.run_until_complete(
            llm_service.format_content_for_platform(content, "linkedin", "post", constraints)
        )
    finally:
        loop.close()

    return LinkedInPostOutput(contenu=formatted)


def _format_instagram_post_sync(content: str, config: PlatformContentConfig) -> InstagramPostOutput:
    """Format content for Instagram Post (synchronous)"""
    constraints = {
        "tone": "décontracté avec émojis",
        "hashtags": config.hashtags,
        "mention": config.mentions[0] if config.mentions else None
    }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        formatted = loop.run_until_complete(
            llm_service.format_content_for_platform(content, "instagram", "post", constraints)
        )
    finally:
        loop.close()

    return InstagramPostOutput(legende=formatted, hashtags=config.hashtags)


def _format_instagram_story_sync(content: str, config: PlatformContentConfig) -> InstagramStoryOutput:
    """Format content for Instagram Story (synchronous)"""
    constraints = {
        "max_length": "50 caractères maximum",
        "style": "très court et percutant",
        "lien_sticker": config.lien_sticker
    }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        formatted = loop.run_until_complete(
            llm_service.format_content_for_platform(content, "instagram", "story", constraints)
        )
    finally:
        loop.close()

    return InstagramStoryOutput(texte_story=formatted[:50])


def _format_instagram_carousel_sync(content: str, config: PlatformContentConfig) -> InstagramCarouselOutput:
    """Format content for Instagram Carousel (synchronous)"""

    # Gestion des images
    images_urls = config.images_urls
    images_generated = False

    if not images_urls:
        # Pas d'images fournies -> génération automatique
        from app.services.tasks.image_generation import generate_images_task

        nb_slides = config.nb_slides or 5
        image_task = generate_images_task.delay(content[:100], nb_slides)
        image_result = image_task.get()  # Attendre le résultat

        images_urls = image_result['images_urls']
        images_generated = True
        logger.info(f"Images générées automatiquement pour le carrousel: {len(images_urls)} images")
    else:
        logger.info(f"Utilisation des images fournies: {len(images_urls)} images")

    constraints = {
        "nb_slides": config.nb_slides or len(images_urls),
        "titre_carousel": config.titre_carousel,
        "hashtags": config.hashtags,
        "style": "découper en points clés",
        "images_provided": not images_generated
    }

    # Prompt spécifique pour carrousel
    system_prompt = f"""Tu es un expert en carrousels Instagram. 
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

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        formatted_json = loop.run_until_complete(
            llm_service.generate_content(content, system_prompt)
        )
    finally:
        loop.close()

    try:
        import json
        parsed = json.loads(formatted_json)
        return InstagramCarouselOutput(
            slides=parsed["slides"][:config.nb_slides or 5],
            legende=parsed["legende"],
            hashtags=config.hashtags,
            images_urls=images_urls,
            images_generated=images_generated
        )
    except Exception as e:
        logger.warning(f"Erreur parsing JSON carrousel: {e}. Utilisation du fallback.")
        # Fallback si le JSON n'est pas valide
        slides = [f"Point {i + 1}: {content[:100]}..." for i in range(config.nb_slides or 3)]
        return InstagramCarouselOutput(
            slides=slides,
            legende=f"📱 Swipe pour découvrir → {' '.join(config.hashtags or [])}",
            hashtags=config.hashtags,
            images_urls=images_urls,
            images_generated=images_generated
        )


@celery_app.task(bind=True, name='content_formatting.format_multiplatform')
def format_multiplatform_task(
        self,
        content: str,
        site_web: str,
        platforms_config: list
) -> Dict[str, Any]:
    """
    Tâche Celery pour formater du contenu pour plusieurs plateformes en parallèle
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': 'Starting multi-platform formatting'})

        logger.info(f"Starting multi-platform formatting for {site_web} - Task {self.request.id}")

        formatting_results = {}

        # Formater pour chaque configuration plateforme
        for config_data in platforms_config:
            try:
                config = PlatformContentConfig.parse_obj(config_data)
                platform = config.platform.value
                content_type = config.content_type.value

                config_key = f"{platform}_{content_type}"

                self.update_state(
                    state='PROGRESS',
                    meta={'step': f'Formatting for {config_key}'}
                )

                # Lancer la tâche de formatage
                result = format_for_platform_task.delay(
                    content,
                    site_web,
                    platform,
                    content_type,
                    config_data
                )

                formatting_results[config_key] = {
                    'task_id': result.id,
                    'status': 'submitted'
                }

            except Exception as e:
                logger.error(f"Error formatting for {config_key}: {str(e)}")
                formatting_results[config_key] = {
                    'status': 'failed',
                    'error': str(e)
                }

        logger.info(f"Multi-platform formatting tasks submitted for {site_web} - Task {self.request.id}")

        return {
            'site_web': site_web,
            'task_id': self.request.id,
            'formatting_results': formatting_results,
            'total_platforms': len(platforms_config),
            'status': 'submitted'
        }

    except Exception as e:
        logger.error(f"Error in multi-platform formatting task {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': 'Multi-platform formatting failed'}
        )
        raise