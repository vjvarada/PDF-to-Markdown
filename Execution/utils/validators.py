"""
Validators for PDF to Markdown conversion
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Tuple


def validate_pdf(pdf_path: str) -> Tuple[bool, List[str]]:
    """
    Validate a PDF file before processing
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Tuple of (is_valid, list of errors/warnings)
    """
    errors = []
    path = Path(pdf_path)
    
    # Check if file exists
    if not path.exists():
        errors.append(f'File not found: {pdf_path}')
        return False, errors
    
    # Check if it's a file
    if not path.is_file():
        errors.append(f'Not a file: {pdf_path}')
        return False, errors
    
    # Check extension
    if path.suffix.lower() != '.pdf':
        errors.append(f'File does not have .pdf extension: {path.suffix}')
    
    # Check file size
    size = path.stat().st_size
    if size == 0:
        errors.append('File is empty')
        return False, errors
    
    if size > 500 * 1024 * 1024:  # 500MB
        errors.append('Warning: Large file (>500MB) may take a long time to process')
    
    # Check PDF header
    try:
        with open(path, 'rb') as f:
            header = f.read(8)
            if not header.startswith(b'%PDF-'):
                errors.append('File does not appear to be a valid PDF (missing PDF header)')
                return False, errors
    except Exception as e:
        errors.append(f'Error reading file: {e}')
        return False, errors
    
    return len([e for e in errors if not e.startswith('Warning')]) == 0, errors


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate configuration dictionary
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Tuple of (is_valid, list of errors/warnings)
    """
    errors = []
    
    # Check LLM configuration if present
    if 'llm' in config:
        llm_config = config['llm']
        
        valid_providers = ['openai', 'anthropic', 'google']
        if 'primary_provider' in llm_config:
            if llm_config['primary_provider'] not in valid_providers:
                errors.append(f"Invalid LLM provider: {llm_config['primary_provider']}")
    
    # Check processing configuration
    if 'processing' in config:
        proc_config = config['processing']
        
        # Validate math settings
        if 'math' in proc_config:
            math_config = proc_config['math']
            if 'confidence_threshold' in math_config:
                threshold = math_config['confidence_threshold']
                if not 0 <= threshold <= 1:
                    errors.append('Math confidence_threshold must be between 0 and 1')
        
        # Validate image settings
        if 'images' in proc_config:
            img_config = proc_config['images']
            if 'max_size_kb' in img_config:
                if img_config['max_size_kb'] < 0:
                    errors.append('Image max_size_kb must be positive')
            
            valid_formats = ['png', 'jpg', 'webp']
            if 'output_format' in img_config:
                if img_config['output_format'] not in valid_formats:
                    errors.append(f"Invalid image format: {img_config['output_format']}")
        
        # Validate table settings
        if 'tables' in proc_config:
            table_config = proc_config['tables']
            valid_formats = ['markdown', 'html', 'auto']
            if 'format' in table_config:
                if table_config['format'] not in valid_formats:
                    errors.append(f"Invalid table format: {table_config['format']}")
    
    # Check logging configuration
    if 'logging' in config:
        log_config = config['logging']
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if 'level' in log_config:
            if log_config['level'].upper() not in valid_levels:
                errors.append(f"Invalid log level: {log_config['level']}")
    
    return len(errors) == 0, errors


def validate_output_path(output_path: str) -> Tuple[bool, List[str]]:
    """
    Validate output path
    
    Args:
        output_path: Output directory or file path
        
    Returns:
        Tuple of (is_valid, list of errors/warnings)
    """
    errors = []
    path = Path(output_path)
    
    # Check if parent directory exists or can be created
    parent = path.parent
    if not parent.exists():
        try:
            # Check if we can create it
            parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            errors.append(f'Cannot create output directory: {parent}')
            return False, errors
        except Exception as e:
            errors.append(f'Error creating output directory: {e}')
            return False, errors
    
    # Check write permissions
    test_file = parent / '.write_test'
    try:
        test_file.touch()
        test_file.unlink()
    except PermissionError:
        errors.append(f'No write permission for directory: {parent}')
        return False, errors
    except Exception as e:
        errors.append(f'Error checking write permissions: {e}')
    
    return len(errors) == 0, errors
