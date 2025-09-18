import os
import json
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class TextProcessor:
    """Handles text processing and content preparation for video generation."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.text_config = config.get('text', {})
        self.paths = config.get('paths', {})
    
    def process_text_content(self, num_images: int) -> Optional[Dict[str, Any]]:
        """
        Process text content based on configuration settings.
        
        Args:
            num_images: Number of images to generate text for
            
        Returns:
            Dictionary containing text settings or None if text is disabled
        """
        if not self.text_config.get('enabled', True):
            logger.info("Text overlays disabled in configuration")
            return None
        
        text_mode = self.text_config.get('mode', 'auto')
        
        logger.info(f"Processing text content in mode: {text_mode}")
        
        if text_mode == "auto":
            return self._auto_detect_text_mode(num_images)
        elif text_mode == "single":
            return self._process_single_text()
        elif text_mode == "per_image":
            return self._process_per_image_text(num_images)
        elif text_mode == "from_file":
            return self._process_from_file_optimized(num_images)  # Use optimized version
        else:
            logger.error(f"Unknown text mode: {text_mode}")
            return None
    
    def _process_from_file_optimized(self, num_images: int) -> Optional[Dict[str, Any]]:
        """Process text content from input file with script optimization."""
        input_text_path = self.paths.get('input_text', 'data/input.txt')
        
        if not os.path.exists(input_text_path):
            logger.error(f"Input text file not found: {input_text_path}")
            return None
        
        try:
            with open(input_text_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                logger.warning("Input text file is empty")
                return None
            
            # Split content into lines
            raw_lines = content.split('\n')
            
            # Import and use script optimizer
            from .script_optimizer import ScriptOptimizer
            optimizer = ScriptOptimizer(self.config)
            
            # Analyze the script first
            analysis = optimizer.analyze_script_distribution(raw_lines, num_images)
            logger.info(f"Script analysis: {analysis['original_lines']} lines -> {analysis['cleaned_lines']} cleaned lines")
            logger.info(f"Average {analysis['lines_per_image_avg']:.1f} lines per image")
            logger.info(f"Recommended method: {analysis['recommended_method']}")
            
            # Optimize distribution
            optimized_settings = optimizer.optimize_script_distribution(raw_lines, num_images)
            
            if optimized_settings:
                # Merge with base text settings
                base_settings = self._create_text_settings('per_image', texts=[])
                base_settings.update(optimized_settings)
                
                logger.info(f"Script optimized successfully: {len(optimized_settings['texts'])} slides created")
                return base_settings
            else:
                logger.error("Failed to optimize script distribution")
                return None
            
        except Exception as e:
            logger.error(f"Error processing optimized text file {input_text_path}: {e}")
            return None
    
    def _auto_detect_text_mode(self, num_images: int) -> Optional[Dict[str, Any]]:
        """Auto-detect the best text processing mode based on available content."""
        
        # Check for JSON file first
        json_result = self._try_load_json_file()
        if json_result:
            logger.info("Auto-detected: Using JSON text configuration")
            return json_result
        
        # Check for input text file with optimization
        input_text_path = self.paths.get('input_text', 'data/input.txt')
        if os.path.exists(input_text_path):
            logger.info("Auto-detected: Using optimized text file processing")
            return self._process_from_file_optimized(num_images)
        
        # Check for default text in config
        default_text = self.text_config.get('default_text', '').strip()
        if default_text:
            logger.info("Auto-detected: Using default text from configuration")
            return self._create_text_settings('single', text=default_text)
        
        # No text content found
        logger.info("Auto-detected: No text content found, disabling text overlays")
        return None
    
    def _process_single_text(self) -> Optional[Dict[str, Any]]:
        """Process single text that applies to all images."""
        default_text = self.text_config.get('default_text', '').strip()
        
        if not default_text:
            logger.warning("Single text mode selected but no default_text provided in config")
            return None
        
        return self._create_text_settings('single', text=default_text)
    
    def _process_per_image_text(self, num_images: int) -> Optional[Dict[str, Any]]:
        """Process individual text for each image."""
        # Generate placeholder text for each image
        texts = []
        for i in range(num_images):
            texts.append(f"Slide {i + 1}")
        
        logger.info(f"Generated placeholder text for {num_images} images")
        return self._create_text_settings('per_image', texts=texts)
    
    def _process_from_file(self, num_images: int) -> Optional[Dict[str, Any]]:
        """Process text content from input file."""
        input_text_path = self.paths.get('input_text', 'data/input.txt')
        
        if not os.path.exists(input_text_path):
            logger.error(f"Input text file not found: {input_text_path}")
            return None
        
        try:
            with open(input_text_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                logger.warning("Input text file is empty")
                return None
            
            # Split content into lines and clean
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            # If we have only one line, use it for all images
            if len(lines) == 1:
                logger.info("Single line found in text file, using for all images")
                return self._create_text_settings('single', text=lines[0])
            
            # Adjust text list to match number of images
            texts = self._adjust_text_list_to_images(lines, num_images)
            
            logger.info(f"Processed {len(texts)} text entries from file")
            return self._create_text_settings('per_image', texts=texts)
            
        except Exception as e:
            logger.error(f"Error reading text file {input_text_path}: {e}")
            return None
    
    def _try_load_json_file(self) -> Optional[Dict[str, Any]]:
        """Try to load text settings from JSON file."""
        # Look for JSON files in data directory
        data_dir = os.path.dirname(self.paths.get('input_text', 'data/input.txt'))
        json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
        
        if not json_files:
            return None
        
        # Use the first JSON file found
        json_path = os.path.join(data_dir, json_files[0])
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Validate JSON structure
            if 'texts' in json_data or 'text' in json_data:
                logger.info(f"Loaded text settings from JSON: {json_path}")
                
                # Create text settings from JSON
                if 'texts' in json_data:
                    return self._create_text_settings('per_image', texts=json_data['texts'], 
                                                    json_settings=json_data.get('settings', {}))
                elif 'text' in json_data:
                    return self._create_text_settings('single', text=json_data['text'],
                                                    json_settings=json_data.get('settings', {}))
            
        except Exception as e:
            logger.error(f"Error loading JSON file {json_path}: {e}")
        
        return None
    
    def _adjust_text_list_to_images(self, texts: List[str], num_images: int) -> List[str]:
        """Adjust text list to match the number of images."""
        if len(texts) == num_images:
            return texts
        elif len(texts) > num_images:
            # Truncate to match number of images
            logger.info(f"Truncating text list from {len(texts)} to {num_images} entries")
            return texts[:num_images]
        else:
            # Extend list by repeating the last entry or using empty strings
            logger.info(f"Extending text list from {len(texts)} to {num_images} entries")
            extended_texts = texts.copy()
            last_text = texts[-1] if texts else ""
            
            while len(extended_texts) < num_images:
                extended_texts.append(last_text)
            
            return extended_texts
    
    def _create_text_settings(self, mode: str, text: str = "", texts: List[str] = None, 
                             json_settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create text settings dictionary."""
        settings = {
            'mode': mode,
            'font_size': self.text_config.get('font_size', 60),
            'color': self.text_config.get('color', 'white'),
            'stroke_color': self.text_config.get('stroke_color', 'black'),
            'stroke_width': self.text_config.get('stroke_width', 3),
            'position': self.text_config.get('position', 'center'),
            'animation': self.text_config.get('animation', {}).get('type', 'fade_in'),
            'animation_duration': self.text_config.get('animation', {}).get('duration', 1.5)
        }
        
        # Override with JSON settings if provided
        if json_settings:
            settings.update(json_settings)
        
        # Add text content based on mode
        if mode == 'single':
            settings['text'] = text
        elif mode == 'per_image':
            settings['texts'] = texts or []
        
        return settings
    
    def save_text_settings(self, text_settings: Dict[str, Any], output_name: str = None) -> bool:
        """Save text settings to JSON file for future use."""
        if not text_settings:
            return False
        
        output_dir = self.paths.get('output_dir', 'data/output')
        os.makedirs(output_dir, exist_ok=True)
        
        if output_name is None:
            output_name = "text_settings.json"
        elif not output_name.endswith('.json'):
            output_name += '.json'
        
        output_path = os.path.join(output_dir, output_name)
        
        try:
            save_data = {
                'mode': text_settings.get('mode'),
                'settings': {
                    'font_size': text_settings.get('font_size'),
                    'color': text_settings.get('color'),
                    'position': text_settings.get('position'),
                    'stroke_color': text_settings.get('stroke_color'),
                    'stroke_width': text_settings.get('stroke_width'),
                    'animation': text_settings.get('animation'),
                    'animation_duration': text_settings.get('animation_duration')
                }
            }
            
            # Add text content
            if text_settings.get('mode') == 'single':
                save_data['text'] = text_settings.get('text', '')
            elif text_settings.get('mode') == 'per_image':
                save_data['texts'] = text_settings.get('texts', [])
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Text settings saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving text settings: {e}")
            return False