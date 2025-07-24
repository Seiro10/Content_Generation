import logging
import asyncio
import json
import time
import requests
from datetime import datetime

from app.agents.base_agent import BasePublisher
from app.models.base import PlatformType, ContentType
from app.models.accounts import SiteWeb, AccountConfig
from app.models.platforms import InstagramPostOutput, InstagramStoryOutput, InstagramCarouselOutput
from app.config.credentials import get_platform_credentials

logger = logging.getLogger(__name__)


class InstagramPublisher(BasePublisher):
    """Publisher spécialisé pour Instagram (post, story, carousel)"""

    def __init__(self):
        super().__init__(PlatformType.INSTAGRAM)

    async def publish_content(
            self,
            formatted_content: any,
            site_web: SiteWeb,
            account: AccountConfig,
            content_type: ContentType = ContentType.POST
    ) -> dict:
        """Publie le contenu formaté sur Instagram"""

        logger.info(f"📸 Publication Instagram {content_type} pour compte: {account.account_name}")

        try:
            # Récupérer les credentials Instagram
            creds = get_platform_credentials(site_web, PlatformType.INSTAGRAM)

            if content_type == ContentType.POST:
                return await self._publish_post(formatted_content, creds)
            elif content_type == ContentType.STORY:
                return await self._publish_story(formatted_content, creds)
            elif content_type == ContentType.CAROUSEL:
                return await self._publish_carousel(formatted_content, creds)
            else:
                return self._create_error_result(f"Type de contenu non supporté: {content_type}")

        except Exception as e:
            error_msg = f"Erreur lors de la publication Instagram: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return self._create_error_result(error_msg)

    async def _publish_post(self, content: InstagramPostOutput, creds) -> dict:
        """Publie un post Instagram classique"""

        logger.info("📸 Publication post Instagram classique")

        def publish_sync():
            # Étape 1: Créer le container média
            container_data = {
                'image_url': 'https://images.unsplash.com/photo-1516251193007-45ef944ab0c6?w=1080',  # Image par défaut
                'caption': content.legende,
                'access_token': creds.access_token
            }

            # Créer le container
            container_url = f"https://graph.facebook.com/v18.0/{creds.business_account_id}/media"
            container_response = requests.post(container_url, data=container_data)

            if container_response.status_code != 200:
                raise Exception(f"Erreur création container: {container_response.text}")

            container_id = container_response.json()['id']
            logger.info(f"✅ Container créé: {container_id}")

            # Étape 2: Publier le container
            publish_data = {
                'creation_id': container_id,
                'access_token': creds.access_token
            }

            publish_url = f"https://graph.facebook.com/v18.0/{creds.business_account_id}/media_publish"
            publish_response = requests.post(publish_url, data=publish_data)

            if publish_response.status_code != 200:
                raise Exception(f"Erreur publication: {publish_response.text}")

            return publish_response.json()

        # Exécuter de manière asynchrone
        result = await asyncio.get_event_loop().run_in_executor(None, publish_sync)
        post_id = result['id']

        logger.info(f"✅ Post Instagram publié ! ID: {post_id}")
        logger.info(f"📝 Légende: {content.legende[:50]}...")

        return self._create_success_result(
            post_id,
            f"https://instagram.com/p/{post_id}",
            {
                "caption": content.legende,
                "hashtags": content.hashtags
            }
        )

    async def _publish_story(self, content: InstagramStoryOutput, creds) -> dict:
        """Publie une story Instagram"""

        logger.info("📸 Publication story Instagram")

        def publish_sync():
            # Créer la story
            story_data = {
                'image_url': 'https://images.unsplash.com/photo-1516251193007-45ef944ab0c6?w=1080',  # Image par défaut
                'media_type': 'STORIES',
                'access_token': creds.access_token
            }

            # Si il y a du texte pour la story
            if content.texte_story:
                # Le texte sera ajouté comme overlay dans une vraie implémentation
                pass

            story_url = f"https://graph.facebook.com/v18.0/{creds.business_account_id}/media"
            container_response = requests.post(story_url, data=story_data)

            if container_response.status_code != 200:
                raise Exception(f"Erreur création story: {container_response.text}")

            container_id = container_response.json()['id']

            # Publier la story
            publish_data = {
                'creation_id': container_id,
                'access_token': creds.access_token
            }

            publish_url = f"https://graph.facebook.com/v18.0/{creds.business_account_id}/media_publish"
            publish_response = requests.post(publish_url, data=publish_data)

            if publish_response.status_code != 200:
                raise Exception(f"Erreur publication story: {publish_response.text}")

            return publish_response.json()

        result = await asyncio.get_event_loop().run_in_executor(None, publish_sync)
        story_id = result['id']

        logger.info(f"✅ Story Instagram publiée ! ID: {story_id}")

        return self._create_success_result(
            story_id,
            f"https://instagram.com/stories/{creds.business_account_id}/{story_id}",
            {
                "text": content.texte_story,
                "type": "story"
            }
        )

    async def _publish_carousel(self, content: InstagramCarouselOutput, creds) -> dict:
        """Publie un carrousel Instagram"""

        logger.info(f"📸 Publication carrousel Instagram ({len(content.slides)} slides)")

        def publish_sync():
            # Étape 1: Créer les containers pour chaque média
            media_ids = []

            for i, image_url in enumerate(content.images_urls or []):
                media_data = {
                    'image_url': image_url,
                    'is_carousel_item': 'true',
                    'access_token': creds.access_token
                }

                media_url = f"https://graph.facebook.com/v18.0/{creds.business_account_id}/media"
                media_response = requests.post(media_url, data=media_data)

                if media_response.status_code != 200:
                    logger.warning(f"Erreur média {i + 1}: {media_response.text}")
                    continue

                media_id = media_response.json()['id']
                media_ids.append(media_id)
                logger.info(f"✅ Média {i + 1} créé: {media_id}")

            if not media_ids:
                raise Exception("Aucun média créé pour le carrousel")

            # Étape 2: Créer le container carrousel
            carousel_data = {
                'media_type': 'CAROUSEL',
                'children': ','.join(media_ids),
                'caption': content.legende,
                'access_token': creds.access_token
            }

            carousel_url = f"https://graph.facebook.com/v18.0/{creds.business_account_id}/media"
            carousel_response = requests.post(carousel_url, data=carousel_data)

            if carousel_response.status_code != 200:
                raise Exception(f"Erreur création carrousel: {carousel_response.text}")

            carousel_id = carousel_response.json()['id']
            logger.info(f"✅ Carrousel créé: {carousel_id}")

            # Étape 3: Publier le carrousel
            publish_data = {
                'creation_id': carousel_id,
                'access_token': creds.access_token
            }

            publish_url = f"https://graph.facebook.com/v18.0/{creds.business_account_id}/media_publish"
            publish_response = requests.post(publish_url, data=publish_data)

            if publish_response.status_code != 200:
                raise Exception(f"Erreur publication carrousel: {publish_response.text}")

            return publish_response.json()

        result = await asyncio.get_event_loop().run_in_executor(None, publish_sync)
        carousel_id = result['id']

        logger.info(f"✅ Carrousel Instagram publié ! ID: {carousel_id}")
        logger.info(f"📊 {len(content.slides)} slides, {len(content.images_urls or [])} images")

        return self._create_success_result(
            carousel_id,
            f"https://instagram.com/p/{carousel_id}",
            {
                "caption": content.legende,
                "slides_count": len(content.slides),
                "images_count": len(content.images_urls or []),
                "hashtags": content.hashtags,
                "images_generated": content.images_generated
            }
        )


# Instance globale
instagram_publisher = InstagramPublisher()