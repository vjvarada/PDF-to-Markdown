\"\"\"
PDF Analyzer - SOP 01 Implementation
Analyzes PDF documents to determine structure and processing strategy
\"\"\"

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import fitz  # PyMuPDF


class DocumentComplexity(Enum):
    SIMPLE = 'simple'
    MODERATE = 'moderate'
    COMPLEX = 'complex'
    RESEARCH_PAPER = 'research_paper'


@dataclass
class ContentTypes:
    has_text: bool = False
    has_math: bool = False
    has_images: bool = False
    has_tables: bool = False
    has_code: bool = False
    has_headers: bool = False
    has_footnotes: bool = False
    has_multi_column: bool = False
    has_forms: bool = False


@dataclass
class PDFAssessment:
    file_path: str
    file_size: int
    page_count: int
    is_valid: bool
    is_encrypted: bool
    needs_ocr: bool
    content_types: ContentTypes
    complexity: DocumentComplexity
    recommended_pipeline: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class PDFAnalyzer:
    \"\"\"
    Analyzes PDF documents following SOP 01
    \"\"\"
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
    def analyze(self, pdf_path: str) -> PDFAssessment:
        \"\"\"
        Perform comprehensive analysis of a PDF document
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            PDFAssessment with analysis results
        \"\"\"
        pdf_path = Path(pdf_path)
        warnings = []
        
        # Step 1: File Validation
        if not pdf_path.exists():
            raise FileNotFoundError(f'PDF file not found: {pdf_path}')
        
        file_size = pdf_path.stat().st_size
        
        # Try to open the PDF
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            raise ValueError(f'Could not open PDF: {e}')
        
        is_encrypted = doc.is_encrypted
        if is_encrypted and not doc.authenticate(''):
            warnings.append('PDF is encrypted and requires a password')
            return PDFAssessment(
                file_path=str(pdf_path),
                file_size=file_size,
                page_count=0,
                is_valid=False,
                is_encrypted=True,
                needs_ocr=False,
                content_types=ContentTypes(),
                complexity=DocumentComplexity.SIMPLE,
                recommended_pipeline=[],
                warnings=warnings,
                metadata={}
            )
        
        page_count = len(doc)
        
        # Step 2: Content Type Detection
        content_types = self._detect_content_types(doc)
        
        # Step 3: OCR Requirement Detection
        needs_ocr = self._check_needs_ocr(doc)
        if needs_ocr:
            warnings.append('Document appears to be scanned - OCR will be required')
        
        # Step 4: Complexity Assessment
        complexity = self._assess_complexity(content_types, doc)
        
        # Step 5: Build recommended pipeline
        pipeline = self._build_pipeline(content_types, needs_ocr, complexity)
        
        # Extract metadata
        metadata = self._extract_metadata(doc)
        
        doc.close()
        
        return PDFAssessment(
            file_path=str(pdf_path),
            file_size=file_size,
            page_count=page_count,
            is_valid=True,
            is_encrypted=is_encrypted,
            needs_ocr=needs_ocr,
            content_types=content_types,
            complexity=complexity,
            recommended_pipeline=pipeline,
            warnings=warnings,
            metadata=metadata
        )
    
    def _detect_content_types(self, doc: fitz.Document) -> ContentTypes:
        \"\"\"Detect what types of content are present in the document\"\"\"
        content = ContentTypes()
        
        for page_num in range(min(len(doc), 10)):  # Sample first 10 pages
            page = doc[page_num]
            
            # Check for text
            text = page.get_text()
            if text.strip():
                content.has_text = True
            
            # Check for images
            images = page.get_images()
            if images:
                content.has_images = True
            
            # Check for tables (heuristic: look for grid-like structures)
            tables = page.find_tables()
            if tables:
                content.has_tables = True
            
            # Check for math (look for common math patterns and symbols)
            math_indicators = ['', '', '', '', 'a', 'ß', '?', 'd', '?', '?', 
                             'µ', 's', 'p', '', '', '', '', '', '', '',
                             'frac', 'sqrt', 'sum', 'int', 'lim']
            text_lower = text.lower()
            if any(indicator in text or indicator in text_lower for indicator in math_indicators):
                content.has_math = True
            
            # Check for code blocks (monospace fonts, indentation patterns)
            blocks = page.get_text('dict')['blocks']
            for block in blocks:
                if block.get('type') == 0:  # Text block
                    for line in block.get('lines', []):
                        for span in line.get('spans', []):
                            font = span.get('font', '').lower()
                            if 'mono' in font or 'courier' in font or 'consolas' in font:
                                content.has_code = True
                                break
            
            # Check for headers (larger font sizes)
            if blocks:
                font_sizes = []
                for block in blocks:
                    if block.get('type') == 0:
                        for line in block.get('lines', []):
                            for span in line.get('spans', []):
                                font_sizes.append(span.get('size', 12))
                
                if font_sizes:
                    avg_size = sum(font_sizes) / len(font_sizes)
                    if any(size > avg_size * 1.3 for size in font_sizes):
                        content.has_headers = True
            
            # Check for multi-column layout
            if self._detect_multi_column(page):
                content.has_multi_column = True
            
            # Check for footnotes (small text at bottom)
            if self._detect_footnotes(page):
                content.has_footnotes = True
        
        return content
    
    def _detect_multi_column(self, page: fitz.Page) -> bool:
        \"\"\"Detect if page has multi-column layout\"\"\"
        blocks = page.get_text('dict')['blocks']
        text_blocks = [b for b in blocks if b.get('type') == 0]
        
        if len(text_blocks) < 3:
            return False
        
        # Get x-coordinates of block centers
        x_centers = [(b['bbox'][0] + b['bbox'][2]) / 2 for b in text_blocks]
        
        if not x_centers:
            return False
        
        # Check if blocks cluster in distinct columns
        page_width = page.rect.width
        mid_point = page_width / 2
        
        left_blocks = sum(1 for x in x_centers if x < mid_point - 50)
        right_blocks = sum(1 for x in x_centers if x > mid_point + 50)
        
        # If significant blocks on both sides, likely multi-column
        return left_blocks >= 2 and right_blocks >= 2
    
    def _detect_footnotes(self, page: fitz.Page) -> bool:
        \"\"\"Detect if page has footnotes\"\"\"
        blocks = page.get_text('dict')['blocks']
        page_height = page.rect.height
        
        for block in blocks:
            if block.get('type') == 0:
                bbox = block['bbox']
                # Check if block is in bottom 15% of page
                if bbox[1] > page_height * 0.85:
                    # Check for small font size
                    for line in block.get('lines', []):
                        for span in line.get('spans', []):
                            if span.get('size', 12) < 10:
                                return True
        return False
    
    def _check_needs_ocr(self, doc: fitz.Document) -> bool:
        \"\"\"Check if document needs OCR (scanned PDF)\"\"\"
        # Sample a few pages
        sample_pages = min(5, len(doc))
        text_found = 0
        
        for i in range(sample_pages):
            page = doc[i]
            text = page.get_text().strip()
            
            # If page has images but very little text, likely scanned
            images = page.get_images()
            
            if text and len(text) > 50:
                text_found += 1
        
        # If less than half the sampled pages have substantial text, needs OCR
        return text_found < sample_pages / 2
    
    def _assess_complexity(self, content: ContentTypes, doc: fitz.Document) -> DocumentComplexity:
        \"\"\"Assess overall document complexity\"\"\"
        complexity_score = 0
        
        if content.has_math:
            complexity_score += 2
        if content.has_tables:
            complexity_score += 1
        if content.has_images:
            complexity_score += 1
        if content.has_multi_column:
            complexity_score += 2
        if content.has_code:
            complexity_score += 1
        if content.has_footnotes:
            complexity_score += 1
        
        # Check for research paper indicators
        first_page_text = doc[0].get_text().lower() if len(doc) > 0 else ''
        research_indicators = ['abstract', 'introduction', 'references', 'bibliography',
                              'acknowledgments', 'methodology', 'conclusion']
        research_score = sum(1 for ind in research_indicators if ind in first_page_text)
        
        if research_score >= 3 and content.has_math:
            return DocumentComplexity.RESEARCH_PAPER
        elif complexity_score >= 4:
            return DocumentComplexity.COMPLEX
        elif complexity_score >= 2:
            return DocumentComplexity.MODERATE
        else:
            return DocumentComplexity.SIMPLE
    
    def _build_pipeline(self, content: ContentTypes, needs_ocr: bool, 
                       complexity: DocumentComplexity) -> List[str]:
        \"\"\"Build recommended processing pipeline\"\"\"
        pipeline = ['analyze']  # Always start with analysis
        
        if needs_ocr:
            pipeline.append('ocr')
        
        pipeline.append('extract_text')
        
        if content.has_math:
            pipeline.append('process_math')
        
        if content.has_images:
            pipeline.append('process_images')
        
        if content.has_tables:
            pipeline.append('process_tables')
        
        pipeline.append('assemble_markdown')
        
        if complexity in [DocumentComplexity.COMPLEX, DocumentComplexity.RESEARCH_PAPER]:
            pipeline.append('llm_review')
        
        pipeline.append('validate')
        
        return pipeline
    
    def _extract_metadata(self, doc: fitz.Document) -> Dict[str, Any]:
        \"\"\"Extract PDF metadata\"\"\"
        metadata = doc.metadata or {}
        
        return {
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
            'subject': metadata.get('subject', ''),
            'creator': metadata.get('creator', ''),
            'producer': metadata.get('producer', ''),
            'creation_date': metadata.get('creationDate', ''),
            'modification_date': metadata.get('modDate', ''),
            'keywords': metadata.get('keywords', ''),
        }
    
    def to_dict(self, assessment: PDFAssessment) -> Dict[str, Any]:
        \"\"\"Convert assessment to dictionary\"\"\"
        result = asdict(assessment)
        result['content_types'] = asdict(assessment.content_types)
        result['complexity'] = assessment.complexity.value
        return result
    
    def to_json(self, assessment: PDFAssessment) -> str:
        \"\"\"Convert assessment to JSON string\"\"\"
        return json.dumps(self.to_dict(assessment), indent=2)
