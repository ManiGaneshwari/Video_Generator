"""
Sequential text animation module for line-by-line text reveals.
"""
import os
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, CompositeVideoClip

logger = logging.getLogger(__name__)


class SequentialTextAnimator:
    """Creates sequential text animations where lines appear one after another."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.text_config = config.get('text', {})
        self.video_config = config.get('video', {})
    
    def create_sequential_text_clip(self, text_content: str, video_size: Tuple[int, int], 
                                   duration: float, text_settings: Dict[str, Any]) -> Optional[CompositeVideoClip]:
        """
        Create a text clip where lines appear sequentially.
        
        Args:
            text_content: Full text content for the slide
            video_size: Video dimensions (width, height)
            duration: Total duration for this slide
            text_settings: Text styling settings
            
        Returns:
            CompositeVideoClip with sequential text animation
        """
        try:
            # Split text into lines
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            
            if not lines:
                logger.warning("No valid lines found in text content")
                return None
            
            logger.info(f"Creating sequential animation for {len(lines)} lines")
            
            # Get sequential animation settings
            sequential_config = text_settings.get('sequential', {})
            line_delay = sequential_config.get('line_delay', 1.5)  # Time between lines
            line_duration = sequential_config.get('line_duration', 'auto')  # How long each line stays
            animation_type = sequential_config.get('animation', 'fade_in')
            stagger_effect = sequential_config.get('stagger', True)  # Keep previous lines visible
            
            # Calculate timing
            if line_duration == 'auto':
                # Each line gets equal share of remaining time after delays
                total_delay_time = (len(lines) - 1) * line_delay
                remaining_time = max(1.0, duration - total_delay_time)
                line_duration = remaining_time / len(lines)
            else:
                line_duration = float(line_duration)
            
            # Create individual line clips
            line_clips = []
            cumulative_height = 0
            
            for i, line in enumerate(lines):
                # Calculate start time for this line
                start_time = i * line_delay
                
                # Calculate end time based on stagger effect
                if stagger_effect:
                    # Line stays until the end of the slide
                    end_time = duration
                else:
                    # Line disappears after its duration
                    end_time = start_time + line_duration
                
                clip_duration = end_time - start_time
                
                if clip_duration > 0:
                    # Create individual line clip
                    line_clip = self._create_single_line_clip(
                        line, video_size, clip_duration, text_settings, i, len(lines)
                    )
                    
                    if line_clip:
                        # Set start time
                        line_clip = line_clip.set_start(start_time)
                        line_clips.append(line_clip)
            
            if not line_clips:
                logger.error("No line clips created")
                return None
            
            # Composite all line clips
            final_clip = CompositeVideoClip(line_clips, size=video_size)
            final_clip = final_clip.set_duration(duration)
            
            logger.info(f"Sequential text animation created with {len(line_clips)} line clips")
            return final_clip
            
        except Exception as e:
            logger.error(f"Error creating sequential text clip: {e}")
            return None
    
    def _create_single_line_clip(self, line: str, video_size: Tuple[int, int], 
                                duration: float, text_settings: Dict[str, Any], 
                                line_index: int, total_lines: int) -> Optional[ImageClip]:
        """Create a clip for a single line of text."""
        try:
            # Create PIL image for this line
            line_img = self._create_line_image(line, video_size, text_settings, line_index, total_lines)
            
            if line_img is None:
                return None
            
            # Convert to MoviePy clip
            img_array = np.array(line_img)
            clip = ImageClip(img_array, ismask=False, transparent=True).set_duration(duration)
            
            # Apply line-specific animation
            sequential_config = text_settings.get('sequential', {})
            animation_type = sequential_config.get('animation', 'fade_in')
            animation_duration = sequential_config.get('animation_duration', 0.5)
            
            clip = self._apply_line_animation(clip, animation_type, animation_duration)
            
            return clip
            
        except Exception as e:
            logger.error(f"Error creating single line clip: {e}")
            return None
    
    def _create_line_image(self, line: str, video_size: Tuple[int, int], 
                          text_settings: Dict[str, Any], line_index: int, total_lines: int) -> Optional[Image.Image]:
        """Create PIL image for a single line positioned correctly."""
        try:
            # Get font settings
            font_size = text_settings.get('font_size', 60)
            color = text_settings.get('color', 'white')
            stroke_color = text_settings.get('stroke_color', 'black')
            stroke_width = text_settings.get('stroke_width', 3)
            
            # Load font
            font = self._load_font(font_size)
            if font is None:
                font = ImageFont.load_default()
            
            # Create temporary image to measure text
            temp_img = Image.new('RGBA', video_size, (0, 0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            
            # Measure line dimensions
            try:
                if hasattr(temp_draw, 'textbbox'):
                    bbox = temp_draw.textbbox((0, 0), line, font=font)
                    line_width = bbox[2] - bbox[0]
                    line_height = bbox[3] - bbox[1]
                else:
                    line_width, line_height = temp_draw.textsize(line, font=font)
            except Exception:
                # Fallback measurement
                line_width = len(line) * (font_size * 0.6)
                line_height = font_size * 1.2
            
            # Calculate positioning
            position_setting = text_settings.get('position', 'center')
            x, y = self._calculate_line_position(
                position_setting, line_width, line_height, video_size, 
                line_index, total_lines, font_size
            )
            
            # Create full-size image with transparent background
            img = Image.new('RGBA', video_size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw stroke
            if stroke_width > 0 and stroke_color != color:
                for adj_x in range(-stroke_width, stroke_width + 1):
                    for adj_y in range(-stroke_width, stroke_width + 1):
                        if adj_x != 0 or adj_y != 0:
                            try:
                                draw.text((x + adj_x, y + adj_y), line, font=font, fill=stroke_color)
                            except Exception as e:
                                logger.warning(f"Error drawing stroke: {e}")
            
            # Draw main text
            try:
                draw.text((x, y), line, font=font, fill=color)
            except Exception as e:
                logger.error(f"Error drawing main text: {e}")
                return None
            
            return img
            
        except Exception as e:
            logger.error(f"Error creating line image: {e}")
            return None
    
    def _calculate_line_position(self, position_setting: str, line_width: int, line_height: int,
                               video_size: Tuple[int, int], line_index: int, total_lines: int,
                               font_size: int) -> Tuple[int, int]:
        """Calculate position for a specific line in sequential display."""
        video_width, video_height = video_size
        
        # Calculate base position
        if isinstance(position_setting, (list, tuple)) and len(position_setting) == 2:
            base_x, base_y = position_setting
        elif position_setting == 'center':
            base_x = (video_width - line_width) // 2
            base_y = (video_height - (total_lines * (line_height + 10))) // 2
        elif position_setting == 'top':
            base_x = (video_width - line_width) // 2
            base_y = 50
        elif position_setting == 'bottom':
            base_x = (video_width - line_width) // 2
            base_y = video_height - (total_lines * (line_height + 10)) - 50
        else:
            # Default to center
            base_x = (video_width - line_width) // 2
            base_y = (video_height - (total_lines * (line_height + 10))) // 2
        
        # Calculate line-specific position
        line_spacing = line_height + 15  # Space between lines
        y = base_y + (line_index * line_spacing)
        
        # Center this specific line horizontally
        x = (video_width - line_width) // 2
        
        # Ensure within bounds
        x = max(10, min(x, video_width - line_width - 10))
        y = max(10, min(y, video_height - line_height - 10))
        
        return (x, y)
    
    def _load_font(self, font_size: int) -> Optional[ImageFont.FreeTypeFont]:
        """Load font from system font paths."""
        font_paths = self.text_config.get('fonts', [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arial.ttf"
        ])
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, font_size)
                except Exception:
                    continue
        
        return None
    
    def _apply_line_animation(self, clip: ImageClip, animation_type: str, animation_duration: float) -> ImageClip:
        """Apply animation to individual line clip."""
        try:
            if animation_type == 'fade_in':
                return clip.crossfadein(min(animation_duration, clip.duration))
            elif animation_type == 'slide_from_left':
                def slide_pos(t):
                    if t < animation_duration:
                        progress = min(t / animation_duration, 1.0)
                        progress = 1 - (1 - progress) ** 3  # Ease-out
                        start_x = -clip.w
                        target_x = 0
                        current_x = start_x + (target_x - start_x) * progress
                        return (current_x, 0)
                    return (0, 0)
                return clip.set_position(slide_pos)
            elif animation_type == 'typewriter':
                def typewriter_fx(get_frame, t):
                    frame = get_frame(t)
                    if t < animation_duration:
                        progress = min(t / animation_duration, 1.0)
                        reveal_width = int(frame.shape[1] * progress)
                        # Create mask
                        mask = np.zeros_like(frame[:, :, 3], dtype=np.uint8)
                        mask[:, :reveal_width] = frame[:, :reveal_width, 3]
                        frame[:, :, 3] = mask
                    return frame
                return clip.fl(typewriter_fx)
            elif animation_type == 'zoom_in':
                def zoom_resize(t):
                    if t < animation_duration:
                        progress = min(t / animation_duration, 1.0)
                        progress = 1 - (1 - progress) ** 3
                        return 0.3 + 0.7 * progress
                    return 1.0
                return clip.resize(zoom_resize)
            else:
                # No animation or unknown type
                return clip
            
        except Exception as e:
            logger.error(f"Error applying line animation '{animation_type}': {e}")
            return clip