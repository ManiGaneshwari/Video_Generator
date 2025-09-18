"""
Automated Slideshow Generator Package

This package provides a complete solution for generating slideshow videos
with animated text overlays, audio synchronization, and subtitle generation.
"""

from .renderer import Renderer
from .text_processor import TextProcessor
from .audio_generator import AudioGenerator
from .video_generator import VideoGenerator
from .subtitle_generator import SubtitleGenerator
from .utils import load_config, setup_logging, ensure_directories

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

__all__ = [
    'Renderer',
    'TextProcessor',
    'AudioGenerator',
    'VideoGenerator',
    'SubtitleGenerator',
    'load_config',
    'setup_logging',
    'ensure_directories'
]