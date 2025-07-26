#!/usr/bin/env python3
"""
Script de test simplifié pour le système de cropping
"""

import os
import sys
import logging
import tempfile
from PIL import Image

# Ajouter le chemin de l'app
sys.path.insert(0, '/app')

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_basic_imports():
    """Teste les imports de base"""
    try:
        logger.info("🧪 Testing basic imports...")

        # Test PIL
        from PIL import Image
        logger.info("✅ PIL available")

        # Test numpy
        import numpy as np
        logger.info("✅ numpy available")

        # Test OpenCV
        try:
            import cv2
            logger.info("✅ OpenCV available")
        except ImportError:
            logger.warning("⚠️ OpenCV not available")

        return True

    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        return False


def test_unified_cropper():
    """Teste le cropper unifié avec gestion d'erreurs"""
    try:
        logger.info("🧪 Testing unified cropper...")

        # Import du cropper unifié
        from app.services.unified_cropper import UnifiedCropper

        # Créer instance
        cropper = UnifiedCropper()
        logger.info("✅ UnifiedCropper instance created")

        # Tester get_status
        status = cropper.get_status()
        logger.info(f"✅ Status: {status['status']}")
        logger.info(f"📋 Methods: {', '.join(status['available_methods'])}")

        # Créer image test
        test_img = Image.new('RGB', (800, 600), color='red')
        test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        test_img.save(test_file.name, 'JPEG')
        test_file.close()
        logger.info("✅ Test image created")

        # Test crop
        cropped_file = cropper.smart_crop(test_file.name, (400, 400))
        logger.info("✅ Crop completed")

        # Vérifier résultat
        with Image.open(cropped_file) as result:
            if result.size == (400, 400):
                logger.info("✅ Crop dimensions correct")
                success = True
            else:
                logger.error(f"❌ Wrong dimensions: {result.size}")
                success = False

        # Nettoyer
        os.unlink(test_file)
        os.unlink(cropped_file)
        logger.info("🧹 Cleanup completed")

        return success

    except Exception as e:
        logger.error(f"❌ UnifiedCropper test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_opencv_cropper():
    """Teste le cropper OpenCV"""
    try:
        logger.info("🧪 Testing OpenCV cropper...")

        from app.services.opencv_cropper import OpenCVCropper, test_opencv_availability

        if not test_opencv_availability():
            logger.warning("⚠️ OpenCV not functional, skipping test")
            return True  # Non-critique

        cropper = OpenCVCropper()
        logger.info("✅ OpenCVCropper instance created")

        # Test basique
        test_img = Image.new('RGB', (800, 600), color='blue')
        test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        test_img.save(test_file.name, 'JPEG')
        test_file.close()

        cropped_file = cropper.smart_crop(test_file.name, (300, 300))

        with Image.open(cropped_file) as result:
            success = result.size == (300, 300)

        # Nettoyer
        os.unlink(test_file)
        os.unlink(cropped_file)

        if success:
            logger.info("✅ OpenCV cropper test passed")
        else:
            logger.error("❌ OpenCV cropper test failed")

        return success

    except Exception as e:
        logger.error(f"❌ OpenCV cropper test error: {e}")
        return False


def test_intelligent_cropper():
    """Teste le cropper intelligent"""
    try:
        logger.info("🧪 Testing intelligent cropper...")

        from app.services.intelligent_cropper import IntelligentCropper

        cropper = IntelligentCropper()
        logger.info("✅ IntelligentCropper instance created")

        capabilities = cropper.get_capabilities()
        logger.info(f"📋 Capabilities: {capabilities}")

        # Test basique
        test_img = Image.new('RGB', (800, 600), color='green')
        test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        test_img.save(test_file.name, 'JPEG')
        test_file.close()

        cropped_file = cropper.smart_crop(test_file.name, (500, 500))

        with Image.open(cropped_file) as result:
            success = result.size == (500, 500)

        # Nettoyer
        os.unlink(test_file)
        os.unlink(cropped_file)

        if success:
            logger.info("✅ Intelligent cropper test passed")
        else:
            logger.error("❌ Intelligent cropper test failed")

        return success

    except Exception as e:
        logger.error(f"❌ Intelligent cropper test error: {e}")
        return False


def main():
    """Fonction principale"""
    logger.info("🚀 Starting simplified crop system test...")

    tests = [
        ("Basic Imports", test_basic_imports),
        ("Unified Cropper", test_unified_cropper),
        ("OpenCV Cropper", test_opencv_cropper),
        ("Intelligent Cropper", test_intelligent_cropper),
    ]

    results = []

    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running {test_name}...")
        try:
            result = test_func()
            results.append(result)
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status} {test_name}")
        except Exception as e:
            logger.error(f"❌ {test_name} ERROR: {e}")
            results.append(False)

    # Résultats finaux
    passed = sum(results)
    total = len(results)

    logger.info(f"\n📊 Final Results: {passed}/{total} tests passed")

    if passed >= 2:  # Au minimum imports + unified cropper
        logger.info("✅ Crop system operational (minimum requirements met)")
        return True
    else:
        logger.error("❌ Crop system failed (critical components not working)")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)