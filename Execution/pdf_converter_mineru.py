"""
PDF to Markdown Converter
Main orchestrator for the conversion pipeline
Uses MinerU Python API for high-quality markdown extraction with native formula/table support
"""

import os
import sys
import json
import logging
import shutil
import copy
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Suppress HuggingFace symlink warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


@dataclass
class ContentTypes:
    """Types of content found in PDF"""
    has_text: bool = True
    has_images: bool = False
    has_tables: bool = False
    has_math: bool = False
    has_code: bool = False


@dataclass 
class PDFAssessment:
    """Assessment results for a PDF"""
    is_valid: bool
    page_count: int
    content_types: ContentTypes
    complexity: str = "simple"
    needs_ocr: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    recommended_pipeline: List[str] = field(default_factory=list)


@dataclass
class MarkdownDocument:
    """Final markdown document"""
    content: str
    title: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class PDFToMarkdownConverter:
    """
    Main converter class that orchestrates the PDF to Markdown conversion
    using MinerU Python API for best-in-class extraction quality.
    
    MinerU Features:
    - Native LaTeX formula recognition (no post-processing needed)
    - Table recognition with HTML output
    - Layout analysis with header/footer removal
    - OCR support for 109 languages
    - 90%+ accuracy on document parsing benchmarks
    """
    
    def __init__(self, config: Dict[str, Any] = None, llm_service=None):
        self.config = config or {}
        self.llm_service = llm_service
        self.logger = self._setup_logging()
        
        # MinerU configuration
        self.backend = config.get("backend", "pipeline") if config else "pipeline"
        self.language = config.get("language", "en") if config else "en"
        self._mineru_initialized = False
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        log_config = self.config.get("logging", {})
        log_level = getattr(logging, log_config.get("level", "INFO"))
        log_file = log_config.get("file", "logs/conversion.log")
        
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger("PDFConverter")
    
    def analyze(self, pdf_path: str) -> PDFAssessment:
        """Analyze PDF to determine content types and complexity"""
        import fitz
        
        path = Path(pdf_path)
        
        if not path.exists():
            return PDFAssessment(
                is_valid=False,
                page_count=0,
                content_types=ContentTypes(),
                warnings=["File not found"]
            )
        
        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            
            has_images = False
            has_tables = False
            has_math = False
            total_text = ""
            
            for page in doc:
                image_list = page.get_images()
                if image_list:
                    has_images = True
                
                text = page.get_text()
                total_text += text
                
                # Check for tables
                if "\t" in text or "|" in text:
                    has_tables = True
                
                # Check for math symbols (using common mathematical indicators)
                math_keywords = ["integral", "sum", "equation", "formula", "theorem", "=", ">=", "<=", "sqrt", "frac"]
                text_lower = text.lower()
                if any(kw in text_lower for kw in math_keywords):
                    has_math = True
                
                # Also check for common math Unicode characters
                for char in text:
                    if ord(char) in range(0x2200, 0x22FF) or ord(char) in range(0x0370, 0x03FF):
                        has_math = True
                        break
            
            metadata = doc.metadata or {}
            doc.close()
            
            complexity = "simple"
            if has_math or has_tables:
                complexity = "moderate"
            if has_math and has_tables and has_images:
                complexity = "complex"
            
            content_types = ContentTypes(
                has_text=len(total_text.strip()) > 0,
                has_images=has_images,
                has_tables=has_tables,
                has_math=has_math
            )
            
            return PDFAssessment(
                is_valid=True,
                page_count=page_count,
                content_types=content_types,
                complexity=complexity,
                needs_ocr=len(total_text.strip()) < 100 and page_count > 0,
                metadata=metadata,
                recommended_pipeline=["mineru"]
            )
            
        except Exception as e:
            return PDFAssessment(
                is_valid=False,
                page_count=0,
                content_types=ContentTypes(),
                warnings=[str(e)]
            )
    
    def extract_with_mineru(self, pdf_path: str, output_dir: str) -> str:
        """
        Extract PDF to Markdown using MinerU Python API.
        
        MinerU provides:
        - Native LaTeX formula recognition
        - Table detection and HTML conversion
        - Layout-aware text extraction
        - Image extraction
        - Header/footer removal
        """
        from mineru.cli.common import read_fn, prepare_env
        from mineru.data.data_reader_writer import FileBasedDataWriter
        from mineru.backend.pipeline.pipeline_analyze import doc_analyze as pipeline_doc_analyze
        from mineru.backend.pipeline.model_json_to_middle_json import result_to_middle_json as pipeline_result_to_middle_json
        from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make as pipeline_union_make
        from mineru.utils.enum_class import MakeMode
        
        pdf_path = Path(pdf_path).resolve()
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"  Using MinerU Python API with backend: {self.backend}")
        self.logger.info(f"  Language: {self.language}")
        
        # Read PDF bytes
        pdf_bytes = read_fn(str(pdf_path))
        pdf_file_name = pdf_path.stem
        
        self.logger.info(f"  Read PDF: {len(pdf_bytes)} bytes")
        
        # Analyze with MinerU pipeline
        self.logger.info("  Starting MinerU analysis (this may take several minutes on CPU)...")
        
        infer_results, all_image_lists, all_pdf_docs, lang_list, ocr_enabled_list = pipeline_doc_analyze(
            [pdf_bytes],
            [self.language],
            parse_method="auto",
            formula_enable=True,
            table_enable=True
        )
        
        self.logger.info("  Analysis complete!")
        
        # Process results
        model_list = infer_results[0]
        model_json = copy.deepcopy(model_list)
        
        # Prepare output directories
        local_image_dir, local_md_dir = prepare_env(str(output_path), pdf_file_name, "auto")
        image_writer = FileBasedDataWriter(local_image_dir)
        md_writer = FileBasedDataWriter(local_md_dir)
        
        images_list = all_image_lists[0]
        pdf_doc = all_pdf_docs[0]
        _lang = lang_list[0]
        _ocr_enable = ocr_enabled_list[0]
        
        # Convert to middle JSON format
        middle_json = pipeline_result_to_middle_json(
            model_list, images_list, pdf_doc, image_writer, _lang, _ocr_enable, True
        )
        
        pdf_info = middle_json["pdf_info"]
        
        # Generate markdown content
        image_dir = str(os.path.basename(local_image_dir))
        md_content = pipeline_union_make(pdf_info, MakeMode.MM_MD, image_dir)
        
        self.logger.info(f"  Generated markdown: {len(md_content)} characters")
        
        # Count images
        image_files = list(Path(local_image_dir).glob("*"))
        self.logger.info(f"  Extracted {len(image_files)} images")
        
        # Copy images to main output directory
        images_dst = output_path / "images"
        if images_dst.exists():
            shutil.rmtree(images_dst)
        if Path(local_image_dir).exists() and list(Path(local_image_dir).glob("*")):
            shutil.copytree(local_image_dir, images_dst)
            
            # Update image paths in markdown
            md_content = md_content.replace(f"({image_dir}/", "(images/")
        
        # URL-encode spaces in image paths for proper markdown rendering
        import re
        def encode_image_path(match):
            alt = match.group(1)
            path = match.group(2)
            encoded_path = path.replace(' ', '%20')
            return f'![{alt}]({encoded_path})'
        md_content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', encode_image_path, md_content)
        
        # Post-process to fix garbled URLs from math conversion
        md_content = self._fix_garbled_urls(md_content)
        
        return md_content
    
    def _fix_garbled_urls(self, content: str) -> str:
        """
        Fix URLs that were garbled by incorrect math symbol conversion.
        
        Common issues:
        - '?id=' becoming '$\\subset$id=' (subset symbol mistaken for ?)
        - Extra spaces in URLs like 'org/ citation' instead of 'org/citation'
        - Other math symbols incorrectly substituted in URLs
        """
        import re
        
        # First, fix broken URLs where spaces were inserted mid-URL
        # Pattern: URL followed by space and what looks like continuation (e.g., 'http://example.org/ path.cfm')
        # This handles cases like 'http://dl.acm.org/ citation.cfm?id=123'
        content = re.sub(r'(https?://[^\s]+)/\s+([a-zA-Z])', r'\1/\2', content)
        
        # Also fix newline breaks in URLs
        content = re.sub(r'(https?://[^\s]+)\s*\n\s*([a-zA-Z0-9])', r'\1\2', content)
        
        # Pattern to find URLs (http/https) - now should capture full URLs
        url_pattern = r'(https?://[^\s\)\]]+)'
        
        def fix_url(match):
            url = match.group(1)
            
            # Fix common math symbol substitutions in URLs
            # $\subset$ or \subset should be ?
            url = re.sub(r'\$?\\subset\$?', '?', url)
            
            # Fix other potential math symbol issues in URLs
            # $\in$ should be ?
            url = re.sub(r'\$?\\in\$?', '?', url)
            
            # $\ni$ or $\owns$ might also be used
            url = re.sub(r'\$?\\(ni|owns)\$?', '?', url)
            
            # Remove any remaining $ delimiters around single characters in URLs
            url = re.sub(r'\$([^$])\$', r'\1', url)
            
            return url
        
        content = re.sub(url_pattern, fix_url, content)
        
        return content
    
    def convert(self, pdf_path: str, output_dir: str = None) -> MarkdownDocument:
        """Convert a PDF file to Markdown using MinerU
        
        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save output files
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if output_dir is None:
            output_dir = pdf_path.parent / "output"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Starting conversion of: {pdf_path}")
        
        # Step 1: Analyze PDF
        self.logger.info("Step 1: Analyzing PDF...")
        assessment = self.analyze(str(pdf_path))
        
        if not assessment.is_valid:
            raise ValueError(f"Invalid PDF: {assessment.warnings}")
        
        self.logger.info(f"  Pages: {assessment.page_count}")
        self.logger.info(f"  Complexity: {assessment.complexity}")
        self.logger.info(f"  Has Images: {assessment.content_types.has_images}")
        self.logger.info(f"  Has Tables: {assessment.content_types.has_tables}")
        self.logger.info(f"  Has Math: {assessment.content_types.has_math}")
        
        # Step 2: Extract with MinerU
        self.logger.info("Step 2: Extracting with MinerU Python API...")
        self.logger.info("  - Native LaTeX formula recognition")
        self.logger.info("  - Table detection and conversion")
        self.logger.info("  - Layout-aware extraction")
        self.logger.info("  - Image extraction")
        
        try:
            content = self.extract_with_mineru(str(pdf_path), str(output_dir))
        except ImportError as exc:
            raise ImportError(
                f"MinerU is not installed or failed to load while converting '{pdf_path.name}'. "
                f"Install it with: pip install mineru. Original error: {exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"MinerU extraction failed for '{pdf_path.name}' "
                f"(page_count={assessment.page_count}, complexity={assessment.complexity}): "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        self.logger.info("  Extraction complete!")
        
        # Step 3: Post-process MinerU output
        self.logger.info("Step 3: Post-processing markdown...")
        try:
            from Execution.processors.post_processor import MarkdownPostProcessor
            post_processor = MarkdownPostProcessor()
            content = post_processor.process(content)
            if post_processor.fixes_applied:
                self.logger.info(
                    f"  Post-processor applied {len(post_processor.fixes_applied)} fix categories"
                )
        except Exception as exc:
            # Post-processing is non-critical – log and continue with raw content
            self.logger.warning(
                f"Post-processing failed for '{pdf_path.name}': {type(exc).__name__}: {exc}. "
                "Saving unprocessed content."
            )

        # Create document
        title = assessment.metadata.get("title", "") or pdf_path.stem
        document = MarkdownDocument(
            content=content,
            title=title,
            metadata=assessment.metadata
        )
        
        # Save the document
        output_file = output_dir / f"{pdf_path.stem}.md"
        try:
            output_file.write_text(document.content, encoding="utf-8")
        except OSError as exc:
            raise OSError(
                f"Failed to write output markdown to '{output_file}': {exc}"
            ) from exc
        
        self.logger.info(f"Saved markdown to: {output_file}")
        
        # Save conversion report
        report = {
            "source": pdf_path.name,
            "converted_at": datetime.now().isoformat(),
            "pages": assessment.page_count,
            "complexity": assessment.complexity,
            "backend": "mineru",
            "mineru_backend": self.backend,
            "has_math": assessment.content_types.has_math,
            "has_tables": assessment.content_types.has_tables,
            "has_images": assessment.content_types.has_images,
            "post_processing_fixes": len(
                post_processor.fixes_applied  # type: ignore[possibly-undefined]
            ) if 'post_processor' in dir() else 0,
        }
        
        report_path = output_dir / "conversion_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        return document


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert PDF to Markdown using MinerU")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("-o", "--output", help="Output directory")
    parser.add_argument("-b", "--backend", default="pipeline",
                        choices=["pipeline", "vlm-auto-engine", "hybrid-auto-engine"],
                        help="MinerU backend (default: pipeline)")
    parser.add_argument("-l", "--language", default="en",
                        help="Document language for OCR (default: en)")
    
    args = parser.parse_args()
    
    config = {
        "backend": args.backend,
        "language": args.language,
    }
    
    converter = PDFToMarkdownConverter(config)
    document = converter.convert(args.pdf_path, args.output)
    print("Conversion complete!")
