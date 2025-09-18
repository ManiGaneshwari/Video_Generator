import os
import logging
from typing import Dict, Any, Optional, Tuple
from moviepy.editor import AudioFileClip, CompositeVideoClip

from .text_processor import TextProcessor
from .audio_generator import AudioGenerator
from .video_generator import VideoGenerator
from .subtitle_generator import SubtitleGenerator
from .utils import get_supported_image_files, sanitize_filename

logger = logging.getLogger(__name__)


class Renderer:
    """Orchestrates the entire video creation workflow."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.text_processor = TextProcessor(config)
        self.audio_generator = AudioGenerator(config)
        self.video_generator = VideoGenerator(config)
        self.subtitle_generator = SubtitleGenerator(config)
        self.paths = config.get('paths', {})
    
    def create_slideshow(self, output_filename: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Create complete slideshow video with all components.
        
        Args:
            output_filename: Optional custom output filename
            
        Returns:
            Tuple of (success: bool, output_path: Optional[str])
        """
        logger.info("Starting slideshow creation process...")
        
        try:
            # Step 1: Load and validate images
            images = self._load_images()
            if not images:
                logger.error("No images found for slideshow creation")
                return False, None
            
            logger.info(f"Found {len(images)} images for slideshow")
            
            # Step 2: Process text content
            text_settings = self.text_processor.process_text_content(len(images))
            if text_settings:
                logger.info(f"Text processing completed in mode: {text_settings.get('mode')}")
            else:
                logger.info("No text overlays will be added")
            
            # Step 3: Generate or load audio
            text_for_tts = self._extract_text_for_tts(text_settings) if text_settings else None
            audio = self.audio_generator.process_audio(text_for_tts)
            if not audio:
                logger.error("No audio available for slideshow")
                return False, None
            
            logger.info(f"Audio loaded successfully (duration: {audio.duration:.2f}s)")
            
            # Step 4: Create video
            video = self.video_generator.create_slideshow_video(images, audio, text_settings)
            if not video:
                logger.error("Failed to create slideshow video")
                return False, None
            
            # Step 5: Save video
            output_path = self._generate_output_path(output_filename)
            success = self._save_video(video, output_path)
            
            if not success:
                logger.error("Failed to save video")
                return False, None
            
            # Step 6: Generate subtitles (optional)
            if text_settings and self.config.get('subtitles', {}).get('generate', False):
                self._generate_subtitles(text_settings, audio.duration, len(images))
            
            # Step 7: Save text settings for future use
            if text_settings:
                self.text_processor.save_text_settings(text_settings, 
                                                     f"{os.path.splitext(os.path.basename(output_path))[0]}_settings")
            
            logger.info(f"Slideshow creation completed successfully: {output_path}")
            return True, output_path
            
        except Exception as e:
            logger.error(f"Error during slideshow creation: {e}")
            return False, None
    
    def _load_images(self) -> list:
        """Load and validate image files."""
        images_dir = self.paths.get('images_dir', 'data/images')
        
        if not os.path.exists(images_dir):
            logger.error(f"Images directory not found: {images_dir}")
            return []
        
        supported_formats = self.config.get('image', {}).get('supported_formats', 
                                           [".jpg", ".jpeg", ".png", ".bmp", ".tiff"])
        images = get_supported_image_files(images_dir, supported_formats)
        
        if not images:
            logger.error(f"No supported image files found in {images_dir}")
            logger.info(f"Supported formats: {', '.join(supported_formats)}")
        
        return images
    
    def _extract_text_for_tts(self, text_settings: Dict[str, Any]) -> str:
        """Extract text content for TTS generation."""
        mode = text_settings.get('mode', 'single')
        
        if mode == 'single':
            return text_settings.get('text', '')
        elif mode in ['per_image', 'from_file']:
            texts = text_settings.get('texts', [])
            # Combine all text entries for TTS
            return ' '.join([text for text in texts if text and text.strip()])
        
        return ''
    
    def _generate_output_path(self, output_filename: Optional[str] = None) -> str:
        """Generate output file path."""
        output_dir = self.paths.get('output_dir', 'data/output')
        os.makedirs(output_dir, exist_ok=True)
        
        if output_filename:
            # Use provided filename
            filename = sanitize_filename(output_filename)
            if not filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                filename += '.mp4'
        else:
            # Generate default filename
            resolution = self.config.get('video', {}).get('resolution', '720p')
            scaling = self.config.get('video', {}).get('scaling_method', 'fit')
            filename = f"slideshow_{resolution}_{scaling}.mp4"
        
        return os.path.join(output_dir, filename)
    
    def _save_video(self, video: CompositeVideoClip, output_path: str) -> bool:
        """Save video to file."""
        try:
            video_config = self.config.get('video', {})
            
            logger.info(f"Saving video to: {output_path}")
            logger.info("This may take several minutes depending on video length and quality...")
            
            video.write_videofile(
                output_path,
                fps=video_config.get('fps', 24),
                codec=video_config.get('codec', 'libx264'),
                audio_codec=video_config.get('audio_codec', 'aac'),
                temp_audiofile="temp-audio.m4a",
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            logger.info(f"Video saved successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving video: {e}")
            return False
    
    def _generate_subtitles(self, text_settings: Dict[str, Any], 
                           audio_duration: float, num_images: int) -> None:
        """Generate subtitle files."""
        try:
            # Generate SRT subtitles
            srt_path = self.subtitle_generator.generate_subtitles(
                text_settings, audio_duration, num_images
            )
            
            # Generate VTT subtitles
            vtt_path = self.subtitle_generator.generate_vtt_subtitles(
                text_settings, audio_duration, num_images
            )
            
            if srt_path or vtt_path:
                logger.info("Subtitle files generated successfully")
            
        except Exception as e:
            logger.error(f"Error generating subtitles: {e}")
    
    def get_project_info(self) -> Dict[str, Any]:
        """Get information about the current project setup."""
        images_dir = self.paths.get('images_dir', 'data/images')
        images = self._load_images()
        
        # Try to find audio
        audio_path = None
        if not self.config.get('audio', {}).get('generate_from_text', False):
            data_dir = os.path.dirname(self.paths.get('input_text', 'data/input.txt'))
            from .utils import find_audio_file
            audio_path = find_audio_file(data_dir)
        
        # Check for text content
        input_text_path = self.paths.get('input_text', 'data/input.txt')
        text_file_exists = os.path.exists(input_text_path)
        
        return {
            'images': {
                'count': len(images),
                'directory': images_dir,
                'files': [os.path.basename(img) for img in images[:5]]  # First 5 files
            },
            'audio': {
                'path': audio_path,
                'tts_enabled': self.config.get('audio', {}).get('generate_from_text', False)
            },
            'text': {
                'file_exists': text_file_exists,
                'file_path': input_text_path,
                'enabled': self.config.get('text', {}).get('enabled', True),
                'mode': self.config.get('text', {}).get('mode', 'auto')
            },
            'video': {
                'resolution': self.config.get('video', {}).get('resolution', '720p'),
                'scaling': self.config.get('video', {}).get('scaling_method', 'fit')
            }
        }
    
    def validate_project_setup(self) -> Tuple[bool, list]:
        """Validate that all required components are available."""
        errors = []
        images = self._load_images()
        
        # Check images
        if not images:
            errors.append("No images found in images directory")
        
        # Check audio (if not using TTS)
        if not self.config.get('audio', {}).get('generate_from_text', False):
            data_dir = os.path.dirname(self.paths.get('input_text', 'data/input.txt'))
            from .utils import find_audio_file
            audio_path = find_audio_file(data_dir)
            if not audio_path:
                errors.append("No audio file found and TTS is not enabled")
        
        # Check text content (if text overlays are enabled)
        if self.config.get('text', {}).get('enabled', True):
            text_mode = self.config.get('text', {}).get('mode', 'auto')
            input_text_path = self.paths.get('input_text', 'data/input.txt')
            default_text = self.config.get('text', {}).get('default_text', '').strip()
            
            if text_mode == 'from_file' and not os.path.exists(input_text_path):
                errors.append(f"Text file not found: {input_text_path}")
            elif text_mode == 'single' and not default_text:
                errors.append("Single text mode selected but no default_text provided")
        
        return len(errors) == 0, errors