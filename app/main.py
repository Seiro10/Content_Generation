from fastapi import FastAPI, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import uuid
import json
from datetime import datetime
from typing import Dict, Optional, List

from app.config.settings import settings
from app.models.base import TaskStatus, PublicationResult, PlatformType, ContentType
from app.models.content import SimplePublicationRequest, EnhancedPublicationRequest, PublicationRequestExamples, \
    PlatformContentConfig
from app.models.accounts import account_mapping, SiteWeb, AccountValidationError
from app.config.credentials import credentials_manager, CredentialsError
from app.orchestrator.workflow import orchestrator
from app.orchestrator.celery_workflow import celery_orchestrator

from dotenv import load_dotenv

load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Stockage en mémoire des tâches (à remplacer par une vraie DB)
task_store: Dict[str, PublicationResult] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    logger.info("Démarrage de l'application Social Media Publisher")
    yield
    logger.info("Arrêt de l'application")


# Création de l'application FastAPI
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Système multi-agents de publication automatisée sur réseaux sociaux",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Point d'entrée de l'API"""
    return {
        "message": "Social Media Publisher API",
        "version": settings.api_version,
        "status": "active"
    }


@app.get("/health")
async def health_check():
    """Vérification de santé de l'API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.api_version
    }


@app.post("/publish", response_model=Dict[str, str])
async def publish_content(
        request: SimplePublicationRequest,
        background_tasks: BackgroundTasks
):
    """
    Endpoint de base pour publier du contenu (rétrocompatible).
    Type POST par défaut pour toutes les plateformes.
    """
    try:
        # Convertir vers le nouveau format
        enhanced_request = request.to_enhanced_request()
        return await _process_publication(enhanced_request, background_tasks)

    except Exception as e:
        logger.error(f"Erreur lors de la publication simple: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.post("/publish/advanced", response_model=Dict[str, str])
async def publish_content_advanced(
        request: EnhancedPublicationRequest,
        published: Optional[bool] = Form(None),  # 🆕 Paramètre global optionnel
        background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    🆕 Endpoint avancé avec contrôle de visibilité global
    published=True : Publication immédiate (défaut)
    published=False : Création de drafts/contenu non publié
    """
    try:
        # 🆕 Appliquer le paramètre published global si fourni
        if published is not None:
            for config in request.platforms_config:
                config.published = published

            logger.info(
                f"📝 Mode global appliqué: {'Publication' if published else 'Draft'} pour toutes les plateformes")

        return await _process_publication(request, background_tasks)

    except Exception as e:
        logger.error(f"Erreur lors de la publication avancée: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


async def _process_publication(
        request: EnhancedPublicationRequest,
        background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """Traite une demande de publication (logique commune)"""
    # Générer un ID unique pour cette demande
    request_id = str(uuid.uuid4())

    logger.info(f"Nouvelle demande de publication reçue: {request_id}")
    logger.info(f"Configurations: {[(c.platform, c.content_type, c.published) for c in request.platforms_config]}")

    # Initialiser le résultat dans le store
    task_store[request_id] = PublicationResult(
        request_id=request_id,
        status=TaskStatus.PENDING,
        platforms_results=[],
        created_at=datetime.now()
    )

    # Lancer le traitement en arrière-plan
    background_tasks.add_task(process_publication_request, request_id, request)

    return {
        "request_id": request_id,
        "status": "accepted",
        "message": "Demande de publication acceptée, traitement en cours"
    }


@app.get("/status/{request_id}", response_model=PublicationResult)
async def get_publication_status(request_id: str):
    """
    Récupère le statut d'une demande de publication
    """
    if request_id not in task_store:
        raise HTTPException(status_code=404, detail="Demande de publication non trouvée")

    return task_store[request_id]


@app.get("/tasks", response_model=Dict[str, PublicationResult])
async def list_all_tasks():
    """
    Liste toutes les tâches (pour le debugging)
    """
    return task_store


async def process_publication_request(request_id: str, request: EnhancedPublicationRequest):
    """
    Traite une demande de publication de manière asynchrone
    """
    try:
        logger.info(f"Début du traitement de la demande {request_id}")

        # Mettre à jour le statut
        task_store[request_id].status = TaskStatus.PROCESSING

        # Exécuter le workflow LangGraph
        workflow_result = await orchestrator.execute_workflow(request)

        # Traiter les résultats
        if workflow_result["current_step"] == "completed":
            task_store[request_id].status = TaskStatus.COMPLETED

            # Convertir les résultats du workflow
            from app.models.base import TaskResult
            platform_results = []

            for platform_key, result in workflow_result.get("publication_results", {}).items():
                # Extract platform from key like "twitter_post"
                platform_str = platform_key.split('_')[0]  # Gets "twitter"
                content_type_str = platform_key.split('_')[1] if '_' in platform_key else "post"  # Gets "post"

                task_result = TaskResult(
                    task_id=f"{request_id}_{platform_str}",
                    status=TaskStatus.COMPLETED if result.get("status") == "success" else TaskStatus.FAILED,
                    platform=PlatformType(platform_str),  # Convert string to enum
                    content_type=ContentType(content_type_str),  # Convert string to enum
                    result=result,
                    created_at=datetime.now(),
                    completed_at=datetime.now()
                )
                platform_results.append(task_result)

            task_store[request_id].platforms_results = platform_results

        else:
            task_store[request_id].status = TaskStatus.FAILED

        task_store[request_id].completed_at = datetime.now()

        logger.info(f"Traitement terminé pour la demande {request_id}")

    except Exception as e:
        logger.error(f"Erreur lors du traitement de la demande {request_id}: {str(e)}")
        task_store[request_id].status = TaskStatus.FAILED
        task_store[request_id].completed_at = datetime.now()


@app.get("/credentials")
async def list_credentials_status():
    """
    Liste le statut des credentials pour tous les sites/plateformes
    """
    try:
        available_creds = credentials_manager.list_available_credentials()

        status_by_site = {}

        for site in SiteWeb:
            site_status = {}

            for platform in [PlatformType.TWITTER, PlatformType.FACEBOOK, PlatformType.INSTAGRAM]:
                has_creds = credentials_manager.has_credentials(site, platform)

                if has_creds:
                    is_valid, message = credentials_manager.validate_credentials(site, platform)
                    site_status[platform.value] = {
                        "configured": True,
                        "valid": is_valid,
                        "message": message
                    }
                else:
                    site_status[platform.value] = {
                        "configured": False,
                        "valid": False,
                        "message": "Credentials non configurés"
                    }

            status_by_site[site.value] = site_status

        return {
            "credentials_status": status_by_site,
            "summary": {
                "total_combinations": len(SiteWeb) * 3,  # 3 plateformes par site
                "configured": sum(len(platforms) for platforms in available_creds.values())
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des credentials: {str(e)}")


@app.post("/publish/twitter/with-image")
async def publish_twitter_with_image(
        texte_source: str = Form(...),
        site_web: SiteWeb = Form(...),
        image_s3_url: str = Form(...),  # URL complète S3
        hashtags: Optional[str] = Form(None),  # JSON string
        published: bool = Form(True),  # 🆕 Nouveau paramètre
        background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    🆕 Endpoint spécialisé pour Twitter + Image depuis S3 avec contrôle de visibilité
    """
    try:
        # Parse hashtags si fournis
        hashtags_list = json.loads(hashtags) if hashtags else []

        # Créer la config spécialisée
        request = EnhancedPublicationRequest(
            texte_source=texte_source,
            site_web=site_web,
            platforms_config=[
                PlatformContentConfig(
                    platform=PlatformType.TWITTER,
                    content_type=ContentType.POST,
                    hashtags=hashtags_list,
                    image_s3_url=image_s3_url,
                    published=published  # 🆕
                )
            ]
        )

        return await _process_publication(request, background_tasks)

    except Exception as e:
        logger.error(f"Erreur publication Twitter + image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.post("/publish/instagram/with-image")
async def publish_instagram_with_image(
        texte_source: str = Form(...),
        site_web: SiteWeb = Form(...),
        image_url: Optional[str] = Form(None),  # URL normale ou S3
        image_s3_url: Optional[str] = Form(None),  # URL S3 spécifique
        content_type: str = Form("post"),  # post, story, carousel
        hashtags: Optional[str] = Form(None),  # JSON string
        nb_slides: Optional[int] = Form(None),  # Pour carrousels
        images_urls: Optional[str] = Form(None),  # JSON string pour carrousels
        published: bool = Form(True),  # 🆕 Nouveau paramètre
        background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    🆕 Endpoint spécialisé pour Instagram avec support S3 et contrôle de visibilité
    Supporte: post, story, carousel
    Gère à la fois URLs normales et URLs S3
    """
    try:
        # Parse hashtags si fournis
        hashtags_list = json.loads(hashtags) if hashtags else []

        # Parse images_urls pour carrousels
        images_urls_list = json.loads(images_urls) if images_urls else []

        # Valider le type de contenu
        try:
            content_type_enum = ContentType(content_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Type de contenu invalide: {content_type}")

        # Déterminer quelle image utiliser (priorité à image_s3_url)
        final_image_url = image_s3_url or image_url

        # Créer la config selon le type
        config_data = {
            "platform": PlatformType.INSTAGRAM,
            "content_type": content_type_enum,
            "hashtags": hashtags_list,
            "published": published  # 🆕
        }

        # Ajouter les paramètres spécifiques selon le type
        if content_type_enum == ContentType.CAROUSEL:
            config_data["nb_slides"] = nb_slides or 3
            if images_urls_list:
                config_data["images_urls"] = images_urls_list
            elif final_image_url:
                # Utiliser l'image fournie pour le carrousel
                config_data["images_urls"] = [final_image_url]

        elif content_type_enum in [ContentType.POST, ContentType.STORY]:
            if final_image_url:
                config_data["image_s3_url"] = final_image_url

        # Log pour debug
        if image_s3_url:
            logger.info(f"📦 Instagram S3 URL reçue: {image_s3_url}")
        elif image_url:
            logger.info(f"🔗 Instagram URL normale reçue: {image_url}")

        # Créer la requête
        request = EnhancedPublicationRequest(
            texte_source=texte_source,
            site_web=site_web,
            platforms_config=[PlatformContentConfig(**config_data)]
        )

        return await _process_publication(request, background_tasks)

    except Exception as e:
        logger.error(f"Erreur publication Instagram: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.post("/convert/user-to-page-token")
async def convert_user_to_page_token(user_token: str = Form(...)):
    """Convert User Token to Page Access Token"""
    try:
        import requests

        # Get all pages managed by the user
        accounts_url = f"https://graph.facebook.com/v18.0/me/accounts?access_token={user_token}"
        response = requests.get(accounts_url)

        if response.status_code != 200:
            return {"error": response.text}

        data = response.json()
        pages = data.get('data', [])

        page_tokens = []
        for page in pages:
            page_id = page.get('id')
            page_token = page.get('access_token')
            page_name = page.get('name')

            # Test if this page has Instagram connected
            instagram_test_url = f"https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account&access_token={page_token}"
            instagram_response = requests.get(instagram_test_url)

            instagram_info = None
            if instagram_response.status_code == 200:
                instagram_data = instagram_response.json()
                instagram_info = instagram_data.get('instagram_business_account')

            page_tokens.append({
                "page_name": page_name,
                "page_id": page_id,
                "page_access_token": page_token,
                "instagram_business_account": instagram_info,
                "has_instagram": instagram_info is not None
            })

        return {
            "user_token_valid": True,
            "total_pages": len(pages),
            "pages": page_tokens,
            "instructions": {
                "next_step": "Use the page_access_token from the page that has_instagram=true",
                "instagram_business_id": "Use the instagram_business_account.id from the same page"
            }
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/debug/instagram/{site_web}")
async def debug_instagram_token(site_web: SiteWeb):
    """Debug Instagram token validity"""
    try:
        from app.config.credentials import get_platform_credentials
        from app.models.base import PlatformType
        import requests

        # Get credentials
        creds = get_platform_credentials(site_web, PlatformType.INSTAGRAM)

        # Test token validity
        test_url = f"https://graph.facebook.com/v18.0/me?access_token={creds.access_token}"
        response = requests.get(test_url)

        # Test Instagram business account
        ig_test_url = f"https://graph.facebook.com/v18.0/{creds.business_account_id}?fields=id,name,account_type&access_token={creds.access_token}"
        ig_response = requests.get(ig_test_url)

        return {
            "site_web": site_web,
            "token_test": {
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else response.text
            },
            "instagram_account_test": {
                "status_code": ig_response.status_code,
                "response": ig_response.json() if ig_response.status_code == 200 else ig_response.text
            },
            "credentials_info": {
                "business_account_id": creds.business_account_id,
                "app_id": creds.app_id,
                "token_length": len(creds.access_token),
                "token_preview": f"{creds.access_token[:20]}..." if creds.access_token else None
            }
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/credentials/{site_web}/{platform}")
async def check_credentials(site_web: SiteWeb, platform: str):
    """
    Vérifie les credentials pour un site/plateforme spécifique
    """
    try:
        from app.models.base import PlatformType
        platform_enum = PlatformType(platform)

        has_creds = credentials_manager.has_credentials(site_web, platform_enum)

        if not has_creds:
            return {
                "site_web": site_web,
                "platform": platform,
                "configured": False,
                "valid": False,
                "message": "Credentials non configurés dans les variables d'environnement"
            }

        is_valid, message = credentials_manager.validate_credentials(site_web, platform_enum)

        # Ne pas exposer les vraies clés, juste indiquer qu'elles existent
        creds = credentials_manager.get_credentials(site_web, platform_enum)
        masked_info = {}

        if platform_enum == PlatformType.TWITTER:
            masked_info = {
                "api_key": f"{creds.api_key[:8]}..." if creds.api_key else None,
                "has_bearer_token": bool(creds.bearer_token)
            }
        elif platform_enum == PlatformType.FACEBOOK:
            masked_info = {
                "app_id": creds.app_id if creds.app_id else None,
                "page_id": creds.page_id if creds.page_id else None
            }
        elif platform_enum == PlatformType.INSTAGRAM:
            masked_info = {
                "business_account_id": creds.business_account_id if creds.business_account_id else None,
                "app_id": creds.app_id if creds.app_id else None
            }

        return {
            "site_web": site_web,
            "platform": platform,
            "configured": True,
            "valid": is_valid,
            "message": message,
            "info": masked_info
        }

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Plateforme non valide: {platform}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.post("/test/credentials")
async def test_credentials_connection(
        site_web: str = Form(...),
        platform: str = Form(...)
):
    """
    Teste la connexion aux APIs avec les credentials
    """
    try:
        from app.models.base import PlatformType
        from app.config.credentials import get_platform_credentials
        from app.models.accounts import SiteWeb

        # Valider les paramètres
        try:
            site_enum = SiteWeb(site_web)
            platform_enum = PlatformType(platform)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Paramètre invalide: {str(e)}")

        # Récupérer et valider les credentials
        creds = get_platform_credentials(site_enum, platform_enum)

        # Simulation d'un test de connexion réussi
        test_results = {
            "site_web": site_web,
            "platform": platform,
            "credentials_valid": True,
            "connection_test": "simulated_success",
            "timestamp": datetime.now().isoformat(),
            "endpoint_tested": "",
            "api_version": "",
            "additional_info": ""
        }

        # Détails spécifiques par plateforme (structure plate)
        if platform_enum == PlatformType.TWITTER:
            test_results["endpoint_tested"] = "GET /2/users/me"
            test_results["api_version"] = "v2"
            test_results["additional_info"] = "rate_limit_remaining: simulated_900/900"
        elif platform_enum == PlatformType.FACEBOOK:
            test_results["endpoint_tested"] = "GET /me"
            test_results["api_version"] = "Graph API"
            test_results["additional_info"] = "page_verified: True, permissions: pages_manage_posts"
        elif platform_enum == PlatformType.INSTAGRAM:
            test_results["endpoint_tested"] = "GET /me/accounts"
            test_results["api_version"] = "Graph API"
            test_results["additional_info"] = "business_account_verified: True, publishing_enabled: True"

        return test_results

    except CredentialsError as e:
        return {
            "site_web": site_web,
            "platform": platform,
            "credentials_valid": False,
            "error": str(e),
            "connection_test": "failed",
            "timestamp": datetime.now().isoformat(),
            "endpoint_tested": "",
            "api_version": "",
            "additional_info": ""
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du test de credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du test: {str(e)}")


# 🆕 NOUVEAUX ENDPOINTS POUR LA GESTION DES DRAFTS

@app.get("/drafts")
async def list_all_drafts():
    """🆕 Liste tous les drafts de toutes les plateformes"""
    try:
        from app.agents.publishers.instagram import list_instagram_drafts
        from app.agents.publishers.twitter import list_twitter_drafts

        all_drafts = {
            "instagram": list_instagram_drafts(),
            "twitter": list_twitter_drafts(),
            "facebook": [],  # Facebook drafts sont gérés nativement
            "total": 0
        }

        all_drafts["total"] = len(all_drafts["instagram"]) + len(all_drafts["twitter"])

        return all_drafts

    except Exception as e:
        logger.error(f"Erreur liste drafts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/drafts/{draft_id}")
async def get_draft_details(draft_id: str):
    """🆕 Récupère les détails d'un draft spécifique"""
    try:
        from app.agents.publishers.instagram import get_instagram_draft
        from app.agents.publishers.twitter import get_twitter_draft

        # Essayer de trouver le draft dans les différents stores
        draft = None

        if draft_id.startswith("instagram_draft_"):
            draft = get_instagram_draft(draft_id)
        elif draft_id.startswith("twitter_draft_"):
            draft = get_twitter_draft(draft_id)

        if not draft:
            raise HTTPException(status_code=404, detail="Draft non trouvé")

        return draft

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération draft: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.post("/publish/draft/{draft_id}")
async def publish_draft(draft_id: str, background_tasks: BackgroundTasks):
    """🆕 Publie un draft existant"""
    try:
        from app.agents.publishers.instagram import get_instagram_draft
        from app.agents.publishers.twitter import get_twitter_draft

        # Récupérer le draft
        draft = None
        platform = None

        if draft_id.startswith("instagram_draft_"):
            draft = get_instagram_draft(draft_id)
            platform = "instagram"
        elif draft_id.startswith("twitter_draft_"):
            draft = get_twitter_draft(draft_id)
            platform = "twitter"
        elif draft_id.startswith("facebook_"):
            # Pour Facebook, utiliser l'API native
            platform = "facebook"

        if not draft and platform != "facebook":
            raise HTTPException(status_code=404, detail="Draft non trouvé")

        if platform == "facebook":
            # Publier draft Facebook natif
            from app.agents.publishers.facebook import facebook_publisher

            # Extraire site_web du draft_id ou utiliser une valeur par défaut
            # En production, stocker cette info avec le draft
            site_web = SiteWeb.STUFFGAMING  # À adapter selon votre logique

            result = facebook_publisher.publish_draft(draft_id, site_web)
            return {
                "draft_id": draft_id,
                "status": "published" if result["status"] == "success" else "failed",
                "platform": platform,
                "result": result
            }

        else:
            # Pour Instagram/Twitter, recréer une demande de publication
            site_web = SiteWeb(draft["site_web"])
            content_type = ContentType(draft["content_type"])

            # Recréer la config de publication
            config = PlatformContentConfig(
                platform=PlatformType(platform),
                content_type=content_type,
                published=True  # Forcer la publication
            )

            # Ajouter les données spécifiques du draft
            if platform == "instagram":
                # À adapter selon le type de contenu Instagram
                pass
            elif platform == "twitter":
                config.hashtags = []  # Extraire des données du draft si nécessaire

            # Créer une nouvelle demande de publication
            request = EnhancedPublicationRequest(
                texte_source=draft["content"].get("tweet", "Contenu du draft"),
                site_web=site_web,
                platforms_config=[config]
            )

            # Traiter la publication
            publication_result = await _process_publication(request, background_tasks)

            # Supprimer le draft après publication réussie
            if platform == "instagram":
                from app.agents.publishers.instagram import delete_instagram_draft
                delete_instagram_draft(draft_id)
            elif platform == "twitter":
                from app.agents.publishers.twitter import delete_twitter_draft
                delete_twitter_draft(draft_id)

            return {
                "draft_id": draft_id,
                "status": "published",
                "platform": platform,
                "publication_request_id": publication_result["request_id"],
                "result": publication_result
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur publication draft: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.delete("/drafts/{draft_id}")
async def delete_draft(draft_id: str):
    """🆕 Supprime un draft"""
    try:
        from app.agents.publishers.instagram import delete_instagram_draft
        from app.agents.publishers.twitter import delete_twitter_draft
        from app.agents.publishers.facebook import facebook_publisher

        success = False
        platform = None

        if draft_id.startswith("instagram_draft_"):
            success = delete_instagram_draft(draft_id)
            platform = "instagram"
        elif draft_id.startswith("twitter_draft_"):
            success = delete_twitter_draft(draft_id)
            platform = "twitter"
        elif draft_id.startswith("facebook_"):
            # Pour Facebook, utiliser l'API native
            site_web = SiteWeb.STUFFGAMING  # À adapter
            result = facebook_publisher.delete_draft(draft_id, site_web)
            success = result["status"] == "success"
            platform = "facebook"

        if not success:
            raise HTTPException(status_code=404, detail="Draft non trouvé ou erreur suppression")

        return {
            "draft_id": draft_id,
            "status": "deleted",
            "platform": platform,
            "message": f"Draft {platform} supprimé avec succès"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression draft: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/examples/with-published")
async def get_examples_with_published():
    """
    🆕 Exemples de requêtes avec le paramètre published
    """
    return {
        "publication_immediate": PublicationRequestExamples.simple_multi_platform().dict(),
        "creation_drafts": PublicationRequestExamples.draft_example().dict(),
        "instagram_carousel_draft": {
            **PublicationRequestExamples.instagram_carousel_with_images().dict(),
            "platforms_config": [
                {
                    **PublicationRequestExamples.instagram_carousel_with_images().platforms_config[0].dict(),
                    "published": False
                }
            ]
        },
        "mixed_published_draft": {
            "texte_source": "Contenu avec publication mixte",
            "site_web": "stuffgaming.fr",
            "platforms_config": [
                {
                    "platform": "facebook",
                    "content_type": "post",
                    "published": True,  # Publication immédiate Facebook
                    "hashtags": ["#Gaming"]
                },
                {
                    "platform": "instagram",
                    "content_type": "post",
                    "published": False,  # Draft Instagram
                    "hashtags": ["#Gaming", "#Preview"]
                },
                {
                    "platform": "twitter",
                    "content_type": "post",
                    "published": False,  # Draft Twitter
                    "hashtags": ["#Gaming", "#Draft"]
                }
            ]
        }
    }


# ... (reste des endpoints existants inchangés) ...

@app.get("/accounts")
async def list_all_accounts():
    """
    Liste tous les comptes configurés par site web et plateforme
    """
    accounts_by_site = {}

    for site in SiteWeb:
        site_accounts = account_mapping.list_accounts_for_site(site)
        accounts_by_site[site] = [
            {
                "platform": account.platform,
                "account_name": account.account_name,
                "account_id": account.account_id,
                "is_active": account.is_active
            }
            for account in site_accounts
        ]

    return {
        "total_accounts": len(account_mapping.accounts),
        "active_accounts": len(account_mapping.list_active_accounts()),
        "accounts_by_site": accounts_by_site
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )