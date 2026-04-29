# SOP 06: Markdown Assembly and Output

## Objective
Assemble all processed components into a cohesive, well-formatted markdown document.

## Trigger
- Prerequisite: All content processing SOPs completed
- Input: Processed text, math, images, and tables

## Procedure

### Step 1: Document Structure Creation
Build document skeleton:
1. Extract document title from first heading or metadata
2. Create table of contents from headers
3. Establish section hierarchy (H1 > H2 > H3...)
4. Identify front matter (abstract, author info)

### Step 2: Content Assembly
Assemble components in reading order:

#### Header Section
- Title (H1)
- Author(s) and affiliations
- Abstract (if present)
- Keywords

#### Body Content
- Sections with proper heading levels
- Paragraphs with preserved formatting
- Lists (bulleted and numbered)
- Block quotes

#### Special Elements
- Equations (inline and display)
- Tables with captions
- Figures with captions and alt text
- Code blocks with language specification

#### End Matter
- References/Bibliography
- Appendices
- Footnotes

### Step 3: Cross-Reference Resolution
Handle internal references:
- Figure references (Figure 1, Fig. 1)
- Table references (Table 1, Tab. 1)
- Equation references (Equation 1, Eq. 1)
- Section references
- Citation references

### Step 4: Formatting Normalization
Apply consistent formatting:
- Heading capitalization (Title Case or Sentence case)
- Consistent spacing between sections
- Proper line breaks (two spaces or blank line)
- List formatting consistency

### Step 5: Metadata Injection
Add document metadata as YAML front matter:
`yaml
---
title: Document Title
author: Author Name
date: YYYY-MM-DD
source: original_filename.pdf
converted: conversion_timestamp
---
`

### Step 6: Quality Assurance
Final validation:
1. Verify all sections are present
2. Check all images are referenced and exist
3. Validate all links (internal and external)
4. Test math rendering
5. Preview table formatting
6. Spell check (optional)

## Output Structure
`
output/
 document_name.md          # Main markdown file
 images/                   # Extracted images
    fig_001.png
    fig_002.png
 metadata.json            # Conversion metadata
`

## Markdown Best Practices

### Headings
- Single H1 for document title
- Logical heading hierarchy
- No skipping levels (H1 > H3)

### Paragraphs
- Blank line between paragraphs
- No trailing whitespace

### Lists
- Consistent markers (- or *)
- Proper indentation for nested lists

### Code
- Triple backticks with language identifier
- Inline code with single backticks

### Links
- Descriptive link text
- Relative paths for local files

## Error Handling
- Missing sections: Log warning, continue assembly
- Broken references: Flag for operator review
- Rendering issues: Test alternatives, document limitations

## Operator Intervention Points
- Final document review
- Reference resolution conflicts
- Formatting decisions for edge cases
- Quality approval before delivery
