# SOP 03: Mathematical Expression Processing

## Objective
Detect, extract, and convert mathematical expressions to LaTeX format for markdown.

## Trigger
- Prerequisite: Text extraction completed
- Condition: Mathematical content detected in assessment

## Procedure

### Step 1: Math Detection
Identify mathematical content:
- **Display Math**: Centered equations, numbered equations
- **Inline Math**: Formulas within text flow
- **Mathematical Symbols**: Greek letters, operators, subscripts, superscripts

### Step 2: Math Region Extraction
For each detected math region:
1. Extract bounding box coordinates
2. Render region as high-resolution image (300 DPI minimum)
3. Apply image preprocessing (contrast, denoising)
4. Store original PDF rendering for comparison

### Step 3: LaTeX Conversion
Use multi-stage conversion:

#### Stage A: Direct Symbol Recognition
For simple expressions:
- Map common symbols to LaTeX equivalents
- Handle subscripts/superscripts via position analysis
- Convert Greek letters and operators

#### Stage B: OCR-based Recognition (Marker/Texify)
For complex expressions:
- Use Texify model for equation recognition
- Apply Marker''s built-in math handling
- Generate LaTeX string

#### Stage C: LLM-Assisted Conversion (Operator Involvement)
For ambiguous or complex cases:
- Send image to vision-capable LLM (GPT-4o, Gemini, Claude)
- Request LaTeX representation
- Validate against rendered output

### Step 4: LaTeX Formatting for Markdown
Format LaTeX for markdown compatibility:
- **Inline Math**: Wrap in single dollar signs `$...$`
- **Display Math**: Wrap in double dollar signs `$$...$$`
- Escape special markdown characters within math
- Ensure proper line breaks around display equations

### Step 5: Validation
For each converted equation:
1. Render LaTeX using KaTeX or MathJax
2. Compare visual output with original PDF rendering
3. Flag discrepancies for operator review
4. Log confidence score

## Output
- LaTeX strings for all mathematical content
- Position mapping to original PDF
- Confidence scores per equation
- Validation results

## Mathematical Symbol Reference

### Common Conversions
| Symbol Type | Example | LaTeX |
|-------------|---------|-------|
| Fractions | a/b | `\frac{a}{b}` |
| Subscripts | x | `x_2` |
| Superscripts | x | `x^2` |
| Greek | a, ß, ? | `\alpha`, `\beta`, `\gamma` |
| Summation | S | `\sum` |
| Integral |  | `\int` |
| Square root |  | `\sqrt{}` |
| Limits | lim | `\lim` |

### Complex Structures
- Matrices: `\begin{bmatrix}...\end{bmatrix}`
- Aligned equations: `\begin{aligned}...\end{aligned}`
- Cases: `\begin{cases}...\end{cases}`

## Error Handling
- Recognition failure: Fall back to image embedding with alt text
- Ambiguous notation: Flag for operator review
- Validation failure: Present both versions for selection

## Operator Intervention Points
- Equations with confidence < 80%
- Complex nested structures
- Novel or domain-specific notation
- Handwritten mathematical content
