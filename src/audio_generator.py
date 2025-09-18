import os
import logging
from typing import Optional, Dict, Any
from moviepy.editor import AudioFileClip
try:
    from gtts import gTTS
    from pydub import AudioSegment
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logging.warning("TTS libraries not available. Install gtts and pydub for text-to-speech functionality.")

logger = logging.getLogger(__name__)


class AudioGenerator:
    """Handles audio processing and text-to-speech generation."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.audio_config = config.get('audio', {})
        self.paths = config.get('paths', {})
    
    def process_audio(self, text_content: str = None) -> Optional[AudioFileClip]:
        """
        Process audio based on configuration settings.
        
        Args:
            text_content: Text content for TTS generation (if needed)
            
        Returns:
            AudioFileClip object or None if no audio is available
        """
        generate_from_text = self.audio_config.get('generate_from_text', False)
        
        if generate_from_text and text_content:
            return self._generate_tts_audio(text_content)
        else:
            return self._load_existing_audio()
    
    def _load_existing_audio(self) -> Optional[AudioFileClip]:
        """Load existing audio file."""
        audio_path = self.paths.get('audio_input')
        
        if not audio_path:
            # Try to find audio file in data directory
            audio_path = self._find_audio_file()
        
        if not audio_path or not os.path.exists(audio_path):
            logger.error("No audio file found. Please provide an audio file or enable TTS generation.")
            return None
        
        try:
            audio = AudioFileClip(audio_path)
            logger.info(f"Loaded audio file: {audio_path} (duration: {audio.duration:.2f}s)")
            return audio
        except Exception as e:
            logger.error(f"Error loading audio file {audio_path}: {e}")
            return None
    
    def _generate_tts_audio(self, text_content: str) -> Optional[AudioFileClip]:
        """Generate audio from text using TTS."""
        if not TTS_AVAILABLE:
            logger.error("TTS libraries not available. Please install gtts and pydub or provide an audio file.")
            return None
        
        tts_config = self.audio_config.get('tts', {})
        language = tts_config.get('language', 'en')
        slow = tts_config.get('slow', False)
        
        # Create output directory
        output_dir = self.paths.get('output_dir', 'data/output')
        os.makedirs(output_dir, exist_ok=True)
        
        temp_audio_path = os.path.join(output_dir, 'generated_audio.mp3')
        
        try:
            # Generate TTS
            logger.info(f"Generating TTS audio in language: {language}")
            tts = gTTS(text=text_content, lang=language, slow=slow)
            tts.save(temp_audio_path)
            
            # Load and return as MoviePy audio clip
            audio = AudioFileClip(temp_audio_path)
            logger.info(f"Generated TTS audio: {temp_audio_path} (duration: {audio.duration:.2f}s)")
            return audio
            
        except Exception as e:
            logger.error(f"Error generating TTS audio: {e}")
            return None
    
    def _find_audio_file(self) -> Optional[str]:
        """Find audio file in data directory."""
        data_dir = os.path.dirname(self.paths.get('input_text', 'data/input.txt'))
        audio_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg']
        
        for file in os.listdir(data_dir):
            if any(file.lower().endswith(ext) for ext in audio_extensions):
                audio_path = os.path.join(data_dir, file)
                logger.info(f"Found audio file: {audio_path}")
                return audio_path
        
        logger.warning(f"No audio file found in {data_dir}")
        return None
    
    def get_audio_duration(self, audio: AudioFileClip) -> float:
        """Get duration of audio clip."""
        if audio is None:
            return 0.0
        return audio.duration
    
    def create_silence(self, duration: float) -> Optional[AudioFileClip]:
        """Create silent audio clip of specified duration."""
        if not TTS_AVAILABLE:
            logger.warning("Cannot create silence without pydub. Using default duration.")
            return None
        
        try:
            # Create silent audio using pydub
            silent_audio = AudioSegment.silent(duration=int(duration * 1000))  # Convert to milliseconds
            
            # Save to temporary file
            output_dir = self.paths.get('output_dir', 'data/output')
            os.makedirs(output_dir, exist_ok=True)
            temp_path = os.path.join(output_dir, 'temp_silence.wav')
            silent_audio.export(temp_path, format="wav")
            
            # Load as MoviePy audio clip
            audio_clip = AudioFileClip(temp_path)
            logger.info(f"Created silent audio clip: {duration:.2f}s")
            
            return audio_clip
            
        except Exception as e:
            logger.error(f"Error creating silent audio: {e}")
            return None
    
    def adjust_audio_duration(self, audio: AudioFileClip, target_duration: float) -> AudioFileClip:
        """Adjust audio duration to match target duration."""
        if audio is None:
            return None
        
        current_duration = audio.duration
        
        if abs(current_duration - target_duration) < 0.1:
            # Duration is close enough
            return audio
        
        if current_duration > target_duration:
            # Trim audio
            logger.info(f"Trimming audio from {current_duration:.2f}s to {target_duration:.2f}s")
            return audio.subclip(0, target_duration)
        else:
            # Extend audio by looping or adding silence
            logger.info(f"Extending audio from {current_duration:.2f}s to {target_duration:.2f}s")
            
            # Calculate how many times to loop
            loop_count = int(target_duration / current_duration) + 1
            
            # Create looped audio
            looped_clips = [audio] * loop_count
            from moviepy.editor import concatenate_audioclips
            extended_audio = concatenate_audioclips(looped_clips)
            
            # Trim to exact duration
            return extended_audio.subclip(0, target_duration)