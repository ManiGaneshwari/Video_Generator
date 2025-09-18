import logging
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional


def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """Setup logging configuration."""
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO').upper())
    
    # Create logs directory if it doesn't exist
    log_file = log_config.get('file', 'logs/app.log')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
        ]
    )
    
    # Add console handler if enabled
    if log_config.get('console', True):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logging.getLogger().addHandler(console_handler)
    
    return logging.getLogger(__name__)


def load_config(config_path: str = "config/settings.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML config: {e}")


def ensure_directories(config: Dict[str, Any]) -> None:
    """Ensure all required directories exist."""
    paths = config.get('paths', {})
    
    # Create directories
    dirs_to_create = [
        os.path.dirname(paths.get('input_text', 'data/input.txt')),
        paths.get('images_dir', 'data/images'),
        paths.get('output_dir', 'data/output'),
        'logs'
    ]
    
    for directory in dirs_to_create:
        if directory:
            os.makedirs(directory, exist_ok=True)


def get_supported_image_files(directory: str, supported_formats: List[str] = None) -> List[str]:
    """Get list of supported image files from directory."""
    if supported_formats is None:
        supported_formats = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]
    
    if not os.path.exists(directory):
        return []
    
    image_files = []
    for file in os.listdir(directory):
        if any(file.lower().endswith(fmt) for fmt in supported_formats):
            image_files.append(os.path.join(directory, file))
    
    # Sort files naturally
    image_files.sort()
    return image_files


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration settings."""
    # Check video resolution
    valid_resolutions = ["1080p", "720p"]
    if config.get('video', {}).get('resolution') not in valid_resolutions:
        raise ValueError(f"Invalid resolution. Must be one of: {valid_resolutions}")
    
    # Check scaling method
    valid_scaling = ["fit", "crop"]
    if config.get('video', {}).get('scaling_method') not in valid_scaling:
        raise ValueError(f"Invalid scaling method. Must be one of: {valid_scaling}")
    
    # Check text mode
    valid_text_modes = ["auto", "single", "per_image", "from_file"]
    if config.get('text', {}).get('mode') not in valid_text_modes:
        raise ValueError(f"Invalid text mode. Must be one of: {valid_text_modes}")
    
    # Check animation type
    valid_animations = [
        "fade_in", "fade_in_out", "slide_from_left", "slide_from_right",
        "slide_from_top", "slide_from_bottom", "zoom_in", "zoom_out",
        "bounce_in", "pulse", "rotate_in", "none"
    ]
    animation_type = config.get('text', {}).get('animation', {}).get('type')
    if animation_type not in valid_animations:
        raise ValueError(f"Invalid animation type. Must be one of: {valid_animations}")
    
    return True


def get_video_size(resolution: str) -> tuple:
    """Get video dimensions for given resolution."""
    sizes = {
        "1080p": (1920, 1080),
        "720p": (1280, 720)
    }
    return sizes.get(resolution, (1280, 720))


def find_audio_file(directory: str = "data") -> Optional[str]:
    """Find audio file in the given directory."""
    audio_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg']
    
    for file in os.listdir(directory):
        if any(file.lower().endswith(ext) for ext in audio_extensions):
            return os.path.join(directory, file)
    
    return None


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to be filesystem-safe."""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200-len(ext)] + ext
    
    return filename


def calculate_crossfade_duration(base_duration: float, config: Dict[str, Any]) -> float:
    """Calculate appropriate crossfade duration."""
    crossfade_setting = config.get('image', {}).get('crossfade_duration', 'auto')
    
    if crossfade_setting == 'auto':
        # Use 1/3 of base duration but cap at reasonable limits
        return min(base_duration / 3.0, max(0.1, base_duration / 4.0))
    else:
        try:
            return float(crossfade_setting)
        except (ValueError, TypeError):
            # Fallback to auto calculation
            return min(base_duration / 3.0, max(0.1, base_duration / 4.0))