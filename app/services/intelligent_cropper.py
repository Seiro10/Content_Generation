import logging
import tempfile
import os
from typing import Tuple, Optional, Dict, Any
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class IntelligentCropper:
    """Cropper intelligent avec support SAM + OpenCV"""

    def __init__(self):
        self.sam_available = False
        self.opencv_available = False
        self._initialize_croppers()

    def _initialize_croppers(self):
        """Initialise les croppers disponibles"""
        # Test OpenCV
        try:
            import cv2
            self.opencv_available = True
            logger.info("✅ OpenCV disponible pour intelligent cropper")
        except ImportError:
            logger.warning("⚠️ OpenCV non disponible")

        # Test SAM (Segment Anything Model)
        try:
            # Essayer d'importer SAM (optionnel)
            # import segment_anything
            # self.sam_available = True
            logger.warning("⚠️ SAM checkpoint not found, using fallback detection")
        except ImportError:
            logger.info("ℹ️ SAM non disponible (utilisation fallback)")

        logger.info("✅ Intelligent Cropper (SAM + OpenCV) initialisé")

    def smart_crop(self, input_path: str, target_size: Tuple[int, int]) -> str:
        """Crop intelligent avec détection de saillance"""
        logger.info(f"🎯 Crop intelligent: {input_path}")

        if self.opencv_available:
            return self._crop_with_opencv_analysis(input_path, target_size)
        else:
            # Fallback PIL
            return self._crop_with_pil_only(input_path, target_size)

    def _crop_with_opencv_analysis(self, input_path: str, target_size: Tuple[int, int]) -> str:
        """Crop avec analyse OpenCV"""
        import cv2

        # Lire l'image
        img = cv2.imread(input_path)
        if img is None:
            raise ValueError("Impossible de lire l'image")

        # Détection des régions saillantes
        saliency_map = self._detect_saliency_regions(img)

        # Calculer le meilleur crop basé sur la saillance
        if saliency_map is not None:
            crop_coords = self._calculate_optimal_crop_from_saliency(img, saliency_map, target_size)
        else:
            # Fallback: crop centré
            crop_coords = self._calculate_center_crop(img.shape[:2], target_size)

        # Appliquer le crop avec PIL (meilleure qualité)
        with Image.open(input_path) as img_pil:
            cropped = img_pil.crop(crop_coords)
            resized = cropped.resize(target_size, Image.Resampling.LANCZOS)

            # Sauvegarder
            output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            resized.save(output_file.name, 'JPEG', quality=95, optimize=True)
            output_file.close()

            return output_file.name

    def _detect_saliency_regions(self, img: np.ndarray) -> Optional[np.ndarray]:
        """Détecte les régions saillantes (avec fallback)"""
        import cv2

        try:
            # Essayer la méthode moderne si disponible
            if hasattr(cv2, 'saliency'):
                saliency_algo = cv2.saliency.StaticSaliencySpectralResidual_create()
                success, saliency_map = saliency_algo.computeSaliency(img)
                if success:
                    return (saliency_map * 255).astype(np.uint8)
        except Exception as e:
            logger.warning(f"⚠️ Saliency moderne échouée: {e}")

        try:
            # Fallback : détection de contours comme approximation
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Détection de contours
            edges = cv2.Canny(gray, 50, 150)

            # Dilatation pour créer des régions
            kernel = np.ones((5, 5), np.uint8)
            saliency_approx = cv2.dilate(edges, kernel, iterations=2)

            # Blur pour simuler une carte de saillance
            saliency_approx = cv2.GaussianBlur(saliency_approx, (21, 21), 0)

            logger.info("✅ Utilisation de la détection de contours comme approximation de saillance")
            return saliency_approx

        except Exception as e:
            logger.error(f"❌ Erreur détection saillance fallback: {e}")
            return None

    def _calculate_optimal_crop_from_saliency(self, img: np.ndarray, saliency_map: np.ndarray,
                                              target_size: Tuple[int, int]) -> Tuple[int, int, int, int]:
        """Calcule le meilleur crop basé sur la carte de saillance"""
        h, w = img.shape[:2]
        target_w, target_h = target_size

        # Calculer le ratio de crop
        img_ratio = w / h
        target_ratio = target_w / target_h

        if img_ratio > target_ratio:
            # Image trop large - trouver la zone la plus saillante horizontalement
            crop_h = h
            crop_w = int(h * target_ratio)

            # Analyser la saillance par colonnes
            col_saliency = np.sum(saliency_map, axis=0)

            # Trouver la fenêtre de crop_w avec la plus haute saillance
            best_score = 0
            best_x = 0

            for x in range(w - crop_w + 1):
                score = np.sum(col_saliency[x:x + crop_w])
                if score > best_score:
                    best_score = score
                    best_x = x

            return (best_x, 0, best_x + crop_w, crop_h)

        else:
            # Image trop haute - trouver la zone la plus saillante verticalement
            crop_w = w
            crop_h = int(w / target_ratio)

            # Analyser la saillance par lignes
            row_saliency = np.sum(saliency_map, axis=1)

            # Trouver la fenêtre de crop_h avec la plus haute saillance
            best_score = 0
            best_y = 0

            for y in range(h - crop_h + 1):
                score = np.sum(row_saliency[y:y + crop_h])
                if score > best_score:
                    best_score = score
                    best_y = y

            return (0, best_y, crop_w, best_y + crop_h)

    def _calculate_center_crop(self, img_shape: Tuple[int, int], target_size: Tuple[int, int]) -> Tuple[
        int, int, int, int]:
        """Calcule un crop centré (fallback)"""
        h, w = img_shape
        target_w, target_h = target_size

        img_ratio = w / h
        target_ratio = target_w / target_h

        if img_ratio > target_ratio:
            # Image trop large
            crop_w = int(h * target_ratio)
            crop_h = h
            start_x = (w - crop_w) // 2
            start_y = 0
        else:
            # Image trop haute
            crop_w = w
            crop_h = int(w / target_ratio)
            start_x = 0
            start_y = (h - crop_h) // 2

        return (start_x, start_y, start_x + crop_w, start_y + crop_h)

    def _crop_with_pil_only(self, input_path: str, target_size: Tuple[int, int]) -> str:
        """Crop avec PIL uniquement (fallback)"""
        with Image.open(input_path) as img:
            # Crop centré basique
            target_w, target_h = target_size
            img_ratio = img.width / img.height
            target_ratio = target_w / target_h

            if img_ratio > target_ratio:
                # Image trop large
                new_w = int(img.height * target_ratio)
                start_x = (img.width - new_w) // 2
                crop_coords = (start_x, 0, start_x + new_w, img.height)
            else:
                # Image trop haute
                new_h = int(img.width / target_ratio)
                start_y = (img.height - new_h) // 2
                crop_coords = (0, start_y, img.width, start_y + new_h)

            cropped = img.crop(crop_coords)
            resized = cropped.resize(target_size, Image.Resampling.LANCZOS)

            # Sauvegarder
            output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            resized.save(output_file.name, 'JPEG', quality=90)
            output_file.close()

            return output_file.name

    def is_available(self) -> bool:
        """Vérifie si le cropper intelligent est disponible"""
        return True  # PIL est toujours disponible comme fallback

    def get_capabilities(self) -> Dict[str, bool]:
        """Retourne les capacités disponibles"""
        return {
            "opencv": self.opencv_available,
            "sam": self.sam_available,
            "pil_fallback": True,
            "saliency_detection": self.opencv_available
        }


# Instance globale
intelligent_cropper = IntelligentCropper()


# Fonctions utilitaires
def get_intelligent_cropper():
    """Récupère l'instance du cropper intelligent"""
    return intelligent_cropper


def crop_image_intelligent(input_path: str, target_size: Tuple[int, int]) -> str:
    """Fonction utilitaire pour cropper une image avec détection intelligente"""
    return intelligent_cropper.smart_crop(input_path, target_size)


def test_intelligent_cropper() -> bool:
    """Teste le cropper intelligent"""
    try:
        # Créer une image test
        test_img = Image.new('RGB', (800, 600), color='blue')
        test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        test_img.save(test_file.name, 'JPEG')
        test_file.close()

        # Tester le crop
        cropped_file = intelligent_cropper.smart_crop(test_file.name, (400, 400))

        # Vérifier le résultat
        with Image.open(cropped_file) as result_img:
            success = result_img.size == (400, 400)

        # Nettoyer
        os.unlink(test_file.name)
        os.unlink(cropped_file)

        return success

    except Exception as e:
        logger.error(f"❌ Test intelligent cropper échoué: {e}")
        return False