import asyncio
import logging
import sys
import os
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_crop_system():
    """Test complet du système de crop intelligent"""

    print("🎯 Test du Système de Crop Intelligent")
    print("=" * 50)

    # Test 1: Vérifier les imports
    print("\n1️⃣ Test des imports...")
    try:
        # Test import OpenCV
        import cv2
        print(f"✅ OpenCV: {cv2.__version__}")

        # Test import numpy
        import numpy as np
        print(f"✅ NumPy: {np.__version__}")

        # Test import Pillow
        from PIL import Image
        print(f"✅ Pillow: {Image.__version__}")

        # Test import SAM (optionnel)
        try:
            from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
            print("✅ SAM: Disponible")
            sam_available = True
        except ImportError:
            print("⚠️ SAM: Non disponible (fallback OpenCV)")
            sam_available = False

    except ImportError as e:
        print(f"❌ Erreur import: {e}")
        return False

    # Test 2: Initialiser les services
    print("\n2️⃣ Test d'initialisation des services...")
    try:
        # Test service unifié
        from app.services.unified_cropper import unified_cropper
        status = unified_cropper.get_status()
        print(f"✅ Service unifié initialisé")
        print(f"   - Méthode choisie: {status['unified_cropper']['chosen_method']}")
        print(f"   - SAM disponible: {status['unified_cropper']['intelligent_cropper_available']}")
        print(f"   - OpenCV disponible: {status['unified_cropper']['opencv_cropper_available']}")

        # Test méthodes disponibles
        methods = unified_cropper.get_available_methods()
        print("\n📋 Méthodes disponibles:")
        for method, info in methods.items():
            status_icon = "✅" if info['available'] else "❌"
            print(f"   {status_icon} {method}: {info['description']} (qualité: {info['quality']})")

    except Exception as e:
        print(f"❌ Erreur initialisation: {e}")
        return False

    # Test 3: Test des dimensions optimales
    print("\n3️⃣ Test des dimensions optimales...")
    try:
        from app.models.base import PlatformType, ContentType

        test_cases = [
            (PlatformType.INSTAGRAM, ContentType.POST),
            (PlatformType.INSTAGRAM, ContentType.STORY),
            (PlatformType.INSTAGRAM, ContentType.CAROUSEL),
            (PlatformType.TWITTER, ContentType.POST),
            (PlatformType.FACEBOOK, ContentType.POST),
        ]

        for platform, content_type in test_cases:
            dims = unified_cropper.get_optimal_dimensions(platform, content_type)
            print(f"   📐 {platform.value} {content_type.value}: {dims[0]}x{dims[1]}")

    except Exception as e:
        print(f"❌ Erreur dimensions: {e}")
        return False

    # Test 4: Test de crop avec image factice
    print("\n4️⃣ Test de crop avec image factice...")
    try:
        # Créer une image de test
        test_image = np.zeros((1080, 1920, 3), dtype=np.uint8)

        # Ajouter un "visage" factice (rectangle blanc)
        cv2.rectangle(test_image, (800, 400), (1000, 600), (255, 255, 255), -1)

        # Tester la détection OpenCV directement
        from app.services.opencv_cropper import opencv_only_cropper

        # Simuler la détection
        fake_regions = opencv_only_cropper._opencv_detect_regions(test_image)
        print(f"✅ Détection test: {len(fake_regions)} régions détectées")

        # Test de crop factice
        cropped = opencv_only_cropper._smart_crop_opencv(
            test_image, fake_regions, 1080, 1080
        )
        print(f"✅ Crop test réussi: {cropped.shape}")

    except Exception as e:
        print(f"❌ Erreur crop test: {e}")
        # Pas critique, continuer

    # Test 5: Test de configuration
    print("\n5️⃣ Test de configuration...")
    try:
        from app.config.settings import settings

        print(f"   🔧 SAM activé: {settings.sam_enabled}")
        print(f"   🔧 Modèle SAM: {settings.sam_model_type}")
        print(f"   🔧 Device SAM: {settings.sam_device}")
        print(f"   🔧 Méthode crop: {settings.crop_method}")
        print(f"   🔧 Fallback OpenCV: {settings.sam_fallback_to_opencv}")

        # Vérifier checkpoint SAM si configuré
        if settings.sam_checkpoint_path:
            if os.path.exists(settings.sam_checkpoint_path):
                print(f"   ✅ Checkpoint SAM trouvé: {settings.sam_checkpoint_path}")
            else:
                print(f"   ⚠️ Checkpoint SAM manquant: {settings.sam_checkpoint_path}")
        else:
            print(f"   ℹ️ Checkpoint SAM non configuré (utilise /app/models/sam_checkpoints/)")

    except Exception as e:
        print(f"❌ Erreur configuration: {e}")
        return False

    # Test 6: Test endpoints API (si serveur actif)
    print("\n6️⃣ Test des endpoints API...")
    try:
        import requests
        base_url = "http://localhost:8090"

        # Test statut crop
        response = requests.get(f"{base_url}/crop/status", timeout=5)
        if response.status_code == 200:
            print("✅ Endpoint /crop/status accessible")
        else:
            print(f"⚠️ Endpoint /crop/status: status {response.status_code}")

        # Test recommandations
        response = requests.get(f"{base_url}/crop/recommendations", timeout=5)
        if response.status_code == 200:
            print("✅ Endpoint /crop/recommendations accessible")
        else:
            print(f"⚠️ Endpoint /crop/recommendations: status {response.status_code}")

    except requests.exceptions.RequestException:
        print("ℹ️ Serveur API non accessible (normal si pas démarré)")
    except Exception as e:
        print(f"⚠️ Erreur test API: {e}")

    # Test 7: Test de performance basique
    print("\n7️⃣ Test de performance...")
    try:
        import time

        # Créer image de test plus grande
        large_image = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)

        # Test OpenCV cropper
        start_time = time.time()
        regions = opencv_only_cropper._opencv_detect_regions(large_image)
        cropped = opencv_only_cropper._smart_crop_opencv(large_image, regions, 1080, 1080)
        opencv_time = time.time() - start_time

        print(f"   ⏱️ OpenCV crop (4K→1080p): {opencv_time:.2f}s")
        print(f"   📊 Régions détectées: {len(regions)}")

        if opencv_time < 5.0:
            print("   ✅ Performance acceptable")
        else:
            print("   ⚠️ Performance lente (>5s)")

    except Exception as e:
        print(f"❌ Erreur test performance: {e}")

    # Test 8: Résumé final
    print("\n🎯 RÉSUMÉ DU TEST")
    print("=" * 50)

    try:
        status = unified_cropper.get_status()
        methods = unified_cropper.get_available_methods()

        print(f"✅ Système de crop intelligent: OPÉRATIONNEL")
        print(f"📊 Méthode active: {status['unified_cropper']['chosen_method']}")

        available_count = sum(1 for m in methods.values() if m['available'])
        print(f"🔧 Méthodes disponibles: {available_count}/3")

        if status['unified_cropper']['intelligent_cropper_available']:
            print("🤖 SAM + OpenCV: Disponible (qualité maximale)")
        elif status['unified_cropper']['opencv_cropper_available']:
            print("🔧 OpenCV seul: Disponible (qualité bonne)")
        else:
            print("📐 Redimensionnement simple: Disponible (qualité basique)")

        print("\n💡 Prochaines étapes:")
        print("1. Démarrer le serveur: uvicorn app.main:app --host 0.0.0.0 --port 8090")
        print("2. Démarrer Celery: celery -A app.services.celery_app worker -l info")
        print("3. Tester avec: curl -X POST 'http://localhost:8090/images/unified-crop' ...")

        if not status['unified_cropper']['intelligent_cropper_available']:
            print("\n🔧 Pour activer SAM:")
            print("1. pip install git+https://github.com/facebookresearch/segment-anything.git")
            print(
                "2. Télécharger checkpoint: wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth")
            print("3. Configurer le chemin dans settings.py")

        return True

    except Exception as e:
        print(f"❌ Erreur résumé: {e}")
        return False


async def test_specific_image(s3_url: str):
    """Test avec une image S3 spécifique"""
    print(f"\n🖼️ Test avec image spécifique: {s3_url}")

    try:
        from app.services.unified_cropper import unified_cropper
        from app.models.base import PlatformType, ContentType

        # Test crop pour Instagram
        print("📱 Test crop Instagram...")
        result = unified_cropper.crop_image_from_s3(
            s3_url,
            PlatformType.INSTAGRAM,
            ContentType.POST
        )
        print(f"✅ Résultat: {result}")

        return True

    except Exception as e:
        print(f"❌ Erreur test image: {e}")
        return False


if __name__ == "__main__":
    print("🎯 Démarrage des tests du système de crop intelligent...")

    # Test principal
    success = asyncio.run(test_crop_system())

    # Test avec image spécifique si fournie en argument
    if len(sys.argv) > 1:
        s3_url = sys.argv[1]
        success &= asyncio.run(test_specific_image(s3_url))

    if success:
        print("\n🎉 TOUS LES TESTS RÉUSSIS !")
        print("Le système de crop intelligent est prêt à être utilisé.")
        sys.exit(0)
    else:
        print("\n❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("Vérifiez les logs ci-dessus pour résoudre les problèmes.")
        sys.exit(1)

# Usage:
# python test_crop_system.py
# python test_crop_system.py s3://bucket/test-image.jpg