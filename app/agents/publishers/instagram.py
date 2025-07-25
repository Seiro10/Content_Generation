import logging
import asyncio
import json
import time
import requests
import boto3
import tempfile
import os
from datetime import datetime

from app.agents.base_agent import BasePublisher
from app.models.base import PlatformType, ContentType
from app.models.accounts import SiteWeb, AccountConfig
from app.models.platforms import InstagramPostOutput, InstagramStoryOutput, InstagramCarouselOutput
from app.config.credentials import get_platform_credentials
from app.config.settings import settings

logger = logging.getLogger(__name__)


class InstagramPublisher(BasePublisher):
    """Publisher spécialisé pour Instagram avec support S3"""

    def __init__(self):
        super().__init__(PlatformType.INSTAGRAM)

    def _get_s3_public_url(self, s3_url: str) -> str:
        """Génère une URL publique temporaire pour un objet S3"""
        try:
            logger.info(f"🔗 Génération URL publique S3: {s3_url}")

            # Parse S3 URL
            if not s3_url.startswith('s3://'):
                raise Exception(f"Format S3 URL non supporté: {s3_url}")

            s3_path = s3_url[5:]  # Remove 's3://'
            bucket, key = s3_path.split('/', 1)

            # Récupérer credentials AWS
            aws_key = settings.aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret = settings.aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
            aws_region = settings.aws_default_region or os.getenv('AWS_DEFAULT_REGION', 'eu-west-3')

            if not aws_key or not aws_secret:
                raise Exception(f"AWS credentials manquantes")

            # Créer le client S3
            s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                region_name=aws_region
            )

            # Générer une URL signée temporaire (15 minutes)
            public_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=900  # 15 minutes
            )

            logger.info(f"✅ URL publique S3 générée: {public_url[:50]}...")
            return public_url

        except Exception as e:
            logger.error(f"❌ Erreur génération URL publique S3: {str(e)}")
            # Fallback vers image par défaut
            return 'https://images.unsplash.com/photo-1516251193007-45ef944ab0c6?w=1080'

    def _is_s3_url(self, url: str) -> bool:
        """Vérifie si l'URL est une URL S3"""
        return url.startswith('s3://') if url else False

    def _download_s3_image(self, s3_url: str) -> str:
        """Télécharge une image S3 et retourne le chemin du fichier temporaire"""
        try:
            logger.info(f"📸 Téléchargement image S3 pour Instagram: {s3_url}")

            # Parse S3 URL (format: s3://bucket/path)
            if not s3_url.startswith('s3://'):
                raise Exception(f"Format S3 URL non supporté: {s3_url}")

            s3_path = s3_url[5:]  # Remove 's3://'
            bucket, key = s3_path.split('/', 1)

            logger.info(f"📦 S3 Bucket: {bucket}, Key: {key}")

            # Récupérer credentials AWS
            aws_key = settings.aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret = settings.aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
            aws_region = settings.aws_default_region or os.getenv('AWS_DEFAULT_REGION', 'eu-west-3')

            if not aws_key or not aws_secret:
                raise Exception(f"AWS credentials manquantes")

            # Créer le client S3
            s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                region_name=aws_region
            )

            # Télécharger vers un fichier temporaire
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            s3_client.download_file(bucket, key, tmp_file.name)
            tmp_file.close()

            logger.info(f"✅ Image S3 téléchargée: {tmp_file.name}")
            return tmp_file.name

        except Exception as e:
            logger.error(f"❌ Erreur téléchargement S3: {str(e)}")
            raise

    async def publish_content(
            self,
            formatted_content: any,
            site_web: SiteWeb,
            account: AccountConfig,
            content_type: ContentType = ContentType.POST
    ) -> dict:
        """Publie le contenu formaté sur Instagram avec support S3"""

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
        """Publie un post Instagram avec support S3"""

        logger.info("📸 Publication post Instagram")

        def publish_sync():
            # Déterminer l'image à utiliser
            image_url = None
            temp_file = None

            try:
                # Déterminer l'image à utiliser et créer le container
                container_url = f"https://graph.facebook.com/v18.0/{creds.business_account_id}/media"

                if content.image_s3_url and self._is_s3_url(content.image_s3_url):
                    # Convertir S3 URL en URL publique temporaire
                    temp_file = self._download_s3_image(content.image_s3_url)
                    public_url = self._get_s3_public_url(content.image_s3_url)
                    logger.info(f"📤 Utilisation de l'URL S3 publique: {public_url}")

                    # Créer le container avec l'URL publique S3
                    container_data = {
                        'image_url': public_url,
                        'caption': content.legende,
                        'access_token': creds.access_token
                    }
                    container_response = requests.post(container_url, data=container_data)
                else:
                    # Utiliser l'image par défaut via URL
                    image_url = 'https://images.unsplash.com/photo-1516251193007-45ef944ab0c6?w=1080'
                    container_data = {
                        'image_url': image_url,
                        'caption': content.legende,
                        'access_token': creds.access_token
                    }
                    container_response = requests.post(container_url, data=container_data)

                if container_response.status_code != 200:
                    raise Exception(f"Erreur création container: {container_response.text}")

                container_id = container_response.json()['id']
                logger.info(f"✅ Container créé: {container_id}")

                # Log source de l'image
                if content.image_s3_url and self._is_s3_url(content.image_s3_url):
                    logger.info(f"✅ Image S3 utilisée: {content.image_s3_url}")
                else:
                    logger.info(f"ℹ️ Image par défaut utilisée (pas d'image S3 fournie)")

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

            finally:
                # Nettoyer le fichier temporaire
                if temp_file and os.path.exists(temp_file):
                    os.unlink(temp_file)
                    logger.info("🧹 Fichier temporaire S3 supprimé")

        # Exécuter de manière asynchrone
        result = await asyncio.get_event_loop().run_in_executor(None, publish_sync)
        post_id = result['id']

        logger.info(f"✅ Post Instagram publié ! ID: {post_id}")
        if content.image_s3_url:
            logger.info(f"🖼️ Image S3 utilisée: {content.image_s3_url}")

        return self._create_success_result(
            post_id,
            f"https://instagram.com/p/{post_id}",
            {
                "caption": content.legende,
                "hashtags": content.hashtags,
                "image_source": "s3" if content.image_s3_url else "default"
            }
        )

    async def _publish_story(self, content: InstagramStoryOutput, creds) -> dict:
        """Publie une story Instagram avec support S3"""

        logger.info("📸 Publication story Instagram")

        def publish_sync():
            # Gérer l'image S3 si présente
            image_url = None
            temp_file = None

            try:
                # Gérer l'image S3 si présente et créer la story
                story_url = f"https://graph.facebook.com/v18.0/{creds.business_account_id}/media"

                if content.image_s3_url and self._is_s3_url(content.image_s3_url):
                    # Générer URL publique S3
                    temp_file = self._download_s3_image(content.image_s3_url)  # Download pour nettoyage
                    public_url = self._get_s3_public_url(content.image_s3_url)
                    logger.info(f"📤 Story avec image S3 publique")

                    story_data = {
                        'image_url': public_url,
                        'media_type': 'STORIES',
                        'access_token': creds.access_token
                    }
                    container_response = requests.post(story_url, data=story_data)
                else:
                    # Utiliser l'image par défaut
                    story_data = {
                        'image_url': 'https://images.unsplash.com/photo-1516251193007-45ef944ab0c6?w=1080',
                        'media_type': 'STORIES',
                        'access_token': creds.access_token
                    }
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

            finally:
                if temp_file and os.path.exists(temp_file):
                    os.unlink(temp_file)
                    logger.info("🧹 Fichier temporaire story supprimé")

        result = await asyncio.get_event_loop().run_in_executor(None, publish_sync)
        story_id = result['id']

        logger.info(f"✅ Story Instagram publiée ! ID: {story_id}")

        return self._create_success_result(
            story_id,
            f"https://instagram.com/stories/{creds.business_account_id}/{story_id}",
            {
                "text": content.texte_story,
                "type": "story",
                "image_source": "s3" if content.image_s3_url else "default"
            }
        )

    async def _publish_carousel(self, content: InstagramCarouselOutput, creds) -> dict:
        """Publie un carrousel Instagram avec support S3"""

        logger.info(f"📸 Publication carrousel Instagram ({len(content.slides)} slides)")

        def publish_sync():
            temp_files = []

            try:
                # Déterminer les images à utiliser
                images_to_process = []

                if content.images_s3_urls:
                    # Utiliser les URLs S3
                    images_to_process = content.images_s3_urls
                    logger.info(f"📦 Traitement de {len(images_to_process)} images S3")
                elif content.images_urls:
                    # Utiliser les URLs normales
                    images_to_process = content.images_urls
                    logger.info(f"🔗 Traitement de {len(images_to_process)} URLs normales")
                else:
                    # Images par défaut
                    images_to_process = ['https://images.unsplash.com/photo-1516251193007-45ef944ab0c6?w=1080'] * len(
                        content.slides)
                    logger.info(f"ℹ️ Utilisation d'images par défaut")

                # Étape 1: Créer les containers pour chaque média
                media_ids = []

                for i, image_source in enumerate(images_to_process):
                    try:
                        media_url = f"https://graph.facebook.com/v18.0/{creds.business_account_id}/media"

                        if self._is_s3_url(image_source):
                            # Générer URL publique S3
                            temp_file = self._download_s3_image(image_source)
                            temp_files.append(temp_file)  # Pour nettoyage
                            public_url = self._get_s3_public_url(image_source)

                            media_data = {
                                'image_url': public_url,
                                'is_carousel_item': 'true',
                                'access_token': creds.access_token
                            }
                            media_response = requests.post(media_url, data=media_data)

                        else:
                            # URL normale
                            media_data = {
                                'image_url': image_source,
                                'is_carousel_item': 'true',
                                'access_token': creds.access_token
                            }
                            media_response = requests.post(media_url, data=media_data)

                        if media_response.status_code != 200:
                            logger.warning(f"Erreur média {i + 1}: {media_response.text}")
                            continue

                        media_id = media_response.json()['id']
                        media_ids.append(media_id)
                        logger.info(f"✅ Média {i + 1} créé: {media_id}")

                    except Exception as e:
                        logger.warning(f"Erreur traitement image {i + 1}: {str(e)}")
                        continue

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

            finally:
                # Nettoyer tous les fichiers temporaires
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                logger.info(f"🧹 {len(temp_files)} fichiers temporaires S3 supprimés")

        result = await asyncio.get_event_loop().run_in_executor(None, publish_sync)
        carousel_id = result['id']

        logger.info(f"✅ Carrousel Instagram publié ! ID: {carousel_id}")
        logger.info(f"📊 {len(content.slides)} slides")
        if content.images_s3_urls:
            logger.info(f"📦 {len(content.images_s3_urls)} images S3 utilisées")
        elif content.images_urls:
            logger.info(f"🔗 {len(content.images_urls)} URLs normales utilisées")
        else:
            logger.info(f"ℹ️ Images par défaut utilisées")

        return self._create_success_result(
            carousel_id,
            f"https://instagram.com/p/{carousel_id}",
            {
                "caption": content.legende,
                "slides_count": len(content.slides),
                "images_count": len(content.images_s3_urls or content.images_urls or []),
                "hashtags": content.hashtags,
                "images_generated": content.images_generated,
                "image_source": "s3" if content.images_s3_urls else "urls" if content.images_urls else "default"
            }
        )


# Instance globale
instagram_publisher = InstagramPublisher()