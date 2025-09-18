"""
Test suite for AudioGenerator class
"""
import os
import tempfile
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from audio_generator import AudioGenerator


class TestAudioGenerator:
    
    def setup_method(self):
        """Setup test configuration."""
        self.config = {
            'audio': {
                'generate_from_text': False,
                'tts': {
                    'language': 'en',
                    'slow': False
                }
            },
            'paths': {
                'audio_input': None,
                'output_dir': 'test_output'
            }
        }
        self.generator = AudioGenerator(self.config)
    
    def test_init(self):
        """Test AudioGenerator initialization."""
        assert self.generator.config == self.config
        assert self.generator.audio_config == self.config['audio']
        assert self.generator.paths == self.config['paths']
    
    @patch('audio_generator.AudioFileClip')
    def test_load_existing_audio_with_path(self, mock_audio_clip):
        """Test loading existing audio file when path is provided."""
        # Setup
        self.config['paths']['audio_input'] = 'test_audio.mp3'
        generator = AudioGenerator(self.config)
        
        mock_audio = Mock()
        mock_audio.duration = 120.0
        mock_audio_clip.return_value = mock_audio
        
        # Mock os.path.exists to return True
        with patch('os.path.exists', return_value=True):
            result = generator._load_existing_audio()
        
        # Assertions
        mock_audio_clip.assert_called_once_with('test_audio.mp3')
        assert result == mock_audio
    
    @patch('audio_generator.AudioFileClip')
    def test_load_existing_audio_file_not_found(self, mock_audio_clip):
        """Test handling when audio file is not found."""
        generator = AudioGenerator(self.config)
        
        with patch('os.path.exists', return_value=False):
            with patch.object(generator, '_find_audio_file', return_value=None):
                result = generator._load_existing_audio()
        
        assert result is None
        mock_audio_clip.assert_not_called()
    
    @patch('audio_generator.AudioFileClip')
    def test_load_existing_audio_with_exception(self, mock_audio_clip):
        """Test handling of exceptions during audio loading."""
        self.config['paths']['audio_input'] = 'corrupt_audio.mp3'
        generator = AudioGenerator(self.config)
        
        mock_audio_clip.side_effect = Exception("Corrupt file")
        
        with patch('os.path.exists', return_value=True):
            result = generator._load_existing_audio()
        
        assert result is None
    
    def test_find_audio_file(self):
        """Test finding audio file in directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test audio file
            audio_file = os.path.join(temp_dir, 'test.mp3')
            with open(audio_file, 'w') as f:
                f.write("dummy")
            
            # Update config to point to temp directory
            self.config['paths']['input_text'] = os.path.join(temp_dir, 'input.txt')
            generator = AudioGenerator(self.config)
            
            result = generator._find_audio_file()
            
            assert result == audio_file
    
    def test_find_audio_file_not_found(self):
        """Test when no audio file is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config['paths']['input_text'] = os.path.join(temp_dir, 'input.txt')
            generator = AudioGenerator(self.config)
            
            result = generator._find_audio_file()
            
            assert result is None
    
    @patch('audio_generator.TTS_AVAILABLE', True)
    @patch('audio_generator.gTTS')
    @patch('audio_generator.AudioFileClip')
    def test_generate_tts_audio(self, mock_audio_clip, mock_gtts):
        """Test TTS audio generation."""
        # Setup
        mock_tts_instance = Mock()
        mock_gtts.return_value = mock_tts_instance
        
        mock_audio = Mock()
        mock_audio.duration = 30.0
        mock_audio_clip.return_value = mock_audio
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config['paths']['output_dir'] = temp_dir
            generator = AudioGenerator(self.config)
            
            result = generator._generate_tts_audio("Hello world")
        
        # Assertions
        mock_gtts.assert_called_once_with(text="Hello world", lang='en', slow=False)
        mock_tts_instance.save.assert_called_once()
        assert result == mock_audio
    
    @patch('audio_generator.TTS_AVAILABLE', False)
    def test_generate_tts_audio_not_available(self):
        """Test TTS generation when libraries not available."""
        generator = AudioGenerator(self.config)
        
        result = generator._generate_tts_audio("Hello world")
        
        assert result is None
    
    def test_get_audio_duration(self):
        """Test getting audio duration."""
        mock_audio = Mock()
        mock_audio.duration = 150.5
        
        duration = self.generator.get_audio_duration(mock_audio)
        
        assert duration == 150.5
    
    def test_get_audio_duration_none(self):
        """Test getting duration when audio is None."""
        duration = self.generator.get_audio_duration(None)
        
        assert duration == 0.0
    
    @patch('audio_generator.AudioFileClip')
    def test_adjust_audio_duration_trim(self, mock_audio_clip):
        """Test trimming audio to shorter duration."""
        mock_audio = Mock()
        mock_audio.duration = 120.0
        mock_trimmed = Mock()
        mock_audio.subclip.return_value = mock_trimmed
        
        result = self.generator.adjust_audio_duration(mock_audio, 90.0)
        
        mock_audio.subclip.assert_called_once_with(0, 90.0)
        assert result == mock_trimmed
    
    @patch('audio_generator.concatenate_audioclips')
    def test_adjust_audio_duration_extend(self, mock_concatenate):
        """Test extending audio to longer duration."""
        mock_audio = Mock()
        mock_audio.duration = 60.0
        mock_extended = Mock()
        mock_extended.subclip.return_value = Mock()
        mock_concatenate.return_value = mock_extended
        
        result = self.generator.adjust_audio_duration(mock_audio, 150.0)
        
        # Should create looped audio and trim to exact duration
        mock_concatenate.assert_called_once()
        mock_extended.subclip.assert_called_once_with(0, 150.0)
    
    def test_adjust_audio_duration_close_enough(self):
        """Test when audio duration is close enough to target."""
        mock_audio = Mock()
        mock_audio.duration = 100.05
        
        result = self.generator.adjust_audio_duration(mock_audio, 100.0)
        
        # Should return original audio when difference is < 0.1s
        assert result == mock_audio
    
    def test_process_audio_existing_file(self):
        """Test processing existing audio file."""
        with patch.object(self.generator, '_load_existing_audio') as mock_load:
            mock_audio = Mock()
            mock_load.return_value = mock_audio
            
            result = self.generator.process_audio()
            
            assert result == mock_audio
            mock_load.assert_called_once()
    
    def test_process_audio_tts_mode(self):
        """Test processing audio in TTS mode."""
        self.config['audio']['generate_from_text'] = True
        generator = AudioGenerator(self.config)
        
        with patch.object(generator, '_generate_tts_audio') as mock_tts:
            mock_audio = Mock()
            mock_tts.return_value = mock_audio
            
            result = generator.process_audio("Test text")
            
            assert result == mock_audio
            mock_tts.assert_called_once_with("Test text")


if __name__ == '__main__':
    pytest.main([__file__])