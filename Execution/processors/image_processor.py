"""
Image Processor - SOP 04 Implementation
Extracts and processes images from PDF documents
"""

import os
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import fitz  # PyMuPDF
from PIL import Image
import io


@dataclass
class ExtractedImage:
    """Represents an extracted image"""
    id: str
    page_num: int
    bbox: Tuple[float, float, float, float]
    image_type: str  # 'figure', 'chart', 'diagram', 'photo', 'logo'
    file_path: str
    width: int
    height: int
    format: str
    alt_text: str = ''
    caption: str = ''
    xref: int = 0


class ImageProcessor:
    """
    Processes images from PDF documents following SOP 04
    """
    
    def __init__(self, config: Dict[str, Any] = None, llm_service=None):
        self.config = config or {}
        self.llm_service = llm_service
        self.output_format = self.config.get('format', 'png')
        self.max_width = self.config.get('max_width', 2000)
        self.jpeg_quality = self.config.get('quality', 85)
        self.generate_alt_text = self.config.get('generate_alt_text', True)
        self.min_size = self.config.get('min_size', 50)  # Minimum dimension to extract
    
    def process(self, pdf_path: str, output_dir: str) -> List[ExtractedImage]:
        """
        Extract and process all images from a PDF
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save extracted images
            
        Returns:
            List of ExtractedImage objects
        """
        doc = fitz.open(pdf_path)
        images = []
        
        # Create output directory
        output_path = Path(output_dir)
        images_dir = output_path / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # Get document name for file naming
        doc_name = Path(pdf_path).stem
        
        image_count = 0
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_images = self._extract_page_images(
                page, page_num, doc, images_dir, doc_name, image_count
            )
            images.extend(page_images)
            image_count += len(page_images)
        
        doc.close()
        
        # Generate alt text for images if enabled
        if self.generate_alt_text and self.llm_service:
            images = self._generate_alt_texts(images)
        
        return images
    
    def _extract_page_images(self, page: fitz.Page, page_num: int, doc: fitz.Document,
                             output_dir: Path, doc_name: str, start_count: int) -> List[ExtractedImage]:
        """Extract images from a single page"""
        images = []
        
        # Get list of images on this page
        image_list = page.get_images(full=True)
        
        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]  # Image xref number
            
            try:
                # Extract the image
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue
                
                image_bytes = base_image['image']
                image_ext = base_image['ext']
                width = base_image['width']
                height = base_image['height']
                
                # Skip small images (likely icons or artifacts)
                if width < self.min_size or height < self.min_size:
                    continue
                
                # Process and save the image
                image_id = start_count + img_idx
                processed_image = self._process_image(
                    image_bytes, image_ext, width, height
                )
                
                if processed_image is None:
                    continue
                
                # Determine image type
                image_type = self._classify_image(processed_image, width, height)
                
                # Generate filename
                filename = f'{doc_name}_fig_{image_id:03d}.{self.output_format}'
                file_path = output_dir / filename
                
                # Save the image
                self._save_image(processed_image, file_path)
                
                # Get image position on page
                bbox = self._get_image_bbox(page, xref)
                
                # Find associated caption
                caption = self._find_caption(page, bbox) if bbox else ''
                
                images.append(ExtractedImage(
                    id=f'page{page_num}_img{img_idx}',
                    page_num=page_num,
                    bbox=bbox or (0, 0, width, height),
                    image_type=image_type,
                    file_path=str(file_path.relative_to(output_dir.parent)),
                    width=width,
                    height=height,
                    format=self.output_format,
                    alt_text='',
                    caption=caption,
                    xref=xref
                ))
                
            except Exception as e:
                print(f'Error extracting image {img_idx} from page {page_num}: {e}')
                continue
        
        return images
    
    def _process_image(self, image_bytes: bytes, ext: str, 
                       width: int, height: int) -> Optional[Image.Image]:
        """Process an extracted image"""
        try:
            # Open image with PIL
            img = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary (for JPEG output)
            if self.output_format.lower() in ['jpg', 'jpeg']:
                if img.mode in ['RGBA', 'P']:
                    # Create white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[3])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
            
            # Resize if too large
            if width > self.max_width:
                ratio = self.max_width / width
                new_height = int(height * ratio)
                img = img.resize((self.max_width, new_height), Image.LANCZOS)
            
            return img
            
        except Exception as e:
            print(f'Error processing image: {e}')
            return None
    
    def _save_image(self, img: Image.Image, file_path: Path) -> None:
        """Save processed image to file"""
        if self.output_format.lower() in ['jpg', 'jpeg']:
            img.save(file_path, 'JPEG', quality=self.jpeg_quality, optimize=True)
        elif self.output_format.lower() == 'png':
            img.save(file_path, 'PNG', optimize=True)
        elif self.output_format.lower() == 'webp':
            img.save(file_path, 'WEBP', quality=self.jpeg_quality)
        else:
            img.save(file_path)
    
    def _classify_image(self, img: Image.Image, width: int, height: int) -> str:
        """Classify the type of image"""
        aspect_ratio = width / height if height > 0 else 1
        
        # Small square-ish images are likely logos/icons
        if width < 200 and height < 200 and 0.8 < aspect_ratio < 1.2:
            return 'logo'
        
        # Very wide images might be charts or diagrams
        if aspect_ratio > 2:
            return 'chart'
        
        # Very tall images might be diagrams
        if aspect_ratio < 0.5:
            return 'diagram'
        
        # Check color distribution for chart detection
        try:
            colors = img.getcolors(maxcolors=1000)
            if colors:
                # Charts often have limited color palettes
                if len(colors) < 50:
                    return 'chart'
        except:
            pass
        
        # Default to figure
        return 'figure'
    
    def _get_image_bbox(self, page: fitz.Page, xref: int) -> Optional[Tuple[float, float, float, float]]:
        """Get the bounding box of an image on the page"""
        # Search for the image in page contents
        for img in page.get_images():
            if img[0] == xref:
                # Try to get the image rectangle
                img_rects = page.get_image_rects(img)
                if img_rects:
                    rect = img_rects[0]
                    return (rect.x0, rect.y0, rect.x1, rect.y1)
        return None
    
    def _find_caption(self, page: fitz.Page, bbox: Tuple[float, float, float, float]) -> str:
        """Find caption text near an image"""
        if not bbox:
            return ''
        
        # Look for text below the image
        search_rect = fitz.Rect(
            bbox[0] - 10,
            bbox[3],  # Start from bottom of image
            bbox[2] + 10,
            bbox[3] + 100  # Search 100 points below
        )
        
        text = page.get_text('text', clip=search_rect).strip()
        
        # Check if it looks like a caption
        import re
        caption_patterns = [
            r'^(Figure|Fig\.?|Image|Img\.?)\s*\d+',
            r'^(Chart|Graph|Diagram)\s*\d+',
        ]
        
        lines = text.split('\\n')
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            if any(re.match(pattern, line, re.IGNORECASE) for pattern in caption_patterns):
                return line
        
        return ''
    
    def _generate_alt_texts(self, images: List[ExtractedImage]) -> List[ExtractedImage]:
        """Generate alt text for images using LLM"""
        for img in images:
            if not img.alt_text and self.llm_service:
                try:
                    img_path = Path(img.file_path)
                    if not img_path.is_absolute():
                        # file_path is stored relative to the output directory parent;
                        # try resolving relative to cwd as a fallback
                        img_path = Path.cwd() / img_path

                    if not img_path.exists():
                        raise FileNotFoundError(f'Image file not found: {img_path}')

                    image_base64 = base64.b64encode(img_path.read_bytes()).decode('utf-8')
                    
                    # Generate description
                    alt_text = self.llm_service.generate_image_description(
                        image_base64, img.image_type
                    )
                    img.alt_text = alt_text
                except Exception as e:
                    print(f'Warning: Could not generate alt text for {img.id}: {e}')
                    img.alt_text = f'{img.image_type.capitalize()} from page {img.page_num + 1}'
        
        return images
    
    def format_for_markdown(self, image: ExtractedImage, relative_path: str = '') -> str:
        """Format an image for markdown output"""
        img_path = f'{relative_path}{image.file_path}' if relative_path else image.file_path
        alt_text = image.alt_text or f'{image.image_type.capitalize()}'
        
        markdown = f'![{alt_text}]({img_path})'
        
        if image.caption:
            markdown += f'\\n*{image.caption}*'
        
        return markdown
    
    def get_image_base64(self, image: ExtractedImage) -> str:
        """Get base64 encoded image data"""
        try:
            return base64.b64encode(Path(image.file_path).read_bytes()).decode('utf-8')
        except Exception:
            return ''
