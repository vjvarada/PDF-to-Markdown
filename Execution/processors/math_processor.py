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
    
    # Common math symbols that indicate mathematical content (using Unicode code points)
    MATH_SYMBOLS = {
        # Greek letters (lowercase)
        '\u03b1': r'\alpha',    # α
        '\u03b2': r'\beta',     # β
        '\u03b3': r'\gamma',    # γ
        '\u03b4': r'\delta',    # δ
        '\u03b5': r'\epsilon',  # ε
        '\u03b6': r'\zeta',     # ζ
        '\u03b7': r'\eta',      # η
        '\u03b8': r'\theta',    # θ
        '\u03b9': r'\iota',     # ι
        '\u03ba': r'\kappa',    # κ
        '\u03bb': r'\lambda',   # λ
        '\u03bc': r'\mu',       # μ
        '\u03bd': r'\nu',       # ν
        '\u03be': r'\xi',       # ξ
        '\u03c0': r'\pi',       # π
        '\u03c1': r'\rho',      # ρ
        '\u03c3': r'\sigma',    # σ
        '\u03c4': r'\tau',      # τ
        '\u03c5': r'\upsilon',  # υ
        '\u03c6': r'\phi',      # φ
        '\u03c7': r'\chi',      # χ
        '\u03c8': r'\psi',      # ψ
        '\u03c9': r'\omega',    # ω
        
        # Greek letters (uppercase)
        '\u0393': r'\Gamma',    # Γ
        '\u0394': r'\Delta',    # Δ
        '\u0398': r'\Theta',    # Θ
        '\u039b': r'\Lambda',   # Λ
        '\u039e': r'\Xi',       # Ξ
        '\u03a0': r'\Pi',       # Π
        '\u03a3': r'\Sigma',    # Σ
        '\u03a6': r'\Phi',      # Φ
        '\u03a8': r'\Psi',      # Ψ
        '\u03a9': r'\Omega',    # Ω
        
        # Mathematical operators
        '\u222b': r'\int',      # ∫
        '\u222c': r'\iint',     # ∬
        '\u222d': r'\iiint',    # ∭
        '\u2211': r'\sum',      # ∑
        '\u220f': r'\prod',     # ∏
        '\u221a': r'\sqrt',     # √
        '\u221e': r'\infty',    # ∞
        '\u2202': r'\partial',  # ∂
        '\u2207': r'\nabla',    # ∇
        '\u00b1': r'\pm',       # ±
        '\u2213': r'\mp',       # ∓
        '\u00d7': r'\times',    # ×
        '\u00f7': r'\div',      # ÷
        '\u2260': r'\neq',      # ≠
        '\u2248': r'\approx',   # ≈
        '\u2264': r'\leq',      # ≤
        '\u2265': r'\geq',      # ≥
        '\u226a': r'\ll',       # ≪
        '\u226b': r'\gg',       # ≫
        '\u2208': r'\in',       # ∈
        '\u2209': r'\notin',    # ∉
        '\u2282': r'\subset',   # ⊂
        '\u2283': r'\supset',   # ⊃
        '\u222a': r'\cup',      # ∪
        '\u2229': r'\cap',      # ∩
        '\u2227': r'\wedge',    # ∧
        '\u2228': r'\vee',      # ∨
        '\u2192': r'\rightarrow',  # →
        '\u2190': r'\leftarrow',   # ←
        '\u2194': r'\leftrightarrow',  # ↔
        '\u21d2': r'\Rightarrow',  # ⇒
        '\u21d0': r'\Leftarrow',   # ⇐
        '\u21d4': r'\Leftrightarrow',  # ⇔
        '\u2200': r'\forall',   # ∀
        '\u2203': r'\exists',   # ∃
    }
    
    # Subscript digit mappings
    SUBSCRIPTS = {
        '\u2080': '0', '\u2081': '1', '\u2082': '2', '\u2083': '3', '\u2084': '4',
        '\u2085': '5', '\u2086': '6', '\u2087': '7', '\u2088': '8', '\u2089': '9',
    }
    
    # Superscript digit mappings
    SUPERSCRIPTS = {
        '\u2070': '0', '\u00b9': '1', '\u00b2': '2', '\u00b3': '3', '\u2074': '4',
        '\u2075': '5', '\u2076': '6', '\u2077': '7', '\u2078': '8', '\u2079': '9',
        '\u207f': 'n',
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
        # Check for math symbols
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
            r'\\frac\{',       # LaTeX fraction
            r'\\sqrt',         # Square root
            r'\\sum',          # Summation
            r'\\int',          # Integral
            r'\\prod',         # Product
            r'\\lim',          # Limit
            r'\^\{[^}]+\}',    # Multi-char exponents: x^{n+1}
            r'_\{[^}]+\}',     # Multi-char subscripts: x_{i,j}
            # Arithmetic only when flanked by variables/parens (not bare numbers in prose)
            r'[a-zA-Z]\s*[+\-*/]\s*[a-zA-Z]',   # x + y, a - b
            r'[a-zA-Z]\s*=\s*[a-zA-Z0-9]',       # x = 5, f = ma
            r'\([a-zA-Z0-9]+\)\s*[+\-*/]',        # (a) +
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
        
        return MathExpression(
            id='',  # Will be set by caller
            page_num=page_num,
            bbox=tuple(bbox),
            expression_type=expr_type,
            original_text=text,
            latex=latex,
            confidence=confidence,
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
        
        # Replace math symbols
        for symbol, latex_cmd in self.MATH_SYMBOLS.items():
            if symbol in latex:
                latex = latex.replace(symbol, latex_cmd)
                conversions_made += 1
        
        # Handle subscripts
        for sub_char, digit in self.SUBSCRIPTS.items():
            if sub_char in latex:
                latex = latex.replace(sub_char, f'_{digit}')
                conversions_made += 1
        
        # Handle superscripts
        for sup_char, digit in self.SUPERSCRIPTS.items():
            if sup_char in latex:
                latex = latex.replace(sup_char, f'^{digit}')
                conversions_made += 1
        
        # Confidence reflects conversion quality:
        # - No conversions needed: text was already LaTeX → high confidence
        # - Some conversions made: deterministic symbol mapping → moderate confidence
        # - Many conversions: more opportunity for mapping errors → slightly lower
        if conversions_made == 0:
            confidence = 1.0
        elif conversions_made <= 3:
            confidence = 0.75
        else:
            confidence = 0.65
        
        return latex, confidence
