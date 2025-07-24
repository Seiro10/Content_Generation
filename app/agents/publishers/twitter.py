import logging
import asyncio
import boto3
import tempfile
import os
from datetime import datetime
from requests_oauthlib import OAuth1Session

from app.agents.base_agent import BasePublisher
from app.models.base import PlatformType
from app.models.accounts import SiteWeb, AccountConfig
from app.models.platforms import TwitterPostOutput
from app.config.credentials import get_platform_credentials
from app.config.settings import settings

logger = logging.getLogger(__name__)


class TwitterPublisher(BasePublisher):
    """Publisher spécialisé pour Twitter avec support d'images S3"""

    def __init__(self):
        super().__init__(PlatformType.TWITTER)

    async def publish_content(
            self,
            formatted_content: TwitterPostOutput,
            site_web: SiteWeb,
            account: AccountConfig
    ) -> dict:
        """Publie le contenu formaté sur Twitter"""

        logger.info(f"🐦 Publication Twitter pour compte: {account.account_name}")

        try:
            # Récupérer les credentials Twitter
            creds = get_platform_credentials(site_web, PlatformType.TWITTER)

            # Préparer le tweet
            tweet_text = formatted_content.tweet

            # Fonction synchrone pour Twitter (requests-oauthlib n'est pas async)
            def post_tweet_with_media():
                # Créer session OAuth 1.0a
                twitter = OAuth1Session(
                    creds.api_key,
                    client_secret=creds.api_secret,
                    resource_owner_key=creds.access_token,
                    resource_owner_secret=creds.access_token_secret,
                )

                media_id = None

                # Gérer l'image S3 si présente
                if formatted_content.image_s3_url:
                    media_id = self._upload_image_to_twitter(
                        twitter,
                        formatted_content.image_s3_url
                    )

                # Payload pour l'API v2
                payload = {"text": tweet_text}
                if media_id:
                    payload["media"] = {"media_ids": [media_id]}

                # Poster le tweet
                response = twitter.post(
                    "https://api.twitter.com/2/tweets",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                return response

            # Exécuter de manière asynchrone
            response = await asyncio.get_event_loop().run_in_executor(None, post_tweet_with_media)

            if response.status_code == 201:
                data = response.json()
                tweet_id = data["data"]["id"]

                logger.info(f"✅ Tweet publié avec succès ! ID: {tweet_id}")
                logger.info(f"📝 Contenu: {tweet_text}")

                if formatted_content.image_s3_url:
                    logger.info(f"🖼️ Image: {formatted_content.image_s3_url}")

                return self._create_success_result(
                    tweet_id,
                    f"https://twitter.com/i/web/status/{tweet_id}",
                    {
                        "tweet_text": tweet_text,
                        "image_uploaded": bool(formatted_content.image_s3_url)
                    }
                )
            else:
                error_msg = f"Twitter API error: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")
                return self._create_error_result(error_msg)

        except Exception as e:
            error_msg = f"Erreur lors de la publication Twitter: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return self._create_error_result(error_msg)

    def _upload_image_to_twitter(self, twitter_session: OAuth1Session, s3_url: str) -> str:
        """Upload une image S3 vers Twitter et retourne le media_id"""

        try:
            logger.info(f"📸 Téléchargement image S3: {s3_url}")

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

            # Créer le client S3 avec credentials explicites
            s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                region_name=aws_region
            )

            logger.info("✅ Client S3 créé avec succès")

            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                logger.info(f"⬇️ Téléchargement de {bucket}/{key}")
                s3_client.download_file(bucket, key, tmp_file.name)
                logger.info("✅ Téléchargement S3 réussi")

                # Upload vers Twitter
                with open(tmp_file.name, 'rb') as img_file:
                    logger.info("⬆️ Upload vers Twitter...")
                    upload_response = twitter_session.post(
                        "https://upload.twitter.com/1.1/media/upload.json",
                        files={"media": img_file}
                    )

                    if upload_response.status_code == 200:
                        media_data = upload_response.json()
                        media_id = media_data["media_id_string"]
                        logger.info(f"✅ Image uploadée vers Twitter, Media ID: {media_id}")
                        return media_id
                    else:
                        logger.error(f"❌ Erreur upload Twitter: {upload_response.status_code} - {upload_response.text}")
                        return None

                # Nettoyer le fichier temporaire
                os.unlink(tmp_file.name)
                logger.info("🧹 Fichier temporaire supprimé")

        except Exception as e:
            logger.error(f"❌ Erreur upload image S3: {str(e)}")
            return None


# Instance globale
twitter_publisher = TwitterPublisher()