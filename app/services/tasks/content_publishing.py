from celery import current_task
from app.services.celery_app import celery_app
from app.config.credentials import get_platform_credentials, CredentialsError
from app.models.accounts import SiteWeb
from app.models.base import PlatformType
from app.models.platforms import *
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='content_publishing.publish_to_twitter')
def publish_to_twitter_task(self, site_web: str, content_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tâche Celery pour publier sur Twitter
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': 'Starting Twitter publication'})

        site = SiteWeb(site_web)

        # Récupérer les credentials
        creds = get_platform_credentials(site, PlatformType.TWITTER)

        logger.info(f"Publishing to Twitter for {site_web} - Task {self.request.id}")

        # Extraire le contenu
        tweet_content = content_data.get('tweet', '')
        if not tweet_content:
            raise ValueError("No tweet content provided")

        self.update_state(state='PROGRESS', meta={'step': 'Calling Twitter API'})

        # TODO: Remplacer par vraie API Twitter
        # Simulation pour l'instant
        result = {
            'platform': 'twitter',
            'site_web': site_web,
            'status': 'success',
            'post_id': f'twitter_{self.request.id}',
            'post_url': f'https://twitter.com/{site_web}/status/{self.request.id}',
            'published_at': 'simulated_timestamp',
            'content_published': tweet_content[:50] + '...'
        }

        logger.info(f"Twitter publication completed for {site_web} - Task {self.request.id}")

        return result

    except CredentialsError as e:
        logger.error(f"Credentials error for Twitter {site_web}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': f'Credentials error: {str(e)}', 'step': 'Twitter credentials validation'}
        )
        raise
    except Exception as e:
        logger.error(f"Error in Twitter publication task {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': 'Twitter publication failed'}
        )
        raise


@celery_app.task(bind=True, name='content_publishing.publish_to_facebook')
def publish_to_facebook_task(self, site_web: str, content_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tâche Celery pour publier sur Facebook
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': 'Starting Facebook publication'})

        site = SiteWeb(site_web)

        # Récupérer les credentials
        creds = get_platform_credentials(site, PlatformType.FACEBOOK)

        logger.info(f"Publishing to Facebook for {site_web} - Task {self.request.id}")

        # Extraire le contenu
        message_content = content_data.get('message', '')
        if not message_content:
            raise ValueError("No Facebook message content provided")

        self.update_state(state='PROGRESS', meta={'step': 'Calling Facebook Graph API'})

        # TODO: Remplacer par vraie API Facebook
        # Simulation pour l'instant
        result = {
            'platform': 'facebook',
            'site_web': site_web,
            'status': 'success',
            'post_id': f'facebook_{self.request.id}',
            'post_url': f'https://facebook.com/{creds.page_id}/posts/{self.request.id}',
            'published_at': 'simulated_timestamp',
            'content_published': message_content[:50] + '...'
        }

        logger.info(f"Facebook publication completed for {site_web} - Task {self.request.id}")

        return result

    except CredentialsError as e:
        logger.error(f"Credentials error for Facebook {site_web}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': f'Credentials error: {str(e)}', 'step': 'Facebook credentials validation'}
        )
        raise
    except Exception as e:
        logger.error(f"Error in Facebook publication task {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': 'Facebook publication failed'}
        )
        raise


@celery_app.task(bind=True, name='content_publishing.publish_to_instagram')
def publish_to_instagram_task(self, site_web: str, content_data: Dict[str, Any], content_type: str = 'post') -> Dict[
    str, Any]:
    """
    Tâche Celery pour publier sur Instagram
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': f'Starting Instagram {content_type} publication'})

        site = SiteWeb(site_web)

        # Récupérer les credentials
        creds = get_platform_credentials(site, PlatformType.INSTAGRAM)

        logger.info(f"Publishing to Instagram ({content_type}) for {site_web} - Task {self.request.id}")

        # Traitement selon le type de contenu
        if content_type == 'post':
            content_key = 'legende'
        elif content_type == 'story':
            content_key = 'texte_story'
        elif content_type == 'carousel':
            content_key = 'legende'
        else:
            raise ValueError(f"Unsupported Instagram content type: {content_type}")

        # Extraire le contenu
        instagram_content = content_data.get(content_key, '')
        if not instagram_content:
            raise ValueError(f"No Instagram {content_type} content provided")

        self.update_state(state='PROGRESS', meta={'step': 'Calling Instagram Graph API'})

        # TODO: Remplacer par vraie API Instagram
        # Simulation pour l'instant
        result = {
            'platform': 'instagram',
            'content_type': content_type,
            'site_web': site_web,
            'status': 'success',
            'post_id': f'instagram_{content_type}_{self.request.id}',
            'post_url': f'https://instagram.com/p/{self.request.id}',
            'published_at': 'simulated_timestamp',
            'content_published': instagram_content[:50] + '...'
        }

        # Ajouter les infos spécifiques au carrousel
        if content_type == 'carousel':
            slides = content_data.get('slides', [])
            images_urls = content_data.get('images_urls', [])
            result['slides_count'] = len(slides)
            result['images_count'] = len(images_urls)
            result['images_generated'] = content_data.get('images_generated', False)

        logger.info(f"Instagram {content_type} publication completed for {site_web} - Task {self.request.id}")

        return result

    except CredentialsError as e:
        logger.error(f"Credentials error for Instagram {site_web}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': f'Credentials error: {str(e)}', 'step': 'Instagram credentials validation'}
        )
        raise
    except Exception as e:
        logger.error(f"Error in Instagram publication task {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': f'Instagram {content_type} publication failed'}
        )
        raise


@celery_app.task(bind=True, name='content_publishing.publish_multiplatform')
def publish_multiplatform_task(self, site_web: str, formatted_contents: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tâche Celery pour publier sur plusieurs plateformes en parallèle
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': 'Starting multi-platform publication'})

        logger.info(f"Starting multi-platform publication for {site_web} - Task {self.request.id}")

        publication_results = {}

        # Publier sur chaque plateforme
        for platform_content_key, content_data in formatted_contents.items():
            try:
                # Parse platform and content type from key (e.g., "twitter_post", "instagram_carousel")
                platform, content_type = platform_content_key.split('_', 1)

                self.update_state(
                    state='PROGRESS',
                    meta={'step': f'Publishing to {platform}_{content_type}'}
                )

                if platform == 'twitter':
                    result = publish_to_twitter_task.delay(site_web, content_data.__dict__)
                    publication_results[platform_content_key] = {
                        'task_id': result.id,
                        'status': 'submitted'
                    }

                elif platform == 'facebook':
                    result = publish_to_facebook_task.delay(site_web, content_data.__dict__)
                    publication_results[platform_content_key] = {
                        'task_id': result.id,
                        'status': 'submitted'
                    }

                elif platform == 'instagram':
                    result = publish_to_instagram_task.delay(site_web, content_data.__dict__, content_type)
                    publication_results[platform_content_key] = {
                        'task_id': result.id,
                        'status': 'submitted'
                    }

                else:
                    logger.warning(f"Unsupported platform: {platform}")
                    publication_results[platform_content_key] = {
                        'status': 'failed',
                        'error': f'Unsupported platform: {platform}'
                    }

            except Exception as e:
                logger.error(f"Error publishing to {platform_content_key}: {str(e)}")
                publication_results[platform_content_key] = {
                    'status': 'failed',
                    'error': str(e)
                }

        logger.info(f"Multi-platform publication tasks submitted for {site_web} - Task {self.request.id}")

        return {
            'site_web': site_web,
            'task_id': self.request.id,
            'publication_results': publication_results,
            'total_platforms': len(formatted_contents),
            'status': 'submitted'
        }

    except Exception as e:
        logger.error(f"Error in multi-platform publication task {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': 'Multi-platform publication failed'}
        )
        raise