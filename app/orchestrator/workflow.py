from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
from app.models.base import PlatformType, TaskStatus, ContentType
from app.models.content import EnhancedPublicationRequest, PlatformContentConfig, PlatformSpecificResult, \
    generate_images
from app.models.platforms import *
from app.models.accounts import validate_account_exists, AccountValidationError
from app.services.llm_service import llm_service
import logging
import uuid
from datetime import datetime
from app.models.accounts import SiteWeb
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """État partagé du workflow LangGraph"""
    request: EnhancedPublicationRequest
    content_generated: Optional[str]
    formatted_content: Dict[str, Any]  # {platform_type_key: formatted_content}
    publication_results: Dict[str, Any]  # {platform_type_key: result}
    errors: List[str]
    current_step: str
    task_id: str


class ContentPublisherOrchestrator:
    """Orchestrateur LangGraph pour la publication multi-plateformes"""

    def __init__(self):
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Construit le graphe LangGraph"""
        workflow = StateGraph(WorkflowState)

        # Définir les nœuds
        workflow.add_node("generate_content", self._generate_content_node)
        workflow.add_node("format_content", self._format_content_node)
        workflow.add_node("publish_content", self._publish_content_node)
        workflow.add_node("finalize_results", self._finalize_results_node)

        # Définir les edges
        workflow.set_entry_point("generate_content")
        workflow.add_edge("generate_content", "format_content")
        workflow.add_edge("format_content", "publish_content")
        workflow.add_edge("publish_content", "finalize_results")
        workflow.add_edge("finalize_results", END)

        return workflow.compile()

    async def _generate_content_node(self, state: WorkflowState) -> WorkflowState:
        """Nœud de génération de contenu avec Claude"""
        logger.info(f"Génération de contenu pour la tâche {state['task_id']}")

        try:
            request = state["request"]

            # Prompt pour la génération de contenu de base
            system_prompt = """Tu es un expert en création de contenu pour les réseaux sociaux.
            Génère un contenu de base qui pourra être adapté pour différentes plateformes (Twitter, Facebook, LinkedIn, Instagram).
            Le contenu doit être informatif, engageant et facilement adaptable."""

            prompt = f"""
            Texte source à transformer:
            {request.texte_source}

            Plateformes cibles: {', '.join(request.plateformes)}

            Génère un contenu de base qui servira de fondation pour l'adaptation sur chaque plateforme.
            """

            generated_content = await llm_service.generate_content(prompt, system_prompt)

            state["content_generated"] = generated_content
            state["current_step"] = "content_generated"

            logger.info("Contenu généré avec succès")

        except Exception as e:
            error_msg = f"Erreur lors de la génération de contenu: {str(e)}"
            logger.error(error_msg)
            state["errors"].append(error_msg)

        return state

    async def _format_content_node(self, state: WorkflowState) -> WorkflowState:
        """Nœud de formatage pour chaque plateforme/type avec validation des comptes"""
        logger.info(f"Formatage du contenu pour la tâche {state['task_id']}")

        if not state.get("content_generated"):
            state["errors"].append("Aucun contenu généré à formater")
            return state

        request = state["request"]
        base_content = state["content_generated"]
        formatted_content = {}

        # Formater pour chaque configuration plateforme/type
        for config in request.platforms_config:
            try:
                # Valider que le compte existe
                account = validate_account_exists(request.site_web, config.platform)
                logger.info(f"Compte validé: {account.account_name} pour {request.site_web}/{config.platform}")

                # Créer une clé unique pour cette combinaison plateforme/type
                config_key = f"{config.platform.value}_{config.content_type.value}"

                if config.platform == PlatformType.TWITTER:
                    formatted = await self._format_twitter_content(base_content, config, account)
                    formatted_content[config_key] = formatted

                elif config.platform == PlatformType.FACEBOOK:
                    formatted = await self._format_facebook_content(base_content, config, account)
                    formatted_content[config_key] = formatted

                elif config.platform == PlatformType.LINKEDIN:
                    formatted = await self._format_linkedin_content(base_content, config, account)
                    formatted_content[config_key] = formatted

                elif config.platform == PlatformType.INSTAGRAM:
                    if config.content_type == ContentType.POST:
                        formatted = await self._format_instagram_post(base_content, config, account)
                    elif config.content_type == ContentType.STORY:
                        formatted = await self._format_instagram_story(base_content, config, account)
                    elif config.content_type == ContentType.CAROUSEL:
                        formatted = await self._format_instagram_carousel(base_content, config, account)
                    else:
                        raise ValueError(f"Type de contenu non supporté pour Instagram: {config.content_type}")

                    formatted_content[config_key] = formatted

                logger.info(
                    f"Contenu formaté pour {config.platform}_{config.content_type} (compte: {account.account_name})")

            except AccountValidationError as e:
                error_msg = f"Erreur validation compte {config.platform}: {str(e)}"
                logger.error(error_msg)
                state["errors"].append(error_msg)
            except Exception as e:
                error_msg = f"Erreur formatage {config.platform}_{config.content_type}: {str(e)}"
                logger.error(error_msg)
                state["errors"].append(error_msg)

        state["formatted_content"] = formatted_content
        state["current_step"] = "content_formatted"

        return state

    async def _publish_content_node(self, state: WorkflowState) -> WorkflowState:
        """Nœud de publication (simulé pour l'instant)"""
        logger.info(f"Publication du contenu pour la tâche {state['task_id']}")

        formatted_content = state.get("formatted_content", {})
        publication_results = {}

        for platform, content in formatted_content.items():
            try:
                # Pour l'instant, on simule la publication
                # Dans la vraie implémentation, ici on appellerait les agents de publication
                result = await self._simulate_publication(platform, content)
                publication_results[platform] = result

                logger.info(f"Publication simulée réussie pour {platform}")

            except Exception as e:
                error_msg = f"Erreur publication {platform}: {str(e)}"
                logger.error(error_msg)
                state["errors"].append(error_msg)
                publication_results[platform] = {"status": "failed", "error": str(e)}

        state["publication_results"] = publication_results
        state["current_step"] = "content_published"

        return state

    async def _finalize_results_node(self, state: WorkflowState) -> WorkflowState:
        """Nœud de finalisation des résultats"""
        logger.info(f"Finalisation des résultats pour la tâche {state['task_id']}")

        state["current_step"] = "completed"

        # Calculer le statut global
        publication_results = state.get("publication_results", {})
        has_errors = len(state.get("errors", [])) > 0

        if has_errors or not publication_results:
            state["current_step"] = "failed"

        return state

    # === Méthodes de formatage avec comptes ===

    async def _format_twitter_content(self, content: str, config: PlatformContentConfig, account) -> TwitterPostOutput:
        """Formate le contenu pour Twitter"""
        constraints = {
            "max_length": "280 caractères",
            "hashtags": config.hashtags,
            "mentions": config.mentions,
            "account": account.account_name
        }

        formatted = await llm_service.format_content_for_platform(
            content, "twitter", "post", constraints
        )

        twitter_output = TwitterPostOutput(
            tweet=formatted,
            image_s3_url=config.image_s3_url
        )

        if config.image_s3_url:
            twitter_output.image_s3_url = config.image_s3_url
            logger.info(f"🖼️ Image S3 ajoutée au formatting: {config.image_s3_url}")

        return twitter_output

    async def _format_facebook_content(self, content: str, config: PlatformContentConfig,
                                       account) -> FacebookPostOutput:
        """Formate le contenu pour Facebook"""
        constraints = {
            "lien_source": config.lien_source,
            "hashtags": config.hashtags,
            "account": account.account_name
        }

        formatted = await llm_service.format_content_for_platform(
            content, "facebook", "post", constraints
        )

        return FacebookPostOutput(message=formatted)

    async def _format_linkedin_content(self, content: str, config: PlatformContentConfig,
                                       account) -> LinkedInPostOutput:
        """Formate le contenu pour LinkedIn"""
        constraints = {
            "tone": "professionnel",
            "lien_source": config.lien_source,
            "hashtags": config.hashtags,
            "account": account.account_name
        }

        formatted = await llm_service.format_content_for_platform(
            content, "linkedin", "post", constraints
        )

        return LinkedInPostOutput(contenu=formatted)

    async def _format_instagram_post(self, content: str, config: PlatformContentConfig, account) -> InstagramPostOutput:
        """Formate le contenu pour Instagram Post"""
        constraints = {
            "tone": "décontracté avec émojis",
            "hashtags": config.hashtags,
            "mention": config.mentions[0] if config.mentions else None,
            "account": account.account_name
        }

        formatted = await llm_service.format_content_for_platform(
            content, "instagram", "post", constraints
        )

        return InstagramPostOutput(legende=formatted, hashtags=config.hashtags)

    async def _format_instagram_story(self, content: str, config: PlatformContentConfig,
                                      account) -> InstagramStoryOutput:
        """Formate le contenu pour Instagram Story"""
        constraints = {
            "max_length": "50 caractères maximum",
            "style": "très court et percutant",
            "lien_sticker": config.lien_sticker,
            "account": account.account_name
        }

        formatted = await llm_service.format_content_for_platform(
            content, "instagram", "story", constraints
        )

        return InstagramStoryOutput(texte_story=formatted[:50])  # Sécurité longueur

    async def _format_instagram_carousel(self, content: str, config: PlatformContentConfig,
                                         account) -> InstagramCarouselOutput:
        """Formate le contenu pour Instagram Carousel avec gestion des images"""

        # Gestion des images
        images_urls = config.images_urls
        images_generated = False

        if not images_urls:
            # Pas d'images fournies -> génération automatique
            nb_slides = config.nb_slides or 5
            images_urls = generate_images(nb_slides, content[:100])
            images_generated = True
            logger.info(f"Images générées automatiquement pour le carrousel: {len(images_urls)} images")
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

    async def _simulate_publication(self, platform: str, content: Any) -> Dict[str, Any]:
        """Publication réelle ou simulée selon la plateforme"""
        if platform == "twitter_post":
            return await self._publish_to_twitter(content)
        else:
            # Simulation pour les autres plateformes
            return {
                "status": "success",
                "post_id": f"fake_id_{uuid.uuid4().hex[:8]}",
                "post_url": f"https://{platform}.com/fake_post",
                "published_at": datetime.now().isoformat()
            }

    # Dans app/orchestrator/workflow.py, remplacer _publish_to_twitter() :

    async def _publish_to_twitter(self, content) -> Dict[str, Any]:
        """Publication réelle sur Twitter avec support d'image S3"""
        try:
            from app.config.credentials import get_platform_credentials
            from requests_oauthlib import OAuth1Session
            import asyncio
            import json
            import boto3
            import tempfile
            import os

            # Récupérer les credentials Twitter pour StuffGaming
            creds = get_platform_credentials(SiteWeb.STUFFGAMING, PlatformType.TWITTER)

            # Préparer le tweet
            tweet_text = content.tweet if hasattr(content, 'tweet') else str(content)

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
                if hasattr(content, 'image_s3_url') and content.image_s3_url:
                    try:
                        from app.config.settings import settings
                        import os

                        logger.info(f"📸 Téléchargement image S3: {content.image_s3_url}")

                        # ✅ DEBUG : Vérifier les credentials
                        aws_key = settings.aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
                        aws_secret = settings.aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
                        aws_region = settings.aws_default_region or os.getenv('AWS_DEFAULT_REGION', 'eu-west-3')

                        logger.info(f"🔑 AWS Key: {aws_key[:10] + '...' if aws_key else 'NOT_SET'}")
                        logger.info(f"🌍 AWS Region: {aws_region}")

                        if not aws_key or not aws_secret:
                            raise Exception(
                                f"AWS credentials manquantes - Key: {bool(aws_key)}, Secret: {bool(aws_secret)}")

                        # Parse S3 URL (format: s3://bucket/path)
                        if content.image_s3_url.startswith('s3://'):
                            s3_path = content.image_s3_url[5:]  # Remove 's3://'
                            bucket, key = s3_path.split('/', 1)
                        else:
                            raise Exception(f"Format S3 URL non supporté: {content.image_s3_url}")

                        logger.info(f"📦 S3 Bucket: {bucket}, Key: {key}")

                        # ✅ CORRECTION : Créer le client S3 avec credentials explicites
                        s3_client = boto3.client(
                            's3',
                            aws_access_key_id=aws_key,
                            aws_secret_access_key=aws_secret,
                            region_name=aws_region
                        )

                        logger.info("✅ Client S3 créé avec succès")

                        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                            logger.info(f"⬇️ Téléchargement de {bucket}/{key} vers {tmp_file.name}")
                            s3_client.download_file(bucket, key, tmp_file.name)
                            logger.info("✅ Téléchargement S3 réussi")

                            # Upload vers Twitter
                            with open(tmp_file.name, 'rb') as img_file:
                                logger.info("⬆️ Upload vers Twitter...")
                                upload_response = twitter.post(
                                    "https://upload.twitter.com/1.1/media/upload.json",
                                    files={"media": img_file}
                                )

                                if upload_response.status_code == 200:
                                    media_data = upload_response.json()
                                    media_id = media_data["media_id_string"]
                                    logger.info(f"✅ Image uploadée vers Twitter, Media ID: {media_id}")
                                else:
                                    logger.error(
                                        f"❌ Erreur upload Twitter: {upload_response.status_code} - {upload_response.text}")

                            # Nettoyer le fichier temporaire
                            os.unlink(tmp_file.name)
                            logger.info("🧹 Fichier temporaire supprimé")

                    except Exception as e:
                        logger.error(f"❌ Erreur traitement image S3: {str(e)}")

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

                # Ajouter info image si présente
                if hasattr(content, 'image_s3_url') and content.image_s3_url:
                    logger.info(f"🖼️ Image: {content.image_s3_url}")

                return {
                    "status": "success",
                    "post_id": tweet_id,
                    "post_url": f"https://twitter.com/i/web/status/{tweet_id}",
                    "published_at": datetime.now().isoformat(),
                    "tweet_text": tweet_text,
                    "image_uploaded": bool(hasattr(content, 'image_s3_url') and content.image_s3_url)
                }
            else:
                logger.error(f"❌ Erreur Twitter API: {response.status_code} - {response.text}")
                return {
                    "status": "failed",
                    "error": f"Twitter API error: {response.status_code}",
                    "details": response.text
                }

        except Exception as e:
            logger.error(f"❌ Erreur lors de la publication Twitter: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }

    async def execute_workflow(self, request: EnhancedPublicationRequest) -> WorkflowState:
        """Exécute le workflow complet"""
        task_id = str(uuid.uuid4())

        initial_state: WorkflowState = {
            "request": request,
            "content_generated": None,
            "formatted_content": {},
            "publication_results": {},
            "errors": [],
            "current_step": "initialized",
            "task_id": task_id
        }

        logger.info(f"Démarrage du workflow {task_id}")
        logger.info(f"Configurations: {[(c.platform, c.content_type) for c in request.platforms_config]}")

        try:
            final_state = await self.workflow.ainvoke(initial_state)
            logger.info(f"Workflow {task_id} terminé avec statut: {final_state['current_step']}")
            return final_state

        except Exception as e:
            logger.error(f"Erreur dans le workflow {task_id}: {str(e)}")
            initial_state["errors"].append(f"Erreur workflow: {str(e)}")
            initial_state["current_step"] = "failed"
            return initial_state


# Instance globale de l'orchestrateur
orchestrator = ContentPublisherOrchestrator()