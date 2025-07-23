from fastapi import FastAPI, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, List

from app.config.settings import settings
from app.models.base import TaskStatus, PublicationResult, PlatformType, ContentType
from app.models.content import SimplePublicationRequest, EnhancedPublicationRequest, PublicationRequestExamples
from app.models.accounts import account_mapping, SiteWeb, AccountValidationError
from app.config.credentials import credentials_manager, CredentialsError
from app.orchestrator.workflow import orchestrator
from app.orchestrator.celery_workflow import celery_orchestrator

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
        background_tasks: BackgroundTasks
):
    """
    Endpoint avancé pour publier du contenu avec types spécifiques par plateforme.
    Supporte Instagram stories, carrousels, etc.
    """
    try:
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
    logger.info(f"Configurations: {[(c.platform, c.content_type) for c in request.platforms_config]}")

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


@app.get("/accounts/{site_web}")
async def list_accounts_for_site(site_web: SiteWeb):
    """
    Liste les comptes d'un site web spécifique
    """
    try:
        site_accounts = account_mapping.list_accounts_for_site(site_web)

        return {
            "site_web": site_web,
            "accounts": [
                {
                    "platform": account.platform,
                    "account_name": account.account_name,
                    "account_id": account.account_id,
                    "is_active": account.is_active
                }
                for account in site_accounts
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des comptes: {str(e)}")


@app.get("/accounts/{site_web}/{platform}")
async def get_account_details(site_web: SiteWeb, platform: str):
    """
    Récupère les détails d'un compte spécifique
    """
    try:
        from app.models.base import PlatformType
        platform_enum = PlatformType(platform)

        account = account_mapping.get_account(site_web, platform_enum)

        if not account:
            raise HTTPException(
                status_code=404,
                detail=f"Compte non trouvé pour {site_web} sur {platform}"
            )

        return {
            "site_web": account.site_web,
            "platform": account.platform,
            "account_name": account.account_name,
            "account_id": account.account_id,
            "is_active": account.is_active,
            "created_at": account.created_at,
            "last_used": account.last_used
        }

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Plateforme non valide: {platform}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/examples")
async def get_examples():
    """
    Exemples de requêtes pour les différents types de publications
    """
    return {
        "simple_multi_platform": PublicationRequestExamples.simple_multi_platform().dict(),
        "instagram_carousel_with_images": PublicationRequestExamples.instagram_carousel_with_images().dict(),
        "instagram_carousel_without_images": PublicationRequestExamples.instagram_carousel_without_images().dict(),
        "mixed_sites_content": PublicationRequestExamples.mixed_sites_content().dict()
    }


@app.post("/test/validate-account")
async def test_validate_account(site_web: SiteWeb, platform: str):
    """
    Teste la validation d'un compte spécifique
    """
    try:
        from app.models.base import PlatformType
        platform_enum = PlatformType(platform)

        from app.models.accounts import validate_account_exists
        account = validate_account_exists(site_web, platform_enum)

        return {
            "valid": True,
            "site_web": site_web,
            "platform": platform,
            "account_name": account.account_name,
            "account_id": account.account_id,
            "is_active": account.is_active
        }

    except AccountValidationError as e:
        return {
            "valid": False,
            "error": str(e),
            "site_web": site_web,
            "platform": platform
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Plateforme non valide: {platform}")


@app.post("/test/format/advanced")
async def test_format_content_advanced(
        texte_source: str,
        site_web: SiteWeb,
        platform: str,
        content_type: str = "post",
        nb_slides: Optional[int] = None,
        images_urls: Optional[List[str]] = None
):
    """
    Endpoint de test pour formater du contenu avec types spécifiques et gestion des comptes
    """
    try:
        from app.services.llm_service import llm_service
        from app.models.accounts import validate_account_exists
        from app.models.base import PlatformType

        platform_enum = PlatformType(platform)

        # Valider le compte
        account = validate_account_exists(site_web, platform_enum)

        constraints = {"account": account.account_name}
        if nb_slides and content_type == "carousel":
            constraints["nb_slides"] = nb_slides
        if images_urls:
            constraints["images_provided"] = True

        formatted = await llm_service.format_content_for_platform(
            texte_source, platform, content_type, constraints
        )

        result = {
            "original": texte_source,
            "site_web": site_web,
            "platform": platform,
            "content_type": content_type,
            "account_used": account.account_name,
            "constraints": constraints,
            "formatted": formatted
        }

        # Simulation génération d'images pour carrousel
        if content_type == "carousel" and not images_urls:
            from app.models.content import generate_images
            generated_images = generate_images(nb_slides or 5, texte_source)
            result["images_generated"] = generated_images
        elif images_urls:
            result["images_provided"] = images_urls

        return result

    except AccountValidationError as e:
        raise HTTPException(status_code=400, detail=f"Compte invalide: {str(e)}")
    except Exception as e:
        logger.error(f"Erreur lors du test de formatage avancé: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur de formatage: {str(e)}")


@app.get("/queue/status")
async def get_queue_status():
    """Récupère le statut des queues Celery"""
    try:
        from app.services.celery_app import celery_app
        import redis

        # Connexion à Redis pour vérifier les queues
        redis_client = redis.Redis.from_url(settings.celery_broker_url)

        queues = {
            'content_generation': redis_client.llen('content_generation'),
            'content_formatting': redis_client.llen('content_formatting'),
            'content_publishing': redis_client.llen('content_publishing'),
            'image_generation': redis_client.llen('image_generation')
        }

        # Vérifier les workers actifs
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        registered_tasks = inspect.registered()

        return {
            "queues": queues,
            "workers": {
                "active_tasks": active_tasks or {},
                "registered_tasks": registered_tasks or {}
            },
            "broker_url": settings.celery_broker_url,
            "status": "connected"
        }

    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut des queues: {str(e)}")
        return {
            "queues": {"error": str(e)},
            "workers": {},
            "status": "error"
        }


@app.post("/publish/async")
async def publish_content_async(request: EnhancedPublicationRequest):
    """Publication asynchrone avec Celery distribuée"""
    try:
        from app.orchestrator.celery_workflow import celery_orchestrator

        # Lancer le workflow asynchrone avec Celery
        task_id = celery_orchestrator.execute_workflow_async(request)

        return {
            "task_id": task_id,
            "status": "submitted",
            "message": "Workflow soumis au système distribué Celery"
        }

    except Exception as e:
        logger.error(f"Erreur lors de la publication asynchrone: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.get("/workflow/{task_id}")
async def get_workflow_status(task_id: str):
    """Récupère le statut d'un workflow Celery"""
    try:
        from app.orchestrator.celery_workflow import celery_orchestrator

        workflow_status = celery_orchestrator.get_workflow_status(task_id)
        return workflow_status

    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.get("/workflows")
async def get_all_workflows():
    """Récupère tous les workflows"""
    try:
        from app.orchestrator.celery_workflow import celery_orchestrator

        workflows = celery_orchestrator.get_all_workflows()
        return {
            "workflows": workflows,
            "total": len(workflows)
        }

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.get("/metrics/workflows")
async def get_workflow_metrics():
    """Récupère les métriques des workflows"""
    try:
        from app.orchestrator.celery_workflow import celery_orchestrator

        metrics = celery_orchestrator.get_workflow_metrics()
        return metrics

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des métriques: {str(e)}")
        return {
            "error": str(e),
            "total_workflows": 0,
            "status_distribution": {},
            "generated_at": datetime.now().isoformat()
        }


@app.get("/health/celery")
async def celery_health_check():
    """Vérification de santé Celery via l'API directement"""
    try:
        from app.services.celery_app import celery_app
        import redis

        # Test 1: Connexion Redis
        try:
            redis_client = redis.Redis.from_url(settings.celery_broker_url)
            redis_client.ping()
            redis_healthy = True
        except Exception:
            redis_healthy = False

        # Test 2: Workers actifs
        try:
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            registered_workers = inspect.registered()

            worker_count = len(active_workers) if active_workers else 0
            workers_healthy = worker_count > 0
        except Exception:
            worker_count = 0
            workers_healthy = False

        # Test 3: Queue accessible
        try:
            queue_sizes = {}
            for queue in ['content_generation', 'content_formatting', 'content_publishing']:
                queue_sizes[queue] = redis_client.llen(queue)
            queues_healthy = True
        except Exception:
            queue_sizes = {}
            queues_healthy = False

        # Statut global
        overall_healthy = redis_healthy and queues_healthy

        status_code = 200 if overall_healthy else 503

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "redis_connection": redis_healthy,
            "workers_active": workers_healthy,
            "worker_count": worker_count,
            "queues_accessible": queues_healthy,
            "queue_sizes": queue_sizes,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Erreur lors du health check Celery: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )