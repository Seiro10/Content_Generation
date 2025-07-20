from celery import current_task
from app.services.celery_app import celery_app
from app.services.llm_service import llm_service
from app.models.content import EnhancedPublicationRequest
from app.orchestrator.workflow import orchestrator
import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='content_generation.generate_base_content')
def generate_base_content_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tâche Celery pour générer le contenu de base avec Claude
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': 'Starting content generation'})

        # Reconstruire l'objet request à partir des données
        request = EnhancedPublicationRequest.parse_obj(request_data)

        logger.info(f"Starting content generation for task {self.request.id}")

        # Appeler le service LLM de manière synchrone
        system_prompt = """Tu es un expert en création de contenu pour les réseaux sociaux.
        Génère un contenu de base qui pourra être adapté pour différentes plateformes."""

        prompt = f"""
        Texte source à transformer:
        {request.texte_source}

        Site web: {request.site_web}
        Plateformes cibles: {', '.join([c.platform.value for c in request.platforms_config])}

        Génère un contenu de base engageant et informatif.
        """

        self.update_state(state='PROGRESS', meta={'step': 'Calling Claude LLM'})

        # Utiliser asyncio.run pour exécuter la fonction async de manière synchrone
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            generated_content = loop.run_until_complete(
                llm_service.generate_content(prompt, system_prompt)
            )
        finally:
            loop.close()

        logger.info(f"Content generation completed for task {self.request.id}")

        return {
            'task_id': self.request.id,
            'status': 'completed',
            'generated_content': generated_content,
            'request_data': request_data
        }

    except Exception as e:
        logger.error(f"Error in content generation task {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': 'Content generation failed'}
        )
        raise


@celery_app.task(bind=True, name='content_generation.process_publication_workflow')
def process_publication_workflow_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tâche Celery pour traiter le workflow complet de publication
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': 'Starting publication workflow'})

        # Reconstruire l'objet request
        request = EnhancedPublicationRequest.parse_obj(request_data)

        logger.info(f"Starting publication workflow for task {self.request.id}")

        # Exécuter le workflow LangGraph de manière synchrone
        self.update_state(state='PROGRESS', meta={'step': 'Executing LangGraph workflow'})

        # Utiliser asyncio.run pour exécuter le workflow async de manière synchrone
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(orchestrator.execute_workflow(request))
        finally:
            loop.close()

        logger.info(f"Publication workflow completed for task {self.request.id}")

        return {
            'task_id': self.request.id,
            'status': 'completed',
            'workflow_result': result,
            'request_data': request_data
        }

    except Exception as e:
        logger.error(f"Error in publication workflow task {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': 'Publication workflow failed'}
        )
        raise


@celery_app.task(bind=True, name='content_generation.generate_images')
def generate_images_task(self, context: str, nb_images: int = 5) -> Dict[str, Any]:
    """
    Tâche Celery pour générer des images (placeholder pour l'instant)
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': 'Starting image generation'})

        logger.info(f"Starting image generation for task {self.request.id}")

        # Utiliser la fonction de génération d'images
        from app.models.content import generate_images

        self.update_state(state='PROGRESS', meta={'step': 'Generating images'})

        generated_urls = generate_images(nb_images, context)

        logger.info(f"Image generation completed for task {self.request.id}")

        return {
            'task_id': self.request.id,
            'status': 'completed',
            'images_urls': generated_urls,
            'context': context,
            'nb_images': nb_images
        }

    except Exception as e:
        logger.error(f"Error in image generation task {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': 'Image generation failed'}
        )
        raise