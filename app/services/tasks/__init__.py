# app/services/tasks/__init__.py

# Import all task modules to ensure they are registered
from . import content_generation
from . import content_formatting
from . import content_publishing
from . import image_generation

__all__ = [
    'content_generation',
    'content_formatting',
    'content_publishing',
    'image_generation'
]