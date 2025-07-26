from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
import logging
import uuid
from datetime import datetime

from app.models.base import PlatformType, TaskStatus, ContentType
from app.models.content import EnhancedPublicationRequest, PlatformContentConfig
from app.models.accounts import validate_account_exists, AccountValidationError
from app.services.llm_service import llm_service

# Import des agents formatters
from app.agents.formatters.twitter import twitter_formatter
from app.agents.formatters.instagram import instagram_formatter

# Import des agents publishers
from app.agents.publishers.twitter import twitter_publisher
from app.agents.publishers.instagram import instagram_publisher

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
    """Orchestrateur LangGraph simplifié utilisant les agents spécialisés"""

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
        """Nœud de formatage utilisant les agents formatters"""
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

                # Utiliser les agents formatters spécialisés
                if config.platform == PlatformType.TWITTER:
                    formatted = await twitter_formatter.format_content(base_content, config, account)
                    formatted_content[config_key] = formatted

                elif config.platform == PlatformType.INSTAGRAM:
                    formatted = await instagram_formatter.format_content(base_content, config, account)
                    formatted_content[config_key] = formatted

                # TODO: Ajouter Facebook et LinkedIn formatters
                elif config.platform == PlatformType.FACEBOOK:
                    # Temporaire: formatage simple
                    formatted_content[config_key] = {"message": f"[Facebook] {base_content}"}

                elif config.platform == PlatformType.LINKEDIN:
                    # Temporaire: formatage simple
                    formatted_content[config_key] = {"contenu": f"[LinkedIn] {base_content}"}

                else:
                    raise ValueError(f"Plateforme non supportée: {config.platform}")

                logger.info(f"Contenu formaté pour {config_key} (compte: {account.account_name})")

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
        """Nœud de publication utilisant les agents publishers avec respect du paramètre published"""
        logger.info(f"Publication du contenu pour la tâche {state['task_id']}")

        formatted_content = state.get("formatted_content", {})
        publication_results = {}
        request = state["request"]

        for platform_key, content in formatted_content.items():
            try:
                # Parse platform and content type from key
                platform_str, content_type_str = platform_key.split('_', 1)
                platform = PlatformType(platform_str)
                content_type = ContentType(content_type_str)

                # 🆕 TROUVER LA CONFIG CORRESPONDANTE POUR VÉRIFIER LE PARAMÈTRE PUBLISHED
                matching_config = None
                for config in request.platforms_config:
                    if config.platform == platform and config.content_type == content_type:
                        matching_config = config
                        break

                if not matching_config:
                    logger.warning(f"Config non trouvée pour {platform_key}")
                    continue

                # 🆕 VÉRIFIER LE PARAMÈTRE PUBLISHED
                if not matching_config.published:
                    logger.info(f"🚫 Publication ignorée pour {platform_key} (published=False)")
                    publication_results[platform_key] = {
                        "status": "draft_created",
                        "platform": platform_str,
                        "content_type": content_type_str,
                        "message": "Contenu sauvegardé en draft (non publié)",
                        "published": False
                    }
                    continue

                # Récupérer le compte
                account = validate_account_exists(request.site_web, platform)

                # 🆕 PASSER LE PARAMÈTRE PUBLISHED AUX PUBLISHERS
                if platform == PlatformType.TWITTER:
                    result = await twitter_publisher.publish_content(
                        content, request.site_web, account, published=matching_config.published
                    )
                    publication_results[platform_key] = result

                elif platform == PlatformType.INSTAGRAM:
                    result = await instagram_publisher.publish_content(
                        content, request.site_web, account, content_type, published=matching_config.published
                    )
                    publication_results[platform_key] = result

                else:
                    # Simulation pour les autres plateformes
                    if matching_config.published:
                        result = {
                            "status": "simulated_success",
                            "post_id": f"fake_id_{uuid.uuid4().hex[:8]}",
                            "post_url": f"https://{platform_str}.com/fake_post",
                            "published_at": datetime.now().isoformat(),
                            "published": True
                        }
                    else:
                        result = {
                            "status": "draft_created",
                            "draft_id": f"fake_draft_{uuid.uuid4().hex[:8]}",
                            "platform": platform_str,
                            "message": "Draft simulé créé",
                            "published": False
                        }
                    publication_results[platform_key] = result

                if matching_config.published:
                    logger.info(f"✅ Publication terminée pour {platform_key}: {result.get('status')}")
                else:
                    logger.info(f"📝 Draft créé pour {platform_key}: {result.get('status')}")

            except Exception as e:
                error_msg = f"Erreur publication {platform_key}: {str(e)}"
                logger.error(error_msg)
                state["errors"].append(error_msg)
                publication_results[platform_key] = {"status": "failed", "error": str(e)}

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