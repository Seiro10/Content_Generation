import logging
import asyncio
import requests
import uuid
from datetime import datetime

from app.agents.base_agent import BasePublisher
from app.models.base import PlatformType
from app.models.accounts import SiteWeb, AccountConfig
from app.models.platforms import FacebookPostOutput
from app.config.credentials import get_platform_credentials

logger = logging.getLogger(__name__)


class FacebookPublisher(BasePublisher):
    """Publisher spécialisé pour Facebook avec support des drafts"""

    def __init__(self):
        super().__init__(PlatformType.FACEBOOK)

    async def publish_content(
            self,
            formatted_content: FacebookPostOutput,
            site_web: SiteWeb,
            account: AccountConfig,
            published: bool = True  # 🆕 Nouveau paramètre
    ) -> dict:
        """Publie le contenu formaté sur Facebook avec support draft"""

        logger.info(f"📘 Publication Facebook pour compte: {account.account_name}")
        logger.info(f"📝 Mode: {'Publication' if published else 'Draft/Non publié'}")

        try:
            # Récupérer les credentials Facebook
            creds = get_platform_credentials(site_web, PlatformType.FACEBOOK)

            # Fonction synchrone pour Facebook (requests n'est pas async)
            def post_facebook_content():
                # Préparer les données avec le paramètre published
                post_data = {
                    'message': formatted_content.message,
                    'access_token': creds.access_token
                }

                # 🆕 Gestion du paramètre published
                if not published:
                    post_data['published'] = False
                    post_data['unpublished_content_type'] = 'DRAFT'
                    logger.info("📝 Création d'un draft Facebook")
                else:
                    post_data['published'] = True
                    logger.info("📤 Publication directe sur Facebook")

                # Ajouter le média si fourni
                if hasattr(formatted_content, 'media') and formatted_content.media:
                    post_data['link'] = formatted_content.media

                # Appel à l'API Facebook Graph
                url = f"https://graph.facebook.com/v18.0/{creds.page_id}/feed"
                response = requests.post(url, data=post_data)

                if response.status_code != 200:
                    raise Exception(f"Erreur Facebook API: {response.status_code} - {response.text}")

                return response.json()

            # Exécuter de manière asynchrone
            result = await asyncio.get_event_loop().run_in_executor(None, post_facebook_content)
            post_id = result['id']

            # Adapter le message et l'URL de retour selon le mode
            if published:
                status_message = "Publié avec succès sur Facebook"
                post_url = f"https://facebook.com/{creds.page_id}/posts/{post_id}"
                additional_data = {
                    "message": formatted_content.message,
                    "published": True,
                    "platform_specific": {
                        "facebook_post_id": post_id,
                        "facebook_page_id": creds.page_id
                    }
                }
            else:
                status_message = "Draft créé sur Facebook"
                post_url = f"https://facebook.com/{creds.page_id}/publishing_tools/"
                additional_data = {
                    "message": formatted_content.message,
                    "published": False,
                    "draft_id": post_id,
                    "status_message": "Draft Facebook créé - visible dans les outils de publication",
                    "facebook_drafts_url": f"https://facebook.com/{creds.page_id}/publishing_tools/?tab=drafts",
                    "platform_specific": {
                        "facebook_draft_id": post_id,
                        "facebook_page_id": creds.page_id,
                        "can_publish_later": True
                    },
                    "instructions": {
                        "how_to_publish": "Connectez-vous à Facebook > Outils de publication > Drafts > Publier",
                        "how_to_edit": "Le draft peut être modifié avant publication"
                    }
                }

            logger.info(f"✅ Facebook - {status_message} ! ID: {post_id}")

            return self._create_success_result(
                post_id,
                post_url,
                additional_data
            )

        except Exception as e:
            error_msg = f"Erreur lors de la publication Facebook: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return self._create_error_result(error_msg)

    def publish_draft(self, draft_id: str, site_web: SiteWeb) -> dict:
        """🆕 Méthode pour publier un draft Facebook existant"""
        try:
            creds = get_platform_credentials(site_web, PlatformType.FACEBOOK)

            # Publier le draft en mettant published=true
            url = f"https://graph.facebook.com/v18.0/{draft_id}"
            data = {
                'is_published': True,
                'access_token': creds.access_token
            }

            response = requests.post(url, data=data)

            if response.status_code == 200:
                logger.info(f"✅ Draft Facebook {draft_id} publié avec succès")
                return {
                    "status": "success",
                    "message": "Draft publié avec succès",
                    "draft_id": draft_id,
                    "published_at": datetime.now().isoformat()
                }
            else:
                error_msg = f"Erreur publication draft: {response.text}"
                logger.error(f"❌ {error_msg}")
                return {"status": "failed", "error": error_msg}

        except Exception as e:
            error_msg = f"Erreur lors de la publication du draft: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"status": "failed", "error": error_msg}

    def delete_draft(self, draft_id: str, site_web: SiteWeb) -> dict:
        """🆕 Méthode pour supprimer un draft Facebook"""
        try:
            creds = get_platform_credentials(site_web, PlatformType.FACEBOOK)

            url = f"https://graph.facebook.com/v18.0/{draft_id}"
            params = {'access_token': creds.access_token}

            response = requests.delete(url, params=params)

            if response.status_code == 200:
                logger.info(f"✅ Draft Facebook {draft_id} supprimé")
                return {
                    "status": "success",
                    "message": "Draft supprimé avec succès",
                    "draft_id": draft_id
                }
            else:
                error_msg = f"Erreur suppression draft: {response.text}"
                logger.error(f"❌ {error_msg}")
                return {"status": "failed", "error": error_msg}

        except Exception as e:
            error_msg = f"Erreur lors de la suppression du draft: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"status": "failed", "error": error_msg}


# Instance globale
facebook_publisher = FacebookPublisher()