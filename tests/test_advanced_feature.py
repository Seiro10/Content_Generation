#!/usr/bin/env python3
"""
Script de test pour les fonctionnalités avancées (types spécifiques par plateforme)
"""
import asyncio
import json
from datetime import datetime
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.base import PlatformType, ContentType
from app.models.content import EnhancedPublicationRequest, PlatformContentConfig, PublicationRequestExamples
from app.orchestrator.workflow import orchestrator


async def test_instagram_carousel():
    """Test spécifique Instagram Carousel"""
    print("=== Test Instagram Carousel ===")

    request = EnhancedPublicationRequest(
        texte_source="""
        Guide complet pour optimiser votre présence sur les réseaux sociaux en 2024:

        1. Définissez votre stratégie de contenu
        2. Créez un calendrier éditorial cohérent
        3. Engagez authentiquement avec votre audience
        4. Analysez vos performances régulièrement
        5. Adaptez-vous aux nouvelles tendances
        """,
        platforms_config=[
            PlatformContentConfig(
                platform=PlatformType.INSTAGRAM,
                content_type=ContentType.CAROUSEL,
                nb_slides=5,
                titre_carousel="Guide Réseaux Sociaux 2024",
                hashtags=["#SocialMedia", "#Marketing", "#Guide2024", "#Instagram"]
            )
        ]
    )

    try:
        result = await orchestrator.execute_workflow(request)

        print(f"Statut: {result['current_step']}")

        if result.get('formatted_content'):
            carousel_content = result['formatted_content'].get('instagram_carousel')
            if carousel_content:
                print(f"\n=== Contenu Carrousel ===")
                print(f"Nombre de slides: {len(carousel_content.slides)}")

                for i, slide in enumerate(carousel_content.slides, 1):
                    print(f"\nSlide {i}: {slide}")

                print(f"\nLégende: {carousel_content.legende}")
                print(f"Hashtags: {carousel_content.hashtags}")

        return result

    except Exception as e:
        print(f"Erreur: {str(e)}")
        return None


async def test_instagram_story():
    """Test spécifique Instagram Story"""
    print("\n=== Test Instagram Story ===")

    request = EnhancedPublicationRequest(
        texte_source="Nouvelle fonctionnalité révolutionnaire lancée aujourd'hui ! Découvrez comment elle va transformer votre workflow.",
        platforms_config=[
            PlatformContentConfig(
                platform=PlatformType.INSTAGRAM,
                content_type=ContentType.STORY,
                lien_sticker="https://example.com/nouvelle-fonction"
            )
        ]
    )

    try:
        result = await orchestrator.execute_workflow(request)

        if result.get('formatted_content'):
            story_content = result['formatted_content'].get('instagram_story')
            if story_content:
                print(f"Texte story: '{story_content.texte_story}'")
                print(f"Longueur: {len(story_content.texte_story)} caractères")

                if len(story_content.texte_story) <= 50:
                    print("✅ Contrainte de longueur respectée")
                else:
                    print("❌ Story trop longue!")

        return result

    except Exception as e:
        print(f"Erreur: {str(e)}")
        return None


async def test_mixed_platforms():
    """Test avec types mixtes sur plusieurs plateformes"""
    print("\n=== Test Plateformes Mixtes ===")

    request = EnhancedPublicationRequest(
        texte_source="Annonce importante: Nous lançons notre nouvelle solution d'IA pour automatiser vos publications sur les réseaux sociaux!",
        platforms_config=[
            # Twitter classique
            PlatformContentConfig(
                platform=PlatformType.TWITTER,
                content_type=ContentType.POST,
                hashtags=["#IA", "#Innovation", "#SocialMedia"]
            ),
            # Facebook classique
            PlatformContentConfig(
                platform=PlatformType.FACEBOOK,
                content_type=ContentType.POST,
                hashtags=["#Innovation", "#IA"],
                lien_source="https://example.com/lancement"
            ),
            # LinkedIn professionnel
            PlatformContentConfig(
                platform=PlatformType.LINKEDIN,
                content_type=ContentType.POST,
                hashtags=["#ArtificialIntelligence", "#MarketingTech", "#Innovation"]
            ),
            # Instagram post
            PlatformContentConfig(
                platform=PlatformType.INSTAGRAM,
                content_type=ContentType.POST,
                hashtags=["#IA", "#Tech", "#Innovation", "#NewProduct"]
            ),
            # Instagram story
            PlatformContentConfig(
                platform=PlatformType.INSTAGRAM,
                content_type=ContentType.STORY,
                lien_sticker="https://example.com/lancement"
            )
        ]
    )

    try:
        result = await orchestrator.execute_workflow(request)

        print(f"Statut: {result['current_step']}")
        print(f"Erreurs: {len(result['errors'])}")

        if result.get('formatted_content'):
            print(f"\n=== Contenu formaté ({len(result['formatted_content'])} formats) ===")

            for key, content in result['formatted_content'].items():
                platform, content_type = key.split('_', 1)
                print(f"\n{platform.upper()} ({content_type}):")

                # Afficher selon le type
                if hasattr(content, 'tweet'):
                    print(f"  Tweet: {content.tweet} ({len(content.tweet)} chars)")
                elif hasattr(content, 'message'):
                    print(f"  Message: {content.message[:100]}...")
                elif hasattr(content, 'contenu'):
                    print(f"  Contenu: {content.contenu[:100]}...")
                elif hasattr(content, 'legende'):
                    print(f"  Légende: {content.legende[:100]}...")
                elif hasattr(content, 'texte_story'):
                    print(f"  Story: {content.texte_story}")
                else:
                    print(f"  {content}")

        return result

    except Exception as e:
        print(f"Erreur: {str(e)}")
        return None


async def test_examples():
    """Test des exemples prédéfinis"""
    print("\n=== Test des Exemples ===")

    examples = [
        ("Simple Multi-Platform", PublicationRequestExamples.simple_multi_platform().to_enhanced_request()),
        ("Instagram Carousel", PublicationRequestExamples.instagram_carousel()),
        ("Mixed Content Types", PublicationRequestExamples.mixed_content_types())
    ]

    results = []

    for name, example in examples:
        print(f"\n--- {name} ---")
        try:
            result = await orchestrator.execute_workflow(example)
            success = result['current_step'] == 'completed'
            results.append((name, success))
            print(f"Résultat: {'✅ RÉUSSI' if success else '❌ ÉCHEC'}")

        except Exception as e:
            print(f"Erreur: {str(e)}")
            results.append((name, False))

    return results


async def main():
    """Fonction principale de test"""
    print("🚀 Tests des fonctionnalités avancées")
    print("=" * 60)

    # Tests spécifiques
    test_results = []

    # Test 1: Instagram Carousel
    result1 = await test_instagram_carousel()
    test_results.append(("Instagram Carousel", result1 and result1.get('current_step') == 'completed'))

    # Test 2: Instagram Story
    result2 = await test_instagram_story()
    test_results.append(("Instagram Story", result2 and result2.get('current_step') == 'completed'))

    # Test 3: Plateformes mixtes
    result3 = await test_mixed_platforms()
    test_results.append(("Plateformes Mixtes", result3 and result3.get('current_step') == 'completed'))

    # Test 4: Exemples
    example_results = await test_examples()
    test_results.extend(example_results)

    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
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
        print("🎉 Tous les tests sont passés!")
    else:
        print(f"⚠️  {total - passed} test(s) ont échoué")


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