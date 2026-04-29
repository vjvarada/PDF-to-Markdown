# PDF to Markdown Converter

A PDF-to-Markdown conversion pipeline built on the **Directives-Operator-Execution (DOE)** framework. Designed for academic and technical documents — handles complex layouts, mathematical expressions, tables, figures, and OCR artifacts.

Primary backend is [MinerU](https://github.com/opendatalab/MinerU) (native LaTeX formula recognition, layout-aware extraction, multi-language OCR). Falls back to PyMuPDF when MinerU is unavailable. An optional LLM layer (OpenAI / Anthropic / Google) improves math conversion, image captioning, and table reconstruction.

---

## Features

| Capability | Details |
|---|---|
| Text extraction | Reading-order–aware, multi-column layout detection |
| Math | Unicode → LaTeX conversion; MinerU native formula recognition; optional LLM fallback |
| Tables | PyMuPDF table detection; Markdown or HTML output |
| Images | Extraction + optional LLM-generated alt text |
| Post-processing | Fixes garbled URLs, split DOIs, OCR ligatures, spaced decimals, false math regions |
| LLM integration | OpenAI, Anthropic, Google — with exponential-backoff retry on rate limits |
| Output | `{stem}.md` + `conversion_report.json` + `images/` per document |

---

## Project Structure

```
PDF-to-Markdown/
├── convert.py                  # CLI entry point
├── requirements.txt
├── .env.template               # API key template
│
├── Directives/                 # SOPs defining each processing stage
│   ├── SOP_01_PDF_ANALYSIS.md
│   ├── SOP_02_TEXT_EXTRACTION.md
│   ├── SOP_03_MATH_PROCESSING.md
│   ├── SOP_04_IMAGE_PROCESSING.md
│   ├── SOP_05_TABLE_PROCESSING.md
│   ├── SOP_06_MARKDOWN_ASSEMBLY.md
│   └── SOP_07_POST_CONVERSION_FIXES.md
│
├── Operator/
│   ├── agent_config.yaml       # LLM provider / model configuration
│   └── llm_service.py          # OpenAI + Anthropic API calls with retry
│
├── Execution/
│   ├── pdf_converter_mineru.py # Primary converter (MinerU backend)
│   ├── pdf_converter.py        # Fallback converter (PyMuPDF backend)
│   └── processors/
│       ├── pdf_analyzer.py     # PDF assessment and routing
│       ├── text_extractor.py   # Text extraction + ligature repair
│       ├── math_processor.py   # Unicode → LaTeX conversion
│       ├── image_processor.py  # Image extraction + alt text
│       ├── table_processor.py  # Table detection and formatting
│       └── post_processor.py   # Post-conversion fixes
│
├── tests/
│   └── test_post_processor.py  # 24 unit tests for post-processing
│
└── input/                      # Drop PDFs here
```

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> MinerU requires additional model weights on first run — it will download them automatically.  
> For OCR on scanned PDFs, install [Tesseract](https://github.com/tesseract-ocr/tesseract) and ensure it is on your `PATH`.

### 2. Configure environment (optional — required for `--use-llm`)

```bash
cp .env.template .env
# Edit .env and add your API keys
```

### 3. Convert a PDF

```bash
# Basic conversion
python convert.py document.pdf

# Specify output directory
python convert.py document.pdf -o ./output

# Enable LLM assistance (requires API keys in .env)
python convert.py document.pdf --use-llm

# Use Anthropic instead of OpenAI
python convert.py document.pdf --use-llm --provider anthropic

# Skip image extraction
python convert.py document.pdf --no-images

# Force OCR (for scanned PDFs)
python convert.py document.pdf --ocr

# Add YAML front matter and table of contents
python convert.py document.pdf --include-metadata --include-toc
```

Output is written to `output/{document_stem}/`:

```
output/my-paper/
├── my-paper.md
├── conversion_report.json
└── images/
    ├── figure-1.png
    └── ...
```

---

## CLI Reference

```
usage: convert.py [-h] [-o OUTPUT_DIR] [--use-llm] [--provider {openai,anthropic,google}]
                  [--no-images] [--no-tables] [--no-math] [--ocr]
                  [--include-toc] [--include-metadata]
                  [-c CONFIG] [-v] [-q]
                  pdf_path

positional arguments:
  pdf_path                      Path to the PDF file

options:
  -o, --output OUTPUT_DIR       Output directory (default: ./output/{stem})
  --use-llm                     Enable LLM assistance for complex content
  --provider {openai,anthropic,google}
                                LLM provider (default: openai)
  --no-images                   Skip image extraction
  --no-tables                   Skip table processing
  --no-math                     Skip math expression conversion
  --ocr                         Force OCR for text extraction
  --include-toc                 Add table of contents
  --include-metadata            Add YAML front matter
  -c, --config CONFIG           Path to custom agent_config.yaml
  -v, --verbose                 Verbose output
  -q, --quiet                   Suppress all output
```

---

## LLM Configuration

Edit `Operator/agent_config.yaml` to change models or providers:

```yaml
llm:
  primary:
    provider: openai       # openai | anthropic | google
    model: gpt-4o
    temperature: 0.1
  fallback:
    provider: openai
    model: gpt-4o-mini
  vision:
    provider: openai
    model: gpt-4o
```

Supported providers: **OpenAI** (GPT-4o), **Anthropic** (Claude 3.5 Sonnet), **Google** (Gemini 1.5 Pro).

API calls include automatic exponential-backoff retry (up to 3 attempts) on rate-limit and transient errors.

---

## Architecture — DOE Framework

```
Directives  →  SOPs in /Directives/*.md   (what to do and why)
Operator    →  LLM service + config        (how to use AI assistance)
Execution   →  Processors + converters     (implementation)
```

The seven SOPs define processing stages from PDF analysis through final markdown assembly. `pdf_converter_mineru.py` orchestrates the pipeline: assess → extract (MinerU) → post-process → write output.

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

24 tests cover URL fixing, DOI repair, math formula correction, OCR ligature replacement, table of contents detection, and whitespace normalisation.

---

## Requirements

- Python 3.9+
- PyMuPDF ≥ 1.24.0
- MinerU (installed via `pip install magic-pdf` or `marker-pdf`)
- Pillow ≥ 10.0.0
- An OpenAI / Anthropic / Google API key *(only needed for `--use-llm`)*

See `requirements.txt` for the full dependency list.

---

## License

MIT
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
