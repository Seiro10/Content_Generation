from pydantic import BaseModel, Field
from typing import Dict, Optional
import os
from app.models.accounts import SiteWeb
from app.models.base import PlatformType


class TwitterCredentials(BaseModel):
    """Credentials pour Twitter API v2"""
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str
    bearer_token: Optional[str] = None


class FacebookCredentials(BaseModel):
    """Credentials pour Facebook Graph API"""
    app_id: str
    app_secret: str
    access_token: str  # Page Access Token
    page_id: str


class InstagramCredentials(BaseModel):
    """Credentials pour Instagram Graph API"""
    access_token: str  # Same as Facebook for Business accounts
    business_account_id: str
    app_id: str  # Facebook App ID
    app_secret: str  # Facebook App Secret


class LinkedInCredentials(BaseModel):
    """Credentials pour LinkedIn API"""
    client_id: str
    client_secret: str
    access_token: str
    organization_id: Optional[str] = None  # Pour les pages entreprise


class CredentialsManager:
    """Gestionnaire centralisé des credentials par site/plateforme"""

    def __init__(self):
        self.credentials: Dict[str, Dict[str, object]] = {}
        self._load_credentials_from_env()

    def _load_credentials_from_env(self):
        """Charge les credentials depuis les variables d'environnement"""

        for site in SiteWeb:
            site_key = site.value.replace('.', '_').upper()  # STUFFGAMING_FR
            self.credentials[site.value] = {}

            # Twitter credentials
            twitter_creds = self._load_twitter_credentials(site_key)
            if twitter_creds:
                self.credentials[site.value][PlatformType.TWITTER] = twitter_creds

            # Facebook credentials
            facebook_creds = self._load_facebook_credentials(site_key)
            if facebook_creds:
                self.credentials[site.value][PlatformType.FACEBOOK] = facebook_creds

            # Instagram credentials
            instagram_creds = self._load_instagram_credentials(site_key)
            if instagram_creds:
                self.credentials[site.value][PlatformType.INSTAGRAM] = instagram_creds

            # LinkedIn credentials
            linkedin_creds = self._load_linkedin_credentials(site_key)
            if linkedin_creds:
                self.credentials[site.value][PlatformType.LINKEDIN] = linkedin_creds

    def _load_twitter_credentials(self, site_key: str) -> Optional[TwitterCredentials]:
        """Charge les credentials Twitter pour un site"""
        try:
            return TwitterCredentials(
                api_key=os.getenv(f"{site_key}_TWITTER_API_KEY"),
                api_secret=os.getenv(f"{site_key}_TWITTER_API_SECRET"),
                access_token=os.getenv(f"{site_key}_TWITTER_ACCESS_TOKEN"),
                access_token_secret=os.getenv(f"{site_key}_TWITTER_ACCESS_TOKEN_SECRET"),
                bearer_token=os.getenv(f"{site_key}_TWITTER_BEARER_TOKEN")
            )
        except Exception:
            return None

    def _load_facebook_credentials(self, site_key: str) -> Optional[FacebookCredentials]:
        """Charge les credentials Facebook pour un site"""
        try:
            return FacebookCredentials(
                app_id=os.getenv(f"{site_key}_FACEBOOK_APP_ID"),
                app_secret=os.getenv(f"{site_key}_FACEBOOK_APP_SECRET"),
                access_token=os.getenv(f"{site_key}_FACEBOOK_ACCESS_TOKEN"),
                page_id=os.getenv(f"{site_key}_FACEBOOK_PAGE_ID")
            )
        except Exception:
            return None

    def _load_instagram_credentials(self, site_key: str) -> Optional[InstagramCredentials]:
        """Charge les credentials Instagram pour un site"""
        try:
            return InstagramCredentials(
                access_token=os.getenv(f"{site_key}_INSTAGRAM_ACCESS_TOKEN"),
                business_account_id=os.getenv(f"{site_key}_INSTAGRAM_BUSINESS_ACCOUNT_ID"),
                app_id=os.getenv(f"{site_key}_FACEBOOK_APP_ID"),  # Same as Facebook
                app_secret=os.getenv(f"{site_key}_FACEBOOK_APP_SECRET")  # Same as Facebook
            )
        except Exception:
            return None

    def _load_linkedin_credentials(self, site_key: str) -> Optional[LinkedInCredentials]:
        """Charge les credentials LinkedIn pour un site"""
        try:
            return LinkedInCredentials(
                client_id=os.getenv(f"{site_key}_LINKEDIN_CLIENT_ID"),
                client_secret=os.getenv(f"{site_key}_LINKEDIN_CLIENT_SECRET"),
                access_token=os.getenv(f"{site_key}_LINKEDIN_ACCESS_TOKEN"),
                organization_id=os.getenv(f"{site_key}_LINKEDIN_ORGANIZATION_ID")
            )
        except Exception:
            return None

    def get_credentials(self, site_web: SiteWeb, platform: PlatformType) -> Optional[object]:
        """Récupère les credentials pour un site/plateforme"""
        site_creds = self.credentials.get(site_web.value, {})
        return site_creds.get(platform)

    def has_credentials(self, site_web: SiteWeb, platform: PlatformType) -> bool:
        """Vérifie si les credentials existent pour un site/plateforme"""
        return self.get_credentials(site_web, platform) is not None

    def list_available_credentials(self) -> Dict[str, list]:
        """Liste les credentials disponibles par site"""
        result = {}
        for site, platforms in self.credentials.items():
            result[site] = list(platforms.keys())
        return result

    def validate_credentials(self, site_web: SiteWeb, platform: PlatformType) -> tuple[bool, str]:
        """Valide que tous les champs requis sont présents"""
        creds = self.get_credentials(site_web, platform)

        if not creds:
            return False, f"Aucun credential configuré pour {site_web.value}/{platform.value}"

        # Vérification par type de plateforme
        if platform == PlatformType.TWITTER:
            if not all([creds.api_key, creds.api_secret, creds.access_token, creds.access_token_secret]):
                return False, "Credentials Twitter incomplets"

        elif platform == PlatformType.FACEBOOK:
            if not all([creds.app_id, creds.app_secret, creds.access_token, creds.page_id]):
                return False, "Credentials Facebook incomplets"

        elif platform == PlatformType.INSTAGRAM:
            if not all([creds.access_token, creds.business_account_id, creds.app_id]):
                return False, "Credentials Instagram incomplets"

        elif platform == PlatformType.LINKEDIN:
            if not all([creds.client_id, creds.client_secret, creds.access_token]):
                return False, "Credentials LinkedIn incomplets"

        return True, "Credentials valides"


# Instance globale du gestionnaire de credentials
credentials_manager = CredentialsManager()


class CredentialsError(Exception):
    """Erreur liée aux credentials"""
    pass


def get_platform_credentials(site_web: SiteWeb, platform: PlatformType):
    """
    Fonction utilitaire pour récupérer les credentials avec validation
    """
    creds = credentials_manager.get_credentials(site_web, platform)

    if not creds:
        raise CredentialsError(
            f"Credentials manquants pour {site_web.value}/{platform.value}"
        )

    is_valid, message = credentials_manager.validate_credentials(site_web, platform)
    if not is_valid:
        raise CredentialsError(f"Credentials invalides: {message}")

    return creds