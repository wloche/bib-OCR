# bib_gemma.py

Detects runner/rider bib numbers in race photos using a local **vision-language model** (Google's Gemma, served through [Ollama](https://ollama.com)) instead of plain OCR.

## Why this instead of bib_ocr.py

A vision-language model can *reason* about the image — telling a pinned bib number apart from a sponsor banner number, handling partial occlusion, inferring a likely digit from context — rather than just transcribing whatever text it finds. It should be noticeably more reliable than EasyOCR, closer to the results you'd get from a hosted vision model, at the cost of a heavier local setup (Ollama + a multi-GB model) and slower per-photo processing.

## One-time setup

1. **Install Ollama** (the local model runtime):

   ```bash
   brew install ollama          # or download from https://ollama.com
   ```

   Then either open the Ollama app, or start the background server manually:

   ```bash
   ollama serve
   ```

2. **Pull the vision model** this script targets by default (~4GB download, one-time):

   ```bash
   ollama pull gemma4:e4b
   ```

   Other sizes work too (pass `--model` to use them):

   ```bash
   ollama pull gemma4:e2b     # smaller/faster, less accurate, ~3GB
   ollama pull gemma4:12b     # bigger/slower, more accurate
   ```

3. **Install the Python client:**

   ```bash
   pip install ollama
   ```

## Usage

```bash
# Basic run, CSV output
python bib_gemma.py --input /path/to/photos --output bib_numbers_gemma.csv

# Include subfolders
python bib_gemma.py --input /path/to/photos --output bib_numbers_gemma.csv --recursive

# Styled spreadsheet instead of CSV
python bib_gemma.py --input /path/to/photos --output bib_numbers_gemma.xlsx

# Use a bigger, more accurate model
python bib_gemma.py --input /path/to/photos --model gemma4:12b --output out.csv
```

## Options

| Flag | Default | Purpose |
|---|---|---|
| `--input` | *(required)* | Folder containing JPG photos |
| `--output` | `bib_numbers_gemma.csv` | Output path — `.csv` or `.xlsx` |
| `--recursive` | off | Also search subfolders |
| `--model` | `gemma4:e4b` | Ollama model tag to use |
| `--host` | `http://localhost:11434` | Ollama server URL |
| `--retries` | `1` | Retries if a response can't be parsed |

## Output format

CSV/XLSX with three columns:

| filename | bib_numbers | notes |
|---|---|---|
| `_5D_0004.JPG` | `129;1171` | |
| `_5D_0100.JPG` | `none` | cyclists in team kits, no pinned bib visible |
| `_5D_0200.JPG` | `parse_error` | *(raw model response, truncated)* |

- Multiple bibs in one photo are semicolon-separated.
- `none` means the model found no legible bib number in the photo.
- `parse_error` means the model's reply didn't follow the expected format even after retries — the raw response is kept in `notes` so you can see what happened, rather than the script silently guessing.

## How it works internally

Each photo is sent to the model with a fixed prompt asking it to reply in exactly this shape:

```
BIBS: <comma-separated numbers, or "none">
NOTES: <one short phrase, optional>
```

The script regex-parses that fixed format rather than relying on free-form text, which keeps results consistent across runs.

## Performance

This runs entirely on your machine's CPU/GPU — no internet connection or API key needed once the model is downloaded. Without a GPU, expect roughly a few seconds to tens of seconds per photo depending on model size; processing 566 photos on `e4b` on CPU alone could take anywhere from ~30 minutes to a few hours. A GPU will be dramatically faster. If speed matters more than accuracy, try `--model gemma4:e2b`.

## Limitations

Smaller local vision models are still not as reliable as a top-tier hosted model — expect some misses on very small, heavily motion-blurred, or steeply angled bibs. It should still substantially outperform `../local-OCR/bib_ocr.py` on the same photos, since it can reason about context instead of just transcribing text. Compare its output against `../local-OCR/bib_ocr.py`'s to see where the two disagree, and spot-check `none`/`parse_error` rows manually.
