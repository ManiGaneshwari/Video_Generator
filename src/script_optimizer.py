"""
Script optimization module for distributing script content across available images.
"""
import os
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
import math

logger = logging.getLogger(__name__)


class ScriptOptimizer:
    """Optimizes script distribution across available images."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.text_config = config.get('text', {})
        self.paths = config.get('paths', {})
    
    def optimize_script_distribution(self, script_lines: List[str], num_images: int) -> Dict[str, Any]:
        """
        Distribute script lines optimally across available images.
        
        Args:
            script_lines: List of script lines to distribute
            num_images: Number of images/slides available
            
        Returns:
            Dictionary with optimized text settings
        """
        if not script_lines:
            logger.warning("No script lines provided")
            return None
        
        # Clean and filter script lines
        cleaned_lines = self._clean_script_lines(script_lines)
        
        if not cleaned_lines:
            logger.warning("No valid script lines after cleaning")
            return None
        
        logger.info(f"Distributing {len(cleaned_lines)} script lines across {num_images} images")
        
        # Choose distribution strategy based on content
        distribution_method = self._choose_distribution_method(cleaned_lines, num_images)
        logger.info(f"Using distribution method: {distribution_method}")
        
        if distribution_method == 'intelligent_grouping':
            distributed_texts = self._intelligent_grouping(cleaned_lines, num_images)
        elif distribution_method == 'semantic_grouping':
            distributed_texts = self._semantic_grouping(cleaned_lines, num_images)
        elif distribution_method == 'balanced_length':
            distributed_texts = self._balanced_length_distribution(cleaned_lines, num_images)
        else:  # even_distribution
            distributed_texts = self._even_distribution(cleaned_lines, num_images)
        
        # Create text settings
        text_settings = self._create_optimized_text_settings(distributed_texts)
        
        logger.info(f"Script optimized: {len(distributed_texts)} slides created")
        for i, text in enumerate(distributed_texts[:3], 1):  # Show first 3 as preview
            preview = text[:100] + "..." if len(text) > 100 else text
            logger.info(f"  Slide {i}: {preview}")
        
        return text_settings
    
    def _clean_script_lines(self, lines: List[str]) -> List[str]:
        """Clean and prepare script lines."""
        cleaned = []
        
        for line in lines:
            # Strip whitespace
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip lines that are just punctuation or numbers
            if re.match(r'^[\d\s\.\-_=]+$', line):
                continue
            
            # Skip very short lines (likely formatting artifacts)
            if len(line) < 3:
                continue
            
            # Clean up formatting
            line = re.sub(r'\s+', ' ', line)  # Multiple spaces to single
            line = re.sub(r'[\r\n]+', ' ', line)  # Remove line breaks within content
            
            cleaned.append(line)
        
        return cleaned
    
    def _choose_distribution_method(self, lines: List[str], num_images: int) -> str:
        """Choose the best distribution method based on content analysis."""
        total_lines = len(lines)
        avg_line_length = sum(len(line) for line in lines) / len(lines) if lines else 0
        
        # Calculate ratios
        lines_per_image = total_lines / num_images if num_images > 0 else 0
        
        # Decision logic
        if lines_per_image <= 2 and avg_line_length > 100:
            # Few long lines - use intelligent grouping
            return 'intelligent_grouping'
        elif lines_per_image > 10 and avg_line_length < 50:
            # Many short lines - use semantic grouping
            return 'semantic_grouping'
        elif total_lines > num_images * 3:
            # Significantly more lines than images - use balanced length
            return 'balanced_length'
        else:
            # Default case
            return 'even_distribution'
    
    def _intelligent_grouping(self, lines: List[str], num_images: int) -> List[str]:
        """Group lines intelligently based on content structure."""
        grouped_texts = []
        
        # Look for natural grouping indicators
        current_group = []
        
        for i, line in enumerate(lines):
            current_group.append(line)
            
            # Check if this line ends a logical group
            should_break = False
            
            # Check for natural breaks
            if line.endswith('.') or line.endswith('!') or line.endswith('?'):
                # Check if next line starts a new topic
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # New paragraph indicators
                    if (next_line.startswith('Now') or next_line.startswith('Next') or
                        next_line.startswith('Then') or next_line.startswith('Finally') or
                        next_line.startswith('In conclusion')):
                        should_break = True
                else:
                    should_break = True  # Last line
            
            # Check group size limits
            total_chars = sum(len(l) for l in current_group)
            if total_chars > 500:  # Max characters per slide
                should_break = True
            
            # Force break if we have too many groups already
            if len(grouped_texts) >= num_images - 1 and i < len(lines) - 1:
                continue  # Don't break, save remaining for last slide
            
            if should_break and current_group:
                grouped_text = ' '.join(current_group)
                grouped_texts.append(grouped_text)
                current_group = []
                
                if len(grouped_texts) >= num_images:
                    break
        
        # Add remaining lines to last group or create new one
        if current_group:
            if grouped_texts and len(grouped_texts) < num_images:
                # Create new group
                grouped_text = ' '.join(current_group)
                grouped_texts.append(grouped_text)
            elif grouped_texts:
                # Add to last group
                grouped_texts[-1] += ' ' + ' '.join(current_group)
        
        # Add remaining lines if we didn't process them all
        remaining_lines = lines[sum(len(group.split()) for group in grouped_texts):]
        if remaining_lines and len(grouped_texts) < num_images:
            grouped_texts.append(' '.join(remaining_lines))
        
        return self._ensure_exact_count(grouped_texts, num_images)
    
    def _semantic_grouping(self, lines: List[str], num_images: int) -> List[str]:
        """Group lines by semantic similarity and topics."""
        # Simple keyword-based grouping
        grouped_texts = []
        
        # Define topic keywords for grouping
        topic_keywords = {
            'introduction': ['introduction', 'welcome', 'hello', 'start', 'begin'],
            'technical': ['technical', 'system', 'process', 'method', 'algorithm'],
            'benefits': ['benefit', 'advantage', 'improve', 'better', 'enhance'],
            'conclusion': ['conclusion', 'summary', 'finally', 'end', 'thank']
        }
        
        # Group lines by topics
        topic_groups = {topic: [] for topic in topic_keywords}
        ungrouped = []
        
        for line in lines:
            line_lower = line.lower()
            assigned = False
            
            for topic, keywords in topic_keywords.items():
                if any(keyword in line_lower for keyword in keywords):
                    topic_groups[topic].append(line)
                    assigned = True
                    break
            
            if not assigned:
                ungrouped.append(line)
        
        # Create balanced groups
        lines_per_group = len(lines) // num_images
        remainder = len(lines) % num_images
        
        all_lines = []
        # Add topic groups first
        for topic, group_lines in topic_groups.items():
            all_lines.extend(group_lines)
        all_lines.extend(ungrouped)
        
        # Distribute evenly
        for i in range(num_images):
            start_idx = i * lines_per_group
            end_idx = start_idx + lines_per_group
            if i < remainder:
                end_idx += 1
            
            group_lines = all_lines[start_idx:end_idx]
            if group_lines:
                grouped_texts.append(' '.join(group_lines))
        
        return self._ensure_exact_count(grouped_texts, num_images)
    
    def _balanced_length_distribution(self, lines: List[str], num_images: int) -> List[str]:
        """Distribute lines to create balanced text length per slide."""
        # Calculate character lengths
        line_lengths = [len(line) for line in lines]
        total_length = sum(line_lengths)
        target_length_per_slide = total_length // num_images
        
        grouped_texts = []
        current_group = []
        current_length = 0
        
        for line in lines:
            line_length = len(line)
            
            # Check if adding this line would exceed target
            if (current_length + line_length > target_length_per_slide and 
                current_group and 
                len(grouped_texts) < num_images - 1):
                
                # Finalize current group
                grouped_texts.append(' '.join(current_group))
                current_group = [line]
                current_length = line_length
            else:
                current_group.append(line)
                current_length += line_length
        
        # Add final group
        if current_group:
            grouped_texts.append(' '.join(current_group))
        
        return self._ensure_exact_count(grouped_texts, num_images)
    
    def _even_distribution(self, lines: List[str], num_images: int) -> List[str]:
        """Distribute lines evenly across images."""
        lines_per_image = len(lines) // num_images
        remainder = len(lines) % num_images
        
        grouped_texts = []
        start_idx = 0
        
        for i in range(num_images):
            # Calculate how many lines for this image
            lines_for_this_image = lines_per_image
            if i < remainder:
                lines_for_this_image += 1
            
            end_idx = start_idx + lines_for_this_image
            group_lines = lines[start_idx:end_idx]
            
            if group_lines:
                grouped_texts.append(' '.join(group_lines))
            else:
                grouped_texts.append('')  # Empty slide if no content
            
            start_idx = end_idx
        
        return grouped_texts
    
    def _ensure_exact_count(self, grouped_texts: List[str], num_images: int) -> List[str]:
        """Ensure we have exactly the right number of text groups."""
        while len(grouped_texts) < num_images:
            if grouped_texts:
                # Split the longest text
                longest_idx = max(range(len(grouped_texts)), key=lambda i: len(grouped_texts[i]))
                longest_text = grouped_texts[longest_idx]
                
                # Split roughly in half
                sentences = longest_text.split('. ')
                if len(sentences) > 1:
                    mid_point = len(sentences) // 2
                    first_half = '. '.join(sentences[:mid_point])
                    second_half = '. '.join(sentences[mid_point:])
                    
                    grouped_texts[longest_idx] = first_half
                    grouped_texts.append(second_half)
                else:
                    # If no sentences, split by words
                    words = longest_text.split()
                    if len(words) > 2:
                        mid_point = len(words) // 2
                        first_half = ' '.join(words[:mid_point])
                        second_half = ' '.join(words[mid_point:])
                        
                        grouped_texts[longest_idx] = first_half
                        grouped_texts.append(second_half)
                    else:
                        grouped_texts.append('')  # Add empty slide
            else:
                grouped_texts.append('')  # Add empty slide
        
        # If we have too many, merge the shortest ones
        while len(grouped_texts) > num_images:
            # Find two shortest adjacent groups to merge
            shortest_pair_idx = 0
            shortest_combined_length = float('inf')
            
            for i in range(len(grouped_texts) - 1):
                combined_length = len(grouped_texts[i]) + len(grouped_texts[i + 1])
                if combined_length < shortest_combined_length:
                    shortest_combined_length = combined_length
                    shortest_pair_idx = i
            
            # Merge the pair
            merged_text = grouped_texts[shortest_pair_idx] + ' ' + grouped_texts[shortest_pair_idx + 1]
            grouped_texts[shortest_pair_idx] = merged_text.strip()
            grouped_texts.pop(shortest_pair_idx + 1)
        
        return grouped_texts
    
    def _create_optimized_text_settings(self, distributed_texts: List[str]) -> Dict[str, Any]:
        """Create text settings for optimized distribution."""
        # Check if sequential animation is enabled in config
        sequential_enabled = self.text_config.get('sequential', {}).get('enabled', False)
        
        # If sequential animation is enabled, preserve line breaks within each slide
        if sequential_enabled:
            # Convert combined texts back to multi-line format for sequential display
            processed_texts = []
            for text in distributed_texts:
                # Split long combined text into readable lines
                lines = self._split_text_into_lines(text)
                # Join with newlines for sequential animation
                processed_text = '\n'.join(lines)
                processed_texts.append(processed_text)
            
            distributed_texts = processed_texts
        
        # Use existing text configuration as base
        text_settings = {
            'mode': 'per_image',
            'texts': distributed_texts,
            'font_size': self.text_config.get('font_size', 80),
            'color': self.text_config.get('color', 'white'),
            'stroke_color': self.text_config.get('stroke_color', 'black'),
            'stroke_width': self.text_config.get('stroke_width', 3),
            'position': self.text_config.get('position', 'center'),
            'animation': self.text_config.get('animation', {}).get('type', 'fade_in'),
            'animation_duration': self.text_config.get('animation', {}).get('duration', 1.5),
            'optimized': True,  # Flag to indicate this was optimized
            'sequential': self.text_config.get('sequential', {})  # Pass through sequential settings
        }
        
        return text_settings
    
    def _split_text_into_lines(self, text: str, max_chars_per_line: int = 80) -> List[str]:
        """Split long text into readable lines for sequential animation."""
        if not text or not text.strip():
            return []
        
        # First split by sentences
        sentences = []
        current_sentence = ""
        
        # Split by common sentence endings
        import re
        sentence_parts = re.split(r'([.!?]+\s*)', text)
        
        for i in range(0, len(sentence_parts), 2):
            sentence = sentence_parts[i]
            if i + 1 < len(sentence_parts):
                sentence += sentence_parts[i + 1]
            
            if sentence.strip():
                sentences.append(sentence.strip())
        
        # If no sentences found, split by commas or length
        if not sentences:
            # Split by commas first
            parts = [part.strip() for part in text.split(',') if part.strip()]
            
            if len(parts) > 1:
                sentences = parts
            else:
                # Split by length as last resort
                words = text.split()
                current_line = ""
                sentences = []
                
                for word in words:
                    if len(current_line + " " + word) <= max_chars_per_line:
                        current_line += " " + word if current_line else word
                    else:
                        if current_line:
                            sentences.append(current_line)
                        current_line = word
                
                if current_line:
                    sentences.append(current_line)
        
        # Ensure each line is not too long
        final_lines = []
        for sentence in sentences:
            if len(sentence) <= max_chars_per_line:
                final_lines.append(sentence)
            else:
                # Split long sentence into multiple lines
                words = sentence.split()
                current_line = ""
                
                for word in words:
                    if len(current_line + " " + word) <= max_chars_per_line:
                        current_line += " " + word if current_line else word
                    else:
                        if current_line:
                            final_lines.append(current_line)
                        current_line = word
                
                if current_line:
                    final_lines.append(current_line)
        
        return final_lines if final_lines else [text]
    
    def analyze_script_distribution(self, script_lines: List[str], num_images: int) -> Dict[str, Any]:
        """Analyze how the script would be distributed."""
        cleaned_lines = self._clean_script_lines(script_lines)
        
        analysis = {
            'original_lines': len(script_lines),
            'cleaned_lines': len(cleaned_lines),
            'available_images': num_images,
            'lines_per_image_avg': len(cleaned_lines) / num_images if num_images > 0 else 0,
            'total_characters': sum(len(line) for line in cleaned_lines),
            'avg_line_length': sum(len(line) for line in cleaned_lines) / len(cleaned_lines) if cleaned_lines else 0,
            'recommended_method': self._choose_distribution_method(cleaned_lines, num_images)
        }
        
        return analysis