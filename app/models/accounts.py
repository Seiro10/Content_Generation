from pydantic import BaseModel, Field
from typing import Dict, Optional, List
from enum import Enum

from app.models.base import PlatformType


class SiteWeb(str, Enum):
    """Sites web supportés"""
    STUFFGAMING = "stuffgaming.fr"
    GAMING = "gaming.com"
    FOOTBALL = "football.com"


class AccountConfig(BaseModel):
    """Configuration d'un compte spécifique"""
    site_web: SiteWeb
    platform: PlatformType

    # Identifiants de compte
    account_id: str = Field(..., description="Identifiant unique du compte")
    account_name: str = Field(..., description="Nom d'affichage du compte")

    # Tokens/clés d'authentification
    access_token: Optional[str] = None
    access_token_secret: Optional[str] = None  # Pour Twitter
    app_id: Optional[str] = None  # Pour Facebook/Instagram

    # Configuration spécifique plateforme
    business_account_id: Optional[str] = None  # Instagram Business
    page_id: Optional[str] = None  # Facebook Page

    # Métadonnées
    is_active: bool = True
    created_at: Optional[str] = None
    last_used: Optional[str] = None


class AccountMapping(BaseModel):
    """Mapping complet des comptes par site/plateforme"""
    accounts: Dict[str, AccountConfig] = Field(default_factory=dict)

    def get_account_key(self, site_web: SiteWeb, platform: PlatformType) -> str:
        """Génère la clé unique pour un compte"""
        return f"{site_web}_{platform}"

    def add_account(self, account: AccountConfig) -> None:
        """Ajoute un compte au mapping"""
        key = self.get_account_key(account.site_web, account.platform)
        self.accounts[key] = account

    def get_account(self, site_web: SiteWeb, platform: PlatformType) -> Optional[AccountConfig]:
        """Récupère la configuration d'un compte"""
        key = self.get_account_key(site_web, platform)
        return self.accounts.get(key)

    def list_accounts_for_site(self, site_web: SiteWeb) -> List[AccountConfig]:
        """Liste tous les comptes d'un site"""
        return [
            account for account in self.accounts.values()
            if account.site_web == site_web
        ]

    def list_active_accounts(self) -> List[AccountConfig]:
        """Liste tous les comptes actifs"""
        return [
            account for account in self.accounts.values()
            if account.is_active
        ]


# Configuration par défaut des 9 comptes
def create_default_accounts() -> AccountMapping:
    """Crée la configuration par défaut des comptes"""
    mapping = AccountMapping()

    sites = [SiteWeb.STUFFGAMING, SiteWeb.GAMING, SiteWeb.FOOTBALL]
    platforms = [PlatformType.INSTAGRAM, PlatformType.TWITTER, PlatformType.FACEBOOK]

    for site in sites:
        for platform in platforms:
            account = AccountConfig(
                site_web=site,
                platform=platform,
                account_id=f"{site}_{platform}_account_id",
                account_name=f"{site.replace('.', '_').title()} {platform.title()}",
                # Les tokens seront configurés via les variables d'environnement
                access_token=f"token_{site}_{platform}",
                is_active=True
            )

            # Configuration spécifique par plateforme
            if platform == PlatformType.INSTAGRAM:
                account.business_account_id = f"ig_business_{site}"
            elif platform == PlatformType.FACEBOOK:
                account.page_id = f"fb_page_{site}"
                account.app_id = f"fb_app_{site}"
            elif platform == PlatformType.TWITTER:
                account.access_token_secret = f"token_secret_{site}"

            mapping.add_account(account)

    return mapping


# Instance globale du mapping des comptes
account_mapping = create_default_accounts()


class AccountValidationError(Exception):
    """Erreur de validation de compte"""
    pass


def validate_account_exists(site_web: SiteWeb, platform: PlatformType) -> AccountConfig:
    """Valide qu'un compte existe et le retourne"""
    account = account_mapping.get_account(site_web, platform)

    if not account:
        raise AccountValidationError(
            f"Aucun compte configuré pour {site_web} sur {platform}"
        )

    if not account.is_active:
        raise AccountValidationError(
            f"Le compte {site_web}/{platform} est désactivé"
        )

    return account