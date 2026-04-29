# PDF to Markdown Converter

A PDF-to-Markdown conversion pipeline built on the **Directives-Operator-Execution (DOE)** framework. Designed for academic and technical documents — handles complex layouts, mathematical expressions, tables, figures, and OCR artifacts.

Primary backend is [MinerU](https://github.com/opendatalab/MinerU) (native LaTeX formula recognition, layout-aware extraction, multi-language OCR). Falls back to PyMuPDF when MinerU is unavailable. An optional LLM layer (OpenAI / Anthropic / Google) improves math conversion, image captioning, and table reconstruction.

---

## Features

| Capability | Details |
|---|---|
| Text extraction | Reading-order-aware, multi-column layout detection |
| Math | Unicode to LaTeX conversion; MinerU native formula recognition; optional LLM fallback |
| Tables | PyMuPDF table detection; Markdown or HTML output |
| Images | Extraction + optional LLM-generated alt text |
| Post-processing | Fixes garbled URLs, split DOIs, OCR ligatures, spaced decimals, false math regions |
| LLM integration | OpenAI, Anthropic, Google with exponential-backoff retry on rate limits |
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
│       ├── math_processor.py   # Unicode to LaTeX conversion
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

> MinerU requires additional model weights on first run and will download them automatically.
> For OCR on scanned PDFs, install [Tesseract](https://github.com/tesseract-ocr/tesseract) and ensure it is on your `PATH`.

### 2. Configure environment (optional, required for `--use-llm`)

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

| Flag | Description |
|---|---|
| `pdf_path` | Path to the PDF file (required) |
| `-o, --output OUTPUT_DIR` | Output directory (default: `./output/{stem}`) |
| `--use-llm` | Enable LLM assistance for complex content |
| `--provider {openai,anthropic,google}` | LLM provider (default: `openai`) |
| `--no-images` | Skip image extraction |
| `--no-tables` | Skip table processing |
| `--no-math` | Skip math expression conversion |
| `--ocr` | Force OCR for text extraction |
| `--include-toc` | Add table of contents |
| `--include-metadata` | Add YAML front matter |
| `-c, --config CONFIG` | Path to custom `agent_config.yaml` |
| `-v, --verbose` | Verbose output |
| `-q, --quiet` | Suppress all output |

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

All API calls include automatic exponential-backoff retry (up to 3 attempts) on rate-limit and transient errors.

---

## Architecture

The project follows the **Directives-Operator-Execution (DOE)** pattern:

| Layer | Location | Role |
|---|---|---|
| Directives | `Directives/*.md` | SOPs defining what each stage does and why |
| Operator | `Operator/` | LLM service and configuration |
| Execution | `Execution/` | Processors and converters |

`pdf_converter_mineru.py` orchestrates the full pipeline: assess PDF → extract with MinerU → post-process → write output.

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

24 tests cover URL fixing, DOI repair, math formula correction, OCR ligature replacement, heading detection, and whitespace normalisation.

---

## Requirements

- Python 3.9+
- PyMuPDF >= 1.24.0
- MinerU (`pip install magic-pdf` or `marker-pdf`)
- Pillow >= 10.0.0
- OpenAI / Anthropic / Google API key *(only needed for `--use-llm`)*

See `requirements.txt` for the full dependency list.

---

## License

MIT