from celery import current_task
from app.services.celery_app import celery_app
from app.services.image_resizer import image_resizer
from app.models.base import PlatformType, ContentType
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='image_optimization.resize_image_for_platform')
def resize_image_for_platform_task(
        self,
        s3_url: str,
        platform: str,
        content_type: str
) -> Dict[str, Any]:
    """
    Tâche Celery pour redimensionner une image S3 pour une plateforme spécifique
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': f'Starting image resize for {platform}_{content_type}'})

        logger.info(f"🔄 Redimensionnement image: {s3_url} pour {platform}_{content_type} - Task {self.request.id}")

        # Convertir les enums
        platform_enum = PlatformType(platform)
        content_type_enum = ContentType(content_type)

        # Obtenir les infos de l'image originale
        self.update_state(state='PROGRESS', meta={'step': 'Analyzing original image'})
        original_info = image_resizer.get_image_info(s3_url)

        # Redimensionner l'image
        self.update_state(state='PROGRESS', meta={'step': 'Resizing image'})
        resized_s3_url = image_resizer.resize_image_from_s3(s3_url, platform_enum, content_type_enum)

        # Obtenir les infos de l'image redimensionnée
        self.update_state(state='PROGRESS', meta={'step': 'Analyzing resized image'})
        resized_info = image_resizer.get_image_info(resized_s3_url) if resized_s3_url != s3_url else None

        # Dimensions optimales
        optimal_dims = image_resizer.get_optimal_dimensions(platform_enum, content_type_enum)

        logger.info(f"✅ Image redimensionnée: {resized_s3_url} - Task {self.request.id}")

        return {
            'task_id': self.request.id,
            'status': 'completed',
            'original_url': s3_url,
            'resized_url': resized_s3_url,
            'platform': platform,
            'content_type': content_type,
            'original_info': original_info,
            'resized_info': resized_info,
            'optimal_dimensions': optimal_dims,
            'was_resized': resized_s3_url != s3_url
        }

    except Exception as e:
        logger.error(f"❌ Erreur redimensionnement image {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': f'{platform}_{content_type} image resize failed'}
        )
        raise


@celery_app.task(bind=True, name='image_optimization.resize_multiple_images')
def resize_multiple_images_task(
        self,
        images_s3_urls: List[str],
        platform: str,
        content_type: str
) -> Dict[str, Any]:
    """
    Tâche Celery pour redimensionner plusieurs images S3 (pour carrousels)
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': f'Starting batch resize for {platform}_{content_type}'})

        logger.info(f"🔄 Redimensionnement batch: {len(images_s3_urls)} images pour {platform}_{content_type}")

        platform_enum = PlatformType(platform)
        content_type_enum = ContentType(content_type)

        resized_results = []

        for i, s3_url in enumerate(images_s3_urls):
            try:
                progress = 20 + (i * 60 / len(images_s3_urls))
                self.update_state(state='PROGRESS', meta={
                    'step': f'Resizing image {i + 1}/{len(images_s3_urls)}',
                    'progress': int(progress)
                })

                # Redimensionner chaque image
                resized_url = image_resizer.resize_image_from_s3(s3_url, platform_enum, content_type_enum)

                resized_results.append({
                    'original_url': s3_url,
                    'resized_url': resized_url,
                    'was_resized': resized_url != s3_url,
                    'index': i
                })

                logger.info(f"✅ Image {i + 1} redimensionnée: {resized_url}")

            except Exception as e:
                logger.error(f"❌ Erreur redimensionnement image {i + 1}: {str(e)}")
                resized_results.append({
                    'original_url': s3_url,
                    'resized_url': s3_url,  # Fallback vers l'original
                    'was_resized': False,
                    'error': str(e),
                    'index': i
                })

        # Extraire les URLs redimensionnées
        resized_urls = [result['resized_url'] for result in resized_results]
        successful_resizes = sum(1 for result in resized_results if result['was_resized'])

        logger.info(f"✅ Redimensionnement batch terminé: {successful_resizes}/{len(images_s3_urls)} réussies")

        return {
            'task_id': self.request.id,
            'status': 'completed',
            'platform': platform,
            'content_type': content_type,
            'original_urls': images_s3_urls,
            'resized_urls': resized_urls,
            'resize_results': resized_results,
            'total_images': len(images_s3_urls),
            'successful_resizes': successful_resizes,
            'optimal_dimensions': image_resizer.get_optimal_dimensions(platform_enum, content_type_enum)
        }

    except Exception as e:
        logger.error(f"❌ Erreur redimensionnement batch {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': f'{platform}_{content_type} batch resize failed'}
        )
        raise


@celery_app.task(bind=True, name='image_optimization.get_platform_recommendations')
def get_platform_recommendations_task(self) -> Dict[str, Any]:
    """
    Tâche Celery pour obtenir les recommandations de dimensions par plateforme
    """
    try:
        logger.info(f"📐 Récupération recommandations dimensions - Task {self.request.id}")

        recommendations = {}

        # Instagram
        recommendations['instagram'] = {
            'post': {
                'dimensions': image_resizer.get_optimal_dimensions(PlatformType.INSTAGRAM, ContentType.POST),
                'ratio': '1:1',
                'description': 'Format carré optimal pour les posts Instagram'
            },
            'story': {
                'dimensions': image_resizer.get_optimal_dimensions(PlatformType.INSTAGRAM, ContentType.STORY),
                'ratio': '9:16',
                'description': 'Format portrait pour les stories Instagram'
            },
            'carousel': {
                'dimensions': image_resizer.get_optimal_dimensions(PlatformType.INSTAGRAM, ContentType.CAROUSEL),
                'ratio': '1:1',
                'description': 'Format carré pour les carrousels Instagram'
            }
        }

        # Twitter
        recommendations['twitter'] = {
            'post': {
                'dimensions': image_resizer.get_optimal_dimensions(PlatformType.TWITTER, ContentType.POST),
                'ratio': '16:9',
                'description': 'Format paysage pour les posts Twitter'
            }
        }

        # Facebook
        recommendations['facebook'] = {
            'post': {
                'dimensions': image_resizer.get_optimal_dimensions(PlatformType.FACEBOOK, ContentType.POST),
                'ratio': '1.91:1',
                'description': 'Format paysage pour les posts Facebook'
            }
        }

        logger.info(f"✅ Recommandations récupérées - Task {self.request.id}")

        return {
            'task_id': self.request.id,
            'status': 'completed',
            'recommendations': recommendations,
            'total_platforms': len(recommendations)
        }

    except Exception as e:
        logger.error(f"❌ Erreur récupération recommandations {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': 'Platform recommendations failed'}
        )
        raise