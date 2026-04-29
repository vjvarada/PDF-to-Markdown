"""
Helper utilities for PDF to Markdown conversion
"""

import os
import re
from pathlib import Path
from typing import Union


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename to be safe for filesystem use
    
    Args:
        filename: Original filename
        max_length: Maximum allowed length
        
    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    
    # Truncate if too long
    if len(sanitized) > max_length:
        name, ext = os.path.splitext(sanitized)
        max_name_length = max_length - len(ext)
        sanitized = name[:max_name_length] + ext
    
    # Handle empty result
    if not sanitized:
        sanitized = 'untitled'
    
    return sanitized


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary
    
    Args:
        path: Directory path
        
    Returns:
        Path object for the directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., '1.5 MB')
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f'{size_bytes:.1f} {unit}'
        size_bytes /= 1024
    return f'{size_bytes:.1f} TB'


def clean_text(text: str) -> str:
    """
    Clean extracted text by normalizing whitespace and removing artifacts
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text
    """
    # Normalize line endings
    text = text.replace('\\r\\n', '\\n').replace('\\r', '\\n')
    
    # Remove excessive whitespace while preserving paragraph breaks
    lines = text.split('\\n')
    cleaned_lines = []
    
    for line in lines:
        # Collapse multiple spaces
        line = re.sub(r' +', ' ', line)
        # Strip leading/trailing whitespace
        line = line.strip()
        cleaned_lines.append(line)
    
    # Rejoin, collapsing multiple blank lines to max 2
    text = '\\n'.join(cleaned_lines)
    text = re.sub(r'\\n{3,}', '\\n\\n', text)
    
    return text.strip()


def slugify(text: str) -> str:
    """
    Convert text to a URL-safe slug
    
    Args:
        text: Text to slugify
        
    Returns:
        URL-safe slug
    """
    # Convert to lowercase
    slug = text.lower()
    
    # Replace spaces and special chars with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    return slug


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Truncate text to a maximum length with suffix
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to append when truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rsplit(' ', 1)[0] + suffix
