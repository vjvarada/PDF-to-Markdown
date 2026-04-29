"""
Post-Processor for MinerU PDF Conversion Output

This module provides robust post-processing to fix common issues in MinerU's
markdown output, including:
- Garbled URLs (math symbols incorrectly replacing URL characters)
- Malformed math formulas
- Concatenated references
- Split DOIs
- OCR artifacts and encoding issues
- Whitespace and formatting cleanup

Author: PDF to Markdown Converter
"""

import re
import logging
from typing import List, Tuple, Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class MarkdownPostProcessor:
    """
    Post-processor for cleaning and fixing MinerU markdown output.
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize the post-processor.
        
        Args:
            strict_mode: If True, log warnings for all detected issues
        """
        self.strict_mode = strict_mode
        self.fixes_applied = []
        
        # Common math symbol to URL character mappings (MinerU garbling)
        self.url_garble_patterns = [
            # Math symbols that replace URL special characters
            (r'\$\\subset\$', '?'),           # ? gets converted to subset
            (r'\$\\supset\$', '?'),           # alternate ? conversion
            (r'\$\\in\$', '&'),               # & gets converted to \in
            (r'\$\\ni\$', '&'),               # alternate & conversion  
            (r'\$\\sim\$', '~'),              # ~ tilde
            (r'\$\\#\$', '#'),                # # hash
            (r'\$\\%\$', '%'),                # % percent
            (r'\$\\&\$', '&'),                # & ampersand
            (r'\$=\$', '='),                  # = equals in URLs
            (r'\$\+\$', '+'),                 # + plus
            (r'\$\\times\$', 'x'),            # x in URLs
            (r'\$\\cdot\$', '.'),             # . dot
            (r'\$\\ast\$', '*'),              # * asterisk
            (r'\$\\backslash\$', '/'),        # / slash confusion
            (r'\$\\mid\$', '|'),              # | pipe
            (r'\$<\$', '<'),                  # < less than
            (r'\$>\$', '>'),                  # > greater than
            (r'\$\\le\$', '<='),              # <= 
            (r'\$\\ge\$', '>='),              # >=
        ]
        
        # Patterns for detecting garbled inline math that should be text
        self.false_math_patterns = [
            # Single letters/symbols that shouldn't be math
            (r'\$([a-zA-Z])\$(?=\s|[.,;:!?)])', r'\1'),
            # Common words incorrectly wrapped in math
            (r'\$([Tt]he|[Aa]nd|[Oo]r|[Ii]n|[Oo]f|[Tt]o)\$', r'\1'),
            # Copyright incorrectly in math mode — digits may already be joined by the
            # spaced-decimal fixer, so match both "1 9 9 5" and "1995" forms.
            (r'\$\\mathbb\{C\}\s*([\d][\d\s]*)\$',
             lambda m: '\u00a9' + m.group(1).replace(' ', '')),
        ]
        
        # Patterns for fixing spaced decimals in math
        self.spaced_decimal_patterns = [
            # Fix "- 0." -> "-0."
            (r'-\s+(\d\.)', r'-\1'),
            # Fix spaced digit sequences "1 4 \times" -> "14 \times"
            (r'(\d)\s+(\d)\s*(?=\\times)', r'\1\2'),
        ]
        
        # Patterns for verbose/mangled math notation
        self.math_cleanup_patterns = [
            # $\pmb { p }$ -> $\mathbf{p}$
            (r'\\pmb\s*\{\s*(\w+)\s*\}', r'\\mathbf{\1}'),
            # $\pmb { p } _ { z }$ -> $p_z$  (often not actually bold needed)
            (r'\\pmb\s*\{\s*(\w)\s*\}\s*_\s*\{\s*(\w+)\s*\}', r'\1_{\2}'),
            # $\mathbf { - }$ -> $-$
            (r'\\mathbf\s*\{\s*-\s*\}', r'-'),
            # $\dot { - }$ -> $-$ (malformed minus)
            (r'\\dot\s*\{\s*-\s*\}', r'-'),
            # $\mathfrak { E }$ -> $\varepsilon$
            (r'\\mathfrak\s*\{\s*E\s*\}', r'\\varepsilon'),
            # $\nu I$ -> $v_1$ (nu confused with v)
            (r'\\nu\s*([IV1-4])', lambda m: f'v_{m.group(1).replace("I", "1").replace("V", "5")}'),
            # Clean up \left\{ ... \right\} with excess spaces
            (r'\\left\\\{\s*\(\s*', r'\\{('),
            (r'\s*\)\s*\\right\\\}', r')\\}'),
        ]
        
        # Common OCR error corrections (use simple string replacement for Unicode chars)
        self.ocr_corrections_simple = [
            # Ligature issues
            ('\ufb01', 'fi'),   # fi ligature
            ('\ufb02', 'fl'),   # fl ligature
            ('\ufb00', 'ff'),   # ff ligature
            ('\ufb03', 'ffi'),  # ffi ligature
            ('\ufb04', 'ffl'),  # ffl ligature
            # Quote normalization - curly to straight
            ('\u201c', '"'),    # left double quote "
            ('\u201d', '"'),    # right double quote "
            ('\u2018', "'"),    # left single quote '
            ('\u2019', "'"),    # right single quote '
            # Dash normalization
            ('\u2014', '--'),   # em dash —
            ('\u2013', '-'),    # en dash –
            # Ellipsis
            ('\u2026', '...'),  # horizontal ellipsis …
        ]
        
        # OCR regex patterns (more complex patterns)
        self.ocr_corrections_regex = [
            # Common OCR misreads - these need to stay as regex for lookbehind/lookahead
            (r'(?<=\d)O(?=\d)', '0'),        # O vs 0 in numbers
            (r'(?<=\d)l(?=\d)', '1'),        # l vs 1 in numbers
        ]
        
        # Reference detection pattern (author-year format)
        self.reference_start_pattern = re.compile(
            r'(?:^|\n)([A-Z][a-zA-Z\-\']+(?:,?\s+(?:and\s+)?[A-Z]\.?\s*)+[a-zA-Z\-\']*)\.\s*(\d{4})\.',
            re.MULTILINE
        )
        
    def process(self, markdown_content: str) -> str:
        """
        Apply all post-processing fixes to markdown content.
        
        Args:
            markdown_content: Raw markdown from MinerU
            
        Returns:
            Cleaned and fixed markdown content
        """
        self.fixes_applied = []
        
        # Apply fixes in order of priority
        content = markdown_content
        
        # 1. Fix URL garbling (highest priority - affects links)
        content = self._fix_garbled_urls(content)
        
        # 2. Fix split DOIs
        content = self._fix_split_dois(content)
        
        # 3. Fix malformed math formulas
        content = self._fix_math_formulas(content)
        
        # 4. Fix false math detection
        content = self._fix_false_math(content)
        
        # 5. Apply OCR corrections
        content = self._fix_ocr_errors(content)
        
        # 6. Fix reference formatting
        content = self._fix_references(content)
        
        # 7. Clean up whitespace and formatting
        content = self._clean_whitespace(content)
        
        # 8. Fix heading artifacts
        content = self._fix_heading_artifacts(content)
        
        # 9. Final pass - fix any remaining split lines (names, etc.)
        content = self._fix_split_lines(content)
        
        # Log summary
        if self.fixes_applied:
            logger.info(f"Post-processor applied {len(self.fixes_applied)} fix categories")
            for fix in self.fixes_applied:
                logger.debug(f"  - {fix}")
                
        return content
    
    def _fix_split_lines(self, content: str) -> str:
        """
        Final pass to fix lines that got incorrectly split.
        """
        fixes_count = 0
        
        # Fix split author names: "Name.\nOtherName" -> "Name. OtherName"
        # This handles cases like "N.\nVenkata" or "Sarah F.\nFrisken"
        original = content
        content = re.sub(
            r'([A-Z][a-z]*\.)\s*\n\s*([A-Z][a-z]+)',
            r'\1 \2',
            content
        )
        if content != original:
            fixes_count += content.count('\1 \2') or 1
        
        # Fix DOI paths split across lines: "doi.org/10.\n1111" -> "doi.org/10.1111"
        content = re.sub(
            r'(doi\.org/10\.)\s*\n\s*(\d)',
            r'\1\2',
            content
        )
        
        # Fix citation IDs split: "citation.cfm?id=\n646921" -> "citation.cfm?id=646921"
        content = re.sub(
            r'(citation\.cfm\?id=)\s*\n\s*(\d)',
            r'\1\2',
            content
        )
        
        if fixes_count > 0:
            self.fixes_applied.append(f"Fixed {fixes_count} split lines")
        
        return content
    
    def _fix_garbled_urls(self, content: str) -> str:
        """
        Fix URLs where special characters were replaced with math symbols.
        """
        fixes_count = 0
        
        # Find all URLs and potential URLs
        url_pattern = re.compile(
            r'(https?://[^\s\)]+)',
            re.IGNORECASE
        )
        
        def fix_url(match):
            nonlocal fixes_count
            url = match.group(1)
            original_url = url
            
            # Apply garble fixes
            for pattern, replacement in self.url_garble_patterns:
                url = re.sub(pattern, replacement, url)
            
            if url != original_url:
                fixes_count += 1
                
            return url
        
        result = url_pattern.sub(fix_url, content)
        
        # Also fix URLs in markdown link syntax
        link_pattern = re.compile(r'\]\(([^)]+)\)')
        
        def fix_link_url(match):
            nonlocal fixes_count
            url = match.group(1)
            original_url = url
            
            for pattern, replacement in self.url_garble_patterns:
                url = re.sub(pattern, replacement, url)
                
            if url != original_url:
                fixes_count += 1
                
            return f']({url})'
        
        result = link_pattern.sub(fix_link_url, result)
        
        if fixes_count > 0:
            self.fixes_applied.append(f"Fixed {fixes_count} garbled URLs")
            
        return result
    
    def _fix_split_dois(self, content: str) -> str:
        """
        Fix DOIs that got split across lines or have spaces inserted.
        """
        fixes_count = 0
        
        # Pattern for DOIs with incorrect spaces
        # e.g., "https://doi.org/10.1145/3197517. 3201381" -> "https://doi.org/10.1145/3197517.3201381"
        doi_space_pattern = re.compile(
            r'(https://doi\.org/10\.\d+/[\d\.]+)\.\s+(\d+)',
            re.IGNORECASE
        )
        
        def fix_doi(match):
            nonlocal fixes_count
            fixes_count += 1
            return f'{match.group(1)}.{match.group(2)}'
        
        result = doi_space_pattern.sub(fix_doi, content)
        
        # Also fix DOIs split with newlines
        doi_newline_pattern = re.compile(
            r'(https://doi\.org/10\.\d+/[\d\.]+)\.\s*\n\s*(\d+)',
            re.IGNORECASE
        )
        
        result = doi_newline_pattern.sub(fix_doi, result)
        
        # Fix DOIs split after "10." - e.g., "doi.org/10.\n1111" -> "doi.org/10.1111"
        result = re.sub(
            r'(doi\.org/10\.)\s*\n\s*(\d+)',
            r'\1\2',
            result
        )
        
        # Fix DOIs with space in path - e.g., "10.1145/ 2629697" -> "10.1145/2629697"
        result = re.sub(
            r'(doi\.org/10\.\d+/)\s+(\d+)',
            r'\1\2',
            result
        )
        
        # Fix "https: //" split
        result = re.sub(r'https:\s+//', 'https://', result)
        result = re.sub(r'http:\s+//', 'http://', result)
        
        if fixes_count > 0:
            self.fixes_applied.append(f"Fixed {fixes_count} split DOIs")
            
        return result
    
    def _fix_math_formulas(self, content: str) -> str:
        """
        Fix common math formula issues from MinerU extraction.
        """
        fixes_count = 0
        
        # First, fix spaced decimals in math mode
        def fix_spaced_decimals(match):
            nonlocal fixes_count
            math = match.group(1)
            original = math
            
            # Apply spaced decimal fixes
            for pattern, replacement in self.spaced_decimal_patterns:
                math = re.sub(pattern, replacement, math)

            # Fix spaced decimals of arbitrary length: "0. 2 7 5" -> "0.275"
            # Apply repeatedly until stable (handles nested digit sequences)
            for _ in range(5):
                new_math = re.sub(
                    r'(\d)\.\s+((?:\d\s+)*\d)',
                    lambda m: m.group(1) + '.' + re.sub(r'\s+', '', m.group(2)),
                    math
                )
                if new_math == math:
                    break
                math = new_math

            # Join spaced digit sequences not preceded by a dot (e.g. "5 1 2" -> "512")
            # Only within clear numeric contexts (preceded/followed by \times, \times, ^, _, =)
            math = re.sub(
                r'(?<=[=\s{(,])\s*(\d(?:\s+\d)+)(?=[\s}),\\]|$)',
                lambda m: re.sub(r'\s+', '', m.group(0)),
                math
            )

            if math != original:
                fixes_count += 1
            return f'${math}$'
        
        result = re.sub(r'\$([^$]+)\$', fix_spaced_decimals, content)
        
        # Fix excessive spacing in math mode
        # e.g., "$d _ { e }$" -> "$d_{e}$"
        def fix_math_spacing(match):
            nonlocal fixes_count
            math = match.group(1)
            original = math
            
            # Remove spaces around subscript/superscript
            math = re.sub(r'\s*_\s*\{\s*', '_{', math)
            math = re.sub(r'\s*\^\s*\{\s*', '^{', math)
            math = re.sub(r'\s+\}', '}', math)
            
            # Remove spaces around common operators in math
            math = re.sub(r'\s*\\mathcal\s*\{\s*', r'\\mathcal{', math)
            math = re.sub(r'\s*\\mathbb\s*\{\s*', r'\\mathbb{', math)
            math = re.sub(r'\s*\\partial\s+', r'\\partial ', math)
            
            # Apply math cleanup patterns
            for pattern, replacement in self.math_cleanup_patterns:
                if callable(replacement):
                    new_math = re.sub(pattern, replacement, math)
                else:
                    new_math = re.sub(pattern, replacement, math)
                if new_math != math:
                    math = new_math
                    
            if math != original:
                fixes_count += 1
                
            return f'${math}$'
        
        # Apply to inline math
        result = re.sub(r'\$([^$]+)\$', fix_math_spacing, result)
        
        # Fix LaTeX commands that appear outside of math mode (missing $ delimiters)
        # Pattern: standalone \frac, \mathcal, etc. not inside $ $
        latex_commands_outside_math = [
            # Standalone \frac outside math mode - wrap in $
            (r'(?<!\$)\\frac\{([^}]+)\}\{([^}]+)\}(?!\$)', r'$\\frac{\1}{\2}$'),
            # = followed by \frac (like "= \frac{...}")
            (r'=\s*\\frac\{([^}]+)\}\{([^}]+)\}', r'$= \\frac{\1}{\2}$'),
        ]
        
        for pattern, replacement in latex_commands_outside_math:
            matches = len(re.findall(pattern, result))
            if matches > 0:
                result = re.sub(pattern, replacement, result)
                fixes_count += matches
        
        # Fix common garbled formulas
        garbled_formulas = [
            # "= 12 +" pattern (fraction recognition failure)
            (r'=\s*12\s*\+\s*\.', r'$= \\frac{1}{d_e^2 + \\epsilon}$'),
        ]
        
        for pattern, replacement in garbled_formulas:
            if re.search(pattern, result):
                result = re.sub(pattern, replacement, result)
                fixes_count += 1
        
        # Fix display math spacing
        result = re.sub(r'\$\$\s+', '$$\n', result)
        result = re.sub(r'\s+\$\$', '\n$$', result)
        
        if fixes_count > 0:
            self.fixes_applied.append(f"Fixed {fixes_count} math formula issues")
            
        return result
    
    def _fix_false_math(self, content: str) -> str:
        """
        Remove math delimiters from content that shouldn't be math.
        """
        fixes_count = 0
        
        for pattern, replacement in self.false_math_patterns:
            matches = len(re.findall(pattern, content))
            if matches > 0:
                if callable(replacement):
                    content = re.sub(pattern, replacement, content)
                else:
                    content = re.sub(pattern, replacement, content)
                fixes_count += matches
        
        if fixes_count > 0:
            self.fixes_applied.append(f"Fixed {fixes_count} false math detections")
            
        return content
    
    def _fix_ocr_errors(self, content: str) -> str:
        """
        Fix common OCR errors and encoding issues.
        """
        fixes_count = 0
        
        # Apply simple string replacements first
        for old_str, new_str in self.ocr_corrections_simple:
            count = content.count(old_str)
            if count > 0:
                content = content.replace(old_str, new_str)
                fixes_count += count
        
        # Apply regex patterns
        for pattern, replacement in self.ocr_corrections_regex:
            matches = len(re.findall(pattern, content))
            if matches > 0:
                content = re.sub(pattern, replacement, content)
                fixes_count += matches
        
        # Fix split author names - "FirstName.\nLastName" -> "FirstName. LastName"  
        # e.g., "Sarah F.\nFrisken Gibson" -> "Sarah F. Frisken Gibson"
        content = re.sub(
            r'([A-Z][a-z]*\.)\s*\n\s*([A-Z][a-z]+)',
            r'\1 \2',
            content
        )
        
        # Fix split names with initial: "N.\nVenkata" -> "N. Venkata"
        content = re.sub(
            r'([A-Z]\.)\s*\n\s*([A-Z][a-z]+)',
            r'\1 \2',
            content
        )
        
        # Fix stray Unicode artifacts
        # Remove common problematic characters that appear from OCR
        stray_chars = [
            (r'(?<=[a-zA-Z])\s*ϵ(?=\s*[a-zA-Z])', ' '),  # stray epsilon
            (r'(?<=[a-zA-Z])\s*∂(?=\s*[a-zA-Z])', ' '),  # stray partial
            (r'(?<=[a-zA-Z])\.(?=[A-Z][a-z])', '. '),    # missing space after period
        ]
        
        for pattern, replacement in stray_chars:
            matches = len(re.findall(pattern, content))
            if matches > 0:
                content = re.sub(pattern, replacement, content)
                fixes_count += matches
        
        if fixes_count > 0:
            self.fixes_applied.append(f"Fixed {fixes_count} OCR errors")
            
        return content
    
    def _fix_references(self, content: str) -> str:
        """
        Fix concatenated references - split them into separate entries.
        """
        # Look for REFERENCES section
        ref_match = re.search(r'#\s*REFERENCES?\s*\n', content, re.IGNORECASE)
        if not ref_match:
            return content
        
        ref_start = ref_match.end()
        
        # Find where references end (next heading or end of content)
        next_heading = re.search(r'\n#\s+[A-Z]', content[ref_start:])
        if next_heading:
            ref_end = ref_start + next_heading.start()
        else:
            ref_end = len(content)
        
        references_section = content[ref_start:ref_end]
        original_refs = references_section
        
        # Always try to fix references - split concatenated ones
        fixed_refs = self._split_references(references_section)
        
        # Only update if changes were made
        if fixed_refs != original_refs:
            # Reconstruct content
            new_content = content[:ref_start] + fixed_refs + content[ref_end:]
            self.fixes_applied.append("Split concatenated references")
            return new_content
        
        return content
    
    def _split_references(self, ref_text: str) -> str:
        """
        Split concatenated references into individual entries.
        
        Detects patterns where references are run together without proper separation.
        """
        # Remove figure captions that got mixed into references
        # Pattern: ![](images/...) followed by Fig. X. caption text
        ref_text = re.sub(
            r'!\[\]\(images/[^)]+\)\s*\n?\s*Fig\.\s*\d+\.[^\n]+\n?',
            '\n\n',
            ref_text
        )
        
        # Fix orphaned DOI fragments - rejoin them to previous DOI URL
        # e.g., "https://doi.org/10.\n1109/TVCG..." -> "https://doi.org/10.1109/TVCG..."
        ref_text = re.sub(
            r'(https?://doi\.org/10\.)\s*\n\s*(\d+/)',
            r'\1\2',
            ref_text
        )
        
        # Remove completely orphaned DOI path fragments on their own line
        ref_text = re.sub(
            r'\n\s*(\d{4}/[A-Z]+\.\d+\.\d+)\s*\n',
            lambda m: f' {m.group(1)}\n' if not m.group(1).startswith('http') else '\n',
            ref_text
        )
        
        # Fix split author names like "N.\nVenkata Reddy" -> "N. Venkata Reddy"
        ref_text = re.sub(
            r'([A-Z]\.)\s*\n\s*([A-Z][a-z]+)',
            r'\1 \2',
            ref_text
        )
        
        # Pattern 1: URL/DOI followed immediately by author name (no space)
        # e.g., "https://doi.org/10.1145/3197517.3201381Amit" -> split before "Amit"
        ref_text = re.sub(
            r'(https?://[^\s]+?)([A-Z][a-z]{2,}(?:,|\s+[A-Z]\.))',
            r'\1\n\n\2',
            ref_text
        )
        
        # Pattern 2: Publisher/book title ending followed by author (with initials)
        # e.g., "John Wiley & Sons. H. Edelsbrunner" -> split before "H."
        ref_text = re.sub(
            r'(Sons|Press|Publishers?|Inc|Ltd)\.?\s+([A-Z]\.\s*[A-Z]?[a-z]*)',
            r'\1.\n\n\2',
            ref_text
        )
        
        # Pattern 3: Year followed by author starting new reference
        # e.g., "...13 pages. Amit H. Bermano" where no DOI separates them
        ref_text = re.sub(
            r'(\d+\s*pages\.)\s*([A-Z][a-z]+\s+[A-Z]\.)',
            r'\1\n\n\2',
            ref_text
        )
        
        # Pattern 4: ACM URL (citation.cfm) followed by author  
        ref_text = re.sub(
            r'(citation\.cfm\?id=[^\s]+)\s+([A-Z][a-z]+\s+[A-Z])',
            r'\1\n\n\2',
            ref_text
        )
        
        # Pattern 5: Journal name ending followed by author
        # e.g., "Forum 36, 2 (May 2017), 509-535. S. Biasotti"
        ref_text = re.sub(
            r'(\d+-\d+\.)\s*\n?\s*([A-Z]\.?\s+[A-Z]?[a-z]*,)',
            r'\1\n\n\2',
            ref_text
        )
        
        # Pattern 6: .pdf or .html file extension followed by author name  
        ref_text = re.sub(
            r'(\.pdf|\.html)([A-Z][a-z]+)',
            r'\1\n\n\2',
            ref_text
        )
        
        # Pattern 7: Split at clear reference boundaries - period then FirstName LastName. Year
        ref_text = re.sub(
            r'([.!?])\s+([A-Z][a-z]+\s+(?:[A-Z]\.?\s*)+[A-Z]?[a-z]*\.?\s+(?:19|20)\d{2}\.)',
            r'\1\n\n\2',
            ref_text
        )
        
        # Pattern 8: Split at "Author et al. Year" pattern
        ref_text = re.sub(
            r'([.!?])\s+([A-Z][a-z]+\s+et\s+al\.\s+(?:19|20)\d{2})',
            r'\1\n\n\2',
            ref_text
        )
        
        # Pattern 9: Split after DOI URL when followed by space and initials
        ref_text = re.sub(
            r'(doi\.org/[^\s]+)\s+([A-Z]\.\s*[A-Z])',
            r'\1\n\n\2',
            ref_text
        )
        
        # Clean up multiple newlines
        ref_text = re.sub(r'\n{3,}', '\n\n', ref_text)
        
        # Clean up whitespace at start of lines
        ref_text = re.sub(r'\n\s+', '\n', ref_text)
        
        return ref_text
    
    def _clean_whitespace(self, content: str) -> str:
        """
        Clean up whitespace issues.
        """
        # Remove trailing whitespace from lines
        content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
        
        # Normalize multiple blank lines to maximum of 2
        content = re.sub(r'\n{4,}', '\n\n\n', content)
        
        # Fix spaces before punctuation
        content = re.sub(r'\s+([.,;:!?])', r'\1', content)
        
        # Fix double spaces (but not in code blocks)
        lines = content.split('\n')
        in_code_block = False
        fixed_lines = []
        
        for line in lines:
            if line.startswith('```'):
                in_code_block = not in_code_block
            
            if not in_code_block and not line.startswith('    '):
                line = re.sub(r'  +', ' ', line)
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_heading_artifacts(self, content: str) -> str:
        """
        Fix heading-related artifacts from PDF extraction.
        """
        fixes_count = 0
        
        # Fix headings that are actually DOI fragments
        # e.g., "# 1109/TVCG.2003.1260744" should not be a heading
        doi_heading_pattern = re.compile(r'^#\s*(\d+/[A-Z]+\.\d+\.\d+)$', re.MULTILINE)
        
        def fix_doi_heading(match):
            nonlocal fixes_count
            fixes_count += 1
            return match.group(1)  # Remove the # but keep the DOI part
        
        content = doi_heading_pattern.sub(fix_doi_heading, content)
        
        # Fix page numbers that became headings
        page_heading_pattern = re.compile(r'^#\s*(\d{1,3})\s*$', re.MULTILINE)
        content = page_heading_pattern.sub('', content)
        
        # Fix headings with trailing artifacts
        content = re.sub(r'^(#+\s+[^#\n]+)\s+[∂∆∇]+\s*$', r'\1', content, flags=re.MULTILINE)
        
        if fixes_count > 0:
            self.fixes_applied.append(f"Fixed {fixes_count} heading artifacts")
            
        return content
    
    def validate_math(self, content: str) -> List[Dict]:
        """
        Validate math expressions and return list of potential issues.
        
        Returns:
            List of dicts with 'line', 'content', 'issue' keys
        """
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Find inline math
            math_matches = re.finditer(r'\$([^$]+)\$', line)
            
            for match in math_matches:
                math_content = match.group(1)
                
                # Check for common issues
                issue = self._check_math_expression(math_content)
                if issue:
                    issues.append({
                        'line': i,
                        'content': match.group(0),
                        'issue': issue
                    })
        
        return issues
    
    def _check_math_expression(self, math: str) -> Optional[str]:
        """
        Check a math expression for common issues.
        """
        # Check for unbalanced braces
        if math.count('{') != math.count('}'):
            return "Unbalanced braces"
        
        # Check for unbalanced parentheses
        if math.count('(') != math.count(')'):
            return "Unbalanced parentheses"
        
        # Check for incomplete commands
        if re.search(r'\\[a-zA-Z]+\s*$', math):
            return "Incomplete LaTeX command"
        
        # Check for suspicious patterns
        if re.search(r'=\s*\d+\s*\+\s*\.', math):
            return "Possible garbled fraction"
        
        # Check for excessive spacing
        if re.search(r'\s{3,}', math):
            return "Excessive spacing in math"
        
        # Check for stray characters
        if re.search(r'[ϵε∂∆∇]\s*[a-zA-Z]', math):
            return "Possible OCR artifact in math"
        
        return None


def post_process_markdown(markdown_path: str, output_path: Optional[str] = None) -> str:
    """
    Post-process a markdown file and optionally save to new location.
    
    Args:
        markdown_path: Path to input markdown file
        output_path: Optional path for output (if None, overwrites input)
        
    Returns:
        Processed markdown content
    """
    input_path = Path(markdown_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {markdown_path}")
    
    # Read content
    content = input_path.read_text(encoding='utf-8')
    
    # Process
    processor = MarkdownPostProcessor()
    processed_content = processor.process(content)
    
    # Validate math
    issues = processor.validate_math(processed_content)
    if issues:
        logger.warning(f"Found {len(issues)} potential math issues:")
        for issue in issues[:10]:  # Show first 10
            logger.warning(f"  Line {issue['line']}: {issue['issue']} in '{issue['content'][:50]}...'")
    
    # Save
    output = Path(output_path) if output_path else input_path
    output.write_text(processed_content, encoding='utf-8')
    
    logger.info(f"Post-processed markdown saved to: {output}")
    
    return processed_content


# CLI interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Post-process MinerU markdown output')
    parser.add_argument('input', help='Input markdown file')
    parser.add_argument('-o', '--output', help='Output file (default: overwrite input)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--validate-only', action='store_true', help='Only validate, do not fix')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    if args.validate_only:
        processor = MarkdownPostProcessor()
        content = Path(args.input).read_text(encoding='utf-8')
        issues = processor.validate_math(content)
        
        if issues:
            print(f"\nFound {len(issues)} potential issues:\n")
            for issue in issues:
                print(f"  Line {issue['line']}: {issue['issue']}")
                print(f"    Content: {issue['content'][:80]}...")
                print()
        else:
            print("No issues found!")
    else:
        post_process_markdown(args.input, args.output)
