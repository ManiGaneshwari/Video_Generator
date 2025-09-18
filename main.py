#!/usr/bin/env python3
"""
Automated Slideshow Generator - Main Entry Point

This script provides the main entry point for creating automated slideshow videos
with configurable settings, eliminating the need for manual intervention.

Usage:
    python main.py [options]
    
Examples:
    python main.py                           # Use default config
    python main.py --config custom.yaml     # Use custom config
    python main.py --output my_video.mp4    # Custom output filename
    python main.py --info                   # Show project info
    python main.py --validate               # Validate setup
"""

import argparse
import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils import load_config, setup_logging, ensure_directories, validate_config
from src.renderer import Renderer


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Automated Slideshow Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           Create slideshow with default settings
  %(prog)s --config custom.yaml     Use custom configuration file
  %(prog)s --output my_video.mp4    Specify output filename
  %(prog)s --info                   Show project information
  %(prog)s --validate               Validate project setup
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        default='config/settings.yaml',
        help='Path to configuration file (default: config/settings.yaml)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output video filename (optional)'
    )
    
    parser.add_argument(
        '--info', '-i',
        action='store_true',
        help='Show project information and exit'
    )
    
    parser.add_argument(
        '--validate', '-v',
        action='store_true',
        help='Validate project setup and exit'
    )
    
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug logging'
    )
    
    return parser.parse_args()


def show_project_info(renderer: Renderer):
    """Display project information."""
    info = renderer.get_project_info()
    
    print("\n" + "="*60)
    print("PROJECT INFORMATION")
    print("="*60)
    
    # Images
    print(f"\nIMAGES:")
    print(f"  Count: {info['images']['count']}")
    print(f"  Directory: {info['images']['directory']}")
    if info['images']['files']:
        print(f"  Sample files: {', '.join(info['images']['files'])}")
        if info['images']['count'] > 5:
            print(f"  ... and {info['images']['count'] - 5} more files")
    else:
        print("  No image files found")
    
    # Audio
    print(f"\nAUDIO:")
    if info['audio']['tts_enabled']:
        print("  Mode: Text-to-Speech (TTS)")
        print("  Audio will be generated from text content")
    else:
        print("  Mode: External audio file")
        if info['audio']['path']:
            print(f"  File: {info['audio']['path']}")
        else:
            print("  No audio file found")
    
    # Text
    print(f"\nTEXT OVERLAYS:")
    print(f"  Enabled: {info['text']['enabled']}")
    print(f"  Mode: {info['text']['mode']}")
    print(f"  Text file exists: {info['text']['file_exists']}")
    if info['text']['file_exists']:
        print(f"  Text file: {info['text']['file_path']}")
    
    # Video
    print(f"\nVIDEO SETTINGS:")
    print(f"  Resolution: {info['video']['resolution']}")
    print(f"  Scaling method: {info['video']['scaling']}")
    
    print("\n" + "="*60)


def validate_project_setup(renderer: Renderer):
    """Validate project setup."""
    print("\n" + "="*60)
    print("PROJECT VALIDATION")
    print("="*60)
    
    is_valid, errors = renderer.validate_project_setup()
    
    if is_valid:
        print("\n✅ Project setup is valid!")
        print("Ready to create slideshow.")
    else:
        print("\n❌ Project setup has issues:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease fix these issues before creating the slideshow.")
    
    print("\n" + "="*60)
    return is_valid


def main():
    """Main entry point."""
    args = parse_arguments()
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Override log level if debug is enabled
        if args.debug:
            config['logging']['level'] = 'DEBUG'
        
        # Validate configuration
        validate_config(config)
        
        # Setup directories and logging
        ensure_directories(config)
        logger = setup_logging(config)
        
        # Create renderer
        renderer = Renderer(config)
        
        # Handle info request
        if args.info:
            show_project_info(renderer)
            return 0
        
        # Handle validation request
        if args.validate:
            is_valid = validate_project_setup(renderer)
            return 0 if is_valid else 1
        
        # Validate setup before creating slideshow
        is_valid, errors = renderer.validate_project_setup()
        if not is_valid:
            logger.error("Project setup validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            logger.error("Please fix these issues before creating the slideshow.")
            return 1
        
        # Create slideshow
        logger.info("Starting automated slideshow generation...")
        logger.info(f"Configuration: {args.config}")
        
        success, output_path = renderer.create_slideshow(args.output)
        
        if success:
            print("\n" + "="*60)
            print("SUCCESS!")
            print("="*60)
            print(f"Slideshow created successfully: {output_path}")
            
            # Show file size
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
                print(f"File size: {file_size:.1f} MB")
            
            print("="*60)
            return 0
        else:
            logger.error("Failed to create slideshow")
            return 1
    
    except FileNotFoundError as e:
        print(f"Error: Configuration file not found: {e}")
        return 1
    
    except ValueError as e:
        print(f"Error: Invalid configuration: {e}")
        return 1
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())