"""
Table Processor - SOP 05 Implementation
Detects and converts tables to markdown format
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import fitz  # PyMuPDF


@dataclass
class TableCell:
    """Represents a single table cell"""
    row: int
    col: int
    content: str
    rowspan: int = 1
    colspan: int = 1
    is_header: bool = False
    alignment: str = 'left'


@dataclass  
class ExtractedTable:
    """Represents an extracted table"""
    id: str
    page_num: int
    bbox: Tuple[float, float, float, float]
    rows: int
    cols: int
    cells: List[List[str]]
    has_header: bool
    has_merged_cells: bool
    caption: str = ''
    markdown: str = ''
    confidence: float = 1.0


class TableProcessor:
    """
    Processes tables from PDF documents following SOP 05
    """
    
    def __init__(self, config: Dict[str, Any] = None, llm_service=None):
        self.config = config or {}
        self.llm_service = llm_service
        self.use_llm = self.config.get('use_llm', True)
        self.prefer_html = self.config.get('prefer_html', False)
    
    def process(self, pdf_path: str) -> List[ExtractedTable]:
        """
        Extract and process all tables from a PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of ExtractedTable objects
        """
        doc = fitz.open(pdf_path)
        tables = []
        
        table_count = 0
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_tables = self._extract_page_tables(page, page_num, table_count)
            tables.extend(page_tables)
            table_count += len(page_tables)
        
        doc.close()
        return tables
    
    def _extract_page_tables(self, page: fitz.Page, page_num: int, 
                             start_count: int) -> List[ExtractedTable]:
        """Extract tables from a single page"""
        tables = []
        
        # Use PyMuPDF's table detection
        detected_tables = page.find_tables()
        
        for idx, table in enumerate(detected_tables):
            try:
                table_id = start_count + idx
                extracted = self._process_table(table, page, page_num, table_id)
                if extracted:
                    tables.append(extracted)
            except Exception as e:
                print(f'Error processing table {idx} on page {page_num}: {e}')
        
        return tables
    
    def _process_table(self, table, page: fitz.Page, page_num: int, 
                       table_id: int) -> Optional[ExtractedTable]:
        """Process a single detected table"""
        # Extract cells
        cells = table.extract()
        
        if not cells or len(cells) == 0:
            return None
        
        rows = len(cells)
        cols = max(len(row) for row in cells) if cells else 0
        
        if rows == 0 or cols == 0:
            return None
        
        # Normalize cells (ensure all rows have same number of columns)
        normalized_cells = []
        for row in cells:
            if len(row) < cols:
                row = list(row) + [''] * (cols - len(row))
            normalized_cells.append([str(cell) if cell else '' for cell in row])
        
        # Detect if first row is header
        has_header = self._detect_header(normalized_cells, table)
        
        # Detect merged cells
        has_merged_cells = self._detect_merged_cells(table)
        
        # Get bounding box
        bbox = tuple(table.bbox) if hasattr(table, 'bbox') else (0, 0, 0, 0)
        
        # Find caption
        caption = self._find_table_caption(page, bbox)
        
        # Convert to markdown
        if has_merged_cells and (self.prefer_html or not self._can_represent_in_markdown(normalized_cells)):
            markdown = self._convert_to_html(normalized_cells, has_header)
            confidence = 0.9
        else:
            markdown = self._convert_to_markdown(normalized_cells, has_header)
            confidence = 1.0
        
        return ExtractedTable(
            id=f'page{page_num}_table{table_id}',
            page_num=page_num,
            bbox=bbox,
            rows=rows,
            cols=cols,
            cells=normalized_cells,
            has_header=has_header,
            has_merged_cells=has_merged_cells,
            caption=caption,
            markdown=markdown,
            confidence=confidence
        )
    
    def _detect_header(self, cells: List[List[str]], table) -> bool:
        """Detect if the first row is a header row"""
        if not cells or len(cells) < 2:
            return False
        
        first_row = cells[0]
        
        # Check if first row has distinct formatting or content
        # Headers often have short text, no numbers, etc.
        header_indicators = 0
        
        for cell in first_row:
            cell = cell.strip()
            # Short text is common in headers
            if len(cell) < 30:
                header_indicators += 1
            # No numbers in headers typically
            if not re.search(r'\\d', cell):
                header_indicators += 1
            # Headers often don't have special characters
            if not re.search(r'[%$@#]', cell):
                header_indicators += 1
        
        # If most cells look like headers
        return header_indicators > len(first_row) * 1.5
    
    def _detect_merged_cells(self, table) -> bool:
        """Detect if table has merged cells"""
        # Check for cells with colspan/rowspan > 1
        if hasattr(table, 'cells'):
            for cell in table.cells:
                if hasattr(cell, 'colspan') and cell.colspan > 1:
                    return True
                if hasattr(cell, 'rowspan') and cell.rowspan > 1:
                    return True
        return False
    
    def _can_represent_in_markdown(self, cells: List[List[str]]) -> bool:
        """Check if table can be represented in basic markdown"""
        if not cells:
            return True
        
        # Check for multi-line cells
        for row in cells:
            for cell in row:
                if '\n' in cell:
                    return False
        
        return True
    
    def _convert_to_markdown(self, cells: List[List[str]], has_header: bool) -> str:
        """Convert table cells to markdown format"""
        if not cells:
            return ''
        
        # Use the widest row to determine column count
        cols = max(len(row) for row in cells)
        
        lines = []
        for i, row in enumerate(cells):
            # Pad short rows so every row has the same column count
            padded = list(row) + [''] * (cols - len(row))
            processed_row = [self._clean_cell_content(cell) for cell in padded]
            line = '| ' + ' | '.join(processed_row) + ' |'
            lines.append(line)
            
            # Markdown tables always need a separator after the first (header) row
            if i == 0:
                separator = '|' + '|'.join(['---'] * cols) + '|'
                lines.append(separator)
        
        return '\n'.join(lines)
    
    def _convert_to_html(self, cells: List[List[str]], has_header: bool) -> str:
        """Convert table cells to HTML format for complex tables"""
        if not cells:
            return ''
        
        lines = ['<table>']
        
        for i, row in enumerate(cells):
            lines.append('  <tr>')
            tag = 'th' if (i == 0 and has_header) else 'td'
            
            for cell in row:
                cell = self._clean_cell_content(cell, for_html=True)
                lines.append(f'    <{tag}>{cell}</{tag}>')
            
            lines.append('  </tr>')
        
        lines.append('</table>')
        return '\n'.join(lines)
    
    def _clean_cell_content(self, content: str, for_html: bool = False) -> str:
        """Clean cell content for markdown/HTML output"""
        if not content:
            return ''
        
        # Replace newlines
        content = content.replace('\n', ' ').replace('\r', '')
        
        # Trim whitespace
        content = ' '.join(content.split())
        
        if not for_html:
            # Escape markdown pipe characters
            content = content.replace('|', '\\|')
        else:
            # Escape HTML characters
            content = content.replace('&', '&amp;')
            content = content.replace('<', '&lt;')
            content = content.replace('>', '&gt;')
        
        return content
    
    def _find_table_caption(self, page: fitz.Page, bbox: Tuple[float, float, float, float]) -> str:
        """Find caption text near a table"""
        if bbox == (0, 0, 0, 0):
            return ''
        
        # Look for text above the table
        search_rect = fitz.Rect(
            bbox[0] - 10,
            bbox[1] - 50,  # Search 50 points above
            bbox[2] + 10,
            bbox[1]
        )
        
        text = page.get_text('text', clip=search_rect).strip()
        
        # Check if it looks like a caption
        caption_patterns = [
            r'^(Table|Tab\.?)\s*\d+',
        ]
        
        lines = text.split('\n')
        for line in reversed(lines):  # Check from bottom up (closest to table)
            line = line.strip()
            if any(re.match(pattern, line, re.IGNORECASE) for pattern in caption_patterns):
                return line
        
        # Also check below the table
        search_rect = fitz.Rect(
            bbox[0] - 10,
            bbox[3],
            bbox[2] + 10,
            bbox[3] + 50
        )
        
        text = page.get_text('text', clip=search_rect).strip()
        lines = text.split('\n')
        for line in lines[:2]:
            line = line.strip()
            if any(re.match(pattern, line, re.IGNORECASE) for pattern in caption_patterns):
                return line
        
        return ''
    
    def format_for_markdown(self, table: ExtractedTable) -> str:
        """Format a table for markdown output"""
        result = ''
        
        if table.caption:
            result += f'**{table.caption}**\n\n'
        
        result += table.markdown
        
        return result
