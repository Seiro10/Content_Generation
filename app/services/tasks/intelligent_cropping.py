from celery import current_task
from app.services.celery_app import celery_app
import logging
import boto3
import tempfile
import os
from PIL import Image
from typing import Dict, Any, Tuple, Optional, List
import numpy as np

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='intelligent_cropping.smart_crop_for_platform')
def smart_crop_for_platform_task(
        self,
        s3_url: str,
        platform: str,
        content_type: str = "post"
) -> Dict[str, Any]:
    """
    Tâche Celery pour redimensionner intelligemment une image selon la plateforme
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': 'Starting intelligent cropping'})

        logger.info(f"Starting intelligent cropping for {platform}_{content_type} - Task {self.request.id}")


        # Définir les dimensions cibles par plateforme
        target_dimensions = _get_target_dimensions(platform, content_type)

        # Télécharger l'image S3
        temp_input = _download_s3_image(s3_url)

        # Cropper intelligemment
        temp_output = _intelligent_crop(temp_input, target_dimensions)

        # Upload vers S3
        output_s3_url = _upload_cropped_to_s3(temp_output, s3_url, platform, content_type)

        # Nettoyer les fichiers temporaires
        os.unlink(temp_input)
        os.unlink(temp_output)

        logger.info(f"Intelligent cropping completed - Task {self.request.id}")

        return {
            'task_id': self.request.id,
            'status': 'completed',
            'original_s3_url': s3_url,
            'cropped_s3_url': output_s3_url,
            'platform': platform,
            'content_type': content_type,
            'target_dimensions': target_dimensions
        }

    except Exception as e:
        logger.error(f"Error in intelligent cropping task {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': 'Intelligent cropping failed'}
        )
        raise


def _get_target_dimensions(platform: str, content_type: str) -> Tuple[int, int]:
    """Retourne les dimensions cibles selon la plateforme"""
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


def _download_s3_image(s3_url: str) -> str:
    """Télécharge l'image S3 vers un fichier temporaire"""
    from app.config.settings import settings

    # Parse S3 URL
    s3_path = s3_url[5:]  # Remove 's3://'
    bucket, key = s3_path.split('/', 1)

    # Client S3
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_default_region
    )

    # Télécharger
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    s3_client.download_file(bucket, key, tmp_file.name)
    tmp_file.close()

    return tmp_file.name


def _intelligent_crop(input_path: str, target_dimensions: Tuple[int, int]) -> str:
    """Redimensionne intelligemment l'image"""
    target_width, target_height = target_dimensions

    with Image.open(input_path) as img:
        # Calculer le ratio de crop intelligent (centre)
        img_ratio = img.width / img.height
        target_ratio = target_width / target_height

        if img_ratio > target_ratio:
            # Image trop large - crop les côtés
            new_width = int(img.height * target_ratio)
            left = (img.width - new_width) // 2
            cropped = img.crop((left, 0, left + new_width, img.height))
        else:
            # Image trop haute - crop le haut/bas
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            cropped = img.crop((0, top, img.width, top + new_height))

        # Redimensionner aux dimensions finales
        final = cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)

        # Sauvegarder
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        final.save(output_file.name, 'JPEG', quality=90)
        output_file.close()

        return output_file.name


def _detect_saliency_regions(self, img: np.ndarray) -> Optional[np.ndarray]:
    """Détecte les régions saillantes (avec fallback)"""
    try:
        # Essayer la méthode moderne
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


def _upload_cropped_to_s3(local_path: str, original_s3_url: str, platform: str, content_type: str) -> str:
    """Upload l'image croppée vers S3"""
    from app.config.settings import settings

    # Parse original URL
    s3_path = original_s3_url[5:]
    bucket, original_key = s3_path.split('/', 1)

    # Nouveau nom avec suffix
    name_parts = original_key.rsplit('.', 1)
    new_key = f"{name_parts[0]}_cropped_{platform}_{content_type}.{name_parts[1] if len(name_parts) > 1 else 'jpg'}"

    # Client S3
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_default_region
    )

    # Upload
    s3_client.upload_file(local_path, bucket, new_key)

    return f"s3://{bucket}/{new_key}"