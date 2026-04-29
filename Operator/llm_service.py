"""
LLM Service Module for PDF to Markdown Agent
Handles all LLM interactions for the Operator role
"""

import os
import base64
import json
from typing import Optional, Dict, Any, List
from pathlib import Path
import yaml
from openai import OpenAI
from anthropic import Anthropic

import time
import logging

logger = logging.getLogger(__name__)

# Errors that are safe to retry (transient network / rate-limit issues)
_RETRYABLE_EXCEPTIONS = (ConnectionError, TimeoutError, OSError)

def _retry(fn, max_attempts: int = 3, base_delay: float = 1.0):
    """Call fn with exponential back-off on transient errors.  Raises the last
    exception if all attempts fail."""
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(max_attempts):
        try:
            return fn()
        except _RETRYABLE_EXCEPTIONS as exc:
            last_exc = exc
        except Exception as exc:
            exc_str = str(exc).lower()
            rate_limited = any(
                kw in exc_str
                for kw in ("rate limit", "rate_limit", "429", "too many requests", "overloaded")
            )
            if not rate_limited:
                raise
            last_exc = exc
        if attempt < max_attempts - 1:
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "LLM call failed (attempt %d/%d): %s – retrying in %.1fs",
                attempt + 1, max_attempts, last_exc, delay,
            )
            time.sleep(delay)
    raise last_exc


class LLMService:
    """Service class for LLM interactions"""
    
    def __init__(self, config_path: str = None):
        """Initialize LLM service with configuration"""
        if config_path is None:
            config_path = Path(__file__).parent / 'agent_config.yaml'
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.llm_config = self.config.get('llm', {})
        self._init_clients()
    
    def _init_clients(self):
        """Initialize LLM API clients"""
        self.openai_client = None
        self.anthropic_client = None
        
        # Initialize OpenAI client if API key is available
        if os.getenv('OPENAI_API_KEY'):
            self.openai_client = OpenAI()
        
        # Initialize Anthropic client if API key is available
        if os.getenv('ANTHROPIC_API_KEY'):
            self.anthropic_client = Anthropic()
    
    def _get_client_and_model(self, task_type: str = 'primary'):
        """Get appropriate client and model for task type"""
        llm_settings = self.llm_config.get(task_type, self.llm_config.get('primary', {}))
        provider = llm_settings.get('provider', 'openai')
        model = llm_settings.get('model', 'gpt-4o-mini')
        
        if provider == 'openai' and self.openai_client:
            return self.openai_client, model, 'openai'
        elif provider == 'anthropic' and self.anthropic_client:
            return self.anthropic_client, model, 'anthropic'
        elif self.openai_client:
            return self.openai_client, 'gpt-4o-mini', 'openai'
        else:
            raise ValueError('No LLM client available. Please set API keys.')
    
    def convert_math_to_latex(self, image_base64: str, context: str = '') -> Dict[str, Any]:
        """
        Convert mathematical expression image to LaTeX
        
        Args:
            image_base64: Base64 encoded image of the equation
            context: Surrounding text context for better interpretation
            
        Returns:
            Dict with 'latex' string and 'confidence' score
        """
        client, model, provider = self._get_client_and_model('vision')
        
        prompt = f"""Analyze this mathematical expression image and convert it to LaTeX.

Context from surrounding text: {context if context else 'None provided'}

Instructions:
1. Identify all mathematical symbols, operators, and structures
2. Convert to proper LaTeX syntax
3. Use standard LaTeX packages (amsmath, amssymb) conventions
4. For fractions use \\frac{{}}{{}}
5. For subscripts use _{{}}
6. For superscripts use ^{{}}
7. For Greek letters use proper commands (\\alpha, \\beta, etc.)

Return ONLY a JSON object with:
- "latex": The LaTeX representation (without dollar sign delimiters)
- "confidence": A number 0-1 indicating your confidence
- "notes": Any ambiguities or assumptions made
"""
        
        if provider == 'openai':
            response = _retry(lambda: client.chat.completions.create(
                model=model,
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': prompt},
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:image/png;base64,{image_base64}'
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1024,
                temperature=0.1
            ))
            result_text = response.choices[0].message.content
        else:
            # Anthropic
            response = _retry(lambda: client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'image',
                                'source': {
                                    'type': 'base64',
                                    'media_type': 'image/png',
                                    'data': image_base64
                                }
                            },
                            {'type': 'text', 'text': prompt}
                        ]
                    }
                ]
            ))
            result_text = response.content[0].text
        
        # Parse JSON response
        try:
            # Try to extract JSON from response
            if '`json' in result_text:
                json_str = result_text.split('`json')[1].split('`')[0]
            elif '`' in result_text:
                json_str = result_text.split('`')[1].split('`')[0]
            else:
                json_str = result_text
            return json.loads(json_str.strip())
        except:
            return {
                'latex': result_text.strip(),
                'confidence': 0.5,
                'notes': 'Could not parse structured response'
            }
    
    def generate_image_description(self, image_base64: str, image_type: str = 'figure') -> str:
        """
        Generate alt text description for an image
        
        Args:
            image_base64: Base64 encoded image
            image_type: Type of image (figure, chart, diagram, photo)
            
        Returns:
            Descriptive alt text string
        """
        client, model, provider = self._get_client_and_model('vision')
        
        prompt = f"""Generate a concise but descriptive alt text for this {image_type}.

Guidelines:
1. Describe the main content and purpose
2. For charts/graphs: mention type, axes, and key trends
3. For diagrams: describe structure and relationships
4. For figures: explain what is being shown
5. Keep it under 150 words but be comprehensive
6. Focus on information that would be useful for someone who cannot see the image

Return only the alt text description, no formatting or quotes.
"""
        
        if provider == 'openai':
            response = _retry(lambda: client.chat.completions.create(
                model=model,
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': prompt},
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:image/png;base64,{image_base64}'
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.3
            ))
            return response.choices[0].message.content.strip()
        else:
            response = _retry(lambda: client.messages.create(
                model=model,
                max_tokens=500,
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'image',
                                'source': {
                                    'type': 'base64',
                                    'media_type': 'image/png',
                                    'data': image_base64
                                }
                            },
                            {'type': 'text', 'text': prompt}
                        ]
                    }
                ]
            ))
            return response.content[0].text.strip()
    
    def reconstruct_table(self, table_image_base64: str, partial_text: str = '') -> Dict[str, Any]:
        """
        Reconstruct table structure from image
        
        Args:
            table_image_base64: Base64 encoded table image
            partial_text: Any text already extracted from the table
            
        Returns:
            Dict with 'markdown' table and 'confidence' score
        """
        client, model, provider = self._get_client_and_model('vision')
        
        prompt = f"""Analyze this table image and convert it to Markdown format.

Partially extracted text (may be incomplete or incorrectly ordered):
{partial_text if partial_text else 'None'}

Instructions:
1. Identify all rows and columns
2. Determine header row(s)
3. Handle any merged cells by noting them
4. Preserve numerical precision
5. Use proper Markdown table syntax

Return a JSON object with:
- "markdown": The Markdown table
- "has_merged_cells": boolean
- "confidence": 0-1 confidence score
- "notes": Any issues or assumptions
"""
        
        if provider == 'openai':
            response = _retry(lambda: client.chat.completions.create(
                model=model,
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': prompt},
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:image/png;base64,{table_image_base64}'
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2048,
                temperature=0.1
            ))
            result_text = response.choices[0].message.content
        else:
            response = _retry(lambda: client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'image',
                                'source': {
                                    'type': 'base64',
                                    'media_type': 'image/png',
                                    'data': table_image_base64
                                }
                            },
                            {'type': 'text', 'text': prompt}
                        ]
                    }
                ]
            ))
            result_text = response.content[0].text
        
        try:
            if '`json' in result_text:
                json_str = result_text.split('`json')[1].split('`')[0]
            elif '`' in result_text:
                json_str = result_text.split('`')[1].split('`')[0]
            else:
                json_str = result_text
            return json.loads(json_str.strip())
        except:
            return {
                'markdown': result_text,
                'has_merged_cells': False,
                'confidence': 0.5,
                'notes': 'Could not parse structured response'
            }
    
    def improve_markdown(self, markdown_content: str, issues: List[str] = None) -> str:
        """
        Review and improve markdown content
        
        Args:
            markdown_content: Current markdown content
            issues: List of known issues to address
            
        Returns:
            Improved markdown content
        """
        client, model, provider = self._get_client_and_model('primary')
        
        issues_text = '\\n'.join(f'- {issue}' for issue in issues) if issues else 'None specified'
        
        prompt = f"""Review and improve this Markdown content converted from a PDF.

Known issues to address:
{issues_text}

Improvements to make:
1. Fix any formatting inconsistencies
2. Ensure proper heading hierarchy
3. Fix broken lists or tables
4. Improve readability while preserving content
5. Ensure math expressions are properly delimited
6. Fix any obvious OCR errors if present

Content to improve:
---
{markdown_content[:8000]}  # Truncate for token limits
---

Return the improved Markdown content only, no explanations.
"""
        
        if provider == 'openai':
            response = client.chat.completions.create(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=4096,
                temperature=0.1
            )
            return response.choices[0].message.content
        else:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{'role': 'user', 'content': prompt}]
            )
            return response.content[0].text
    
    def determine_reading_order(self, page_layout: Dict[str, Any]) -> List[int]:
        """
        Determine correct reading order for multi-column layouts
        
        Args:
            page_layout: Dictionary describing page layout with block positions
            
        Returns:
            List of block indices in reading order
        """
        client, model, provider = self._get_client_and_model('fallback')
        
        prompt = f"""Given this page layout with text blocks, determine the correct reading order.

Page layout (blocks with positions):
{json.dumps(page_layout, indent=2)}

Consider:
1. Multi-column layouts (left to right, then top to bottom within columns)
2. Headers that span columns
3. Captions near figures
4. Footnotes at page bottom

Return a JSON array of block indices in the correct reading order.
Example: [0, 2, 1, 3, 4]
"""
        
        if provider == 'openai':
            response = client.chat.completions.create(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=500,
                temperature=0.1
            )
            result_text = response.choices[0].message.content
        else:
            response = client.messages.create(
                model=model,
                max_tokens=500,
                messages=[{'role': 'user', 'content': prompt}]
            )
            result_text = response.content[0].text
        
        try:
            # Extract JSON array from response
            import re
            match = re.search(r'\[[\d,\s]+\]', result_text)
            if match:
                return json.loads(match.group())
        except:
            pass
        
        # Fallback: return original order
        return list(range(len(page_layout.get('blocks', []))))


# Convenience function for quick access
def get_llm_service(config_path: str = None) -> LLMService:
    """Get a configured LLM service instance"""
    return LLMService(config_path)
