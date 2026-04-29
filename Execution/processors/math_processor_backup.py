"""
Math Processor - SOP 03 Implementation
Detects and converts mathematical expressions to LaTeX
"""

import re
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import fitz  # PyMuPDF


@dataclass
class MathExpression:
    """Represents a detected mathematical expression"""
    id: str
    page_num: int
    bbox: Tuple[float, float, float, float]
    expression_type: str  # 'inline', 'display', 'equation_number'
    original_text: str
    latex: str
    confidence: float
    image_base64: Optional[str] = None
    needs_review: bool = False


class MathProcessor:
    """
    Processes mathematical expressions following SOP 03
    """
    
    # Common math symbols that indicate mathematical content
    MATH_SYMBOLS = {
        # Greek letters
        'a': r'\\alpha', 'ß': r'\\beta', '?': r'\\gamma', 'd': r'\\delta',
        'e': r'\\epsilon', '?': r'\\zeta', '?': r'\\eta', '?': r'\\theta',
        '?': r'\\iota', '?': r'\\kappa', '?': r'\\lambda', 'µ': r'\\mu',
        '?': r'\\nu', '?': r'\\xi', 'p': r'\\pi', '?': r'\\rho',
        's': r'\\sigma', 't': r'\\tau', '?': r'\\upsilon', 'f': r'\\phi',
        '?': r'\\chi', '?': r'\\psi', '?': r'\\omega',
        'G': r'\\Gamma', '?': r'\\Delta', 'T': r'\\Theta', '?': r'\\Lambda',
        '?': r'\\Xi', '?': r'\\Pi', 'S': r'\\Sigma', 'F': r'\\Phi',
        '?': r'\\Psi', 'O': r'\\Omega',
        
        # Operators and symbols
        '': r'\\int', '': r'\\iint', '': r'\\iiint',
        '': r'\\sum', '': r'\\prod',
        '': r'\\sqrt', '': r'\\sqrt[3]',
        '': r'\\infty', '': r'\\partial',
        '': r'\\nabla', '': r'\\Delta',
        '': r'\\pm', '': r'\\mp',
        '': r'\\times', '': r'\\div',
        '': r'\\neq', '': r'\\approx',
        '': r'\\leq', '': r'\\geq',
        '': r'\\ll', '': r'\\gg',
        '': r'\\in', '': r'\\notin',
        '': r'\\subset', '': r'\\supset',
        '': r'\\cup', '': r'\\cap',
        '': r'\\wedge', '': r'\\vee',
        '': r'\\rightarrow', '': r'\\leftarrow',
        '': r'\\leftrightarrow',
        '': r'\\Rightarrow', '': r'\\Leftarrow',
        '': r'\\Leftrightarrow',
        '': r'\\forall', '': r'\\exists',
        '': "'", '': "''",
    }
    
    # Subscript and superscript mappings
    SUBSCRIPTS = {
        '': '0', '': '1', '': '2', '': '3', '': '4',
        '': '5', '': '6', '': '7', '': '8', '': '9',
        '?': 'a', '?': 'e', '': 'h', '?': 'i', '?': 'j',
        '': 'k', '': 'l', '': 'm', '': 'n', '?': 'o',
        '': 'p', '?': 'r', '': 's', '': 't', '?': 'u',
        '?': 'v', '?': 'x',
    }
    
    SUPERSCRIPTS = {
        '': '0', '': '1', '': '2', '': '3', '': '4',
        '': '5', '': '6', '': '7', '': '8', '': '9',
        'n': 'n', '?': 'i',
    }
    
    def __init__(self, config: Dict[str, Any] = None, llm_service=None):
        self.config = config or {}
        self.llm_service = llm_service
        self.confidence_threshold = self.config.get('confidence_threshold', 0.8)
        self.use_llm = self.config.get('use_llm', True)
    
    def process(self, pdf_path: str, pages_content: List[Any] = None) -> List[MathExpression]:
        """
        Process PDF to extract and convert mathematical expressions
        
        Args:
            pdf_path: Path to PDF file
            pages_content: Optional pre-extracted page content
            
        Returns:
            List of MathExpression objects
        """
        doc = fitz.open(pdf_path)
        expressions = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_expressions = self._process_page(page, page_num)
            expressions.extend(page_expressions)
        
        doc.close()
        return expressions
    
    def _process_page(self, page: fitz.Page, page_num: int) -> List[MathExpression]:
        """Process a single page for mathematical content"""
        expressions = []
        expr_id = 0
        
        # Get text with detailed info
        text_dict = page.get_text('dict')
        
        for block in text_dict.get('blocks', []):
            if block.get('type') == 0:  # Text block
                block_expressions = self._analyze_text_block(block, page_num, page)
                for expr in block_expressions:
                    expr.id = f'page{page_num}_math{expr_id}'
                    expressions.append(expr)
                    expr_id += 1
        
        return expressions
    
    def _analyze_text_block(self, block: Dict, page_num: int, page: fitz.Page) -> List[MathExpression]:
        """Analyze a text block for mathematical content"""
        expressions = []
        
        for line in block.get('lines', []):
            line_text = ''
            line_bbox = line.get('bbox', [0, 0, 0, 0])
            
            for span in line.get('spans', []):
                span_text = span.get('text', '')
                line_text += span_text
            
            # Check for math content
            if self._contains_math(line_text):
                expr = self._extract_math_expression(line_text, line_bbox, page_num, page)
                if expr:
                    expressions.append(expr)
        
        return expressions
    
    def _contains_math(self, text: str) -> bool:
        """Check if text contains mathematical content"""
        # Check for Greek letters and math symbols
        for symbol in self.MATH_SYMBOLS:
            if symbol in text:
                return True
        
        # Check for subscripts/superscripts
        for sub in self.SUBSCRIPTS:
            if sub in text:
                return True
        for sup in self.SUPERSCRIPTS:
            if sup in text:
                return True
        
        # Check for common math patterns
        math_patterns = [
            r'[a-zA-Z]\s*[=<>]\s*',  # Variable comparison
            r'\d+\s*[+\-*/^]\s*\d+',  # Arithmetic
            r'\\frac\{',  # LaTeX fraction
            r'\\sqrt',  # Square root
            r'\\sum',  # Summation
            r'\\int',  # Integral
            r'\^\{?\d+\}?',  # Exponents
            r'_\{?\d+\}?',  # Subscripts in LaTeX style
        ]
        
        for pattern in math_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _extract_math_expression(self, text: str, bbox: List[float], 
                                  page_num: int, page: fitz.Page) -> Optional[MathExpression]:
        """Extract and convert a mathematical expression"""
        # Determine expression type
        expr_type = self._determine_expression_type(text, bbox, page)
        
        # Convert to LaTeX
        latex, confidence = self._convert_to_latex(text)
        
        # Check if LLM assistance needed
        needs_review = confidence < self.confidence_threshold
        image_base64 = None
        
        if needs_review and self.use_llm and self.llm_service:
            # Capture image of the region for LLM processing
            image_base64 = self._capture_region_image(page, bbox)
            
            # Try LLM conversion
            llm_result = self.llm_service.convert_math_to_latex(image_base64, text)
            if llm_result.get('confidence', 0) > confidence:
                latex = llm_result.get('latex', latex)
                confidence = llm_result.get('confidence', confidence)
                needs_review = confidence < self.confidence_threshold
        
        return MathExpression(
            id='',  # Will be set by caller
            page_num=page_num,
            bbox=tuple(bbox),
            expression_type=expr_type,
            original_text=text,
            latex=latex,
            confidence=confidence,
            image_base64=image_base64,
            needs_review=needs_review
        )
    
    def _determine_expression_type(self, text: str, bbox: List[float], page: fitz.Page) -> str:
        """Determine if expression is inline or display math"""
        page_width = page.rect.width
        block_width = bbox[2] - bbox[0]
        block_center = (bbox[0] + bbox[2]) / 2
        page_center = page_width / 2
        
        # Check for equation number pattern
        if re.search(r'\(\d+\)\s*$', text.strip()) or re.search(r'^\s*\(\d+\)', text.strip()):
            return 'equation_number'
        
        # Display math: centered, wider expressions
        if abs(block_center - page_center) < page_width * 0.1 and block_width > page_width * 0.3:
            return 'display'
        
        # Default to inline
        return 'inline'
    
    def _convert_to_latex(self, text: str) -> Tuple[str, float]:
        """Convert text to LaTeX representation"""
        latex = text
        confidence = 1.0
        conversions_made = 0
        
        # Replace Greek letters and math symbols
        for symbol, latex_cmd in self.MATH_SYMBOLS.items():
            if symbol in latex:
                latex = latex.replace(symbol, latex_cmd)
                conversions_made += 1
        
        # Handle subscripts
        for sub, char in self.SUBSCRIPTS.items():
            if sub in latex:
                latex = latex.replace(sub, f'_{{{char}}}')
                conversions_made += 1
        
        # Handle superscripts
        for sup, char in self.SUPERSCRIPTS.items():
            if sup in latex:
                latex = latex.replace(sup, f'^{{{char}}}')
                conversions_made += 1
        
        # Convert common patterns
        latex = self._convert_patterns(latex)
        
        # Calculate confidence based on complexity
        if conversions_made > 5:
            confidence = 0.7
        elif conversions_made > 10:
            confidence = 0.5
        
        # Lower confidence for complex structures
        if any(pattern in text for pattern in ['', '', '', '']):
            confidence *= 0.9
        
        return latex, confidence
    
    def _convert_patterns(self, text: str) -> str:
        """Convert common mathematical patterns to LaTeX"""
        result = text
        
        # Convert fractions like a/b to \\frac{a}{b}
        # Only for simple cases
        result = re.sub(r'(\w+)/(\w+)', r'\\frac{\1}{\2}', result)
        
        # Convert simple exponents
        result = re.sub(r'(\w)\^(\d+)', r'\1^{\2}', result)
        
        # Convert simple subscripts
        result = re.sub(r'(\w)_(\d+)', r'\1_{\2}', result)
        
        return result
    
    def _capture_region_image(self, page: fitz.Page, bbox: List[float], dpi: int = 300) -> str:
        """Capture an image of a specific region for LLM processing"""
        # Add some padding around the bbox
        padding = 5
        rect = fitz.Rect(
            bbox[0] - padding,
            bbox[1] - padding,
            bbox[2] + padding,
            bbox[3] + padding
        )
        
        # Render at high resolution
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, clip=rect)
        
        # Convert to base64
        img_bytes = pix.tobytes('png')
        return base64.b64encode(img_bytes).decode('utf-8')
    
    def format_for_markdown(self, expression: MathExpression) -> str:
        """Format a math expression for markdown output"""
        latex = expression.latex
        
        if expression.expression_type == 'display':
            return f'"""
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
        
        # Fix common OCR issues
        text = text.replace('?', 'fi')
        text = text.replace('?', 'fl')
        text = text.replace('?', 'ff')
        text = text.replace('?', 'ffi')
        text = text.replace('?', 'ffl')
        
        return text.strip()
    
    def to_plain_text(self, pages: List[PageContent]) -> str:
        """Convert extracted pages to plain text"""
        result = []
        for page in pages:
            page_text = []
            for block in sorted(page.blocks, key=lambda b: b.reading_order):
                page_text.append(block.text)
            result.append('\\n\\n'.join(page_text))
        
        return '\\n\\n---\\n\\n'.join(result){latex}"""
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
        
        # Fix common OCR issues
        text = text.replace('?', 'fi')
        text = text.replace('?', 'fl')
        text = text.replace('?', 'ff')
        text = text.replace('?', 'ffi')
        text = text.replace('?', 'ffl')
        
        return text.strip()
    
    def to_plain_text(self, pages: List[PageContent]) -> str:
        """Convert extracted pages to plain text"""
        result = []
        for page in pages:
            page_text = []
            for block in sorted(page.blocks, key=lambda b: b.reading_order):
                page_text.append(block.text)
            result.append('\\n\\n'.join(page_text))
        
        return '\\n\\n---\\n\\n'.join(result)'
        else:
            return f'$'
    
    def process_text_for_math(self, text: str) -> str:
        """Process text string to convert math symbols to LaTeX"""
        result = text
        
        # Replace symbols
        for symbol, latex_cmd in self.MATH_SYMBOLS.items():
            if symbol in result:
                # Wrap in math delimiters if not already
                result = result.replace(symbol, f'$')
        
        # Merge adjacent math delimiters
        result = re.sub(r'\$\$\s*\$\$', '', result)
        result = re.sub(r'\$\s*\$', '', result)
        
        return result
