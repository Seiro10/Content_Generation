import logging
import tempfile
import os
from typing import Dict, Tuple, Optional
from PIL import Image, ImageOps
import boto3
from io import BytesIO

from app.config.settings import settings
from app.models.base import PlatformType, ContentType

logger = logging.getLogger(__name__)


class ImageResizerService:
    """Service de redimensionnement d'images pour les réseaux sociaux"""

    def __init__(self):
        self.s3_client = None
        self._init_s3_client()

    def _init_s3_client(self):
        """Initialise le client S3"""
        try:
            aws_key = settings.aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret = settings.aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
            aws_region = settings.aws_default_region or os.getenv('AWS_DEFAULT_REGION', 'eu-west-3')

            if aws_key and aws_secret:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=aws_key,
                    aws_secret_access_key=aws_secret,
                    region_name=aws_region
                )
                logger.info("✅ S3 client initialized for image resizing")
            else:
                logger.warning("❌ AWS credentials not found - image resizing disabled")
        except Exception as e:
            logger.error(f"❌ Failed to initialize S3 client: {str(e)}")

    def get_optimal_dimensions(self, platform: PlatformType, content_type: ContentType) -> Tuple[int, int]:
        """Retourne les dimensions optimales pour une plateforme/type"""

        dimensions_map = {
            PlatformType.INSTAGRAM: {
                ContentType.POST: (1080, 1080),  # Carré
                ContentType.STORY: (1080, 1920),  # Portrait 9:16
                ContentType.CAROUSEL: (1080, 1080)  # Carré
            },
            PlatformType.TWITTER: {
                ContentType.POST: (1200, 675),  # Paysage 16:9
            },
            PlatformType.FACEBOOK: {
                ContentType.POST: (1200, 630),  # Paysage ~1.9:1
            }
        }

        platform_dims = dimensions_map.get(platform, {})
        return platform_dims.get(content_type, (1080, 1080))  # Default carré

    def resize_image_from_s3(
            self,
            s3_url: str,
            platform: PlatformType,
            content_type: ContentType
    ) -> Optional[str]:
        """
        Redimensionne une image S3 et retourne l'URL de l'image redimensionnée
        """
        if not self.s3_client:
            logger.error("❌ S3 client not available")
            return s3_url  # Retourner l'original si pas de client

        try:
            logger.info(f"🔄 Redimensionnement image S3: {s3_url}")

            # Parse S3 URL
            if not s3_url.startswith('s3://'):
                logger.warning(f"⚠️ URL non-S3 détectée: {s3_url}")
                return s3_url

            s3_path = s3_url[5:]  # Remove 's3://'
            bucket, key = s3_path.split('/', 1)

            # Télécharger l'image originale
            original_obj = self.s3_client.get_object(Bucket=bucket, Key=key)
            image_data = original_obj['Body'].read()

            # Ouvrir avec Pillow
            with Image.open(BytesIO(image_data)) as img:
                # Convertir en RGB si nécessaire
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Obtenir les dimensions cibles
                target_width, target_height = self.get_optimal_dimensions(platform, content_type)

                logger.info(f"📐 Original: {img.size} → Target: {target_width}x{target_height}")

                # Redimensionner avec maintien du ratio et crop si nécessaire
                resized_img = ImageOps.fit(
                    img,
                    (target_width, target_height),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5)
                )

                # Sauvegarder dans un buffer
                output_buffer = BytesIO()
                resized_img.save(output_buffer, format='JPEG', quality=85, optimize=True)
                output_buffer.seek(0)

                # Générer nouvelle clé S3
                resized_key = self._generate_resized_key(key, platform, content_type)

                # Upload de l'image redimensionnée
                self.s3_client.put_object(
                    Bucket=bucket,
                    Key=resized_key,
                    Body=output_buffer.getvalue(),
                    ContentType='image/jpeg'
                )

                # Construire l'URL S3 de l'image redimensionnée
                resized_s3_url = f"s3://{bucket}/{resized_key}"

                logger.info(f"✅ Image redimensionnée: {resized_s3_url}")
                return resized_s3_url

        except Exception as e:
            logger.error(f"❌ Erreur redimensionnement: {str(e)}")
            return s3_url  # Retourner l'original en cas d'erreur

    def _generate_resized_key(self, original_key: str, platform: PlatformType, content_type: ContentType) -> str:
        """Génère une nouvelle clé S3 pour l'image redimensionnée"""
        # Séparer le nom et l'extension
        base_name, ext = os.path.splitext(original_key)

        # Ajouter suffixe avec plateforme et type
        suffix = f"_resized_{platform.value}_{content_type.value}"

        return f"{base_name}{suffix}.jpg"  # Toujours en .jpg pour optimisation

    def get_image_info(self, s3_url: str) -> Optional[Dict]:
        """Récupère les informations d'une image S3"""
        if not self.s3_client or not s3_url.startswith('s3://'):
            return None

        try:
            s3_path = s3_url[5:]
            bucket, key = s3_path.split('/', 1)

            # Métadonnées S3
            response = self.s3_client.head_object(Bucket=bucket, Key=key)

            # Télécharger pour obtenir les dimensions
            obj = self.s3_client.get_object(Bucket=bucket, Key=key)
            with Image.open(BytesIO(obj['Body'].read())) as img:
                width, height = img.size

            return {
                'url': s3_url,
                'dimensions': (width, height),
                'file_size': response.get('ContentLength', 0),
                'content_type': response.get('ContentType', 'unknown'),
                'last_modified': response.get('LastModified')
            }

        except Exception as e:
            logger.error(f"❌ Erreur récupération info image: {str(e)}")
            return None


# Instance globale
image_resizer = ImageResizerService()