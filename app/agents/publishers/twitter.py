import logging
import asyncio
import boto3
import tempfile
import os
import uuid
from datetime import datetime
from requests_oauthlib import OAuth1Session

from app.agents.base_agent import BasePublisher
from app.models.base import PlatformType
from app.models.accounts import SiteWeb, AccountConfig
from app.models.platforms import TwitterPostOutput
from app.config.credentials import get_platform_credentials
from app.config.settings import settings

logger = logging.getLogger(__name__)

# 🆕 Store temporaire pour les drafts Twitter (en production, utiliser Redis ou DB)
twitter_drafts_store = {}


class TwitterPublisher(BasePublisher):
    """Publisher spécialisé pour Twitter avec support d'images S3 et drafts simulés"""

    def __init__(self):
        super().__init__(PlatformType.TWITTER)

    async def publish_content(
            self,
            formatted_content: TwitterPostOutput,
            site_web: SiteWeb,
            account: AccountConfig,
            published: bool = True  # 🆕 Nouveau paramètre
    ) -> dict:
        """Publie le contenu formaté sur Twitter avec support drafts"""

        logger.info(f"🐦 Twitter pour compte: {account.account_name}")
        logger.info(f"📝 Mode: {'Publication' if published else 'Draft simulé'}")

        try:
            # 🆕 Si draft demandé, créer un draft simulé
            if not published:
                return self._create_draft_simulation(formatted_content, site_web, account)

            # Publication normale si published=True
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
                        "image_uploaded": bool(formatted_content.image_s3_url),
                        "published": True,
                        "character_count": len(tweet_text)
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

    def _create_draft_simulation(self, formatted_content, site_web, account) -> dict:
        """🆕 Simule un draft Twitter en stockant les données"""
        draft_id = f"twitter_draft_{uuid.uuid4().hex[:8]}"

        # Analyser le contenu du tweet
        tweet_analysis = self._analyze_tweet_content(formatted_content.tweet)

        # Stocker le draft avec métadonnées
        draft_data = {
            "draft_id": draft_id,
            "content": {
                "tweet": formatted_content.tweet,
                "image_s3_url": formatted_content.image_s3_url
            },
            "site_web": site_web.value,
            "account": account.account_name,
            "content_type": "post",
            "created_at": datetime.now().isoformat(),
            "status": "draft",
            "platform": "twitter",
            "analysis": tweet_analysis
        }

        # Stocker dans le store temporaire (en production: Redis/DB)
        twitter_drafts_store[draft_id] = draft_data

        logger.info(f"📝 Draft Twitter simulé créé: {draft_id}")

        return self._create_success_result(
            draft_id,
            f"internal://drafts/twitter/{draft_id}",
            {
                "content_preview": {
                    "tweet_text": formatted_content.tweet,
                    "character_count": len(formatted_content.tweet),
                    "character_limit": 280,
                    "has_image": bool(formatted_content.image_s3_url),
                    "image_s3_url": formatted_content.image_s3_url,
                    "analysis": tweet_analysis
                },
                "published": False,
                "status_message": "Draft Twitter sauvegardé",
                "draft_info": {
                    "platform": "twitter",
                    "content_type": "post",
                    "can_edit": True,
                    "can_publish": True,
                    "can_delete": True
                },
                "note": "Twitter API v2 ne supporte pas les drafts natifs - contenu stocké en interne",
                "actions": {
                    "publish": f"POST /publish/draft/{draft_id}",
                    "preview": f"GET /drafts/{draft_id}/preview",
                    "edit": f"PUT /drafts/{draft_id}",
                    "delete": f"DELETE /drafts/{draft_id}"
                },
                "limitations": [
                    "Draft simulé - non visible dans l'app Twitter",
                    "Expiration possible selon la configuration du serveur",
                    "Pour publication immédiate: utiliser published=true"
                ],
                "recommendations": self._get_tweet_recommendations(tweet_analysis)
            }
        )

    def _analyze_tweet_content(self, tweet_text: str) -> dict:
        """🆕 Analyse le contenu du tweet pour donner des insights"""
        analysis = {
            "character_count": len(tweet_text),
            "character_limit": 280,
            "character_remaining": 280 - len(tweet_text),
            "is_valid_length": len(tweet_text) <= 280,
            "hashtags": [],
            "mentions": [],
            "links": [],
            "emojis_count": 0
        }

        # Analyser les hashtags
        import re
        hashtag_pattern = r'#\w+'
        analysis["hashtags"] = re.findall(hashtag_pattern, tweet_text)

        # Analyser les mentions
        mention_pattern = r'@\w+'
        analysis["mentions"] = re.findall(mention_pattern, tweet_text)

        # Analyser les liens
        link_pattern = r'https?://\S+'
        analysis["links"] = re.findall(link_pattern, tweet_text)

        # Compter les emojis (approximatif)
        emoji_pattern = r'[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff\U0001f1e0-\U0001f1ff]+'
        emojis = re.findall(emoji_pattern, tweet_text)
        analysis["emojis_count"] = len(emojis)

        # Évaluation de la qualité
        analysis["quality_score"] = self._calculate_tweet_quality_score(analysis)

        return analysis

    def _calculate_tweet_quality_score(self, analysis: dict) -> dict:
        """🆕 Calcule un score de qualité pour le tweet"""
        score = 100
        recommendations = []

        # Pénalité si trop long
        if not analysis["is_valid_length"]:
            score -= 50
            recommendations.append("Tweet trop long - réduire le texte")

        # Pénalité si trop court
        elif analysis["character_count"] < 50:
            score -= 20
            recommendations.append("Tweet très court - ajouter du contenu")

        # Bonus pour hashtags (mais pas trop)
        hashtags_count = len(analysis["hashtags"])
        if hashtags_count == 0:
            score -= 10
            recommendations.append("Ajouter 1-2 hashtags pertinents")
        elif hashtags_count > 3:
            score -= 15
            recommendations.append("Trop de hashtags - limiter à 2-3")

        # Bonus pour engagement
        if analysis["emojis_count"] > 0:
            score += 5

        if len(analysis["mentions"]) > 0:
            score += 5

        # Évaluation finale
        if score >= 90:
            quality = "excellent"
        elif score >= 75:
            quality = "bon"
        elif score >= 60:
            quality = "moyen"
        else:
            quality = "à améliorer"

        return {
            "score": max(0, min(100, score)),
            "quality": quality,
            "recommendations": recommendations
        }

    def _get_tweet_recommendations(self, analysis: dict) -> list:
        """🆕 Génère des recommandations pour améliorer le tweet"""
        recommendations = analysis["quality_score"]["recommendations"].copy()

        # Recommandations additionnelles
        if analysis["character_remaining"] > 100:
            recommendations.append("Espace disponible - ajouter plus de détails")

        if len(analysis["hashtags"]) > 0 and len(analysis["mentions"]) == 0:
            recommendations.append("Considérer ajouter des mentions pertinentes")

        if analysis["emojis_count"] == 0:
            recommendations.append("Ajouter 1-2 emojis pour plus d'engagement")

        return recommendations

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


# 🆕 Fonctions utilitaires pour les drafts Twitter
def get_twitter_draft(draft_id: str) -> dict:
    """Récupère un draft Twitter"""
    return twitter_drafts_store.get(draft_id)


def list_twitter_drafts() -> list:
    """Liste tous les drafts Twitter"""
    return list(twitter_drafts_store.values())


def delete_twitter_draft(draft_id: str) -> bool:
    """Supprime un draft Twitter"""
    if draft_id in twitter_drafts_store:
        del twitter_drafts_store[draft_id]
        return True
    return False


def update_twitter_draft(draft_id: str, new_tweet_text: str) -> dict:
    """🆕 Met à jour un draft Twitter"""
    if draft_id in twitter_drafts_store:
        draft = twitter_drafts_store[draft_id]

        # Créer un nouveau TwitterPostOutput pour l'analyse
        from app.models.platforms import TwitterPostOutput
        new_content = TwitterPostOutput(
            tweet=new_tweet_text,
            image_s3_url=draft["content"].get("image_s3_url")
        )

        # Analyser le nouveau contenu
        publisher = TwitterPublisher()
        new_analysis = publisher._analyze_tweet_content(new_tweet_text)

        # Mettre à jour le draft
        draft["content"]["tweet"] = new_tweet_text
        draft["analysis"] = new_analysis
        draft["updated_at"] = datetime.now().isoformat()

        return draft
    return None


# Instance globale
twitter_publisher = TwitterPublisher()