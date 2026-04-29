# SOP 02: Text Extraction

## Objective
Extract raw text content from PDF while preserving structural information.

## Trigger
- Prerequisite: SOP 01 completed successfully
- Input: PDF document and assessment report

## Procedure

### Step 1: Text Extraction Method Selection
Based on PDF type from assessment:
- **Digital PDF**: Use PyMuPDF direct text extraction
- **Scanned PDF**: Use OCR pipeline (Surya OCR via Marker)
- **Mixed PDF**: Use hybrid approach per page

### Step 2: Extract Text with Position Data
For each page:
1. Extract text blocks with bounding boxes
2. Preserve font information (size, style, family)
3. Record reading order
4. Identify paragraph breaks and line breaks

### Step 3: Structure Identification
Detect and tag:
- **Headers**: Large font, bold, short text blocks
- **Body Text**: Regular font, continuous paragraphs
- **Lists**: Bullet points, numbered items
- **Captions**: Text near figures/tables, often italicized
- **Footnotes**: Small font at page bottom

### Step 4: Text Cleanup
1. Remove hyphenation at line breaks
2. Merge split paragraphs across pages
3. Handle ligatures and special characters
4. Normalize whitespace
5. Preserve intentional formatting

## Output
- Structured text blocks with metadata
- Position information for each block
- Font and style information
- Reading order mapping

## Quality Checks
- Verify no text blocks are missed
- Check for encoding issues (garbled text)
- Validate reading order makes sense
- Compare extracted page count with PDF page count

## Error Handling
- Encoding errors: Try multiple encodings, log warning
- Missing fonts: Use fallback rendering
- OCR failures: Retry with different settings, mark as uncertain
