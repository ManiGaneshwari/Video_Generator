#!/usr/bin/env python3
"""
Script Analyzer Tool - Analyze how your script will be distributed across images.

Usage:
    python script_analyzer.py [script_file] [num_images]
    
Examples:
    python script_analyzer.py data/input.txt 5
    python script_analyzer.py my_script.txt 10
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.script_optimizer import ScriptOptimizer
from src.utils import load_config


def analyze_script(script_path: str, num_images: int):
    """Analyze script distribution."""
    print(f"\n{'='*60}")
    print("SCRIPT DISTRIBUTION ANALYSIS")
    print(f"{'='*60}")
    
    # Check if file exists
    if not os.path.exists(script_path):
        print(f"Error: Script file not found: {script_path}")
        return
    
    # Load script
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        print(f"Script file: {script_path}")
        print(f"Available images: {num_images}")
        print()
        
        # Load config (use defaults if not found)
        try:
            config = load_config()
        except:
            # Use default config
            config = {
                'text': {
                    'optimization': {
                        'enabled': True,
                        'max_chars_per_slide': 500,
                        'min_words_per_slide': 5,
                        'prefer_sentence_breaks': True
                    }
                },
                'paths': {}
            }
        
        # Analyze distribution
        optimizer = ScriptOptimizer(config)
        analysis = optimizer.analyze_script_distribution(lines, num_images)
        
        print("ANALYSIS RESULTS:")
        print(f"  Original lines: {analysis['original_lines']}")
        print(f"  Cleaned lines: {analysis['cleaned_lines']}")
        print(f"  Total characters: {analysis['total_characters']:,}")
        print(f"  Average line length: {analysis['avg_line_length']:.1f} characters")
        print(f"  Lines per image (avg): {analysis['lines_per_image_avg']:.1f}")
        print(f"  Recommended method: {analysis['recommended_method']}")
        print()
        
        # Show distribution preview
        print("DISTRIBUTION PREVIEW:")
        print("-" * 40)
        
        optimized_settings = optimizer.optimize_script_distribution(lines, num_images)
        
        if optimized_settings and optimized_settings.get('texts'):
            distributed_texts = optimized_settings['texts']
            
            for i, text in enumerate(distributed_texts, 1):
                print(f"\nSlide {i} ({len(text)} chars):")
                preview = text[:200] + "..." if len(text) > 200 else text
                print(f"  {preview}")
        
        print(f"\n{'='*60}")
        print("RECOMMENDATIONS:")
        
        # Provide recommendations
        if analysis['lines_per_image_avg'] > 15:
            print("  • Consider using more images or shorter script lines")
            print("  • Current ratio may result in crowded slides")
        elif analysis['lines_per_image_avg'] < 2:
            print("  • Consider using fewer images or adding more content")
            print("  • Some slides may appear sparse")
        else:
            print("  • Good balance between content and images")
        
        if analysis['avg_line_length'] > 150:
            print("  • Consider breaking long lines into shorter ones")
            print("  • Long lines may require smaller fonts")
        elif analysis['avg_line_length'] < 30:
            print("  • Lines are quite short - good for readability")
        
        # Method-specific recommendations
        method = analysis['recommended_method']
        if method == 'intelligent_grouping':
            print("  • Script will use intelligent grouping based on content structure")
            print("  • Natural breaks and topics will be detected")
        elif method == 'balanced_length':
            print("  • Script will use balanced length distribution")
            print("  • Slides will have similar amounts of text")
        elif method == 'semantic_grouping':
            print("  • Script will group content by topics/themes")
            print("  • Related content will appear together")
        else:
            print("  • Script will use even distribution")
            print("  • Equal number of lines per slide")
        
        print(f"\n{'='*60}")
        
    except Exception as e:
        print(f"Error analyzing script: {e}")


def main():
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python script_analyzer.py [script_file] [num_images]")
        print()
        print("Examples:")
        print("  python script_analyzer.py data/input.txt 5")
        print("  python script_analyzer.py my_script.txt 10")
        sys.exit(1)
    
    script_path = sys.argv[1]
    try:
        num_images = int(sys.argv[2])
        if num_images <= 0:
            raise ValueError("Number of images must be positive")
    except ValueError as e:
        print(f"Error: Invalid number of images: {sys.argv[2]}")
        print("Number of images must be a positive integer")
        sys.exit(1)
    
    analyze_script(script_path, num_images)


if __name__ == "__main__":
    main()