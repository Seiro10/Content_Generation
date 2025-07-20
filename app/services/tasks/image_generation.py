from celery import current_task
from app.services.celery_app import celery_app
import logging
from typing import Dict, Any, List
import uuid
import time

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='image_generation.generate_images')
def generate_images_task(self, context: str, nb_images: int = 5) -> Dict[str, Any]:
    """
    Tâche Celery pour générer des images (placeholder pour l'instant)
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': 'Starting image generation'})

        logger.info(f"Starting image generation for task {self.request.id}")

        # Simulation du processus de génération
        self.update_state(state='PROGRESS', meta={
            'step': 'Analyzing context',
            'progress': 20
        })

        # Analyser le contexte
        context_analysis = _analyze_image_context(context)

        self.update_state(state='PROGRESS', meta={
            'step': 'Generating images',
            'progress': 50
        })

        # Générer les images (simulation)
        generated_urls = []
        for i in range(nb_images):
            # Simulation d'une génération d'image
            image_id = str(uuid.uuid4())[:8]
            image_url = f"https://generated-images.s3.amazonaws.com/carousel_{image_id}.jpg"
            generated_urls.append(image_url)

            # Simuler le temps de génération
            time.sleep(0.5)

            # Mettre à jour le progrès
            progress = 50 + (i + 1) * (40 / nb_images)
            self.update_state(state='PROGRESS', meta={
                'step': f'Generated image {i + 1}/{nb_images}',
                'progress': int(progress)
            })

        # Afficher le message dans les logs (comme demandé)
        print(f"Images generated: {nb_images} images pour le contexte '{context[:50]}...'")
        logger.info(f"Images generated: {nb_images} images pour le contexte '{context[:50]}...'")

        self.update_state(state='PROGRESS', meta={
            'step': 'Finalizing generation',
            'progress': 95
        })

        logger.info(f"Image generation completed for task {self.request.id}")

        return {
            'task_id': self.request.id,
            'status': 'completed',
            'images_urls': generated_urls,
            'context': context,
            'context_analysis': context_analysis,
            'nb_images': nb_images,
            'generation_method': 'simulated'
        }

    except Exception as e:
        logger.error(f"Error in image generation task {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': 'Image generation failed'}
        )
        raise


@celery_app.task(bind=True, name='image_generation.generate_carousel_images')
def generate_carousel_images_task(
        self,
        context: str,
        slides_text: List[str],
        style: str = "gaming"
) -> Dict[str, Any]:
    """
    Tâche Celery pour générer des images spécifiques à un carrousel
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': 'Starting carousel image generation'})

        logger.info(f"Starting carousel image generation for task {self.request.id}")

        nb_images = len(slides_text)

        # Analyser le style demandé
        style_config = _get_style_configuration(style)

        self.update_state(state='PROGRESS', meta={
            'step': 'Analyzing slides content',
            'progress': 10
        })

        # Générer une image pour chaque slide
        generated_images = []

        for i, slide_text in enumerate(slides_text):
            self.update_state(state='PROGRESS', meta={
                'step': f'Generating image for slide {i + 1}',
                'progress': 20 + (i * 60 / nb_images)
            })

            # Simulation de génération d'image basée sur le texte du slide
            image_info = _generate_slide_image(slide_text, style_config, i + 1)
            generated_images.append(image_info)

            logger.info(f"Generated image {i + 1}/{nb_images} for slide: {slide_text[:30]}...")

        # Message dans les logs
        print(f"Images generated: {nb_images} carousel images pour le style '{style}'")
        logger.info(f"Images generated: {nb_images} carousel images pour le style '{style}'")

        self.update_state(state='PROGRESS', meta={
            'step': 'Finalizing carousel images',
            'progress': 95
        })

        logger.info(f"Carousel image generation completed for task {self.request.id}")

        return {
            'task_id': self.request.id,
            'status': 'completed',
            'images': generated_images,
            'images_urls': [img['url'] for img in generated_images],
            'context': context,
            'slides_text': slides_text,
            'style': style,
            'style_config': style_config,
            'nb_images': nb_images,
            'generation_method': 'carousel_specific'
        }

    except Exception as e:
        logger.error(f"Error in carousel image generation task {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': 'Carousel image generation failed'}
        )
        raise


@celery_app.task(bind=True, name='image_generation.optimize_images')
def optimize_images_task(self, images_urls: List[str], target_platform: str) -> Dict[str, Any]:
    """
    Tâche Celery pour optimiser les images pour une plateforme spécifique
    """
    try:
        self.update_state(state='PROGRESS', meta={'step': 'Starting image optimization'})

        logger.info(f"Starting image optimization for {target_platform} - Task {self.request.id}")

        # Configuration d'optimisation par plateforme
        optimization_config = _get_platform_optimization_config(target_platform)

        optimized_images = []

        for i, image_url in enumerate(images_urls):
            self.update_state(state='PROGRESS', meta={
                'step': f'Optimizing image {i + 1}',
                'progress': 20 + (i * 60 / len(images_urls))
            })

            # Simulation d'optimisation
            optimized_info = _optimize_image_for_platform(image_url, optimization_config)
            optimized_images.append(optimized_info)

        logger.info(f"Image optimization completed for {target_platform} - Task {self.request.id}")

        return {
            'task_id': self.request.id,
            'status': 'completed',
            'original_images': images_urls,
            'optimized_images': optimized_images,
            'optimized_urls': [img['optimized_url'] for img in optimized_images],
            'target_platform': target_platform,
            'optimization_config': optimization_config,
            'total_images': len(images_urls)
        }

    except Exception as e:
        logger.error(f"Error in image optimization task {self.request.id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'step': 'Image optimization failed'}
        )
        raise


# === Fonctions utilitaires ===

def _analyze_image_context(context: str) -> Dict[str, Any]:
    """Analyse le contexte pour déterminer le type d'images à générer"""
    context_lower = context.lower()

    analysis = {
        'theme': 'general',
        'style': 'modern',
        'colors': ['blue', 'white'],
        'keywords': []
    }

    # Détection du thème
    if any(word in context_lower for word in ['gaming', 'jeu', 'game', 'joueur']):
        analysis['theme'] = 'gaming'
        analysis['colors'] = ['purple', 'neon', 'black']
        analysis['keywords'].extend(['gaming', 'esport', 'controller'])

    elif any(word in context_lower for word in ['football', 'sport', 'équipe', 'match']):
        analysis['theme'] = 'sport'
        analysis['colors'] = ['green', 'white', 'red']
        analysis['keywords'].extend(['football', 'terrain', 'ballon'])

    elif any(word in context_lower for word in ['tech', 'ai', 'intelligence', 'robot']):
        analysis['theme'] = 'technology'
        analysis['colors'] = ['blue', 'silver', 'white']
        analysis['keywords'].extend(['tech', 'innovation', 'futuristic'])

    return analysis


def _get_style_configuration(style: str) -> Dict[str, Any]:
    """Retourne la configuration de style pour la génération d'images"""
    styles = {
        'gaming': {
            'colors': ['purple', 'neon', 'black', 'cyan'],
            'mood': 'energetic',
            'elements': ['controller', 'screen', 'keyboard'],
            'font_style': 'bold_futuristic'
        },
        'sport': {
            'colors': ['green', 'white', 'red', 'blue'],
            'mood': 'dynamic',
            'elements': ['ball', 'field', 'trophy'],
            'font_style': 'strong_athletic'
        },
        'business': {
            'colors': ['blue', 'gray', 'white', 'navy'],
            'mood': 'professional',
            'elements': ['chart', 'office', 'laptop'],
            'font_style': 'clean_corporate'
        },
        'lifestyle': {
            'colors': ['pastel', 'pink', 'beige', 'gold'],
            'mood': 'relaxed',
            'elements': ['coffee', 'plant', 'book'],
            'font_style': 'elegant_casual'
        }
    }

    return styles.get(style, styles['business'])


def _generate_slide_image(slide_text: str, style_config: Dict[str, Any], slide_number: int) -> Dict[str, Any]:
    """Simule la génération d'une image pour un slide spécifique"""
    image_id = str(uuid.uuid4())[:8]

    return {
        'slide_number': slide_number,
        'slide_text': slide_text,
        'url': f"https://generated-images.s3.amazonaws.com/slide_{slide_number}_{image_id}.jpg",
        'style_applied': style_config,
        'dimensions': '1080x1080',  # Format carré pour Instagram
        'file_size': f"{220 + slide_number * 10}KB",  # Simulation
        'generated_at': time.time()
    }


def _get_platform_optimization_config(platform: str) -> Dict[str, Any]:
    """Retourne la configuration d'optimisation pour une plateforme"""
    configs = {
        'instagram': {
            'dimensions': {
                'post': '1080x1080',
                'story': '1080x1920',
                'carousel': '1080x1080'
            },
            'max_file_size': '30MB',
            'formats': ['JPG', 'PNG'],
            'quality': 85
        },
        'twitter': {
            'dimensions': {
                'post': '1200x675',
                'header': '1500x500'
            },
            'max_file_size': '5MB',
            'formats': ['JPG', 'PNG', 'GIF'],
            'quality': 80
        },
        'facebook': {
            'dimensions': {
                'post': '1200x630',
                'cover': '820x312'
            },
            'max_file_size': '4MB',
            'formats': ['JPG', 'PNG'],
            'quality': 85
        }
    }

    return configs.get(platform, configs['instagram'])


def _optimize_image_for_platform(image_url: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Simule l'optimisation d'une image pour une plateforme"""
    image_id = str(uuid.uuid4())[:8]

    return {
        'original_url': image_url,
        'optimized_url': f"https://optimized-images.s3.amazonaws.com/opt_{image_id}.jpg",
        'optimization_applied': config,
        'size_reduction': '45%',  # Simulation
        'new_dimensions': config.get('dimensions', {}).get('post', '1080x1080'),
        'new_file_size': f"{180}KB",  # Simulation
        'quality_score': config.get('quality', 85)
    }