# PDF to Markdown Converter

A sophisticated PDF to Markdown conversion agent built using the **Directives-Operator-Execution (DOE)** framework. This tool handles complex PDFs including mathematical expressions, images, and tables, converting them to clean, structured Markdown.

## Features

- **Text Extraction**: High-fidelity text extraction with reading order preservation
- **Math Processing**: Convert mathematical expressions to LaTeX (inline `$...$` and display `# PDF to Markdown Converter - Environment Variables
# Copy this file to .env and fill in your API keys

# ===========================================
# LLM API Keys (required for --use-llm flag)
# ===========================================

# OpenAI API Key (for GPT-4, GPT-4o)
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-openai-api-key-here

# Anthropic API Key (for Claude)
# Get from: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# Google API Key (for Gemini)
# Get from: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=your-google-api-key-here

# ===========================================
# Optional Configuration
# ===========================================

# Default LLM provider (openai, anthropic, or google)
DEFAULT_LLM_PROVIDER=openai

# Model overrides (optional)
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
GOOGLE_MODEL=gemini-1.5-pro

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Output directory (default: ./output)
# OUTPUT_DIR=./output

# Maximum image size in KB (images larger will be compressed)
# MAX_IMAGE_SIZE_KB=500

# ===========================================
# OCR Configuration (optional)
# ===========================================

# Tesseract OCR path (if not in system PATH)
# Windows: C:\\Program Files\\Tesseract-OCR\\tesseract.exe
# Linux/Mac: /usr/bin/tesseract
# TESSERACT_PATH=

# OCR language (default: eng)
# OCR_LANGUAGE=eng...# PDF to Markdown Converter - Environment Variables
# Copy this file to .env and fill in your API keys

# ===========================================
# LLM API Keys (required for --use-llm flag)
# ===========================================

# OpenAI API Key (for GPT-4, GPT-4o)
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-openai-api-key-here

# Anthropic API Key (for Claude)
# Get from: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# Google API Key (for Gemini)
# Get from: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=your-google-api-key-here

# ===========================================
# Optional Configuration
# ===========================================

# Default LLM provider (openai, anthropic, or google)
DEFAULT_LLM_PROVIDER=openai

# Model overrides (optional)
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
GOOGLE_MODEL=gemini-1.5-pro

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Output directory (default: ./output)
# OUTPUT_DIR=./output

# Maximum image size in KB (images larger will be compressed)
# MAX_IMAGE_SIZE_KB=500

# ===========================================
# OCR Configuration (optional)
# ===========================================

# Tesseract OCR path (if not in system PATH)
# Windows: C:\\Program Files\\Tesseract-OCR\\tesseract.exe
# Linux/Mac: /usr/bin/tesseract
# TESSERACT_PATH=

# OCR language (default: eng)
# OCR_LANGUAGE=eng`)
- **Image Handling**: Extract and embed images with captions and alt text
- **Table Conversion**: Convert tables to Markdown or HTML format
- **LLM Integration**: Optional LLM assistance for complex conversions
- **Multiple LLM Providers**: Support for OpenAI, Anthropic, and Google

## Architecture (DOE Framework)

`
PDF to Markdown/
+-- Directives/           # SOPs for processing alignment
|   +-- SOP_01_PDF_ANALYSIS.md
|   +-- SOP_02_TEXT_EXTRACTION.md
|   +-- SOP_03_MATH_PROCESSING.md
|   +-- SOP_04_IMAGE_PROCESSING.md
|   +-- SOP_05_TABLE_PROCESSING.md
|   +-- SOP_06_MARKDOWN_ASSEMBLY.md
+-- Operator/             # LLM thinking and decision making
|   +-- agent_config.yaml
|   +-- llm_service.py
+-- Execution/            # Deterministic processing scripts
|   +-- pdf_converter.py
|   +-- processors/
|       +-- pdf_analyzer.py
|       +-- text_extractor.py
|       +-- math_processor.py
|       +-- image_processor.py
|       +-- table_processor.py
|       +-- markdown_assembler.py
+-- input/                # Place PDFs here
+-- output/               # Converted files go here
+-- convert.py            # CLI entry point
`

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pdf-to-markdown.git
cd pdf-to-markdown
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. (Optional) Set up LLM integration:
```bash
cp .env.template .env
# Edit .env with your API keys
```

## Usage

### Basic Conversion

```bash
python convert.py document.pdf
```

### Specify Output Directory

```bash
python convert.py document.pdf -o ./my_output
```

### Use LLM Assistance

```bash
python convert.py document.pdf --use-llm
python convert.py document.pdf --use-llm --provider anthropic
```

### Additional Options

```bash
python convert.py document.pdf --include-toc        # Add table of contents
python convert.py document.pdf --include-metadata   # Add YAML front matter
python convert.py document.pdf --no-images          # Skip image extraction
python convert.py document.pdf --ocr                # Force OCR mode
python convert.py document.pdf -v                   # Verbose output
```

### Using Configuration File

```bash
python convert.py document.pdf -c Operator/agent_config.yaml
```

## Configuration

The `Operator/agent_config.yaml` file controls all aspects of the conversion:

```yaml
llm:
  primary_provider: openai
  models:
    openai: gpt-4o
    anthropic: claude-3-5-sonnet-20241022
    google: gemini-1.5-pro

processing:
  math:
    enabled: true
    prefer_latex: true
  images:
    enabled: true
    max_size_kb: 500
  tables:
    format: markdown  # or html
```

## Math Expression Handling

Mathematical expressions are converted to LaTeX format:

- **Inline math**: ` = mc^2$`
- **Display math**: 
  ```
  # PDF to Markdown Converter - Environment Variables
# Copy this file to .env and fill in your API keys

# ===========================================
# LLM API Keys (required for --use-llm flag)
# ===========================================

# OpenAI API Key (for GPT-4, GPT-4o)
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-openai-api-key-here

# Anthropic API Key (for Claude)
# Get from: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# Google API Key (for Gemini)
# Get from: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=your-google-api-key-here

# ===========================================
# Optional Configuration
# ===========================================

# Default LLM provider (openai, anthropic, or google)
DEFAULT_LLM_PROVIDER=openai

# Model overrides (optional)
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
GOOGLE_MODEL=gemini-1.5-pro

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Output directory (default: ./output)
# OUTPUT_DIR=./output

# Maximum image size in KB (images larger will be compressed)
# MAX_IMAGE_SIZE_KB=500

# ===========================================
# OCR Configuration (optional)
# ===========================================

# Tesseract OCR path (if not in system PATH)
# Windows: C:\\Program Files\\Tesseract-OCR\\tesseract.exe
# Linux/Mac: /usr/bin/tesseract
# TESSERACT_PATH=

# OCR language (default: eng)
# OCR_LANGUAGE=eng
  \int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
  # PDF to Markdown Converter - Environment Variables
# Copy this file to .env and fill in your API keys

# ===========================================
# LLM API Keys (required for --use-llm flag)
# ===========================================

# OpenAI API Key (for GPT-4, GPT-4o)
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-openai-api-key-here

# Anthropic API Key (for Claude)
# Get from: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# Google API Key (for Gemini)
# Get from: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=your-google-api-key-here

# ===========================================
# Optional Configuration
# ===========================================

# Default LLM provider (openai, anthropic, or google)
DEFAULT_LLM_PROVIDER=openai

# Model overrides (optional)
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
GOOGLE_MODEL=gemini-1.5-pro

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Output directory (default: ./output)
# OUTPUT_DIR=./output

# Maximum image size in KB (images larger will be compressed)
# MAX_IMAGE_SIZE_KB=500

# ===========================================
# OCR Configuration (optional)
# ===========================================

# Tesseract OCR path (if not in system PATH)
# Windows: C:\\Program Files\\Tesseract-OCR\\tesseract.exe
# Linux/Mac: /usr/bin/tesseract
# TESSERACT_PATH=

# OCR language (default: eng)
# OCR_LANGUAGE=eng
  ```

The converter handles:
- Greek letters (alpha, beta, gamma, etc.)
- Operators (sum, integral, product, etc.)
- Fractions, subscripts, and superscripts
- Matrices and equation arrays

## LLM Integration

When `--use-llm` is enabled, the LLM assists with:

1. **Complex math recognition**: Converting ambiguous mathematical notation
2. **Image descriptions**: Generating alt text for figures
3. **Table reconstruction**: Fixing malformed tables
4. **Reading order**: Determining correct text flow in multi-column layouts

## Output Format

The converter generates:

1. **Markdown file** (`document.md`): The converted content
2. **Images folder** (`images/`): Extracted figures and diagrams
3. **Conversion report** (`conversion_report.json`): Processing metadata

## SOPs (Standard Operating Procedures)

The Directives folder contains detailed SOPs that guide the conversion:

| SOP | Purpose |
|-----|---------|
| SOP 01 | PDF Analysis and Assessment |
| SOP 02 | Text Extraction Protocol |
| SOP 03 | Mathematical Expression Processing |
| SOP 04 | Image Processing and Embedding |
| SOP 05 | Table Detection and Conversion |
| SOP 06 | Final Markdown Assembly |

## Requirements

- Python 3.9+
- PyMuPDF (fitz)
- Pillow
- PyYAML
- python-dotenv
- Optional: OpenAI/Anthropic/Google API keys for LLM features

## License

MIT License

## Contributing

Contributions are welcome! Please read the SOPs in the Directives folder to understand the processing pipeline before making changes.
