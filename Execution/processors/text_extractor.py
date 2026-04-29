"""
Text Extractor - SOP 02 Implementation
Extracts text content from PDF while preserving structure
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import fitz  # PyMuPDF


@dataclass
class TextBlock:
    """Represents a text block with metadata"""
    id: str
    text: str
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    page_num: int
    block_type: str  # 'text', 'header', 'list', 'caption', 'footnote', 'code'
    font_info: Dict[str, Any] = field(default_factory=dict)
    reading_order: int = 0


@dataclass
class PageContent:
    """Content extracted from a single page"""
    page_num: int
    width: float
    height: float
    blocks: List[TextBlock] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)


class TextExtractor:
    """
    Extracts text from PDF documents following SOP 02
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.force_ocr = self.config.get('force_ocr', False)
    
    def extract(self, pdf_path: str) -> List[PageContent]:
        """
        Extract text content from all pages
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of PageContent objects
        """
        doc = fitz.open(pdf_path)
        pages = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_content = self._extract_page(page, page_num)
            pages.append(page_content)
        
        doc.close()
        
        # Post-process: merge split paragraphs, clean text
        pages = self._post_process(pages)
        
        return pages
    
    def _extract_page(self, page: fitz.Page, page_num: int) -> PageContent:
        """Extract content from a single page"""
        page_content = PageContent(
            page_num=page_num,
            width=page.rect.width,
            height=page.rect.height
        )
        
        # Get detailed text with formatting info
        text_dict = page.get_text('dict')
        
        block_id = 0
        for block in text_dict.get('blocks', []):
            if block.get('type') == 0:  # Text block
                text_block = self._process_text_block(block, page_num, block_id)
                if text_block and text_block.text.strip():
                    page_content.blocks.append(text_block)
                    block_id += 1
            elif block.get('type') == 1:  # Image block
                image_info = self._process_image_block(block, page_num)
                page_content.images.append(image_info)
        
        # Extract tables
        tables = page.find_tables()
        for i, table in enumerate(tables):
            table_info = self._process_table(table, page_num, i)
            page_content.tables.append(table_info)
        
        # Determine reading order
        page_content.blocks = self._determine_reading_order(page_content.blocks, page)
        
        return page_content
    
    def _process_text_block(self, block: Dict, page_num: int, block_id: int) -> Optional[TextBlock]:
        """Process a text block and extract metadata"""
        lines = block.get('lines', [])
        if not lines:
            return None
        
        # Collect all text and font info
        text_parts = []
        font_sizes = []
        fonts = []
        is_bold = False
        is_italic = False
        
        for line in lines:
            line_text = ''
            for span in line.get('spans', []):
                span_text = span.get('text', '')
                line_text += span_text
                
                font_sizes.append(span.get('size', 12))
                fonts.append(span.get('font', ''))
                
                flags = span.get('flags', 0)
                if flags & 2 ** 0:  # Bold
                    is_bold = True
                if flags & 2 ** 1:  # Italic
                    is_italic = True
            
            text_parts.append(line_text)
        
        full_text = '\\n'.join(text_parts)
        
        # Determine block type
        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 12
        block_type = self._classify_block_type(full_text, avg_font_size, is_bold, block['bbox'])
        
        return TextBlock(
            id=f'page{page_num}_block{block_id}',
            text=full_text,
            bbox=tuple(block['bbox']),
            page_num=page_num,
            block_type=block_type,
            font_info={
                'avg_size': avg_font_size,
                'fonts': list(set(fonts)),
                'is_bold': is_bold,
                'is_italic': is_italic
            }
        )
    
    def _classify_block_type(self, text: str, font_size: float, 
                            is_bold: bool, bbox: List[float]) -> str:
        """Classify the type of text block"""
        text_stripped = text.strip()
        
        # Check for header (large font, bold, short)
        if font_size > 14 and len(text_stripped) < 200:
            return 'header'
        if is_bold and len(text_stripped) < 100 and '\\n' not in text_stripped:
            return 'header'
        
        # Check for list items
        list_patterns = [
            r'^\\s*[\\-\\*]\\s+',  # Bullet points
            r'^\\s*\\d+[\\.)\\]]\\s+',  # Numbered lists
            r'^\\s*[a-zA-Z][\\.)\\]]\\s+',  # Lettered lists
            r'^\\s*[ivxIVX]+[\\.)\\]]\\s+'  # Roman numerals
        ]
        if any(re.match(pattern, text_stripped) for pattern in list_patterns):
            return 'list'
        
        # Check for caption (starts with Figure/Table, short)
        caption_patterns = [
            r'^\\s*(Figure|Fig\\.?)\\s*\\d+',
            r'^\\s*(Table|Tab\\.?)\\s*\\d+',
            r'^\\s*(Chart|Graph)\\s*\\d+'
        ]
        if any(re.match(pattern, text_stripped, re.IGNORECASE) for pattern in caption_patterns):
            return 'caption'
        
        # Check for code (monospace indicators in font)
        # This is handled more in font analysis
        
        # Check for footnote (small font size, typically)
        if font_size < 9:
            return 'footnote'
        
        return 'text'
    
    def _process_image_block(self, block: Dict, page_num: int) -> Dict[str, Any]:
        """Process an image block"""
        return {
            'page_num': page_num,
            'bbox': block.get('bbox', []),
            'width': block.get('width', 0),
            'height': block.get('height', 0),
        }
    
    def _process_table(self, table, page_num: int, table_id: int) -> Dict[str, Any]:
        """Process a detected table"""
        return {
            'id': f'page{page_num}_table{table_id}',
            'page_num': page_num,
            'bbox': list(table.bbox) if hasattr(table, 'bbox') else [],
            'row_count': table.row_count if hasattr(table, 'row_count') else 0,
            'col_count': table.col_count if hasattr(table, 'col_count') else 0,
            'cells': table.extract() if hasattr(table, 'extract') else []
        }
    
    def _determine_reading_order(self, blocks: List[TextBlock], page: fitz.Page) -> List[TextBlock]:
        """Determine the correct reading order for blocks"""
        if not blocks:
            return blocks
        
        # Check if multi-column layout
        page_width = page.rect.width
        mid_point = page_width / 2
        
        # Separate blocks into potential columns
        left_blocks = []
        right_blocks = []
        center_blocks = []  # Blocks spanning both columns
        
        for block in blocks:
            block_center_x = (block.bbox[0] + block.bbox[2]) / 2
            block_width = block.bbox[2] - block.bbox[0]
            
            # If block is wide (>60% of page), it's likely spanning
            if block_width > page_width * 0.6:
                center_blocks.append(block)
            elif block_center_x < mid_point - 20:
                left_blocks.append(block)
            else:
                right_blocks.append(block)
        
        # Sort each group by vertical position
        def sort_by_y(blks):
            return sorted(blks, key=lambda b: b.bbox[1])
        
        center_blocks = sort_by_y(center_blocks)
        left_blocks = sort_by_y(left_blocks)
        right_blocks = sort_by_y(right_blocks)
        
        # If significant content in both columns, use column-based ordering
        if len(left_blocks) > 2 and len(right_blocks) > 2:
            # Interleave center blocks at appropriate positions
            ordered = []
            left_idx, right_idx, center_idx = 0, 0, 0
            
            while left_idx < len(left_blocks) or right_idx < len(right_blocks):
                # Add any center blocks that should come before current left/right
                while center_idx < len(center_blocks):
                    center_y = center_blocks[center_idx].bbox[1]
                    left_y = left_blocks[left_idx].bbox[1] if left_idx < len(left_blocks) else float('inf')
                    if center_y < left_y:
                        ordered.append(center_blocks[center_idx])
                        center_idx += 1
                    else:
                        break
                
                # Add left column blocks
                if left_idx < len(left_blocks):
                    ordered.append(left_blocks[left_idx])
                    left_idx += 1
            
            # Add remaining center and right blocks
            ordered.extend(center_blocks[center_idx:])
            ordered.extend(right_blocks)
        else:
            # Single column - just sort by y position
            ordered = sort_by_y(blocks)
        
        # Assign reading order
        for i, block in enumerate(ordered):
            block.reading_order = i
        
        return ordered
    
    def _post_process(self, pages: List[PageContent]) -> List[PageContent]:
        """Post-process extracted content"""
        for page in pages:
            for block in page.blocks:
                # Clean up text
                block.text = self._clean_text(block.text)
        
        return pages
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove soft hyphens at line breaks
        text = re.sub(r'-\\n(\\s*)', '', text)
        
        # Normalize whitespace
        text = re.sub(r'[ \\t]+', ' ', text)
        
        # Fix common OCR issues - replace Unicode ligature characters with ASCII equivalents
        # These ligatures (U+FB00–U+FB04) often survive PDF extraction uncombined
        text = text.replace('\ufb01', 'fi')   # ﬁ fi ligature
        text = text.replace('\ufb02', 'fl')   # ﬂ fl ligature
        text = text.replace('\ufb00', 'ff')   # ﬀ ff ligature
        text = text.replace('\ufb03', 'ffi')  # ﬃ ffi ligature
        text = text.replace('\ufb04', 'ffl')  # ﬄ ffl ligature
        
        return text.strip()
    
    def to_plain_text(self, pages: List[PageContent]) -> str:
        """Convert extracted pages to plain text"""
        result = []
        for page in pages:
            page_text = []
            for block in sorted(page.blocks, key=lambda b: b.reading_order):
                page_text.append(block.text)
            result.append('\\n\\n'.join(page_text))
        
        return '\\n\\n---\\n\\n'.join(result)
