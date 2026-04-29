# SOP 04: Image and Figure Processing

## Objective
Extract, optimize, and properly reference images and figures in markdown output.

## Trigger
- Prerequisite: PDF analysis completed
- Condition: Images or figures detected in document

## Procedure

### Step 1: Image Detection and Classification
Identify and classify visual content:
- **Photographs**: Raster images, photos
- **Diagrams**: Vector graphics, flowcharts, architecture diagrams
- **Charts**: Bar charts, line graphs, pie charts
- **Figures**: Scientific figures, plots
- **Logos/Icons**: Small graphical elements
- **Equations as Images**: Math rendered as images (convert to LaTeX)

### Step 2: Image Extraction
For each detected image:
1. Extract at highest available resolution
2. Determine optimal format:
   - PNG for diagrams, charts, screenshots (lossless)
   - JPEG for photographs (lossy, smaller size)
   - SVG for vector graphics if available
3. Apply resolution threshold (min 150 DPI for print, 72 DPI for web)
4. Extract image metadata (dimensions, color space)

### Step 3: Image Optimization
Process extracted images:
1. Remove alpha channel if not needed
2. Convert color space to RGB if necessary
3. Compress appropriately (PNG optimization, JPEG quality 85%)
4. Resize if excessively large (max 2000px width for web)
5. Generate thumbnails if needed

### Step 4: Caption Association
Link images with their captions:
1. Find text blocks in proximity to image
2. Identify caption patterns ("Figure X:", "Fig.", caption numbering)
3. Associate caption text with corresponding image
4. Preserve figure numbering for cross-references

### Step 5: Alt Text Generation
For accessibility and SEO:
- **Simple images**: Generate descriptive alt text automatically
- **Complex figures**: Use LLM to generate detailed description
- **Charts/Graphs**: Describe data trends and key values
- **Diagrams**: Describe structure and relationships

### Step 6: Markdown Integration
Format for markdown:
```markdown
![Alt text description](images/figure_001.png)
*Figure 1: Caption text here*
```

Or with HTML for more control:
```markdown
<figure>
  <img src="images/figure_001.png" alt="Alt text">
  <figcaption>Figure 1: Caption text</figcaption>
</figure>
```

## Output
- Extracted image files (organized in images/ folder)
- Image manifest with metadata
- Markdown image references
- Alt text for each image
- Caption associations

## File Naming Convention
Format: `{document_name}_fig_{number}_{type}.{ext}`
Example: `research_paper_fig_001_chart.png`

## Quality Checks
- Verify image quality meets minimum threshold
- Check for corrupt or unreadable images
- Validate all images are properly referenced
- Confirm captions are correctly associated

## Error Handling
- Corrupt image: Log error, attempt re-extraction, use placeholder
- Missing caption: Generate automatic description, flag for review
- Low resolution: Upscale if possible, or note limitation

## Operator Intervention Points
- Images requiring detailed alt text for accessibility
- Figures needing manual caption association
- Complex diagrams requiring interpretation
- Charts where data extraction is beneficial
