# bib_ocr.py

Detects runner/rider bib numbers in race photos using **EasyOCR**, a free, local, offline OCR engine. No API key, no per-image cost, no internet connection required after the initial model download.

## How it works

For each photo, EasyOCR finds every text region and returns a confidence score. The script keeps only the numeric text that clears a confidence threshold and looks like a bib number (2–5 digits by default), then de-duplicates and writes one row per photo.

## Install

```bash
pip install easyocr
```

EasyOCR pulls in PyTorch automatically. The first run also downloads its recognition model (~100MB) and caches it locally — after that, everything runs fully offline.

## Usage

```bash
# Basic run, CSV output
python bib_ocr.py --input /path/to/photos --output bib_numbers.csv

# Include subfolders
python bib_ocr.py --input /path/to/photos --output bib_numbers.csv --recursive

# Styled spreadsheet instead of CSV
python bib_ocr.py --input /path/to/photos --output bib_numbers.xlsx

# Use a GPU if you have one (much faster)
python bib_ocr.py --input /path/to/photos --output bib_numbers.csv --gpu
```

## Options

| Flag | Default | Purpose |
|---|---|---|
| `--input` | *(required)* | Folder containing JPG photos |
| `--output` | `bib_numbers.csv` | Output path — `.csv` or `.xlsx` |
| `--recursive` | off | Also search subfolders |
| `--min-conf` | `0.35` | Minimum OCR confidence (0–1) to keep a reading |
| `--min-digits` | `2` | Minimum digit count to count as a bib number |
| `--max-digits` | `5` | Maximum digit count to count as a bib number |
| `--gpu` | off | Use a CUDA GPU if available |
| `--languages` | `en` | Comma-separated OCR languages |

## Output format

CSV/XLSX with three columns:

| filename | bib_numbers | notes |
|---|---|---|
| `_5D_0004.JPG` | `129;1171` | |
| `_5D_0100.JPG` | `none` | no numeric text met the confidence/length threshold |

- Multiple bibs in one photo are semicolon-separated.
- `none` means nothing plausible was detected.
- `error` means OCR failed to process that specific file.

## Tuning

- Getting junk numbers from banners, signs, or timestamps? Raise `--min-conf` or narrow `--min-digits`/`--max-digits`.
- Missing real bibs? Lower `--min-conf`.

## Limitations

This is plain text detection, not scene understanding — it can't tell a pinned bib apart from any other number-shaped text in frame (banners, clocks, jersey sponsor numbers), and it struggles with angled, small, blurry, or partially obscured bibs, which are common in action race photography.

In a side-by-side test against a vision-based read of the same 566 photos, this script agreed on only ~60% of photos and produced noticeably more false-positive numbers (190 distinct "bibs" found vs. 150 from the vision-based read, with 101 of those never confirmed). Treat its output as a rough first pass that needs manual review, not a source of truth. For higher reliability, see `../Gemma/bib_gemma.py`, which uses a local vision-language model instead of plain OCR.
