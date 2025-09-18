import os
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip

logger = logging.getLogger(__name__)


class VideoGenerator:
    """Handles video generation with text overlays and animations."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.video_config = config.get('video', {})
        self.text_config = config.get('text', {})
        self.paths = config.get('paths', {})
    
    def create_slideshow_video(self, images: List[str], audio: AudioFileClip, 
                              text_settings: Optional[Dict[str, Any]] = None) -> Optional[CompositeVideoClip]:
        """
        Create slideshow video with images, audio, and optional text overlays.
        
        Args:
            images: List of image file paths
            audio: Audio clip for the video
            text_settings: Optional text overlay settings
            
        Returns:
            CompositeVideoClip object or None if creation fails
        """
        if not images:
            logger.error("No images provided for video creation")
            return None
        
        if audio is None:
            logger.error("No audio provided for video creation")
            return None
        
        # Get video dimensions
        resolution = self.video_config.get('resolution', '720p')
        video_size = self._get_video_size(resolution)
        scaling_method = self.video_config.get('scaling_method', 'fit')
        
        logger.info(f"Creating {resolution} video with {len(images)} images")
        logger.info(f"Video size: {video_size}, scaling method: {scaling_method}")
        
        # Import and use audio synchronization
        try:
            from .audio_sync import AudioSyncManager
            sync_manager = AudioSyncManager(self.config)
            slide_timings = sync_manager.calculate_slide_timings(audio, len(images))
            slide_durations = sync_manager.get_slide_durations(slide_timings, audio.duration)
            
            logger.info("Audio-sync enabled:")
            for i, (start_time, duration) in enumerate(zip(slide_timings, slide_durations)):
                logger.info(f"  Slide {i+1}: {start_time:.2f}s - {start_time + duration:.2f}s (duration: {duration:.2f}s)")
                
        except Exception as e:
            logger.error(f"Error in audio synchronization: {e}")
            # Fallback to even distribution
            audio_duration = audio.duration
            base_duration = audio_duration / len(images)
            slide_timings = [i * base_duration for i in range(len(images))]
            slide_durations = [base_duration] * len(images)
            logger.info(f"Fallback: Even distribution with {base_duration:.2f}s per slide")
        
        # Calculate crossfade based on minimum slide duration
        min_slide_duration = min(slide_durations)
        crossfade_duration = min(
            self._calculate_crossfade_duration(min_slide_duration),
            min_slide_duration / 3  # Never more than 1/3 of shortest slide
        )
        
        try:
            # Build slideshow clips with synchronized timing
            clips = self._build_slideshow_clips_with_sync(
                images, video_size, slide_durations, crossfade_duration,
                scaling_method, text_settings
            )
            
            if not clips:
                logger.error("No valid clips created")
                return None
            
            # Concatenate clips
            logger.info("Concatenating synchronized video clips...")
            final_video = concatenate_videoclips(clips, method="compose")
            final_video = final_video.set_duration(audio.duration)
            final_video = final_video.set_audio(audio)
            
            logger.info(f"Synchronized video creation completed: {final_video.duration:.2f}s")
            return final_video
            
        except Exception as e:
            logger.error(f"Error creating slideshow video: {e}")
            return None
    
    def _build_slideshow_clips_with_sync(self, images: List[str], video_size: Tuple[int, int], 
                                        slide_durations: List[float], crossfade_duration: float,
                                        scaling_method: str, text_settings: Optional[Dict[str, Any]]) -> List[ImageClip]:
        """Build individual slideshow clips with synchronized timing."""
        clips = []
        
        for i, (img_path, duration) in enumerate(zip(images, slide_durations)):
            logger.info(f"Processing slide {i+1}/{len(images)}: {os.path.basename(img_path)} (duration: {duration:.2f}s)")
            
            try:
                # Load and scale image
                processed_image = self._process_image(img_path, video_size, scaling_method)
                if processed_image is None:
                    continue
                
                # Create image clip with specific duration
                img_array = np.array(processed_image)
                clip = ImageClip(img_array).set_duration(duration)
                
                # Add text overlay if settings provided
                if text_settings:
                    text_clip = self._create_text_overlay(
                        text_settings, i, video_size, duration
                    )
                    if text_clip:
                        clip = CompositeVideoClip([clip, text_clip])
                
                # Apply crossfade transitions (but respect slide timing)
                if i > 0 and crossfade_duration > 0:
                    # Only apply crossfade if slides are long enough
                    if duration > crossfade_duration * 2 and slide_durations[i-1] > crossfade_duration * 2:
                        clips[-1] = clips[-1].crossfadeout(crossfade_duration)
                        clip = clip.crossfadein(crossfade_duration)
                
                clips.append(clip)
                
            except Exception as e:
                logger.error(f"Error processing image {img_path}: {e}")
                continue
        
        return clips
    
    def _build_slideshow_clips(self, images: List[str], video_size: Tuple[int, int], 
                              base_duration: float, crossfade_duration: float,
                              scaling_method: str, text_settings: Optional[Dict[str, Any]]) -> List[ImageClip]:
        """Build individual slideshow clips with scaling and text overlays."""
        clips = []
        
        for i, img_path in enumerate(images):
            logger.info(f"Processing image {i+1}/{len(images)}: {os.path.basename(img_path)}")
            
            try:
                # Load and scale image
                processed_image = self._process_image(img_path, video_size, scaling_method)
                if processed_image is None:
                    continue
                
                # Create image clip
                img_array = np.array(processed_image)
                clip = ImageClip(img_array).set_duration(base_duration)
                
                # Add text overlay if settings provided
                if text_settings:
                    text_clip = self._create_text_overlay(
                        text_settings, i, video_size, base_duration
                    )
                    if text_clip:
                        clip = CompositeVideoClip([clip, text_clip])
                
                # Apply crossfade transitions
                if i > 0 and crossfade_duration > 0:
                    clips[-1] = clips[-1].crossfadeout(crossfade_duration)
                    clip = clip.crossfadein(crossfade_duration)
                
                clips.append(clip)
                
            except Exception as e:
                logger.error(f"Error processing image {img_path}: {e}")
                continue
        
        return clips
    
    def _process_image(self, img_path: str, video_size: Tuple[int, int], 
                      scaling_method: str) -> Optional[Image.Image]:
        """Process and scale image to fit video dimensions."""
        try:
            img = Image.open(img_path)
            original_size = img.size
            target_size = video_size
            
            if scaling_method == 'crop':
                # Scale and crop to fill frame
                img_aspect = original_size[0] / original_size[1]
                target_aspect = target_size[0] / target_size[1]
                
                if img_aspect > target_aspect:
                    # Image is wider, fit height and crop width
                    new_height = target_size[1]
                    new_width = int(new_height * img_aspect)
                else:
                    # Image is taller, fit width and crop height
                    new_width = target_size[0]
                    new_height = int(new_width / img_aspect)
                
                img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Crop center
                left = (new_width - target_size[0]) // 2
                top = (new_height - target_size[1]) // 2
                img_final = img_resized.crop((left, top, left + target_size[0], top + target_size[1]))
                
            else:  # fit method
                # Scale to fit within frame with letterboxing
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
                img_final = Image.new('RGB', target_size, (0, 0, 0))
                paste_x = (target_size[0] - img.size[0]) // 2
                paste_y = (target_size[1] - img.size[1]) // 2
                img_final.paste(img, (paste_x, paste_y))
            
            return img_final
            
        except Exception as e:
            logger.error(f"Error processing image {img_path}: {e}")
            return None
    
    def _create_text_overlay(self, text_settings: Dict[str, Any], image_index: int, 
                           video_size: Tuple[int, int], duration: float) -> Optional[CompositeVideoClip]:
        """Create text overlay clip for image."""
        try:
            # Get text content for this image
            text_content = self._get_text_for_image(text_settings, image_index)
            if not text_content or not text_content.strip():
                return None
            
            logger.info(f"Creating text overlay: '{text_content[:50]}...'")
            
            # Check if sequential animation is enabled
            sequential_enabled = text_settings.get('sequential', {}).get('enabled', False)
            
            if sequential_enabled and '\n' in text_content:
                # Use sequential text animation
                logger.info("Using sequential text animation (line-by-line)")
                from .sequential_text import SequentialTextAnimator
                
                animator = SequentialTextAnimator(self.config)
                text_clip = animator.create_sequential_text_clip(
                    text_content, video_size, duration, text_settings
                )
                
                if text_clip:
                    logger.info("Sequential text animation created successfully")
                    return text_clip
                else:
                    logger.warning("Sequential animation failed, falling back to standard text")
            
            # Fallback to standard text overlay (all text at once)
            logger.info("Using standard text overlay (all text at once)")
            
            # Create text image using PIL - this creates a tight-fitting image
            text_img = self._create_pil_text_image(
                text_content, video_size,
                text_settings.get('font_size', 60),
                text_settings.get('color', 'white'),
                text_settings.get('stroke_color', 'black'),
                text_settings.get('stroke_width', 3)
            )
            
            if text_img is None:
                logger.error("Failed to create PIL text image")
                return None
            
            # Create MoviePy text clip from the PIL image
            text_array = np.array(text_img)
            text_clip = ImageClip(text_array, ismask=False, transparent=True).set_duration(duration)
            
            logger.info(f"Text clip size: {text_clip.size}, Video size: {video_size}")
            
            # Handle position - get the requested position
            position_setting = text_settings.get('position', 'center')
            logger.info(f"Requested position: {position_setting}")
            
            # Calculate exact coordinates
            position_coords = self._calculate_text_position(position_setting, text_clip.size, video_size)
            
            # Set the position - this is the key fix
            text_clip = text_clip.set_position(position_coords)
            
            # Apply animation if specified
            animation_type = text_settings.get('animation', 'fade_in')
            animation_duration = text_settings.get('animation_duration', 1.0)
            
            if animation_type != 'none':
                logger.info(f"Applying animation: {animation_type} (duration: {animation_duration}s)")
                text_clip = self._apply_text_animation(
                    text_clip, animation_type, animation_duration, video_size, position_coords
                )
            else:
                logger.info("No animation applied")
            
            logger.info(f"Text overlay created successfully at position {position_coords}")
            return text_clip
            
        except Exception as e:
            logger.error(f"Error creating text overlay: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _calculate_text_position(self, position, text_size: Tuple[int, int], video_size: Tuple[int, int]) -> Tuple[int, int]:
        """Calculate exact pixel coordinates for text position."""
        text_width, text_height = text_size
        video_width, video_height = video_size
        
        logger.info(f"Calculating position '{position}' for text size {text_size} on video size {video_size}")
        
        if isinstance(position, (tuple, list)) and len(position) == 2:
            # Direct coordinates provided
            x, y = position
            x = max(0, min(x, video_width - text_width))
            y = max(0, min(y, video_height - text_height))
            logger.info(f"Using direct coordinates: ({x}, {y})")
            return (x, y)
        
        # Handle string positions with generous margins
        margin = 30
        
        if position == 'center':
            x = (video_width - text_width) // 2
            y = (video_height - text_height) // 2
        elif position == 'top':
            x = (video_width - text_width) // 2
            y = margin
        elif position == 'bottom':
            x = (video_width - text_width) // 2
            y = video_height - text_height - margin
        elif position == 'left':
            x = margin
            y = (video_height - text_height) // 2
        elif position == 'right':
            x = video_width - text_width - margin
            y = (video_height - text_height) // 2
        elif position == 'top-left':
            x = margin
            y = margin
        elif position == 'top-right':
            x = video_width - text_width - margin
            y = margin
        elif position == 'bottom-left':
            x = margin
            y = video_height - text_height - margin
        elif position == 'bottom-right':
            x = video_width - text_width - margin
            y = video_height - text_height - margin
        else:
            # Default to center for unknown positions
            logger.warning(f"Unknown position '{position}', using center")
            x = (video_width - text_width) // 2
            y = (video_height - text_height) // 2
        
        # Ensure coordinates are within bounds
        x = max(0, min(x, video_width - text_width))
        y = max(0, min(y, video_height - text_height))
        
        logger.info(f"Calculated position '{position}' -> ({x}, {y})")
        return (x, y)
    
    def _get_text_for_image(self, text_settings: Dict[str, Any], image_index: int) -> str:
        """Get text content for specific image index."""
        mode = text_settings.get('mode', 'single')
        
        if mode == 'single':
            return text_settings.get('text', '')
        elif mode == 'per_image':
            texts = text_settings.get('texts', [])
            if image_index < len(texts):
                return texts[image_index]
        
        return ""
    
    def _create_pil_text_image(self, text: str, size: Tuple[int, int], font_size: int = 50,
                              color: str = 'white', stroke_color: str = 'black', 
                              stroke_width: int = 2) -> Optional[Image.Image]:
        """Create text image using PIL with improved rendering."""
        try:
            img_width, img_height = size
            # Create a smaller canvas that fits just the text, not the full video size
            # This will allow proper positioning later
            
            # First, measure the text to determine required canvas size
            temp_img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            
            # Load font
            font = self._load_font(font_size)
            if font is None:
                logger.warning("Could not load system font, using default")
                try:
                    font = ImageFont.load_default()
                    font_size = min(font_size, 40)
                except Exception:
                    logger.error("Could not load any font")
                    return None
            
            # Handle multi-line text
            lines = text.split('\n') if '\n' in text else [text]
            
            # Adjust font size if auto-scaling is enabled
            scaling_config = self.text_config.get('scaling', {})
            auto_scale = scaling_config.get('auto_scale', True)
            
            if auto_scale:
                font_size, font = self._adjust_font_size(lines, temp_draw, font, font_size, size)
                logger.info(f"Using font size: {font_size} for text: '{text[:50]}...'")
            else:
                logger.info(f"Auto-scaling disabled, using exact font size: {font_size}")
                font = self._load_font(font_size) or font
            
            # Calculate actual text dimensions
            line_heights = []
            line_widths = []
            max_width = 0
            
            for line in lines:
                try:
                    if hasattr(temp_draw, 'textbbox'):
                        bbox = temp_draw.textbbox((0, 0), line, font=font)
                        width = bbox[2] - bbox[0]
                        height = bbox[3] - bbox[1]
                    else:
                        width, height = temp_draw.textsize(line, font=font)
                except Exception as e:
                    logger.warning(f"Could not measure text, using estimates: {e}")
                    width = len(line) * (font_size * 0.6)
                    height = font_size * 1.2
                
                line_widths.append(width)
                line_heights.append(height)
                max_width = max(max_width, width)
            
            total_height = sum(line_heights) + (len(lines) - 1) * 15
            
            # Add padding around text
            padding = max(stroke_width * 2, 10)
            canvas_width = int(max_width + padding * 2)
            canvas_height = int(total_height + padding * 2)
            
            # Create the actual text image with tight bounds
            img = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Position text in the center of this smaller canvas
            start_x = padding
            start_y = padding
            current_y = start_y
            
            # Draw text with stroke
            for i, line in enumerate(lines):
                if not line.strip():
                    current_y += line_heights[i] if i < len(line_heights) else font_size + 15
                    continue
                
                # Center each line horizontally within the text block
                line_x = start_x + (max_width - line_widths[i]) // 2
                
                # Draw stroke/outline
                if stroke_width > 0 and stroke_color != color:
                    for adj_x in range(-stroke_width, stroke_width + 1):
                        for adj_y in range(-stroke_width, stroke_width + 1):
                            if adj_x != 0 or adj_y != 0:
                                try:
                                    draw.text((line_x + adj_x, current_y + adj_y), 
                                            line, font=font, fill=stroke_color)
                                except Exception as e:
                                    logger.warning(f"Error drawing text stroke: {e}")
                
                # Draw main text
                try:
                    draw.text((line_x, current_y), line, font=font, fill=color)
                except Exception as e:
                    logger.error(f"Error drawing main text: {e}")
                
                current_y += line_heights[i] + 15
            
            logger.info(f"Created text image: {canvas_width}x{canvas_height} for text: '{text[:30]}...'")
            return img
            
        except Exception as e:
            logger.error(f"Error creating PIL text image: {e}")
            return None
    
    def _load_font(self, font_size: int) -> Optional[ImageFont.FreeTypeFont]:
        """Load font from system font paths."""
        font_paths = self.text_config.get('fonts', [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
        ])
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, font_size)
                except Exception:
                    continue
        
        return None
    
    def _adjust_font_size(self, lines: List[str], draw: ImageDraw.Draw, font: ImageFont.ImageFont,
                         font_size: int, size: Tuple[int, int]) -> Tuple[int, ImageFont.ImageFont]:
        """Adjust font size to fit within image bounds."""
        # Get scaling configuration
        scaling_config = self.text_config.get('scaling', {})
        auto_scale = scaling_config.get('auto_scale', True)
        min_font_size = scaling_config.get('min_font_size', 20)
        max_font_size = scaling_config.get('max_font_size', 200)
        scale_factor = scaling_config.get('scale_factor', 0.8)
        
        # Clamp initial font size to configured range
        current_font_size = max(min_font_size, min(font_size, max_font_size))
        
        # If auto scaling is disabled, use exact font size requested
        if not auto_scale:
            logger.info(f"Auto-scaling disabled, using exact font size: {font_size}")
            final_font = self._load_font(font_size)
            return font_size, final_font or ImageFont.load_default()
        
        # Rest of auto-scaling logic only runs if auto_scale is True
        max_attempts = 8
        padding = 80
        
        for attempt in range(max_attempts):
            try:
                test_font = self._load_font(current_font_size)
                if test_font is None:
                    test_font = ImageFont.load_default()
                    current_font_size = min(current_font_size, 30)
                
                max_width = 0
                total_height = 0
                
                for line in lines:
                    if not line.strip():
                        total_height += current_font_size * 0.8
                        continue
                        
                    try:
                        if hasattr(draw, 'textbbox'):
                            bbox = draw.textbbox((0, 0), line, font=test_font)
                            width = bbox[2] - bbox[0]
                            height = bbox[3] - bbox[1]
                        else:
                            width, height = draw.textsize(line, font=test_font)
                    except Exception:
                        width = len(line) * (current_font_size * 0.6)
                        height = current_font_size * 1.2
                    
                    max_width = max(max_width, width)
                    total_height += height + 15
                
                total_height = max(0, total_height - 15)
                
                fits_width = max_width <= (size[0] - padding)
                fits_height = total_height <= (size[1] - padding)
                
                if fits_width and fits_height:
                    logger.info(f"Auto-scaled font size {current_font_size} fits well")
                    return current_font_size, test_font
                
                if not fits_width or not fits_height:
                    width_ratio = (size[0] - padding) / max_width if max_width > 0 else 1.0
                    height_ratio = (size[1] - padding) / total_height if total_height > 0 else 1.0
                    needed_scale = min(width_ratio, height_ratio)
                    
                    if needed_scale < scale_factor:
                        current_font_size = max(int(current_font_size * needed_scale), min_font_size)
                    else:
                        current_font_size = max(int(current_font_size * scale_factor), min_font_size)
                
                if current_font_size <= min_font_size:
                    current_font_size = min_font_size
                    break
                    
            except Exception as e:
                logger.warning(f"Error in font size adjustment attempt {attempt}: {e}")
                current_font_size = max(int(current_font_size * 0.8), min_font_size)
                if current_font_size <= min_font_size:
                    break
        
        final_font = self._load_font(current_font_size)
        if final_font is None:
            final_font = ImageFont.load_default()
            current_font_size = min_font_size
        
        logger.info(f"Final auto-scaled font size: {current_font_size}")
        return current_font_size, final_font
    
    def _apply_text_animation(self, text_clip: ImageClip, animation_type: str, 
                             animation_duration: float, video_size: Tuple[int, int], 
                             final_position: Tuple[int, int]) -> ImageClip:
        """Apply animation effects to text clip."""
        try:
            logger.info(f"Applying animation: {animation_type}")
            
            if animation_type == 'fade_in':
                return text_clip.crossfadein(animation_duration)
            
            elif animation_type == 'fade_in_out':
                fade_time = min(animation_duration, text_clip.duration / 3)
                return text_clip.crossfadein(fade_time).crossfadeout(fade_time)
            
            elif animation_type == 'zoom_in':
                def zoom_resize(t):
                    if t < animation_duration:
                        progress = min(t / animation_duration, 1.0)
                        # Ease-out cubic
                        progress = 1 - (1 - progress) ** 3
                        return 0.1 + 0.9 * progress
                    return 1.0
                return text_clip.resize(zoom_resize)
            
            elif animation_type == 'zoom_out':
                def zoom_out_resize(t):
                    if t < animation_duration:
                        progress = min(t / animation_duration, 1.0)
                        progress = 1 - (1 - progress) ** 3
                        return 2.5 - 1.5 * progress  # Start at 2.5x, end at 1.0x
                    return 1.0
                return text_clip.resize(zoom_out_resize)
            
            elif animation_type == 'slide_from_left':
                def slide_left_pos(t):
                    if t < animation_duration:
                        progress = min(t / animation_duration, 1.0)
                        progress = 1 - (1 - progress) ** 3  # Ease-out cubic
                        
                        start_x = -text_clip.w  # Start completely off-screen left
                        target_x = final_position[0]
                        current_x = start_x + (target_x - start_x) * progress
                        
                        return (current_x, final_position[1])
                    return final_position
                
                return text_clip.set_position(slide_left_pos)
            
            elif animation_type == 'slide_from_right':
                def slide_right_pos(t):
                    if t < animation_duration:
                        progress = min(t / animation_duration, 1.0)
                        progress = 1 - (1 - progress) ** 3
                        
                        start_x = video_size[0]  # Start completely off-screen right
                        target_x = final_position[0]
                        current_x = start_x + (target_x - start_x) * progress
                        
                        return (current_x, final_position[1])
                    return final_position
                
                return text_clip.set_position(slide_right_pos)
            
            elif animation_type == 'slide_from_top':
                def slide_top_pos(t):
                    if t < animation_duration:
                        progress = min(t / animation_duration, 1.0)
                        progress = 1 - (1 - progress) ** 3
                        
                        start_y = -text_clip.h  # Start completely off-screen above
                        target_y = final_position[1]
                        current_y = start_y + (target_y - start_y) * progress
                        
                        return (final_position[0], current_y)
                    return final_position
                
                return text_clip.set_position(slide_top_pos)
            
            elif animation_type == 'slide_from_bottom':
                def slide_bottom_pos(t):
                    if t < animation_duration:
                        progress = min(t / animation_duration, 1.0)
                        progress = 1 - (1 - progress) ** 3
                        
                        start_y = video_size[1]  # Start completely off-screen below
                        target_y = final_position[1]
                        current_y = start_y + (target_y - start_y) * progress
                        
                        return (final_position[0], current_y)
                    return final_position
                
                return text_clip.set_position(slide_bottom_pos)
            
            elif animation_type == 'bounce_in':
                def bounce_scale(t):
                    if t < animation_duration:
                        progress = min(t / animation_duration, 1.0)
                        # Bounce effect using sine wave
                        bounce = 1.0 + 0.3 * np.sin(progress * np.pi * 4) * (1 - progress)
                        # Combine with scale up
                        base_scale = 0.3 + 0.7 * progress
                        return base_scale * bounce
                    return 1.0
                
                return text_clip.resize(bounce_scale)
            
            elif animation_type == 'pulse':
                def pulse_scale(t):
                    pulse_speed = 1.0  # Pulses per second
                    scale_variation = 0.1  # 10% size variation
                    pulse = 1.0 + scale_variation * np.sin(t * pulse_speed * 2 * np.pi)
                    return pulse
                
                return text_clip.resize(pulse_scale)
            
            elif animation_type == 'rotate_in':
                def rotate_angle(t):
                    if t < animation_duration:
                        progress = min(t / animation_duration, 1.0)
                        progress = 1 - (1 - progress) ** 3
                        return 180 * (1 - progress)  # Rotate from 180 to 0 degrees
                    return 0
                
                return text_clip.rotate(rotate_angle, expand=False)
            
            elif animation_type == 'none':
                return text_clip
            
            else:
                # Unknown animation, fallback to fade_in
                logger.warning(f"Unknown animation '{animation_type}', using fade_in")
                return text_clip.crossfadein(min(animation_duration, text_clip.duration / 2))
            
        except Exception as e:
            logger.error(f"Animation '{animation_type}' failed: {e}")
            # Return clip with just the position set
            return text_clip
    
    def _get_video_size(self, resolution: str) -> Tuple[int, int]:
        """Get video dimensions for given resolution."""
        sizes = {
            "1080p": (1920, 1080),
            "720p": (1280, 720)
        }
        return sizes.get(resolution, (1280, 720))
    
    def _calculate_crossfade_duration(self, base_duration: float) -> float:
        """Calculate crossfade duration based on image duration."""
        crossfade_setting = self.config.get('image', {}).get('crossfade_duration', 'auto')
        
        if crossfade_setting == 'auto':
            return min(base_duration / 3.0, max(0.1, base_duration / 4.0))
        else:
            try:
                return float(crossfade_setting)
            except (ValueError, TypeError):
                return min(base_duration / 3.0, max(0.1, base_duration / 4.0))