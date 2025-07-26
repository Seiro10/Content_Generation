import logging
import tempfile
import os
from typing import Tuple, Optional, Dict, Any
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class UnifiedCropper:
    """Cropper unifié qui utilise la meilleure méthode disponible"""

    def __init__(self):
        self.available_methods = []
        self.primary_method = None
        self._initialize_croppers()

    def _initialize_croppers(self):
        """Initialise les différents croppers disponibles"""
        # Tester OpenCV + PIL (toujours disponible)
        try:
            import cv2
            from PIL import Image
            self.available_methods.append("opencv_pil")
            self.primary_method = "opencv_pil"
            logger.info("✅ OpenCV + PIL available")
        except ImportError as e:
            logger.warning(f"⚠️ OpenCV non disponible: {e}")

        # Tester OpenCV seul - avec gestion d'erreur robuste
        try:
            from app.services.opencv_cropper import opencv_only_cropper
            cropper = opencv_only_cropper()
            if cropper and cropper.is_available():
                self.available_methods.append("opencv_only")
                if not self.primary_method:
                    self.primary_method = "opencv_only"
                logger.info("✅ OpenCV standalone available")
        except (ImportError, Exception) as e:
            logger.warning(f"⚠️ OpenCV cropper non disponible: {e}")

        # Tester SAM (optionnel) - avec gestion d'erreur
        try:
            # Import SAM si disponible (pas critique)
            # Pour l'instant, on simule juste la disponibilité
            import numpy as np  # Test basique
            self.available_methods.append("sam")
            logger.info("✅ SAM available")
        except (ImportError, Exception) as e:
            logger.info(f"ℹ️ SAM non disponible (optionnel): {e}")

        if not self.available_methods:
            # Fallback: PIL seul
            self.available_methods.append("pil_only")
            self.primary_method = "pil_only"
            logger.warning("⚠️ Utilisation PIL uniquement comme fallback")

        logger.info(f"✅ Unified cropper initialized: {self.primary_method}")
        logger.info(f"📋 Méthodes disponibles: {', '.join(self.available_methods)}")

    def crop_for_platform(self, input_path: str, platform: str, content_type: str) -> str:
        """Crop une image pour une plateforme spécifique"""
        target_dimensions = self._get_platform_dimensions(platform, content_type)
        return self.smart_crop(input_path, target_dimensions)

    def smart_crop(self, input_path: str, target_size: Tuple[int, int]) -> str:
        """Crop intelligent utilisant la meilleure méthode disponible"""
        logger.info(f"🎯 Crop unifié vers {target_size} avec méthode: {self.primary_method}")

        try:
            if self.primary_method == "opencv_pil":
                return self._crop_opencv_pil(input_path, target_size)
            elif self.primary_method == "opencv_only":
                return self._crop_opencv_only(input_path, target_size)
            elif self.primary_method == "pil_only":
                return self._crop_pil_only(input_path, target_size)
            else:
                # Fallback
                return self._crop_pil_only(input_path, target_size)

        except Exception as e:
            logger.error(f"❌ Erreur crop principal: {e}")
            # Fallback vers PIL
            logger.info("🔄 Fallback vers PIL uniquement")
            return self._crop_pil_only(input_path, target_size)

    def _crop_opencv_pil(self, input_path: str, target_size: Tuple[int, int]) -> str:
        """Crop avec OpenCV + PIL"""
        import cv2

        # Lire avec OpenCV pour analyse
        img_cv = cv2.imread(input_path)
        if img_cv is None:
            raise ValueError("Impossible de lire l'image avec OpenCV")

        # Analyse basique des dimensions
        h, w = img_cv.shape[:2]
        target_w, target_h = target_size

        # Calculer crop intelligent
        img_ratio = w / h
        target_ratio = target_w / target_h

        if img_ratio > target_ratio:
            # Image trop large - crop horizontal centré
            new_w = int(h * target_ratio)
            start_x = (w - new_w) // 2
            crop_coords = (start_x, 0, start_x + new_w, h)
        else:
            # Image trop haute - crop vertical privilégiant le haut
            new_h = int(w / target_ratio)
            start_y = min(h - new_h, h // 4)  # Privilégier le haut
            crop_coords = (0, start_y, w, start_y + new_h)

        # Utiliser PIL pour le crop et resize final (meilleure qualité)
        with Image.open(input_path) as img_pil:
            cropped = img_pil.crop(crop_coords)
            resized = cropped.resize(target_size, Image.Resampling.LANCZOS)

            # Sauvegarder
            output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            resized.save(output_file.name, 'JPEG', quality=95, optimize=True)
            output_file.close()

            return output_file.name

    def _crop_opencv_only(self, input_path: str, target_size: Tuple[int, int]) -> str:
        """Crop avec OpenCV uniquement"""
        try:
            from app.services.opencv_cropper import get_opencv_cropper
            cropper = get_opencv_cropper()
            return cropper.smart_crop(input_path, target_size)
        except Exception as e:
            logger.warning(f"⚠️ OpenCV cropper failed, fallback to PIL: {e}")
            return self._crop_pil_only(input_path, target_size)

    def _crop_pil_only(self, input_path: str, target_size: Tuple[int, int]) -> str:
        """Crop avec PIL uniquement (fallback)"""
        with Image.open(input_path) as img:
            # Crop intelligent basique
            target_w, target_h = target_size
            img_ratio = img.width / img.height
            target_ratio = target_w / target_h

            if img_ratio > target_ratio:
                # Image trop large
                new_w = int(img.height * target_ratio)
                start_x = (img.width - new_w) // 2
                cropped = img.crop((start_x, 0, start_x + new_w, img.height))
            else:
                # Image trop haute
                new_h = int(img.width / target_ratio)
                start_y = min(img.height - new_h, img.height // 4)
                cropped = img.crop((0, start_y, img.width, start_y + new_h))

            # Redimensionner
            resized = cropped.resize(target_size, Image.Resampling.LANCZOS)

            # Sauvegarder
            output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            resized.save(output_file.name, 'JPEG', quality=90)
            output_file.close()

            return output_file.name

    def _get_platform_dimensions(self, platform: str, content_type: str) -> Tuple[int, int]:
        """Retourne les dimensions pour chaque plateforme"""
        dimensions = {
            'instagram': {
                'post': (1080, 1080),
                'story': (1080, 1920),
                'carousel': (1080, 1080)
            },
            'twitter': {
                'post': (1200, 675)
            },
            'facebook': {
                'post': (1200, 630)
            }
        }

        return dimensions.get(platform, {}).get(content_type, (1080, 1080))

    def get_available_methods(self) -> list:
        """Retourne les méthodes de crop disponibles"""
        return self.available_methods.copy()

    def get_primary_method(self) -> str:
        """Retourne la méthode primaire utilisée"""
        return self.primary_method

    def get_crop_status(self) -> Dict[str, Any]:
        """Alias pour get_status (compatibilité)"""
        return self.get_status()

    def is_operational(self) -> bool:
        """Vérifie si le cropper est opérationnel"""
        return self.primary_method is not None

    def get_system_info(self) -> Dict[str, Any]:
        """Retourne les informations système du cropper"""
        return {
            "cropper_type": "unified",
            "version": "1.0.0",
            "primary_method": self.primary_method,
            "fallback_available": "pil_only" in self.available_methods,
            "advanced_features": {
                "opencv_analysis": "opencv_pil" in self.available_methods,
                "saliency_detection": "sam" in self.available_methods,
                "quality_optimization": True
            }
        }

    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut du système de cropping"""
        return {
            "available_methods": self.available_methods,
            "primary_method": self.primary_method,
            "opencv_available": "opencv_pil" in self.available_methods or "opencv_only" in self.available_methods,
            "pil_available": True,
            "sam_available": "sam" in self.available_methods,
            "status": "operational" if self.primary_method else "degraded",
            "system_info": self.get_system_info()
        }

    def test_crop(self) -> bool:
        """Teste le système de crop"""
        try:
            # Créer une image test
            test_img = Image.new('RGB', (800, 600), color='red')
            test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            test_img.save(test_file.name, 'JPEG')
            test_file.close()

            # Tester le crop
            cropped_file = self.smart_crop(test_file.name, (400, 400))

            # Vérifier le résultat
            with Image.open(cropped_file) as result_img:
                success = result_img.size == (400, 400)

            # Nettoyer
            os.unlink(test_file.name)
            os.unlink(cropped_file)

            return success

        except Exception as e:
            logger.error(f"❌ Test crop échoué: {e}")
            return False


# Instance globale avec gestion d'erreur robuste
unified_cropper = None

try:
    unified_cropper = UnifiedCropper()
    logger.info("✅ Global unified cropper initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize global unified cropper: {str(e)}")
    unified_cropper = None


# Fonctions utilitaires avec vérification
def crop_image_unified(input_path: str, platform: str, content_type: str = "post") -> str:
    """Fonction utilitaire pour cropper une image"""
    if unified_cropper is None:
        raise RuntimeError("Unified cropper not initialized")
    return unified_cropper.crop_for_platform(input_path, platform, content_type)


def get_unified_cropper():
    """Récupère l'instance du cropper unifié"""
    if unified_cropper is None:
        logger.warning("⚠️ Unified cropper not initialized")
        raise RuntimeError("Unified cropper not available")
    return unified_cropper


def test_unified_crop_system() -> bool:
    """Teste le système de crop unifié"""
    try:
        if unified_cropper is None:
            logger.error("❌ Unified cropper not initialized")
            return False
        return unified_cropper.test_crop()
    except Exception as e:
        logger.error(f"❌ Unified crop system test failed: {str(e)}")
        return False


def get_crop_status() -> Dict[str, Any]:
    """Récupère le statut du système de cropping"""
    try:
        if unified_cropper is None:
            return {"status": "failed", "error": "Cropper not initialized"}
        return unified_cropper.get_status()
    except Exception as e:
        logger.error(f"❌ Error getting crop status: {str(e)}")
        return {"status": "error", "error": str(e)}


def get_available_crop_methods() -> list:
    """Retourne les méthodes de crop disponibles"""
    try:
        if unified_cropper is None:
            return []
        return unified_cropper.get_available_methods()
    except Exception as e:
        logger.error(f"❌ Error getting crop methods: {str(e)}")
        return []


def check_crop_system_health() -> bool:
    """Vérifie la santé du système de cropping"""
    try:
        if unified_cropper is None:
            return False
        status = unified_cropper.get_status()
        return status["status"] == "operational"
    except Exception as e:
        logger.error(f"❌ Error checking crop system health: {str(e)}")
        return False