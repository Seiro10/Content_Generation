#!/usr/bin/env python3
"""
Script de test pour les fonctionnalités multi-sites et multi-comptes
"""
import asyncio
import json
from datetime import datetime
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.base import PlatformType, ContentType
from app.models.accounts import SiteWeb, account_mapping, validate_account_exists, AccountValidationError
from app.models.content import EnhancedPublicationRequest, PlatformContentConfig, PublicationRequestExamples
from app.orchestrator.workflow import orchestrator


async def test_account_validation():
    """Test de validation des comptes"""
    print("=== Test de validation des comptes ===")

    test_cases = [
        (SiteWeb.STUFFGAMING, PlatformType.INSTAGRAM),
        (SiteWeb.GAMING, PlatformType.TWITTER),
        (SiteWeb.FOOTBALL, PlatformType.FACEBOOK),
    ]

    for site, platform in test_cases:
        try:
            account = validate_account_exists(site, platform)
            print(f"✅ {site} / {platform}: {account.account_name}")
        except AccountValidationError as e:
            print(f"❌ {site} / {platform}: {str(e)}")

    # Test compte inexistant
    try:
        validate_account_exists(SiteWeb.STUFFGAMING, PlatformType.LINKEDIN)
        print("❌ Erreur: Compte LinkedIn pour StuffGaming ne devrait pas exister")
    except AccountValidationError:
        print("✅ Validation correcte: LinkedIn non disponible pour StuffGaming")


async def test_carousel_with_images():
    """Test carrousel Instagram avec images S3"""
    print("\n=== Test Carrousel avec Images S3 ===")

    request = EnhancedPublicationRequest(
        texte_source="""
        Top 5 des meilleurs jeux de 2024:
        1. Stellar Blade - Action RPG révolutionnaire
        2. Dragon's Dogma 2 - Suite tant attendue
        3. Black Myth Wukong - Mythologie chinoise
        4. Helldivers 2 - Coopération explosive
        5. Final Fantasy VII Rebirth - Epic continue
        """,
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

    try:
        result = await orchestrator.execute_workflow(request)

        if result.get('formatted_content'):
            carousel_content = result['formatted_content'].get('instagram_carousel')
            if carousel_content:
                print(f"✅ Carrousel créé avec {len(carousel_content.slides)} slides")
                print(f"Images fournies: {len(carousel_content.images_urls)}")
                print(f"Images générées: {carousel_content.images_generated}")

                for i, slide in enumerate(carousel_content.slides, 1):
                    print(f"  Slide {i}: {slide[:60]}...")

                print(f"Légende: {carousel_content.legende[:100]}...")

        return result['current_step'] == 'completed'

    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return False


async def test_carousel_without_images():
    """Test carrousel Instagram sans images (génération auto)"""
    print("\n=== Test Carrousel sans Images (génération auto) ===")

    request = EnhancedPublicationRequest(
        texte_source="""
        Guide stratégique pour débuter au football:
        1. Maîtriser les bases techniques
        2. Développer sa condition physique
        3. Comprendre les tactiques d'équipe
        """,
        site_web=SiteWeb.FOOTBALL,
        platforms_config=[
            PlatformContentConfig(
                platform=PlatformType.INSTAGRAM,
                content_type=ContentType.CAROUSEL,
                nb_slides=3,
                titre_carousel="Guide Football Débutant",
                hashtags=["#Football", "#Conseils", "#Débutant"]
                # Pas d'images_urls = génération automatique
            )
        ]
    )

    try:
        result = await orchestrator.execute_workflow(request)

        if result.get('formatted_content'):
            carousel_content = result['formatted_content'].get('instagram_carousel')
            if carousel_content:
                print(f"✅ Carrousel créé avec génération d'images")
                print(f"Images générées: {carousel_content.images_generated}")
                print(f"URLs générées: {len(carousel_content.images_urls)}")

                for url in carousel_content.images_urls:
                    print(f"  - {url}")

        return result['current_step'] == 'completed'

    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return False


async def test_multisite_publication():
    """Test publication sur plusieurs sites différents"""
    print("\n=== Test Publication Multi-Sites ===")

    # Test avec 3 sites différents
    requests = [
        # StuffGaming - Contenu gaming
        EnhancedPublicationRequest(
            texte_source="Nouvelle mise à jour pour Call of Duty avec des cartes inédites et modes de jeu révolutionnaires!",
            site_web=SiteWeb.STUFFGAMING,
            platforms_config=[
                PlatformContentConfig(platform=PlatformType.INSTAGRAM, content_type=ContentType.POST),
                PlatformContentConfig(platform=PlatformType.TWITTER, content_type=ContentType.POST)
            ]
        ),
        # Gaming.com - Contenu général gaming
        EnhancedPublicationRequest(
            texte_source="L'industrie du jeu vidéo atteint des records historiques avec 3 milliards de joueurs dans le monde.",
            site_web=SiteWeb.GAMING,
            platforms_config=[
                PlatformContentConfig(platform=PlatformType.FACEBOOK, content_type=ContentType.POST),
                PlatformContentConfig(platform=PlatformType.TWITTER, content_type=ContentType.POST)
            ]
        ),
        # Football.com - Contenu sport
        EnhancedPublicationRequest(
            texte_source="Transfert surprenant: Mbappé annonce officiellement son départ du PSG pour Real Madrid!",
            site_web=SiteWeb.FOOTBALL,
            platforms_config=[
                PlatformContentConfig(platform=PlatformType.INSTAGRAM, content_type=ContentType.STORY),
                PlatformContentConfig(platform=PlatformType.FACEBOOK, content_type=ContentType.POST)
            ]
        )
    ]

    results = []

    for i, request in enumerate(requests, 1):
        print(f"\n--- Test Site {i}: {request.site_web} ---")
        try:
            result = await orchestrator.execute_workflow(request)
            success = result['current_step'] == 'completed'
            results.append(success)

            print(f"Statut: {'✅ RÉUSSI' if success else '❌ ÉCHEC'}")
            print(f"Erreurs: {len(result.get('errors', []))}")

            if result.get('formatted_content'):
                print(f"Contenus formatés: {len(result['formatted_content'])}")
                for key in result['formatted_content'].keys():
                    platform, content_type = key.split('_', 1)
                    print(f"  - {platform} ({content_type})")

        except Exception as e:
            print(f"❌ Erreur: {str(e)}")
            results.append(False)

    return results


async def test_account_mapping():
    """Test du mapping des comptes"""
    print("\n=== Test Mapping des Comptes ===")

    print(f"Total comptes configurés: {len(account_mapping.accounts)}")
    print(f"Comptes actifs: {len(account_mapping.list_active_accounts())}")

    for site in SiteWeb:
        site_accounts = account_mapping.list_accounts_for_site(site)
        print(f"\n{site}:")
        for account in site_accounts:
            status = "✅" if account.is_active else "❌"
            print(f"  {status} {account.platform}: {account.account_name}")

    # Test récupération compte spécifique
    account = account_mapping.get_account(SiteWeb.STUFFGAMING, PlatformType.INSTAGRAM)
    if account:
        print(f"\nCompte StuffGaming Instagram: {account.account_name}")
        return True
    else:
        print("❌ Erreur: Compte StuffGaming Instagram non trouvé")
        return False


async def test_examples():
    """Test des nouveaux exemples"""
    print("\n=== Test des Nouveaux Exemples ===")

    examples = [
        ("Simple Multi-Platform", PublicationRequestExamples.simple_multi_platform().to_enhanced_request()),
        ("Carousel avec Images", PublicationRequestExamples.instagram_carousel_with_images()),
        ("Carousel sans Images", PublicationRequestExamples.instagram_carousel_without_images()),
        ("Multi-Sites", PublicationRequestExamples.mixed_sites_content())
    ]

    results = []

    for name, example in examples:
        print(f"\n--- {name} ---")
        print(f"Site: {example.site_web}")
        print(f"Plateformes: {[(c.platform, c.content_type) for c in example.platforms_config]}")

        try:
            result = await orchestrator.execute_workflow(example)
            success = result['current_step'] == 'completed'
            results.append((name, success))
            print(f"Résultat: {'✅ RÉUSSI' if success else '❌ ÉCHEC'}")

        except Exception as e:
            print(f"❌ Erreur: {str(e)}")
            results.append((name, False))

    return results


async def main():
    """Fonction principale de test"""
    print("🚀 Tests des fonctionnalités multi-sites et multi-comptes")
    print("=" * 70)

    test_results = []

    # Test 1: Validation des comptes
    await test_account_validation()

    # Test 2: Mapping des comptes
    mapping_result = await test_account_mapping()
    test_results.append(("Mapping Comptes", mapping_result))

    # Test 3: Carrousel avec images
    carousel_images_result = await test_carousel_with_images()
    test_results.append(("Carrousel + Images", carousel_images_result))

    # Test 4: Carrousel sans images
    carousel_auto_result = await test_carousel_without_images()
    test_results.append(("Carrousel Auto-Images", carousel_auto_result))

    # Test 5: Publication multi-sites
    multisite_results = await test_multisite_publication()
    for i, result in enumerate(multisite_results, 1):
        test_results.append((f"Multi-Site {i}", result))

    # Test 6: Nouveaux exemples
    example_results = await test_examples()
    test_results.extend(example_results)

    # Résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DES TESTS MULTI-SITES")
    print("=" * 70)

    passed = 0
    total = len(test_results)

    for test_name, success in test_results:
        status = "✅ RÉUSSI" if success else "❌ ÉCHEC"
        print(f"{test_name:30} {status}")
        if success:
            passed += 1

    print(f"\nRésultat global: {passed}/{total} tests réussis")

    if passed == total:
        print("🎉 Tous les tests multi-sites sont passés!")
        print("🏆 Système prêt pour la gestion multi-comptes!")
    else:
        print(f"⚠️  {total - passed} test(s) ont échoué")

    # Informations système
    print(f"\n📋 Configuration système:")
    print(f"Sites supportés: {len(SiteWeb)} ({', '.join([s.value for s in SiteWeb])})")
    print(f"Plateformes: {len(PlatformType)} ({', '.join([p.value for p in PlatformType])})")
    print(f"Total comptes: {len(account_mapping.accounts)}")


if __name__ == "__main__":
    # Vérifier la configuration
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("❌ Erreur: La variable d'environnement ANTHROPIC_API_KEY n'est pas définie")
        print("Créez un fichier .env avec votre clé API Anthropic")
        sys.exit(1)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrompus par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur fatale: {str(e)}")
        sys.exit(1)