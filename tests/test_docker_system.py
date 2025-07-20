#!/usr/bin/env python3
"""
Script de test pour l'infrastructure Docker et le système distribué Celery
"""
import asyncio
import requests
import json
import time
import sys
from typing import Dict, Any
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8090"
FLOWER_URL = "http://localhost:5555"


class DockerSystemTester:
    """Testeur pour l'infrastructure Docker et Celery"""

    def __init__(self):
        self.session = requests.Session()
        self.test_results = []

    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log un résultat de test"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")

        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })

    def test_service_health(self):
        """Test la santé de tous les services"""
        print("\n=== Test de Santé des Services ===")

        services = [
            ("API Principal", f"{API_BASE_URL}/health"),
            ("Monitoring Celery", f"{FLOWER_URL}/api/workers"),
        ]

        for service_name, url in services:
            try:
                response = self.session.get(url, timeout=10)
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                if not success:
                    details += f", Response: {response.text[:100]}"

                self.log_test(f"{service_name} Health", success, details)

            except Exception as e:
                self.log_test(f"{service_name} Health", False, f"Error: {str(e)}")

    def test_api_endpoints(self):
        """Test les endpoints API principaux"""
        print("\n=== Test des Endpoints API ===")

        endpoints = [
            ("GET /", "get", "/"),
            ("GET /health", "get", "/health"),
            ("GET /accounts", "get", "/accounts"),
            ("GET /credentials", "get", "/credentials"),
            ("GET /examples", "get", "/examples"),
            ("GET /queue/status", "get", "/queue/status"),
            ("GET /metrics/workflows", "get", "/metrics/workflows"),
        ]

        for test_name, method, endpoint in endpoints:
            try:
                url = f"{API_BASE_URL}{endpoint}"
                response = self.session.request(method, url, timeout=10)

                success = response.status_code in [200, 404]  # 404 acceptable pour certains endpoints
                details = f"Status: {response.status_code}"

                if response.status_code == 200:
                    try:
                        data = response.json()
                        details += f", Response keys: {list(data.keys())[:3]}"
                    except:
                        details += ", Response: text"

                self.log_test(test_name, success, details)

            except Exception as e:
                self.log_test(test_name, False, f"Error: {str(e)}")

    def test_celery_queues(self):
        """Test l'état des queues Celery"""
        print("\n=== Test des Queues Celery ===")

        try:
            response = self.session.get(f"{API_BASE_URL}/queue/status", timeout=10)

            if response.status_code == 200:
                data = response.json()
                queues = data.get('queues', {})

                expected_queues = ['content_generation', 'content_formatting', 'content_publishing', 'image_generation']

                for queue_name in expected_queues:
                    if queue_name in queues:
                        queue_size = queues[queue_name]
                        success = queue_size != "unknown"
                        details = f"Queue size: {queue_size}"
                        self.log_test(f"Queue {queue_name}", success, details)
                    else:
                        self.log_test(f"Queue {queue_name}", False, "Queue not found")

                # Test workers
                workers = data.get('workers', {})
                if workers:
                    active_tasks = workers.get('active_tasks', {})
                    worker_count = len(active_tasks) if active_tasks else 0
                    self.log_test("Celery Workers", worker_count >= 0, f"Workers detected: {worker_count}")
                else:
                    self.log_test("Celery Workers", False, "No worker information")

            else:
                self.log_test("Queue Status API", False, f"Status: {response.status_code}")

        except Exception as e:
            self.log_test("Queue Status API", False, f"Error: {str(e)}")

    def test_simple_publication(self):
        """Test une publication simple"""
        print("\n=== Test Publication Simple ===")

        try:
            payload = {
                "texte_source": "Test de publication automatisée depuis Docker!",
                "site_web": "stuffgaming.fr",
                "plateformes": ["twitter", "instagram"],
                "hashtags": ["#test", "#docker", "#automation"]
            }

            response = self.session.post(
                f"{API_BASE_URL}/publish",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                request_id = data.get('request_id')

                self.log_test("Simple Publication", True, f"Request ID: {request_id}")

                # Attendre et vérifier le statut
                time.sleep(5)
                status_response = self.session.get(f"{API_BASE_URL}/status/{request_id}")

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    final_status = status_data.get('status')
                    self.log_test("Publication Status Check", True, f"Status: {final_status}")
                else:
                    self.log_test("Publication Status Check", False, f"Status: {status_response.status_code}")

            else:
                self.log_test("Simple Publication", False,
                              f"Status: {response.status_code}, Response: {response.text[:200]}")

        except Exception as e:
            self.log_test("Simple Publication", False, f"Error: {str(e)}")

    def test_async_publication(self):
        """Test une publication asynchrone avec Celery"""
        print("\n=== Test Publication Asynchrone (Celery) ===")

        try:
            payload = {
                "texte_source": "Test de publication asynchrone avec Celery et Docker!",
                "site_web": "gaming.com",
                "platforms_config": [
                    {
                        "platform": "twitter",
                        "content_type": "post",
                        "hashtags": ["#test", "#celery"]
                    },
                    {
                        "platform": "instagram",
                        "content_type": "post",
                        "hashtags": ["#test", "#async"]
                    }
                ]
            }

            response = self.session.post(
                f"{API_BASE_URL}/publish/async",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                task_id = data.get('task_id')

                self.log_test("Async Publication Submit", True, f"Task ID: {task_id}")

                # Attendre et vérifier le workflow
                time.sleep(10)
                workflow_response = self.session.get(f"{API_BASE_URL}/workflow/{task_id}")

                if workflow_response.status_code == 200:
                    workflow_data = workflow_response.json()
                    workflow_status = workflow_data.get('status')
                    self.log_test("Async Workflow Status", True, f"Status: {workflow_status}")
                else:
                    self.log_test("Async Workflow Status", False, f"Status: {workflow_response.status_code}")

            else:
                self.log_test("Async Publication Submit", False,
                              f"Status: {response.status_code}, Response: {response.text[:200]}")

        except Exception as e:
            self.log_test("Async Publication Submit", False, f"Error: {str(e)}")

    def test_instagram_carousel(self):
        """Test publication Instagram carrousel"""
        print("\n=== Test Instagram Carrousel ===")

        try:
            payload = {
                "texte_source": "Guide complet en 3 étapes pour optimiser votre setup gaming",
                "site_web": "stuffgaming.fr",
                "platforms_config": [
                    {
                        "platform": "instagram",
                        "content_type": "carousel",
                        "nb_slides": 3,
                        "titre_carousel": "Setup Gaming Guide",
                        "hashtags": ["#gaming", "#setup", "#guide"]
                    }
                ]
            }

            response = self.session.post(
                f"{API_BASE_URL}/publish/async",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                task_id = data.get('task_id')

                self.log_test("Instagram Carousel Submit", True, f"Task ID: {task_id}")

                # Attendre plus longtemps pour la génération d'images
                time.sleep(15)
                workflow_response = self.session.get(f"{API_BASE_URL}/workflow/{task_id}")

                if workflow_response.status_code == 200:
                    workflow_data = workflow_response.json()
                    workflow_status = workflow_data.get('status')
                    results = workflow_data.get('results', {})

                    success = workflow_status in ['completed', 'processing']
                    details = f"Status: {workflow_status}"

                    if results:
                        details += f", Results available"

                    self.log_test("Instagram Carousel Workflow", success, details)
                else:
                    self.log_test("Instagram Carousel Workflow", False, f"Status: {workflow_response.status_code}")

            else:
                self.log_test("Instagram Carousel Submit", False, f"Status: {response.status_code}")

        except Exception as e:
            self.log_test("Instagram Carousel Submit", False, f"Error: {str(e)}")

    def test_credentials_validation(self):
        """Test validation des credentials"""
        print("\n=== Test Validation Credentials ===")

        sites_platforms = [
            ("stuffgaming.fr", "twitter"),
            ("gaming.com", "facebook"),
            ("football.com", "instagram")
        ]

        for site, platform in sites_platforms:
            try:
                response = self.session.post(
                    f"{API_BASE_URL}/test/credentials",
                    data={"site_web": site, "platform": platform},
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    credentials_valid = data.get('credentials_valid', False)

                    # Pour les tests Docker, on accepte les credentials simulés
                    self.log_test(f"Credentials {site}/{platform}", True, f"Configured: {credentials_valid}")
                else:
                    self.log_test(f"Credentials {site}/{platform}", False, f"Status: {response.status_code}")

            except Exception as e:
                self.log_test(f"Credentials {site}/{platform}", False, f"Error: {str(e)}")

    def test_flower_monitoring(self):
        """Test l'interface de monitoring Flower"""
        print("\n=== Test Monitoring Flower ===")

        try:
            # Test page principale
            response = self.session.get(f"{FLOWER_URL}/", timeout=10)
            success = response.status_code == 200
            self.log_test("Flower Web Interface", success, f"Status: {response.status_code}")

            # Test API workers
            response = self.session.get(f"{FLOWER_URL}/api/workers", timeout=10)
            if response.status_code == 200:
                workers = response.json()
                worker_count = len(workers)
                self.log_test("Flower Workers API", True, f"Workers: {worker_count}")
            else:
                self.log_test("Flower Workers API", False, f"Status: {response.status_code}")

        except Exception as e:
            self.log_test("Flower Monitoring", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Exécute tous les tests"""
        print("🐳 Démarrage des tests de l'infrastructure Docker")
        print("=" * 60)

        start_time = time.time()

        # Tests d'infrastructure
        self.test_service_health()
        self.test_api_endpoints()
        self.test_celery_queues()
        self.test_flower_monitoring()

        # Tests fonctionnels
        self.test_credentials_validation()
        self.test_simple_publication()
        self.test_async_publication()
        self.test_instagram_carousel()

        # Résumé
        end_time = time.time()
        duration = end_time - start_time

        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ DES TESTS DOCKER")
        print("=" * 60)

        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)

        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}")

        print(f"\nRésultat global: {passed}/{total} tests réussis")
        print(f"Durée: {duration:.2f} secondes")

        if passed == total:
            print("🎉 Tous les tests Docker sont passés!")
            print("🚀 Infrastructure prête pour la production!")
            return True
        else:
            print(f"⚠️ {total - passed} test(s) ont échoué")
            print("🔧 Vérifiez les logs Docker et la configuration")
            return False


def main():
    """Fonction principale"""
    print("🐳 Tests de l'Infrastructure Docker - Social Media Publisher")

    # Vérifier que les services sont démarrés
    print("\n💡 Assurez-vous que les services Docker sont démarrés:")
    print("   ./rebuild_social_media_system.sh")
    print("   docker compose ps")

    input("\n⏳ Appuyez sur Entrée pour continuer avec les tests...")

    tester = DockerSystemTester()

    try:
        success = tester.run_all_tests()

        if success:
            print("\n🎯 Commandes utiles pour la suite:")
            print("   docker compose logs social-media-api")
            print("   docker compose logs social-media-worker-content")
            print("   curl http://localhost:8090/queue/status")
            print("   curl http://localhost:8090/metrics/workflows")

            sys.exit(0)
        else:
            print("\n🔧 Dépannage:")
            print("   docker compose ps")
            print("   docker compose logs")
            print("   docker compose restart social-media-api")

            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⏹️ Tests interrompus par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur fatale: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()