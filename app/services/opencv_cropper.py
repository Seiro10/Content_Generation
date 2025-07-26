import cv2
import numpy as np
import tempfile
import os
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class OpenCVCropper:
    """Cropper basique avec OpenCV sans saliency"""

    def __init__(self):
        self.available = True
        logger.info("✅ OpenCV Cropper basique initialisé")

    def smart_crop(self, input_path: str, target_size: Tuple[int, int]) -> str:
        """Crop intelligent basique avec détection de contours"""
        try:
            # Lire l'image
            img = cv2.imread(input_path)
            if img is None:
                raise ValueError("Impossible de lire l'image")

            # Vérifier la qualité avant crop
            quality_check = self._check_quality(img, target_size)
            if not quality_check['acceptable']:
                logger.warning(f"⚠️ {quality_check['message']}")

            # Crop intelligent basique
            cropped = self._intelligent_crop_basic(img, target_size)

            # Sauvegarder
            output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            cv2.imwrite(output_file.name, cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
            output_file.close()

            return output_file.name

        except Exception as e:
            logger.error(f"❌ Erreur OpenCV crop: {str(e)}")
            raise

    def _check_quality(self, img: np.ndarray, target_size: Tuple[int, int]) -> dict:
        """Vérifie si le crop maintiendra une qualité acceptable"""
        h, w = img.shape[:2]
        target_w, target_h = target_size

        scale_factor_w = target_w / w
        scale_factor_h = target_h / h
        max_scale = max(scale_factor_w, scale_factor_h)

        if max_scale > 2.0:
            return {
                'acceptable': False,
                'message': f"Agrandissement {max_scale:.1f}x détecté - qualité dégradée probable",
                'scale_factor': max_scale,
                'recommendation': "Utiliser une image source plus grande"
            }
        elif max_scale > 1.5:
            return {
                'acceptable': True,
                'message': f"Agrandissement {max_scale:.1f}x - qualité acceptable mais dégradée",
                'scale_factor': max_scale,
                'recommendation': "Qualité OK mais pourrait être meilleure"
            }
        else:
            return {
                'acceptable': True,
                'message': f"Qualité excellente (scale: {max_scale:.1f}x)",
                'scale_factor': max_scale,
                'recommendation': "Aucune"
            }

    def _intelligent_crop_basic(self, img: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
        """Crop intelligent basique sans saliency"""
        h, w = img.shape[:2]
        target_w, target_h = target_size

        # Calculer le ratio optimal
        img_ratio = w / h
        target_ratio = target_w / target_h

        if img_ratio > target_ratio:
            # Image trop large - crop horizontal au centre
            new_w = int(h * target_ratio)
            start_x = (w - new_w) // 2
            cropped = img[:, start_x:start_x + new_w]
        else:
            # Image trop haute - crop vertical intelligent
            new_h = int(w / target_ratio)
            # Privilégier le tiers supérieur pour les images verticales
            start_y = max(0, min(h - new_h, h // 4))
            cropped = img[start_y:start_y + new_h, :]

        # Redimensionner avec interpolation de haute qualité
        if cropped.shape[1] < target_w or cropped.shape[0] < target_h:
            # Agrandissement - utiliser INTER_CUBIC
            interpolation = cv2.INTER_CUBIC
        else:
            # Réduction - utiliser INTER_AREA
            interpolation = cv2.INTER_AREA

        final = cv2.resize(cropped, target_size, interpolation=interpolation)
        return final


class OpenCVOnlyCropper:
    """Cropper OpenCV simple pour compatibilité"""

    def __init__(self):
        self.opencv_cropper = OpenCVCropper()
        self.available = True
        logger.info("✅ OpenCV Only Cropper initialisé")

    def crop_image(self, input_path: str, target_size: Tuple[int, int]) -> str:
        """Interface simplifiée pour le cropping"""
        return self.opencv_cropper.smart_crop(input_path, target_size)

    def is_available(self) -> bool:
        """Vérifie si OpenCV est disponible"""
        return self.available


# Fonction standalone pour compatibilité
def opencv_only_cropper() -> OpenCVOnlyCropper:
    """Retourne une instance du cropper OpenCV"""
    return OpenCVOnlyCropper()


# Instance globale
opencv_cropper = OpenCVCropper()
opencv_only_cropper_instance = OpenCVOnlyCropper()


# Fonctions utilitaires pour l'export
def get_opencv_cropper():
    """Récupère l'instance du cropper OpenCV"""
    return opencv_cropper


def get_opencv_only_cropper():
    """Récupère l'instance du cropper OpenCV simple"""
    return opencv_only_cropper_instance


def crop_image_opencv(input_path: str, target_size: Tuple[int, int]) -> str:
    """Fonction utilitaire pour cropper une image avec OpenCV"""
    return opencv_cropper.smart_crop(input_path, target_size)


def test_opencv_availability() -> bool:
    """Teste si OpenCV est disponible et fonctionnel"""
    try:
        # Test simple OpenCV
        test_array = np.zeros((100, 100, 3), dtype=np.uint8)
        resized = cv2.resize(test_array, (50, 50))
        return resized.shape == (50, 50, 3)
    except Exception as e:
        logger.error(f"❌ Test OpenCV échoué: {str(e)}")
        return False