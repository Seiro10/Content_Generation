from pydantic import BaseModel, Field, validator
from typing import List, Optional


# === TWITTER ===
class TwitterPostInput(BaseModel):
    """Entrée pour formatage Twitter"""
    texte_source: str
    hashtags: Optional[List[str]] = None
    mentions: Optional[List[str]] = None


class TwitterPostOutput(BaseModel):
    """Sortie formatée pour Twitter"""
    tweet: str = Field(..., max_length=280, description="Tweet formaté (≤280 caractères)")
    medias: Optional[List[str]] = Field(default=None, description="URLs des médias")
    image_s3_url: Optional[str] = Field(default=None)

    @validator('tweet')
    def validate_tweet_length(cls, v):
        if len(v) > 280:
            raise ValueError('Le tweet ne peut pas dépasser 280 caractères')
        return v


# === FACEBOOK ===
class FacebookPostInput(BaseModel):
    """Entrée pour formatage Facebook"""
    texte_source: str
    lien_source: Optional[str] = None
    hashtags: Optional[List[str]] = None


class FacebookPostOutput(BaseModel):
    """Sortie formatée pour Facebook"""
    message: str = Field(..., description="Message Facebook formaté")
    media: Optional[str] = Field(default=None, description="URL du média")


# === LINKEDIN ===
class LinkedInPostInput(BaseModel):
    """Entrée pour formatage LinkedIn"""
    texte_source: str
    lien_source: Optional[str] = None
    hashtags: Optional[List[str]] = None


class LinkedInPostOutput(BaseModel):
    """Sortie formatée pour LinkedIn"""
    contenu: str = Field(..., description="Contenu LinkedIn professionnel")
    media: Optional[str] = Field(default=None, description="URL du média")


# === INSTAGRAM ===
class InstagramPostInput(BaseModel):
    """Entrée pour formatage Instagram Post"""
    texte_source: str
    hashtags: Optional[List[str]] = None
    mention: Optional[str] = None


class InstagramPostOutput(BaseModel):
    """Sortie formatée pour Instagram Post"""
    legende: str = Field(..., max_length=2000, description="Légende Instagram (≤2000 caractères)")
    hashtags: Optional[List[str]] = Field(default=None, description="Hashtags extraits")


class InstagramStoryInput(BaseModel):
    """Entrée pour formatage Instagram Story"""
    texte_source: str
    lien_sticker: Optional[str] = None


class InstagramStoryOutput(BaseModel):
    """Sortie formatée pour Instagram Story"""
    texte_story: str = Field(..., max_length=50, description="Texte story très court (≤50 caractères)")
    elements_graphiques: Optional[List[str]] = Field(default=None, description="Suggestions visuelles")


class InstagramCarouselInput(BaseModel):
    """Entrée pour formatage Instagram Carousel"""
    texte_source: str
    nb_slides: Optional[int] = Field(default=5, ge=2, le=10, description="Nombre de slides (2-10)")
    titre_carousel: Optional[str] = None
    images_urls: Optional[List[str]] = Field(default=None, description="URLs des images S3 pour le carrousel")


class InstagramCarouselOutput(BaseModel):
    """Sortie formatée pour Instagram Carousel"""
    slides: List[str] = Field(..., description="Textes pour chaque slide")
    legende: str = Field(..., description="Légende globale du carrousel")
    hashtags: Optional[List[str]] = Field(default=None, description="Hashtags du carrousel")
    images_urls: Optional[List[str]] = Field(default=None, description="URLs des images à utiliser")
    images_generated: bool = Field(default=False, description="True si les images ont été générées")

    @validator('slides')
    def validate_slides_count(cls, v, values):
        nb_slides = values.get('nb_slides', 5)
        if len(v) < 2 or len(v) > 10:
            raise ValueError('Le carrousel doit contenir entre 2 et 10 slides')
        return v


# === RÉSULTATS DE PUBLICATION ===
class PublicationSuccess(BaseModel):
    """Résultat de publication réussie"""
    post_id: str = Field(..., description="ID du post publié")
    post_url: Optional[str] = Field(default=None, description="URL du post")
    platform: str
    published_at: str


class PublicationError(BaseModel):
    """Erreur de publication"""
    platform: str
    error_code: Optional[str] = None
    error_message: str
    retry_possible: bool = False