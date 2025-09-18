import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import timedelta

logger = logging.getLogger(__name__)


class SubtitleGenerator:
    """Handles subtitle generation for videos."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.paths = config.get('paths', {})
    
    def generate_subtitles(self, text_settings: Optional[Dict[str, Any]], 
                          audio_duration: float, num_images: int) -> Optional[str]:
        """
        Generate SRT subtitle file based on text settings and timing.
        
        Args:
            text_settings: Text overlay settings
            audio_duration: Total duration of the audio/video
            num_images: Number of images/slides
            
        Returns:
            Path to generated SRT file or None if generation fails
        """
        if not text_settings or not text_settings.get('enabled', True):
            logger.info("Subtitles disabled or no text content available")
            return None
        
        try:
            subtitle_entries = self._create_subtitle_entries(text_settings, audio_duration, num_images)
            
            if not subtitle_entries:
                logger.warning("No subtitle entries created")
                return None
            
            # Generate SRT file
            output_dir = self.paths.get('output_dir', 'data/output')
            os.makedirs(output_dir, exist_ok=True)
            srt_path = os.path.join(output_dir, 'subtitles.srt')
            
            with open(srt_path, 'w', encoding='utf-8') as f:
                for i, entry in enumerate(subtitle_entries, 1):
                    f.write(f"{i}\n")
                    f.write(f"{entry['start_time']} --> {entry['end_time']}\n")
                    f.write(f"{entry['text']}\n\n")
            
            logger.info(f"Subtitles generated: {srt_path}")
            return srt_path
            
        except Exception as e:
            logger.error(f"Error generating subtitles: {e}")
            return None
    
    def _create_subtitle_entries(self, text_settings: Dict[str, Any], 
                                audio_duration: float, num_images: int) -> List[Dict[str, Any]]:
        """Create subtitle entries with timing information."""
        entries = []
        mode = text_settings.get('mode', 'single')
        base_duration = audio_duration / num_images
        
        if mode == 'single':
            # Single text for entire video
            text = text_settings.get('text', '').strip()
            if text:
                entries.append({
                    'start_time': self._format_timestamp(0),
                    'end_time': self._format_timestamp(audio_duration),
                    'text': text
                })
        
        elif mode in ['per_image', 'from_file']:
            # Different text for each image/slide
            texts = text_settings.get('texts', [])
            
            for i, text in enumerate(texts):
                if text and text.strip():
                    start_time = i * base_duration
                    end_time = (i + 1) * base_duration
                    
                    entries.append({
                        'start_time': self._format_timestamp(start_time),
                        'end_time': self._format_timestamp(end_time),
                        'text': text.strip()
                    })
        
        return entries
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp in SRT format (HH:MM:SS,mmm)."""
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        milliseconds = int((seconds - total_seconds) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def generate_vtt_subtitles(self, text_settings: Optional[Dict[str, Any]], 
                              audio_duration: float, num_images: int) -> Optional[str]:
        """
        Generate WebVTT subtitle file (alternative format).
        
        Args:
            text_settings: Text overlay settings
            audio_duration: Total duration of the audio/video
            num_images: Number of images/slides
            
        Returns:
            Path to generated VTT file or None if generation fails
        """
        if not text_settings or not text_settings.get('enabled', True):
            return None
        
        try:
            subtitle_entries = self._create_subtitle_entries(text_settings, audio_duration, num_images)
            
            if not subtitle_entries:
                return None
            
            # Generate VTT file
            output_dir = self.paths.get('output_dir', 'data/output')
            os.makedirs(output_dir, exist_ok=True)
            vtt_path = os.path.join(output_dir, 'subtitles.vtt')
            
            with open(vtt_path, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                
                for i, entry in enumerate(subtitle_entries, 1):
                    start_time = entry['start_time'].replace(',', '.')
                    end_time = entry['end_time'].replace(',', '.')
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{entry['text']}\n\n")
            
            logger.info(f"VTT subtitles generated: {vtt_path}")
            return vtt_path
            
        except Exception as e:
            logger.error(f"Error generating VTT subtitles: {e}")
            return None
    
    def create_subtitle_overlay_video(self, video_path: str, subtitle_path: str) -> Optional[str]:
        """
        Create a new video with burned-in subtitles using FFmpeg.
        Note: This requires FFmpeg to be installed on the system.
        
        Args:
            video_path: Path to the input video
            subtitle_path: Path to the subtitle file (SRT or VTT)
            
        Returns:
            Path to output video with burned-in subtitles or None if failed
        """
        try:
            import subprocess
            
            output_dir = self.paths.get('output_dir', 'data/output')
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(output_dir, f"{base_name}_with_subtitles.mp4")
            
            # FFmpeg command to burn in subtitles
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', f"subtitles={subtitle_path}:force_style='FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'",
                '-c:a', 'copy',
                '-y',  # Overwrite output file
                output_path
            ]
            
            logger.info("Burning subtitles into video using FFmpeg...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Video with burned-in subtitles created: {output_path}")
                return output_path
            else:
                logger.error(f"FFmpeg error: {result.stderr}")
                return None
                
        except FileNotFoundError:
            logger.error("FFmpeg not found. Please install FFmpeg to create videos with burned-in subtitles.")
            return None
        except Exception as e:
            logger.error(f"Error creating video with subtitles: {e}")
            return None