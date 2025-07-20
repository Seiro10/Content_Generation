from typing import Dict, Any, List
from app.models.content import EnhancedPublicationRequest, PlatformSpecificResult
from app.models.base import PlatformType, TaskStatus, ContentType
from app.models.accounts import SiteWeb
from app.services.tasks.content_generation import generate_base_content_task
from app.services.tasks.content_formatting import format_multiplatform_task
from app.services.tasks.content_publishing import publish_multiplatform_task
import logging
import uuid
from datetime import datetime
from celery import group, chord, chain
from celery.result import AsyncResult

logger = logging.getLogger(__name__)


class CeleryContentPublisherOrchestrator:
    """
    Orchestrateur utilisant Celery pour la publication multi-plateformes
    Alternative à LangGraph pour un déploiement distribué
    """

    def __init__(self):
        self.task_store: Dict[str, Dict[str, Any]] = {}

    def execute_workflow_async(self, request: EnhancedPublicationRequest) -> str:
        """
        Exécute le workflow de publication de manière asynchrone avec Celery
        Retourne l'ID de la tâche principale
        """
        task_id = str(uuid.uuid4())

        logger.info(f"Starting async workflow {task_id} for {request.site_web}")
        logger.info(f"Platforms: {[(c.platform, c.content_type) for c in request.platforms_config]}")

        # Initialiser le suivi de la tâche
        self.task_store[task_id] = {
            'status': 'pending',
            'request': request.dict(),
            'created_at': datetime.now().isoformat(),
            'steps': [],
            'results': {}
        }

        try:
            # Créer la chaîne de tâches Celery
            workflow_chain = self._create_workflow_chain(request, task_id)

            # Lancer la chaîne
            async_result = workflow_chain.apply_async()

            # Stocker l'ID de la tâche Celery
            self.task_store[task_id]['celery_task_id'] = async_result.id
            self.task_store[task_id]['status'] = 'processing'

            logger.info(f"Workflow {task_id} submitted to Celery with task ID {async_result.id}")

            return task_id

        except Exception as e:
            logger.error(f"Error starting workflow {task_id}: {str(e)}")
            self.task_store[task_id]['status'] = 'failed'
            self.task_store[task_id]['error'] = str(e)
            raise

    def _create_workflow_chain(self, request: EnhancedPublicationRequest, workflow_id: str):
        """
        Crée une chaîne de tâches Celery pour le workflow
        """
        # Étape 1: Génération du contenu de base
        content_generation = generate_base_content_task.s(request.dict())

        # Étape 2: Formatage parallèle pour toutes les plateformes
        formatting_step = format_multiplatform_task.s(
            request.texte_source,
            request.site_web.value,
            [config.dict() for config in request.platforms_config]
        )

        # Étape 3: Publication parallèle sur toutes les plateformes
        publishing_step = publish_multiplatform_task.s(request.site_web.value)

        # Créer la chaîne : génération -> formatage -> publication
        workflow_chain = chain(
            content_generation,
            formatting_step,
            publishing_step
        )

        return workflow_chain

    def get_workflow_status(self, task_id: str) -> Dict[str, Any]:
        """
        Récupère le statut d'un workflow
        """
        if task_id not in self.task_store:
            return {
                'task_id': task_id,
                'status': 'not_found',
                'error': 'Task not found'
            }

        task_info = self.task_store[task_id]

        # Vérifier le statut dans Celery si une tâche est en cours
        if 'celery_task_id' in task_info and task_info['status'] == 'processing':
            try:
                celery_result = AsyncResult(task_info['celery_task_id'])

                # Mettre à jour le statut basé sur Celery
                if celery_result.ready():
                    if celery_result.successful():
                        task_info['status'] = 'completed'
                        task_info['results'] = celery_result.result
                        task_info['completed_at'] = datetime.now().isoformat()
                    else:
                        task_info['status'] = 'failed'
                        task_info['error'] = str(celery_result.info)
                        task_info['completed_at'] = datetime.now().isoformat()
                else:
                    # Récupérer des informations de progression si disponibles
                    if celery_result.info and isinstance(celery_result.info, dict):
                        task_info['current_step'] = celery_result.info.get('step', 'processing')
                        task_info['progress'] = celery_result.info.get('progress', 0)

            except Exception as e:
                logger.error(f"Error checking Celery task status: {str(e)}")
                task_info['status'] = 'failed'
                task_info['error'] = f"Error checking task status: {str(e)}"

        return task_info

    def get_all_workflows(self) -> Dict[str, Dict[str, Any]]:
        """
        Retourne tous les workflows en cours ou terminés
        """
        return self.task_store

    def cancel_workflow(self, task_id: str) -> bool:
        """
        Annule un workflow en cours
        """
        if task_id not in self.task_store:
            return False

        task_info = self.task_store[task_id]

        if 'celery_task_id' in task_info:
            try:
                # Annuler la tâche Celery
                from app.services.celery_app import celery_app
                celery_app.control.revoke(task_info['celery_task_id'], terminate=True)

                task_info['status'] = 'cancelled'
                task_info['cancelled_at'] = datetime.now().isoformat()

                logger.info(f"Workflow {task_id} cancelled")
                return True

            except Exception as e:
                logger.error(f"Error cancelling workflow {task_id}: {str(e)}")
                return False

        return False

    def retry_workflow(self, task_id: str) -> str:
        """
        Relance un workflow qui a échoué
        """
        if task_id not in self.task_store:
            raise ValueError(f"Workflow {task_id} not found")

        original_task = self.task_store[task_id]

        if original_task['status'] not in ['failed', 'cancelled']:
            raise ValueError(f"Cannot retry workflow in status: {original_task['status']}")

        # Recréer la demande originale
        request_data = original_task['request']
        request = EnhancedPublicationRequest.parse_obj(request_data)

        # Lancer un nouveau workflow
        new_task_id = self.execute_workflow_async(request)

        logger.info(f"Workflow {task_id} retried as {new_task_id}")

        return new_task_id

    def get_workflow_metrics(self) -> Dict[str, Any]:
        """
        Retourne des métriques sur les workflows
        """
        total_workflows = len(self.task_store)

        status_counts = {}
        site_counts = {}
        platform_counts = {}

        for task_info in self.task_store.values():
            # Compter par statut
            status = task_info['status']
            status_counts[status] = status_counts.get(status, 0) + 1

            # Compter par site web
            if 'request' in task_info:
                request_data = task_info['request']
                site_web = request_data.get('site_web', 'unknown')
                site_counts[site_web] = site_counts.get(site_web, 0) + 1

                # Compter par plateforme
                platforms_config = request_data.get('platforms_config', [])
                for config in platforms_config:
                    platform = config.get('platform', 'unknown')
                    platform_counts[platform] = platform_counts.get(platform, 0) + 1

        return {
            'total_workflows': total_workflows,
            'status_distribution': status_counts,
            'site_distribution': site_counts,
            'platform_distribution': platform_counts,
            'generated_at': datetime.now().isoformat()
        }


# Instance globale de l'orchestrateur Celery
celery_orchestrator = CeleryContentPublisherOrchestrator()