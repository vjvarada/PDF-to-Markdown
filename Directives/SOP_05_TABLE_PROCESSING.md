# SOP 05: Table Detection and Conversion

## Objective
Detect, extract, and convert tables to proper markdown format.

## Trigger
- Prerequisite: PDF analysis completed
- Condition: Tables detected in document

## Procedure

### Step 1: Table Detection
Identify table regions:
- Bordered tables (visible cell lines)
- Borderless tables (aligned columns)
- Nested tables
- Tables spanning multiple pages

### Step 2: Table Structure Analysis
For each detected table:
1. Identify header rows
2. Determine column count and alignment
3. Detect merged cells (colspan, rowspan)
4. Identify table caption

### Step 3: Cell Content Extraction
Extract content from each cell:
1. Preserve text formatting (bold, italic)
2. Handle multi-line cell content
3. Extract any embedded images or equations
4. Maintain cell alignment

### Step 4: Multi-Page Table Handling
For tables spanning pages:
1. Detect continuation patterns
2. Match header rows across pages
3. Merge table segments
4. Validate row continuity

### Step 5: Markdown Conversion
Convert to GitHub-Flavored Markdown tables.

For complex tables (merged cells), use HTML tables instead.

### Step 6: Alignment Specification
Set column alignment:
- Left: |:---|
- Center: |:---:|
- Right: |---:|

## Output
- Markdown table syntax
- Table metadata (row count, column count)
- Caption associations
- Complexity assessment

## Quality Checks
- Verify all cells are extracted
- Check column alignment is correct
- Validate merged cells render properly
- Test table in markdown preview

## Error Handling
- Complex merged cells: Fall back to HTML table
- Undetected columns: Use LLM for structure inference
- Broken tables: Flag for manual reconstruction

## Operator Intervention Points
- Tables with complex merged cells
- Multi-page tables requiring merge confirmation
- Tables with ambiguous structure
- Financial or data tables requiring accuracy verification
