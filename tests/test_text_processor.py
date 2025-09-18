"""
Test suite for TextProcessor class
"""
import os
import tempfile
import pytest
import sys

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from text_processor import TextProcessor


class TestTextProcessor:
    
    def setup_method(self):
        """Setup test configuration."""
        self.config = {
            'text': {
                'enabled': True,
                'mode': 'auto',
                'font_size': 60,
                'color': 'white',
                'stroke_color': 'black',
                'stroke_width': 3,
                'position': 'center',
                'animation': {
                    'type': 'fade_in',
                    'duration': 1.5
                },
                'default_text': 'Test default text'
            },
            'paths': {
                'input_text': 'data/input.txt'
            }
        }
        self.processor = TextProcessor(self.config)
    
    def test_disabled_text_processing(self):
        """Test text processing when disabled."""
        self.config['text']['enabled'] = False
        processor = TextProcessor(self.config)
        result = processor.process_text_content(5)
        assert result is None
    
    def test_single_text_mode(self):
        """Test single text mode processing."""
        self.config['text']['mode'] = 'single'
        self.config['text']['default_text'] = 'Test text'
        processor = TextProcessor(self.config)
        
        result = processor.process_text_content(3)
        
        assert result is not None
        assert result['mode'] == 'single'
        assert result['text'] == 'Test text'
        assert result['font_size'] == 60
        assert result['animation'] == 'fade_in'
    
    def test_per_image_mode(self):
        """Test per-image text mode."""
        self.config['text']['mode'] = 'per_image'
        processor = TextProcessor(self.config)
        
        result = processor.process_text_content(3)
        
        assert result is not None
        assert result['mode'] == 'per_image'
        assert len(result['texts']) == 3
        assert all('Slide' in text for text in result['texts'])
    
    def test_from_file_mode(self):
        """Test text processing from file."""
        # Create temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Line 1\nLine 2\nLine 3")
            temp_path = f.name
        
        try:
            self.config['text']['mode'] = 'from_file'
            self.config['paths']['input_text'] = temp_path
            processor = TextProcessor(self.config)
            
            result = processor.process_text_content(3)
            
            assert result is not None
            assert result['mode'] == 'per_image'
            assert len(result['texts']) == 3
            assert result['texts'][0] == 'Line 1'
            assert result['texts'][1] == 'Line 2'
            assert result['texts'][2] == 'Line 3'
        
        finally:
            os.unlink(temp_path)
    
    def test_adjust_text_list_to_images(self):
        """Test text list adjustment to match image count."""
        # Test truncation
        texts = ['A', 'B', 'C', 'D', 'E']
        result = self.processor._adjust_text_list_to_images(texts, 3)
        assert len(result) == 3
        assert result == ['A', 'B', 'C']
        
        # Test extension
        texts = ['A', 'B']
        result = self.processor._adjust_text_list_to_images(texts, 4)
        assert len(result) == 4
        assert result == ['A', 'B', 'B', 'B']
    
    def test_create_text_settings(self):
        """Test text settings creation."""
        result = self.processor._create_text_settings(
            'single', 
            text='Test text',
            json_settings={'font_size': 80, 'color': 'red'}
        )
        
        assert result['mode'] == 'single'
        assert result['text'] == 'Test text'
        assert result['font_size'] == 80  # Should be overridden by json_settings
        assert result['color'] == 'red'   # Should be overridden by json_settings
        assert result['stroke_color'] == 'black'  # Should remain from config


if __name__ == '__main__':
    pytest.main([__file__])