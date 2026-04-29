#!/usr/bin/env python3
"""
PDF to Markdown Converter - CLI Entry Point

Usage:
    python convert.py input.pdf
    python convert.py input.pdf -o output_folder
    python convert.py input.pdf --use-llm
    python convert.py input.pdf --use-llm --provider openai
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime


def print_banner():
    """Print application banner"""
    print("""
==================================================================
           PDF to Markdown Converter                       
     Directives-Operator-Execution Framework               
==================================================================
    """)


def main():
    parser = argparse.ArgumentParser(
        description='Convert PDF documents to Markdown with proper handling of images, math, and tables',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python convert.py document.pdf                    # Basic conversion
  python convert.py document.pdf -o ./output        # Specify output directory
  python convert.py document.pdf --use-llm          # Use LLM assistance
  python convert.py document.pdf --verbose          # Verbose output
  python convert.py document.pdf --no-images        # Skip image extraction
        """
    )
    
    # Required arguments
    parser.add_argument('pdf_path', help='Path to the PDF file to convert')
    
    # Output options
    parser.add_argument('-o', '--output', dest='output_dir',
                        help='Output directory for markdown and assets')
    
    # LLM options
    parser.add_argument('--use-llm', action='store_true',
                        help='Enable LLM assistance for complex conversions')
    parser.add_argument('--provider', choices=['openai', 'anthropic', 'google'],
                        default='openai',
                        help='LLM provider to use (default: openai)')
    
    # Processing options
    parser.add_argument('--no-images', action='store_true',
                        help='Skip image extraction')
    parser.add_argument('--no-tables', action='store_true',
                        help='Skip table processing')
    parser.add_argument('--no-math', action='store_true',
                        help='Skip math expression conversion')
    parser.add_argument('--ocr', action='store_true',
                        help='Force OCR for text extraction')
    
    # Output format options
    parser.add_argument('--include-toc', action='store_true',
                        help='Include table of contents')
    parser.add_argument('--include-metadata', action='store_true',
                        help='Include YAML front matter with metadata')
    
    # Configuration
    parser.add_argument('-c', '--config', dest='config_path',
                        help='Path to configuration YAML file')
    
    # Verbosity
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress all output except errors')
    
    args = parser.parse_args()
    
    # Print banner unless quiet mode
    if not args.quiet:
        print_banner()
    
    # Validate input file
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f'Error: PDF file not found: {pdf_path}')
        sys.exit(1)
    
    if not pdf_path.suffix.lower() == '.pdf':
        print(f'Warning: File does not have .pdf extension: {pdf_path}')
    
    # Setup output directory
    output_dir = Path(args.output_dir) if args.output_dir else Path('./output')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build configuration
    config = build_config(args)

    # Validate configuration before doing any heavy work
    try:
        from Execution.utils.validators import validate_config, validate_pdf
    except ImportError as e:
        print(f'Error: Cannot import validators - {e}')
        sys.exit(1)

    cfg_valid, cfg_errors = validate_config(config)
    if not cfg_valid:
        print('Error: Invalid configuration:')
        for err in cfg_errors:
            print(f'  - {err}')
        sys.exit(1)
    elif cfg_errors and not args.quiet:
        for warning in cfg_errors:
            print(f'Warning: {warning}')

    # Deep-validate the PDF (header check, size, readability)
    pdf_valid, pdf_errors = validate_pdf(str(pdf_path))
    if not pdf_valid:
        print('Error: PDF validation failed:')
        for err in pdf_errors:
            print(f'  - {err}')
        sys.exit(1)
    elif pdf_errors and not args.quiet:
        for warning in pdf_errors:
            print(f'Warning: {warning}')

    if not args.quiet:
        print(f'Input:  {pdf_path.absolute()}')
        print(f'Output: {output_dir.absolute()}')
        print(f'LLM:    {"Enabled (" + args.provider + ")" if args.use_llm else "Disabled"}')
        print('-' * 60)
    
    try:
        # Import converter
        from Execution.pdf_converter import PDFToMarkdownConverter
        
        # Initialize LLM service if requested
        llm_service = None
        if args.use_llm:
            llm_service = initialize_llm_service(args.provider, args.quiet)
        
        # Create converter and run
        start_time = datetime.now()
        
        converter = PDFToMarkdownConverter(config, llm_service)
        document = converter.convert(str(pdf_path), str(output_dir))
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Output results - self-contained in document folder
        doc_folder = output_dir / pdf_path.stem
        output_file = doc_folder / f'{pdf_path.stem}.md'
        
        if not args.quiet:
            print('-' * 60)
            print(f'Conversion complete!')
            print(f'  Output folder: {doc_folder}')
            print(f'  Main file:     {output_file.name}')
            print(f'  Time taken:    {duration:.2f} seconds')
            if output_file.exists():
                print(f'  File size:     {output_file.stat().st_size / 1024:.2f} KB')
            print(f'\nOutput contents:')
            for item in doc_folder.iterdir():
                if item.is_dir():
                    print(f'    {item.name}/')
                else:
                    print(f'    {item.name}')
        
        return 0
        
    except ImportError as e:
        print(f'Error: Missing dependency - {e}')
        print('Please install dependencies: pip install -r requirements.txt')
        sys.exit(1)
    except FileNotFoundError as e:
        print(f'Error: File not found - {e}')
        sys.exit(1)
    except ValueError as e:
        print(f'Error: Invalid input - {e}')
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f'Error during conversion of {pdf_path}: {type(e).__name__}: {e}')
        if args.verbose:
            traceback.print_exc()
        else:
            print('Run with --verbose for full traceback.')
        sys.exit(1)


def build_config(args) -> dict:
    """Build configuration dictionary from arguments"""
    import yaml
    
    # Start with default or provided config
    config = {}
    if args.config_path and Path(args.config_path).exists():
        with open(args.config_path) as f:
            config = yaml.safe_load(f) or {}
    
    # Override with command line arguments
    if args.no_images:
        config.setdefault('images', {})['enabled'] = False
    
    if args.no_tables:
        config.setdefault('tables', {})['enabled'] = False
    
    if args.no_math:
        config.setdefault('math', {})['enabled'] = False
    
    if args.ocr:
        config.setdefault('ocr', {})['force'] = True
    
    if args.include_toc:
        config.setdefault('output', {})['include_toc'] = True
    
    if args.include_metadata:
        config.setdefault('output', {})['include_front_matter'] = True
    
    # Logging configuration
    if args.verbose:
        config.setdefault('logging', {})['level'] = 'DEBUG'
    elif args.quiet:
        config.setdefault('logging', {})['level'] = 'ERROR'
    
    return config


def initialize_llm_service(provider: str, quiet: bool = False):
    """Initialize the LLM service"""
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        from Operator.llm_service import LLMService
        
        if not quiet:
            print(f'Initializing LLM service ({provider})...')
        
        service = LLMService(provider=provider)
        return service
    except Exception as e:
        if not quiet:
            print(f'Warning: Could not initialize LLM service: {e}')
        return None


if __name__ == '__main__':
    sys.exit(main())
