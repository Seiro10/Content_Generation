#!/usr/bin/env python3
"""
Script de test pour l'orchestrateur LangGraph
"""
import asyncio
import json
from datetime import datetime
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.base import PublicationRequest, PlatformType
from app.orchestrator.workflow import orchestrator


async def test_basic_workflow():
    """Test de base du workflow"""
    print("=== Test du workflow de base ===")

    # Créer une demande de publication de test
    request = PublicationRequest(
        texte_source="""
        Nous venons de lancer notre nouvelle fonctionnalité d'intelligence artificielle qui permet 
        d'automatiser la publication sur les réseaux sociaux. Cette solution révolutionnaire 
        utilise Claude LLM pour adapter automatiquement votre contenu à chaque plateforme.
        """,
        plateformes=[
            PlatformType.TWITTER,
            PlatformType.FACEBOOK,
            PlatformType.LINKEDIN,
            PlatformType.INSTAGRAM
        ],
        hashtags=["#IA", "#ReseauxSociaux", "#Innovation"],
        lien_source="https://example.com/blog/nouvelle-fonctionnalite"
    )

    print(f"Demande créée à {datetime.now()}")
    print(f"Plateformes: {request.plateformes}")

    try:
        # Exécuter le workflow
        result = await orchestrator.execute_workflow(request)

        print(f"\n=== Résultats ===")
        print(f"ID de tâche: {result['task_id']}")
        print(f"Étape finale: {result['current_step']}")
        print(f"Erreurs: {len(result['errors'])}")

        if result['errors']:
            print("Erreurs rencontrées:")
            for error in result['errors']:
                print(f"  - {error}")

        # Afficher le contenu généré
        if result.get('content_generated'):
            print(f"\n=== Contenu généré ===")
            print(result['content_generated'])

        # Afficher le contenu formaté
        if result.get('formatted_content'):
            print(f"\n=== Contenu formaté par plateforme ===")
            for platform, content in result['formatted_content'].items():
                print(f"\n{platform.upper()}:")
                print(f"  {content}")

        # Afficher les résultats de publication
        if result.get('publication_results'):
            print(f"\n=== Résultats de publication ===")
            for platform, pub_result in result['publication_results'].items():
                print(f"\n{platform.upper()}:")
                print(f"  Statut: {pub_result.get('status')}")
                print(f"  ID: {pub_result.get('post_id')}")
                print(f"  URL: {pub_result.get('post_url')}")

        return result

    except Exception as e:
        print(f"Erreur lors de l'exécution: {str(e)}")
        return None


async def test_single_platform():
    """Test avec une seule plateforme"""
    print("\n=== Test plateforme unique (Twitter) ===")

    request = PublicationRequest(
        texte_source="Test rapide pour Twitter uniquement avec un message court et percutant.",
        plateformes=[PlatformType.TWITTER],
        hashtags=["#test", "#twitter"]
    )

    try:
        result = await orchestrator.execute_workflow(request)

        if result.get('formatted_content') and PlatformType.TWITTER in result['formatted_content']:
            twitter_content = result['formatted_content'][PlatformType.TWITTER]
            print(f"Contenu Twitter formaté: {twitter_content}")

            # Vérifier la longueur
            if hasattr(twitter_content, 'tweet'):
                tweet_length = len(twitter_content.tweet)
                print(f"Longueur du tweet: {tweet_length}/280 caractères")
                if tweet_length <= 280:
                    print("✅ Contrainte de longueur respectée")
                else:
                    print("❌ Tweet trop long!")

        return result

    except Exception as e:
        print(f"Erreur: {str(e)}")
        return None


async def main():
    """Fonction principale de test"""
    print("🚀 Démarrage des tests de l'orchestrateur")
    print("=" * 50)

    # Test 1: Workflow complet
    result1 = await test_basic_workflow()

    # Test 2: Plateforme unique
    result2 = await test_single_platform()

    print("\n" + "=" * 50)
    print("✅ Tests terminés")

    # Résumé
    if result1 and result1.get('current_step') == 'completed':
        print("✅ Test workflow complet: RÉUSSI")
    else:
        print("❌ Test workflow complet: ÉCHEC")

    if result2 and result2.get('current_step') == 'completed':
        print("✅ Test plateforme unique: RÉUSSI")
    else:
        print("❌ Test plateforme unique: ÉCHEC")


if __name__ == "__main__":
    # Vérifier que la variable d'environnement ANTHROPIC_API_KEY est définie
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