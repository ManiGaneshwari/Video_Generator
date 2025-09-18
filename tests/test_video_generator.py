"""
Test suite for VideoGenerator class
"""
import os
import tempfile
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from video_generator import VideoGenerator


class TestVideoGenerator:
    
    def setup_method(self):
        """Setup test configuration."""
        self.config = {
            'video': {
                'resolution': '720p',
                'scaling_method': 'fit',
                'fps': 24,
                'codec': 'libx264',
                'audio_codec': 'aac'
            },
            'text': {
                'fonts': ['/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'],
                'enabled': True
            },
            'image': {
                'crossfade_duration': 'auto'
            },
            'paths': {
                'output_dir': 'test_output'
            }
        }
        self.generator = VideoGenerator(self.config)
    
    def test_init(self):
        """Test VideoGenerator initialization."""
        assert self.generator.config == self.config
        assert self.generator.video_config == self.config['video']
        assert self.generator.text_config == self.config['text']
    
    def test_get_video_size(self):
        """Test getting video dimensions for different resolutions."""
        assert self.generator._get_video_size('1080p') == (1920, 1080)
        assert self.generator._get_video_size('720p') == (1280, 720)
        assert self.generator._get_video_size('unknown') == (1280, 720)  # Default
    
    def test_calculate_crossfade_duration_auto(self):
        """Test automatic crossfade duration calculation."""
        base_duration = 6.0
        crossfade = self.generator._calculate_crossfade_duration(base_duration)
        
        # Should be min(base_duration/3, max(0.1, base_duration/4))
        expected = min(2.0, max(0.1, 1.5))  # min(6/3, max(0.1, 6/4)) = min(2.0, 1.5) = 1.5
        assert crossfade == expected
    
    def test_calculate_crossfade_duration_fixed(self):
        """Test fixed crossfade duration."""
        self.config['image']['crossfade_duration'] = 2.5
        generator = VideoGenerator(self.config)
        
        crossfade = generator._calculate_crossfade_duration(10.0)
        assert crossfade == 2.5
    
    def test_calculate_crossfade_duration_invalid(self):
        """Test handling invalid crossfade duration setting."""
        self.config['image']['crossfade_duration'] = 'invalid'
        generator = VideoGenerator(self.config)
        
        base_duration = 4.0
        crossfade = generator._calculate_crossfade_duration(base_duration)
        
        # Should fallback to auto calculation
        expected = min(base_duration / 3.0, max(0.1, base_duration / 4.0))
        assert crossfade == expected
    
    def test_get_text_for_image_single_mode(self):
        """Test getting text for single text mode."""
        text_settings = {
            'mode': 'single',
            'text': 'Single text for all images'
        }
        
        result = self.generator._get_text_for_image(text_settings, 2)
        assert result == 'Single text for all images'
    
    def test_get_text_for_image_per_image_mode(self):
        """Test getting text for per-image mode."""
        text_settings = {
            'mode': 'per_image',
            'texts': ['Text 1', 'Text 2', 'Text 3']
        }
        
        assert self.generator._get_text_for_image(text_settings, 0) == 'Text 1'
        assert self.generator._get_text_for_image(text_settings, 1) == 'Text 2'
        assert self.generator._get_text_for_image(text_settings, 5) == ''  # Out of range
    
    def test_get_text_for_image_empty_mode(self):
        """Test getting text for unknown mode."""
        text_settings = {'mode': 'unknown'}
        
        result = self.generator._get_text_for_image(text_settings, 0)
        assert result == ''
    
    @patch('PIL.Image.open')
    def test_process_image_fit_method(self, mock_image_open):
        """Test image processing with fit scaling method."""
        # Create mock image
        mock_img = Mock()
        mock_img.size = (800, 600)
        mock_img.thumbnail.return_value = None
        mock_img.resize.return_value = mock_img
        mock_image_open.return_value = mock_img
        
        # Mock PIL Image.new
        mock_final_img = Mock()
        with patch('PIL.Image.new', return_value=mock_final_img) as mock_new:
            result = self.generator._process_image(
                'test.jpg', (1280, 720), 'fit'
            )
        
        mock_image_open.assert_called_once_with('test.jpg')
        mock_new.assert_called_once_with('RGB', (1280, 720), (0, 0, 0))
        assert result == mock_final_img
    
    @patch('PIL.Image.open')
    def test_process_image_crop_method(self, mock_image_open):
        """Test image processing with crop scaling method."""
        # Create mock image that's wider than target aspect ratio
        mock_img = Mock()
        mock_img.size = (1600, 900)  # 16:9 ratio but larger
        mock_resized = Mock()
        mock_img.resize.return_value = mock_resized
        mock_cropped = Mock()
        mock_resized.crop.return_value = mock_cropped
        mock_image_open.return_value = mock_img
        
        result = self.generator._process_image(
            'test.jpg', (1280, 720), 'crop'
        )
        
        mock_image_open.assert_called_once_with('test.jpg')
        # Should resize and crop
        mock_img.resize.assert_called_once()
        mock_resized.crop.assert_called_once()
        assert result == mock_cropped
    
    @patch('PIL.Image.open')
    def test_process_image_exception(self, mock_image_open):
        """Test handling exception during image processing."""
        mock_image_open.side_effect = Exception("File error")
        
        result = self.generator._process_image('bad_image.jpg', (1280, 720), 'fit')
        
        assert result is None
    
    @patch('video_generator.ImageFont.truetype')
    def test_load_font_success(self, mock_truetype):
        """Test successful font loading."""
        mock_font = Mock()
        mock_truetype.return_value = mock_font
        
        with patch('os.path.exists', return_value=True):
            result = self.generator._load_font(24)
        
        mock_truetype.assert_called_once()
        assert result == mock_font
    
    @patch('video_generator.ImageFont.truetype')
    def test_load_font_not_found(self, mock_truetype):
        """Test font loading when no fonts are found."""
        with patch('os.path.exists', return_value=False):
            result = self.generator._load_font(24)
        
        assert result is None
        mock_truetype.assert_not_called()
    
    def test_adjust_font_size(self):
        """Test font size adjustment logic."""
        mock_draw = Mock()
        mock_font = Mock()
        mock_font.path = '/test/font.ttf'
        
        # Mock textbbox to return large dimensions that need adjustment
        mock_draw.textbbox.return_value = (0, 0, 1500, 800)  # Width=1500, Height=800
        
        lines = ['Test line']
        
        with patch.object(self.generator, '_load_font', return_value=mock_font):
            font_size, font = self.generator._adjust_font_size(
                lines, mock_draw, mock_font, 60, (1280, 720)
            )
        
        # Font size should be reduced
        assert font_size < 60
        assert font_size >= 10  # Minimum font size
    
    @patch('video_generator.np.array')
    @patch('video_generator.ImageClip')
    def test_create_text_overlay_success(self, mock_image_clip, mock_array):
        """Test successful text overlay creation."""
        text_settings = {
            'font_size': 50,
            'color': 'white',
            'stroke_color': 'black',
            'stroke_width': 2,
            'position': 'center',
            'animation': 'fade_in',
            'animation_duration': 1.0
        }
        
        mock_text_img = Mock()
        mock_clip = Mock()
        mock_clip.set_duration.return_value = mock_clip
        mock_clip.set_position.return_value = mock_clip
        mock_image_clip.return_value = mock_clip
        
        with patch.object(self.generator, '_get_text_for_image', return_value='Test text'):
            with patch.object(self.generator, '_create_pil_text_image', return_value=mock_text_img):
                with patch.object(self.generator, '_apply_text_animation', return_value=mock_clip):
                    result = self.generator._create_text_overlay(
                        text_settings, 0, (1280, 720), 5.0
                    )
        
        assert result == mock_clip
    
    def test_create_text_overlay_no_text(self):
        """Test text overlay creation when no text content."""
        text_settings = {}
        
        with patch.object(self.generator, '_get_text_for_image', return_value=''):
            result = self.generator._create_text_overlay(
                text_settings, 0, (1280, 720), 5.0
            )
        
        assert result is None
    
    def test_apply_text_animation_fade_in(self):
        """Test fade in animation application."""
        mock_clip = Mock()
        mock_animated = Mock()
        mock_clip.crossfadein.return_value = mock_animated
        
        result = self.generator._apply_text_animation(
            mock_clip, 'fade_in', 1.5, (1280, 720), 'center'
        )
        
        mock_clip.crossfadein.assert_called_once_with(1.5)
        assert result == mock_animated
    
    def test_apply_text_animation_zoom_in(self):
        """Test zoom in animation application."""
        mock_clip = Mock()
        mock_resized = Mock()
        mock_clip.resize.return_value = mock_resized
        
        result = self.generator._apply_text_animation(
            mock_clip, 'zoom_in', 1.0, (1280, 720), 'center'
        )
        
        mock_clip.resize.assert_called_once()
        assert result == mock_resized
    
    def test_apply_text_animation_unknown(self):
        """Test unknown animation type fallback."""
        mock_clip = Mock()
        mock_clip.duration = 5.0
        mock_animated = Mock()
        mock_clip.crossfadein.return_value = mock_animated
        
        result = self.generator._apply_text_animation(
            mock_clip, 'unknown_animation', 1.0, (1280, 720), 'center'
        )
        
        # Should fallback to fade_in
        mock_clip.crossfadein.assert_called_once_with(2.5)  # min(1.0, 5.0/2)
        assert result == mock_animated
    
    def test_apply_text_animation_exception(self):
        """Test animation application with exception."""
        mock_clip = Mock()
        mock_clip.crossfadein.side_effect = Exception("Animation error")
        mock_positioned = Mock()
        mock_clip.set_position.return_value = mock_positioned
        
        result = self.generator._apply_text_animation(
            mock_clip, 'fade_in', 1.0, (1280, 720), 'center'
        )
        
        # Should fallback to just setting position
        mock_clip.set_position.assert_called_once_with('center')
        assert result == mock_positioned
    
    @patch('video_generator.concatenate_videoclips')
    def test_create_slideshow_video_success(self, mock_concatenate):
        """Test successful slideshow video creation."""
        # Setup mocks
        mock_audio = Mock()
        mock_audio.duration = 20.0
        
        mock_final_video = Mock()
        mock_final_video.set_duration.return_value = mock_final_video
        mock_final_video.set_audio.return_value = mock_final_video
        mock_concatenate.return_value = mock_final_video
        
        images = ['img1.jpg', 'img2.jpg']
        
        with patch.object(self.generator, '_build_slideshow_clips') as mock_build:
            mock_clips = [Mock(), Mock()]
            mock_build.return_value = mock_clips
            
            result = self.generator.create_slideshow_video(images, mock_audio, None)
        
        mock_build.assert_called_once()
        mock_concatenate.assert_called_once_with(mock_clips, method="compose")
        assert result == mock_final_video
    
    def test_create_slideshow_video_no_images(self):
        """Test slideshow creation with no images."""
        mock_audio = Mock()
        
        result = self.generator.create_slideshow_video([], mock_audio, None)
        
        assert result is None
    
    def test_create_slideshow_video_no_audio(self):
        """Test slideshow creation with no audio."""
        images = ['img1.jpg']
        
        result = self.generator.create_slideshow_video(images, None, None)
        
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__])