from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from app.models.base import PlatformType, ContentType
from app.models.accounts import SiteWeb


class PlatformContentConfig(BaseModel):
    """Configuration pour une plateforme spécifique"""
    platform: PlatformType
    content_type: ContentType = ContentType.POST
    hashtags: Optional[List[str]] = None
    mentions: Optional[List[str]] = None
    lien_source: Optional[str] = None
    lien_sticker: Optional[str] = None

    # Configuration Instagram carrousel
    nb_slides: Optional[int] = None
    titre_carousel: Optional[str] = None
    images_urls: Optional[List[str]] = None
    # Pour Twitter + image depuis S3
    image_s3_url: Optional[str] = None

    # 🆕 NOUVEAU : Paramètre de visibilité
    published: bool = True  # True = publié immédiatement, False = draft/non publié


class SimplePublicationRequest(BaseModel):
    """Requête de publication simple (rétrocompatible)"""
    texte_source: str = Field(..., description="Texte source à adapter")
    site_web: SiteWeb = Field(..., description="Site web pour lequel publier")
    plateformes: List[PlatformType] = Field(..., description="Plateformes ciblées")
    hashtags: Optional[List[str]] = Field(default=None, description="Hashtags suggérés")
    mentions: Optional[List[str]] = Field(default=None, description="Mentions à inclure")
    lien_source: Optional[str] = Field(default=None, description="Lien vers la source")

    def to_enhanced_request(self) -> 'EnhancedPublicationRequest':
        """Convertit vers le format avancé"""
        platforms_config = []

        for platform in self.plateformes:
            config = PlatformContentConfig(
                platform=platform,
                content_type=ContentType.POST,
                hashtags=self.hashtags,
                mentions=self.mentions,
                lien_source=self.lien_source
            )
            platforms_config.append(config)

        return EnhancedPublicationRequest(
            texte_source=self.texte_source,
            site_web=self.site_web,
            platforms_config=platforms_config
        )


class EnhancedPublicationRequest(BaseModel):
    """Requête de publication avancée avec types spécifiques"""
    texte_source: str = Field(..., description="Texte source à adapter")
    site_web: SiteWeb = Field(..., description="Site web pour lequel publier")
    platforms_config: List[PlatformContentConfig] = Field(..., description="Configurations par plateforme")

    @property
    def plateformes(self) -> List[PlatformType]:
        """Compatibilité avec l'ancien format"""
        return [config.platform for config in self.platforms_config]


class PlatformSpecificResult(BaseModel):
    """Résultat spécifique à une plateforme"""
    platform: PlatformType
    content_type: ContentType
    site_web: SiteWeb
    status: str
    formatted_content: Optional[Dict[str, Any]] = None
    publication_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class PublicationRequestExamples:
    """Exemples de requêtes pour les tests"""

    @staticmethod
    def simple_multi_platform() -> SimplePublicationRequest:
        """Exemple de publication simple multi-plateformes"""
        return SimplePublicationRequest(
            texte_source="Découvrez notre nouvelle fonctionnalité révolutionnaire qui va transformer votre expérience gaming !",
            site_web=SiteWeb.STUFFGAMING,
            plateformes=[PlatformType.TWITTER, PlatformType.INSTAGRAM, PlatformType.FACEBOOK],
            hashtags=["#Gaming", "#Innovation", "#StuffGaming"]
        )

    @staticmethod
    def instagram_carousel_with_images() -> EnhancedPublicationRequest:
        """Exemple de carrousel Instagram avec images S3"""
        return EnhancedPublicationRequest(
            texte_source="Top 5 des jeux les plus attendus de 2024 : des graphismes époustouflants, des histoires captivantes et une jouabilité révolutionnaire vous attendent !",
            site_web=SiteWeb.STUFFGAMING,
            platforms_config=[
                PlatformContentConfig(
                    platform=PlatformType.INSTAGRAM,
                    content_type=ContentType.CAROUSEL,
                    nb_slides=5,
                    titre_carousel="Top 5 Jeux 2024",
                    hashtags=["#Gaming", "#Top5", "#Jeux2024", "#StuffGaming"],
                    images_urls=[
                        "https://s3.amazonaws.com/stuffgaming/games/stellar-blade.jpg",
                        "https://s3.amazonaws.com/stuffgaming/games/dragons-dogma-2.jpg",
                        "https://s3.amazonaws.com/stuffgaming/games/black-myth-wukong.jpg",
                        "https://s3.amazonaws.com/stuffgaming/games/helldivers-2.jpg",
                        "https://s3.amazonaws.com/stuffgaming/games/ff7-rebirth.jpg"
                    ]
                )
            ]
        )

    @staticmethod
    def instagram_carousel_without_images() -> EnhancedPublicationRequest:
        """Exemple de carrousel Instagram sans images (génération auto)"""
        return EnhancedPublicationRequest(
            texte_source="Guide complet pour débuter le gaming compétitif : stratégies, équipement, mentalité et conseils de pros pour progresser rapidement.",
            site_web=SiteWeb.STUFFGAMING,
            platforms_config=[
                PlatformContentConfig(
                    platform=PlatformType.INSTAGRAM,
                    content_type=ContentType.CAROUSEL,
                    nb_slides=4,
                    titre_carousel="Guide Gaming Compétitif",
                    hashtags=["#Gaming", "#Esport", "#Guide", "#Conseils"]
                    # Pas d'images_urls = génération automatique
                )
            ]
        )

    @staticmethod
    def mixed_sites_content() -> EnhancedPublicationRequest:
        """Exemple avec contenu multi-types"""
        return EnhancedPublicationRequest(
            texte_source="Breaking news : le transfert le plus surprenant de l'année vient d'être officialisé ! Les fans sont en délire sur les réseaux sociaux.",
            site_web=SiteWeb.FOOTBALL,
            platforms_config=[
                PlatformContentConfig(
                    platform=PlatformType.INSTAGRAM,
                    content_type=ContentType.STORY,
                    lien_sticker="https://football.com/transfert-choc"
                ),
                PlatformContentConfig(
                    platform=PlatformType.TWITTER,
                    content_type=ContentType.POST,
                    hashtags=["#TransfertChoc", "#Football", "#BreakingNews"]
                ),
                PlatformContentConfig(
                    platform=PlatformType.FACEBOOK,
                    content_type=ContentType.POST,
                    hashtags=["#Football", "#Transfert"],
                    lien_source="https://football.com/article-transfert"
                )
            ]
        )

    @staticmethod
    def draft_example() -> EnhancedPublicationRequest:
        """🆕 Exemple de création de drafts"""
        return EnhancedPublicationRequest(
            texte_source="Contenu à vérifier avant publication",
            site_web=SiteWeb.STUFFGAMING,
            platforms_config=[
                PlatformContentConfig(
                    platform=PlatformType.FACEBOOK,
                    content_type=ContentType.POST,
                    hashtags=["#Gaming", "#Draft"],
                    published=False  # 🆕 Draft Facebook
                ),
                PlatformContentConfig(
                    platform=PlatformType.INSTAGRAM,
                    content_type=ContentType.POST,
                    hashtags=["#Gaming", "#Preview"],
                    published=False  # 🆕 Draft simulé Instagram
                ),
                PlatformContentConfig(
                    platform=PlatformType.TWITTER,
                    content_type=ContentType.POST,
                    hashtags=["#Gaming", "#Review"],
                    published=False  # 🆕 Draft simulé Twitter
                )
            ]
        )

    @staticmethod
    def instagram_carousel() -> EnhancedPublicationRequest:
        """Alias pour la compatibilité"""
        return PublicationRequestExamples.instagram_carousel_without_images()

    @staticmethod
    def mixed_content_types() -> EnhancedPublicationRequest:
        """Alias pour la compatibilité"""
        return PublicationRequestExamples.mixed_sites_content()


def generate_images(nb_images: int, context: str) -> List[str]:
    """
    Fonction utilitaire pour générer des URLs d'images (placeholder)
    """
    import uuid

    generated_urls = []
    for i in range(nb_images):
        image_id = str(uuid.uuid4())[:8]
        # Génération d'URLs d'images simulées
        image_url = f"https://generated-images.s3.amazonaws.com/carousel_{image_id}_{i + 1}.jpg"
        generated_urls.append(image_url)

    return generated_urls