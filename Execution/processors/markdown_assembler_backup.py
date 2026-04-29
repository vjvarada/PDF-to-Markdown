"""
Markdown Assembler - SOP 06 Implementation
Assembles all processed content into a cohesive markdown document
"""

import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class MarkdownDocument:
    """Represents the final markdown document"""
    title: str
    content: str
    metadata: Dict[str, Any]
    images: List[str]
    toc: List[Dict[str, Any]]


class MarkdownAssembler:
    """
    Assembles markdown output following SOP 06
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.include_metadata = self.config.get('include_metadata', True)
        self.include_toc = self.config.get('include_toc', True)
        self.image_folder = self.config.get('image_folder', 'images')
    
    def assemble(self, 
                 pages_content: List[Any],
                 math_expressions: List[Any] = None,
                 images: List[Any] = None,
                 tables: List[Any] = None,
                 pdf_metadata: Dict[str, Any] = None,
                 source_file: str = '') -> MarkdownDocument:
        """
        Assemble all content into a markdown document
        
        Args:
            pages_content: Extracted page content
            math_expressions: Processed math expressions
            images: Extracted images
            tables: Extracted tables
            pdf_metadata: Original PDF metadata
            source_file: Source PDF filename
            
        Returns:
            MarkdownDocument object
        """
        # Build document structure
        sections = self._build_sections(pages_content)
        
        # Generate table of contents
        toc = self._generate_toc(sections)
        
        # Assemble content
        content_parts = []
        
        # Add YAML front matter
        if self.include_metadata:
            front_matter = self._build_front_matter(pdf_metadata, source_file)
            content_parts.append(front_matter)
        
        # Add title
        title = self._extract_title(sections, pdf_metadata)
        if title:
            content_parts.append(f'# {title}\\n')
        
        # Add TOC
        if self.include_toc and len(toc) > 2:
            content_parts.append(self._format_toc(toc))
        
        # Add main content
        main_content = self._assemble_content(
            sections, math_expressions, images, tables
        )
        content_parts.append(main_content)
        
        # Combine all parts
        full_content = '\\n\\n'.join(content_parts)
        
        # Post-process
        full_content = self._post_process(full_content)
        
        # Build metadata
        metadata = {
            'title': title,
            'source': source_file,
            'converted': datetime.now().isoformat(),
            'pages': len(pages_content),
            'images_count': len(images) if images else 0,
            'tables_count': len(tables) if tables else 0,
            **(pdf_metadata or {})
        }
        
        return MarkdownDocument(
            title=title,
            content=full_content,
            metadata=metadata,
            images=[img.file_path for img in images] if images else [],
            toc=toc
        )
    
    def _build_sections(self, pages_content: List[Any]) -> List[Dict[str, Any]]:
        """Build document sections from page content"""
        sections = []
        current_section = None
        
        for page in pages_content:
            for block in sorted(page.blocks, key=lambda b: b.reading_order):
                if block.block_type == 'header':
                    # Determine heading level based on font size
                    level = self._determine_heading_level(block)
                    
                    if current_section:
                        sections.append(current_section)
                    
                    current_section = {
                        'level': level,
                        'title': block.text.strip(),
                        'content': [],
                        'page': page.page_num
                    }
                elif current_section:
                    current_section['content'].append(block)
                else:
                    # Content before first header
                    if not sections:
                        current_section = {
                            'level': 0,
                            'title': '',
                            'content': [block],
                            'page': page.page_num
                        }
        
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def _determine_heading_level(self, block: Any) -> int:
        """Determine the heading level based on font size"""
        font_size = block.font_info.get('avg_size', 12)
        
        if font_size >= 20:
            return 1
        elif font_size >= 16:
            return 2
        elif font_size >= 14:
            return 3
        elif font_size >= 12 and block.font_info.get('is_bold'):
            return 4
        else:
            return 5
    
    def _generate_toc(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate table of contents from sections"""
        toc = []
        
        for section in sections:
            if section['title'] and section['level'] > 0:
                toc.append({
                    'title': section['title'],
                    'level': section['level'],
                    'anchor': self._create_anchor(section['title'])
                })
        
        return toc
    
    def _create_anchor(self, title: str) -> str:
        """Create a URL-safe anchor from a title"""
        anchor = title.lower()
        anchor = re.sub(r'[^a-z0-9\\s-]', '', anchor)
        anchor = re.sub(r'\\s+', '-', anchor)
        return anchor
    
    def _format_toc(self, toc: List[Dict[str, Any]]) -> str:
        """Format table of contents as markdown"""
        lines = ['## Table of Contents\\n']
        
        for item in toc:
            indent = '  ' * (item['level'] - 1)
            lines.append(f"{indent}- [{item['title']}](#{item['anchor']})")
        
        return '\\n'.join(lines)
    
    def _extract_title(self, sections: List[Dict[str, Any]], 
                       pdf_metadata: Dict[str, Any]) -> str:
        """Extract document title"""
        # Try PDF metadata first
        if pdf_metadata and pdf_metadata.get('title'):
            return pdf_metadata['title']
        
        # Find first level-1 heading
        for section in sections:
            if section['level'] == 1 and section['title']:
                return section['title']
        
        # Find any heading
        for section in sections:
            if section['title']:
                return section['title']
        
        return 'Untitled Document'
    
    def _build_front_matter(self, pdf_metadata: Dict[str, Any], 
                            source_file: str) -> str:
        """Build YAML front matter"""
        lines = ['---']
        
        if pdf_metadata:
            if pdf_metadata.get('title'):
                lines.append(f"title: \\"{pdf_metadata['title']}\\"")
            if pdf_metadata.get('author'):
                lines.append(f"author: \\"{pdf_metadata['author']}\\"")
            if pdf_metadata.get('subject'):
                lines.append(f"subject: \\"{pdf_metadata['subject']}\\"")
        
        lines.append(f'source: "{source_file}"')
        lines.append(f'converted: "{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"')
        lines.append('---')
        
        return '\\n'.join(lines)
    
    def _assemble_content(self,
                          sections: List[Dict[str, Any]],
                          math_expressions: List[Any],
                          images: List[Any],
                          tables: List[Any]) -> str:
        """Assemble the main content"""
        content_parts = []
        
        # Create lookup maps for images and tables by page
        images_by_page = {}
        if images:
            for img in images:
                page = img.page_num
                if page not in images_by_page:
                    images_by_page[page] = []
                images_by_page[page].append(img)
        
        tables_by_page = {}
        if tables:
            for table in tables:
                page = table.page_num
                if page not in tables_by_page:
                    tables_by_page[page] = []
                tables_by_page[page].append(table)
        
        current_page = -1
        
        for section in sections:
            # Add heading
            if section['title'] and section['level'] > 0:
                heading = '#' * section['level'] + ' ' + section['title']
                content_parts.append(heading)
            
            # Process content blocks
            for block in section['content']:
                # Check if we've moved to a new page - insert images/tables
                if block.page_num != current_page:
                    # Insert any images from previous page
                    if current_page in images_by_page:
                        for img in images_by_page[current_page]:
                            img_md = self._format_image(img)
                            content_parts.append(img_md)
                        del images_by_page[current_page]
                    
                    # Insert any tables from previous page
                    if current_page in tables_by_page:
                        for table in tables_by_page[current_page]:
                            table_md = self._format_table(table)
                            content_parts.append(table_md)
                        del tables_by_page[current_page]
                    
                    current_page = block.page_num
                
                # Format block based on type
                if block.block_type == 'list':
                    content_parts.append(self._format_list(block.text))
                elif block.block_type == 'code':
                    content_parts.append(self._format_code(block.text))
                elif block.block_type == 'caption':
                    content_parts.append(f'*{block.text}*')
                elif block.block_type == 'footnote':
                    content_parts.append(f'[^{block.text}]')
                else:
                    # Regular text
                    content_parts.append(block.text)
        
        # Add remaining images and tables
        for page_images in images_by_page.values():
            for img in page_images:
                content_parts.append(self._format_image(img))
        
        for page_tables in tables_by_page.values():
            for table in page_tables:
                content_parts.append(self._format_table(table))
        
        return '\\n\\n'.join(content_parts)
    
    def _format_image(self, image: Any) -> str:
        """Format an image for markdown"""
        alt_text = image.alt_text or f'{image.image_type.capitalize()}'
        path = f'{self.image_folder}/{Path(image.file_path).name}'
        
        result = f'![{alt_text}]({path})'
        
        if image.caption:
            result += f'\\n\\n*{image.caption}*'
        
        return result
    
    def _format_table(self, table: Any) -> str:
        """Format a table for markdown"""
        result = ''
        
        if table.caption:
            result += f'**{table.caption}**\\n\\n'
        
        result += table.markdown
        
        return result
    
    def _format_list(self, text: str) -> str:
        """Format list items"""
        lines = text.split('\\n')
        formatted = []
        
        for line in lines:
            line = line.strip()
            if line:
                # Ensure proper list marker
                if not re.match(r'^[-*]\\s', line) and not re.match(r'^\\d+\\.\\s', line):
                    line = f'- {line}'
                formatted.append(line)
        
        return '\\n'.join(formatted)
    
    def _format_code(self, text: str) -> str:
        """Format code blocks"""
        return f'`\\n{text}\\n`'
    
    def _post_process(self, content: str) -> str:
        """Post-process the assembled content"""
        # Fix multiple blank lines
        content = re.sub(r'\\n{4,}', '\\n\\n\\n', content)
        
        # Fix spacing around headers
        content = re.sub(r'(\\n#{1,6}\\s)', r'\\n\\1', content)
        
        # Ensure proper line endings
        content = content.replace('\\r\\n', '\\n')
        
        # Remove trailing whitespace from lines
        lines = content.split('\\n')
        lines = [line.rstrip() for line in lines]
        content = '\\n'.join(lines)
        
        return content.strip()
    
    def save(self, document: MarkdownDocument, output_path: str) -> None:
        """Save the markdown document to file"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(document.content)
        
        # Save metadata
        metadata_path = output_path.with_suffix('.meta.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(document.metadata, f, indent=2)
