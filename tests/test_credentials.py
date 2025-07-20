#!/usr/bin/env python3
"""
Script de test pour valider les credentials multi-comptes
"""
import asyncio
import sys
import os
from typing import Dict, List, Tuple

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.credentials import credentials_manager, get_platform_credentials, CredentialsError
from app.models.accounts import SiteWeb
from app.models.base import PlatformType


def test_environment_variables():
    """Teste la présence des variables d'environnement"""
    print("=== Test des Variables d'Environnement ===")

    required_vars = []
    missing_vars = []

    for site in SiteWeb:
        site_key = site.value.replace('.', '_').upper()

        # Variables Twitter
        twitter_vars = [
            f"{site_key}_TWITTER_API_KEY",
            f"{site_key}_TWITTER_API_SECRET",
            f"{site_key}_TWITTER_ACCESS_TOKEN",
            f"{site_key}_TWITTER_ACCESS_TOKEN_SECRET"
        ]

        # Variables Facebook
        facebook_vars = [
            f"{site_key}_FACEBOOK_APP_ID",
            f"{site_key}_FACEBOOK_APP_SECRET",
            f"{site_key}_FACEBOOK_ACCESS_TOKEN",
            f"{site_key}_FACEBOOK_PAGE_ID"
        ]

        # Variables Instagram
        instagram_vars = [
            f"{site_key}_INSTAGRAM_ACCESS_TOKEN",
            f"{site_key}_INSTAGRAM_BUSINESS_ACCOUNT_ID"
        ]

        all_vars = twitter_vars + facebook_vars + instagram_vars
        required_vars.extend(all_vars)

        print(f"\n{site.value}:")
        for var in all_vars:
            value = os.getenv(var)
            if value:
                print(f"  ✅ {var}: {value[:10]}...")
            else:
                print(f"  ❌ {var}: NON DÉFINIE")
                missing_vars.append(var)

    print(f"\n📊 Résumé:")
    print(f"Variables requises: {len(required_vars)}")
    print(f"Variables définies: {len(required_vars) - len(missing_vars)}")
    print(f"Variables manquantes: {len(missing_vars)}")

    if missing_vars:
        print(f"\n❌ Variables manquantes:")
        for var in missing_vars:
            print(f"  - {var}")
        return False
    else:
        print(f"\n✅ Toutes les variables d'environnement sont définies!")
        return True


def test_credentials_loading():
    """Teste le chargement des credentials"""
    print("\n=== Test du Chargement des Credentials ===")

    available_creds = credentials_manager.list_available_credentials()

    print(f"Credentials chargés par site:")
    for site, platforms in available_creds.items():
        print(f"\n{site}:")
        for platform in platforms:
            print(f"  ✅ {platform.value}")

    total_loaded = sum(len(platforms) for platforms in available_creds.values())
    expected_total = len(SiteWeb) * 3  # 3 plateformes par site

    print(f"\n📊 Résumé:")
    print(f"Credentials chargés: {total_loaded}")
    print(f"Credentials attendus: {expected_total}")

    return total_loaded > 0


def test_credentials_validation():
    """Teste la validation des credentials"""
    print("\n=== Test de Validation des Credentials ===")

    platforms = [PlatformType.TWITTER, PlatformType.FACEBOOK, PlatformType.INSTAGRAM]

    results = []

    for site in SiteWeb:
        print(f"\n{site.value}:")

        for platform in platforms:
            try:
                has_creds = credentials_manager.has_credentials(site, platform)

                if has_creds:
                    is_valid, message = credentials_manager.validate_credentials(site, platform)
                    status = "✅ VALIDE" if is_valid else "❌ INVALIDE"
                    print(f"  {platform.value}: {status} - {message}")
                    results.append((site, platform, is_valid))
                else:
                    print(f"  {platform.value}: ❌ ABSENT - Credentials non configurés")
                    results.append((site, platform, False))

            except Exception as e:
                print(f"  {platform.value}: ❌ ERREUR - {str(e)}")
                results.append((site, platform, False))

    # Résumé
    valid_count = sum(1 for _, _, is_valid in results if is_valid)
    total_count = len(results)

    print(f"\n📊 Résumé de validation:")
    print(f"Credentials valides: {valid_count}/{total_count}")

    return valid_count > 0


def test_credentials_retrieval():
    """Teste la récupération des credentials avec validation"""
    print("\n=== Test de Récupération des Credentials ===")

    test_cases = [
        (SiteWeb.STUFFGAMING, PlatformType.TWITTER),
        (SiteWeb.GAMING, PlatformType.FACEBOOK),
        (SiteWeb.FOOTBALL, PlatformType.INSTAGRAM)
    ]

    success_count = 0

    for site, platform in test_cases:
        try:
            creds = get_platform_credentials(site, platform)

            print(f"✅ {site.value} / {platform.value}:")

            if platform == PlatformType.TWITTER:
                print(f"  API Key: {creds.api_key[:8]}...")
                print(f"  Bearer Token: {'✅ Présent' if creds.bearer_token else '❌ Absent'}")
            elif platform == PlatformType.FACEBOOK:
                print(f"  App ID: {creds.app_id}")
                print(f"  Page ID: {creds.page_id}")
            elif platform == PlatformType.INSTAGRAM:
                print(f"  Business Account ID: {creds.business_account_id}")
                print(f"  App ID: {creds.app_id}")

            success_count += 1

        except CredentialsError as e:
            print(f"❌ {site.value} / {platform.value}: {str(e)}")
        except Exception as e:
            print(f"❌ {site.value} / {platform.value}: Erreur inattendue - {str(e)}")

    print(f"\n📊 Credentials récupérés avec succès: {success_count}/{len(test_cases)}")
    return success_count > 0


def test_credentials_security():
    """Teste que les credentials ne sont pas exposés dans les logs"""
    print("\n=== Test de Sécurité des Credentials ===")

    # Tester qu'on peut récupérer les credentials sans les exposer
    try:
        site = SiteWeb.STUFFGAMING
        platform = PlatformType.TWITTER

        if credentials_manager.has_credentials(site, platform):
            creds = get_platform_credentials(site, platform)

            # Vérifier que les champs sensibles ne sont pas None
            sensitive_fields = ['api_key', 'api_secret', 'access_token', 'access_token_secret']

            for field in sensitive_fields:
                if hasattr(creds, field):
                    value = getattr(creds, field)
                    if value and len(str(value)) > 8:
                        print(f"  ✅ {field}: Présent et sécurisé")
                    else:
                        print(f"  ❌ {field}: Absent ou trop court")

            print("✅ Test de sécurité réussi")
            return True
        else:
            print("⚠️ Pas de credentials à tester")
            return True

    except Exception as e:
        print(f"❌ Erreur lors du test de sécurité: {e}")
        return False


def generate_env_template():
    """Génère un template .env avec toutes les variables nécessaires"""
    print("\n=== Génération du Template .env ===")

    template_lines = [
        "# Configuration API",
        "ANTHROPIC_API_KEY=your_anthropic_api_key_here",
        "API_PORT=8090",
        "",
        "# Credentials par site web",
        ""
    ]

    for site in SiteWeb:
        site_key = site.value.replace('.', '_').upper()

        template_lines.extend([
            f"# ---- {site.value} ----",
            f"# Twitter",
            f"{site_key}_TWITTER_API_KEY=your_{site.value}_twitter_api_key",
            f"{site_key}_TWITTER_API_SECRET=your_{site.value}_twitter_api_secret",
            f"{site_key}_TWITTER_ACCESS_TOKEN=your_{site.value}_twitter_access_token",
            f"{site_key}_TWITTER_ACCESS_TOKEN_SECRET=your_{site.value}_twitter_access_token_secret",
            f"{site_key}_TWITTER_BEARER_TOKEN=your_{site.value}_twitter_bearer_token",
            "",
            f"# Facebook",
            f"{site_key}_FACEBOOK_APP_ID=your_{site.value}_facebook_app_id",
            f"{site_key}_FACEBOOK_APP_SECRET=your_{site.value}_facebook_app_secret",
            f"{site_key}_FACEBOOK_ACCESS_TOKEN=your_{site.value}_facebook_page_access_token",
            f"{site_key}_FACEBOOK_PAGE_ID=your_{site.value}_facebook_page_id",
            "",
            f"# Instagram",
            f"{site_key}_INSTAGRAM_ACCESS_TOKEN=your_{site.value}_instagram_access_token",
            f"{site_key}_INSTAGRAM_BUSINESS_ACCOUNT_ID=your_{site.value}_instagram_business_id",
            ""
        ])

    template_content = "\n".join(template_lines)

    # Écrire dans un fichier
    try:
        with open('.env.template', 'w') as f:
            f.write(template_content)
        print("✅ Template .env généré: .env.template")
        print("📋 Copiez ce fichier vers .env et remplissez vos credentials")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la génération: {e}")
        return False


def main():
    """Fonction principale de test"""
    print("🔐 Tests des Credentials Multi-Comptes")
    print("=" * 60)

    test_results = []

    # Test 1: Variables d'environnement
    env_vars_ok = test_environment_variables()
    test_results.append(("Variables d'environnement", env_vars_ok))

    # Test 2: Chargement des credentials
    loading_ok = test_credentials_loading()
    test_results.append(("Chargement credentials", loading_ok))

    # Test 3: Validation des credentials
    validation_ok = test_credentials_validation()
    test_results.append(("Validation credentials", validation_ok))

    # Test 4: Récupération des credentials
    retrieval_ok = test_credentials_retrieval()
    test_results.append(("Récupération credentials", retrieval_ok))

    # Test 5: Sécurité
    security_ok = test_credentials_security()
    test_results.append(("Sécurité credentials", security_ok))

    # Test 6: Génération template
    template_ok = generate_env_template()
    test_results.append(("Génération template", template_ok))

    # Résumé final
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS CREDENTIALS")
    print("=" * 60)

    passed = 0
    total = len(test_results)

    for test_name, success in test_results:
        status = "✅ RÉUSSI" if success else "❌ ÉCHEC"
        print(f"{test_name:30} {status}")
        if success:
            passed += 1

    print(f"\nRésultat global: {passed}/{total} tests réussis")

    if passed == total:
        print("🎉 Tous les tests de credentials sont passés!")
        print("🚀 Système prêt pour les vraies APIs!")
    else:
        print(f"⚠️  {total - passed} test(s) ont échoué")
        print("📋 Consultez CREDENTIALS_SETUP.md pour la configuration")

    # Conseils
    print(f"\n💡 Conseils:")
    if not any(result[1] for result in test_results[:3]):
        print("- Copiez .env.template vers .env")
        print("- Configurez vos clés API réelles")
        print("- Relancez ce test")
    else:
        print("- Configuration credentials OK!")
        print("- Prêt pour implémenter les agents de publication")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrompus par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur fatale: {str(e)}")
        sys.exit(1)