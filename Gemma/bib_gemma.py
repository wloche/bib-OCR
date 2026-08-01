#!/usr/bin/env python3
"""
bib_gemma.py — Detect runner/rider bib numbers in race photos using a local
vision-language model (Google's Gemma, served through Ollama).

Unlike plain OCR (see bib_ocr.py), a vision-language model can *reason* about
the image — telling a pinned bib number apart from a sponsor banner number,
handling partial occlusion, guessing at an angled/blurry digit from context,
etc. It should be noticeably more reliable than EasyOCR, at the cost of being
slower per photo and needing a heavier local runtime (Ollama + a multi-GB
model download) instead of a small pip package.

────────────────────────────────────────────────────────────────────────────
ONE-TIME SETUP
────────────────────────────────────────────────────────────────────────────
1. Install Ollama (the local model runtime):
     macOS:   brew install ollama        (or download from https://ollama.com)
     Then either open the Ollama app, or start the background server manually:
         ollama serve

2. Pull the vision model this script targets (~4GB download, one-time):
     ollama pull gemma4:e4b

   Other sizes work too (pass --model to use them):
     ollama pull gemma4:e2b     # smaller/faster, less accurate, ~3GB
     ollama pull gemma4:12b     # bigger/slower, more accurate

3. Install the Python client:
     pip install ollama

────────────────────────────────────────────────────────────────────────────
USAGE
────────────────────────────────────────────────────────────────────────────
    python bib_gemma.py --input /path/to/photos --output bib_numbers_gemma.csv
    python bib_gemma.py --input /path/to/photos --output bib_numbers_gemma.xlsx --recursive
    python bib_gemma.py --input /path/to/photos --model gemma4:12b --output out.csv
    python bib_gemma.py --input /path/to/photos --limit 10 --output sample.csv
    python bib_gemma.py --input /path/to/photos --quiet --output out.csv

OUTPUT
    A CSV (or XLSX, if the output filename ends in .xlsx) with one row per photo:
        filename, bib_numbers, notes
    Multiple bibs in one photo are separated with semicolons: "482;217"
    "none" means the model found no legible bib number in the photo.

PROGRESS
    Each photo prints its own line as it finishes, with the time that photo
    took, the total elapsed time, and an ETA for the whole run based on the
    average per-photo time so far:
        [12/566] _5D_0012.JPG ... 129;1171 [8.4s, elapsed 1m 41s, ETA 1h 17m 30s]
    The final summary reports the total wall-clock time and the average time
    per photo, which is handy for estimating a bigger batch or comparing models.

    Use --limit N for a quick trial run over just the first N photos — the
    script says up front how many of the photos it found are being skipped,
    and repeats that reminder at the end so a partial output file isn't
    mistaken for a complete one.

    --quiet silences all of that (progress lines, ETA, the --limit notice and
    the final summary) and leaves only errors and warnings, on stderr: a
    per-photo "parse_error: <file>: <raw response>" line for each photo that
    failed, plus the usual fatal errors. Handy for cron jobs and scripts —
    redirect stderr to a log and no news is good news. The output CSV/XLSX is
    identical either way.

NOTES
    - This calls a local Ollama server (default http://localhost:11434) — no
      internet connection or API key is used once the model is downloaded.
    - Runs entirely on your machine's CPU/GPU. Without a GPU, expect roughly
      a few seconds to tens of seconds per photo depending on model size —
      566 photos could take anywhere from ~30 minutes to a few hours on the
      e4b model on CPU alone. A GPU will be dramatically faster.
    - If a response can't be parsed (model didn't follow the expected format),
      the row is marked "parse_error" with the raw response in notes so you
      can inspect what happened, rather than silently guessing.
"""

import argparse
import base64
import csv
import re
import sys
import time
from pathlib import Path

PROMPT = """You are looking at a photo from a running/cycling race. Look carefully at every person in the frame for a race bib number — a numbered card, tag, or plate pinned to someone's chest, waist, or back (or printed directly on a jersey).

Respond in EXACTLY this format, nothing else:

BIBS: <comma-separated numbers, or "none" if no legible bib is visible>
NOTES: <one short phrase — leave blank if nothing notable, e.g. "back bib" or "partially obscured">

Examples of valid responses:
BIBS: 482
NOTES:

BIBS: 482, 217, 90
NOTES: one bib partially cropped at frame edge

BIBS: none
NOTES: cyclists in team kits, no pinned bib visible
"""

BIBS_RE = re.compile(r"BIBS:\s*(.+)", re.IGNORECASE)
NOTES_RE = re.compile(r"NOTES:\s*(.*)", re.IGNORECASE)


def format_duration(seconds: float) -> str:
    """Human-readable duration: '42s', '3m 07s', '1h 24m 09s'."""
    seconds = int(round(max(seconds, 0)))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def find_images(input_dir: Path, recursive: bool, extensions):
    pattern = "**/*" if recursive else "*"
    files = []
    for ext in extensions:
        files.extend(input_dir.glob(f"{pattern}.{ext}"))
        files.extend(input_dir.glob(f"{pattern}.{ext.upper()}"))
    return sorted(set(files))


def parse_response(text: str):
    """Pull bib numbers + notes out of the model's reply. Returns (bibs_str, notes, ok)."""
    bibs_match = BIBS_RE.search(text)
    if not bibs_match:
        return None, text.strip()[:200], False

    raw_bibs = bibs_match.group(1).strip()
    notes_match = NOTES_RE.search(text)
    notes = notes_match.group(1).strip() if notes_match else ""

    if raw_bibs.lower().startswith("none"):
        return "none", notes, True

    # pull out just the digit runs, in order, deduplicated
    nums = re.findall(r"\d+", raw_bibs)
    seen = set()
    unique = []
    for n in nums:
        if n not in seen:
            seen.add(n)
            unique.append(n)

    if not unique:
        return "none", notes, True

    return ";".join(unique), notes, True


def write_csv(rows, output_path: Path):
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "bib_numbers", "notes"])
        writer.writerows(rows)


def write_xlsx(rows, output_path: Path):
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
    except ImportError:
        print("openpyxl is required for .xlsx output. Install it with:\n    pip install openpyxl",
              file=sys.stderr)
        sys.exit(1)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bib Numbers"

    ws.append(["Photo Filename", "Bib Number(s)", "Notes"])
    for row in rows:
        ws.append(row)

    header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
    header_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    for col in range(1, 4):
        c = ws.cell(row=1, column=col)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center", vertical="center")

    body_font = Font(name="Arial", size=10)
    none_fill = PatternFill(start_color="F3F4F6", end_color="F3F4F6", fill_type="solid")
    error_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    for r in range(2, ws.max_row + 1):
        for c in range(1, 4):
            ws.cell(row=r, column=c).font = body_font
        val = str(ws.cell(row=r, column=2).value or "").strip().lower()
        if val == "none":
            ws.cell(row=r, column=2).fill = none_fill
        elif val in ("parse_error", "error"):
            ws.cell(row=r, column=2).fill = error_fill

    for i, w in enumerate([22, 30, 55], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:C{ws.max_row}"
    wb.save(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Detect bib numbers in race photos using a local Gemma vision model via Ollama."
    )
    parser.add_argument("--input", required=True, help="Folder containing JPG photos")
    parser.add_argument("--output", default="bib_numbers_gemma.csv",
                         help="Output path (.csv or .xlsx). Default: bib_numbers_gemma.csv")
    parser.add_argument("--recursive", action="store_true", help="Also search subfolders")
    parser.add_argument("--model", default="gemma4:e4b",
                         help="Ollama model tag to use. Default: gemma4:e4b")
    parser.add_argument("--host", default="http://localhost:11434",
                         help="Ollama server URL. Default: http://localhost:11434")
    parser.add_argument("--retries", type=int, default=1,
                         help="Retries if the model's response can't be parsed. Default: 1")
    parser.add_argument("--limit", type=int, default=None,
                         help="Only process the first N photos found (useful for a quick "
                              "test run or benchmarking a model). Default: all of them")
    parser.add_argument("--quiet", action="store_true",
                         help="Suppress progress, ETA and summary output — report only "
                              "errors and warnings (on stderr). Useful for cron/scripts.")
    args = parser.parse_args()

    def info(*parts, **kwargs):
        """Print normal progress output, unless --quiet was passed."""
        if not args.quiet:
            print(*parts, **kwargs)

    input_dir = Path(args.input)
    if not input_dir.is_dir():
        print(f"Error: '{input_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    if args.limit is not None and args.limit < 1:
        print("Error: --limit must be 1 or greater", file=sys.stderr)
        sys.exit(1)

    try:
        import ollama
    except ImportError:
        print("The 'ollama' Python package is not installed. Install it with:\n    pip install ollama",
              file=sys.stderr)
        sys.exit(1)

    client = ollama.Client(host=args.host)

    # Fail fast with a clear message if Ollama isn't reachable or the model isn't pulled.
    try:
        available = {m["model"] for m in client.list().get("models", [])}
    except Exception as e:
        print(f"Could not reach Ollama at {args.host} ({e}).\n"
              f"Make sure Ollama is running (try: ollama serve) and try again.", file=sys.stderr)
        sys.exit(1)

    if available and not any(args.model in m or m.startswith(args.model) for m in available):
        print(f"Warning: '{args.model}' doesn't appear in `ollama list`. "
              f"If this fails, run: ollama pull {args.model}", file=sys.stderr)

    images = find_images(input_dir, args.recursive, extensions=["jpg", "jpeg"])
    if not images:
        print(f"No JPG files found in '{input_dir}'"
              f"{' (searched recursively)' if args.recursive else ''}.", file=sys.stderr)
        sys.exit(1)

    total_found = len(images)
    if args.limit is not None and args.limit < total_found:
        images = images[:args.limit]
        info(f"NOTE: --limit {args.limit} is set — only the first {args.limit} of "
             f"{total_found} photo(s) found will be processed. The output file will "
             f"cover those {args.limit} photo(s) only.")

    info(f"Processing {len(images)} photo(s). Using model '{args.model}' via Ollama at {args.host}.")

    rows = []
    run_start = time.monotonic()
    for i, img_path in enumerate(images, 1):
        # No newline yet: the timing/ETA is appended once this photo is done.
        info(f"[{i}/{len(images)}] {img_path.name} ... ", end="", flush=True)
        photo_start = time.monotonic()

        bibs, notes, ok = None, "", False
        last_raw = ""
        for attempt in range(args.retries + 1):
            try:
                response = client.chat(
                    model=args.model,
                    messages=[{
                        "role": "user",
                        "content": PROMPT,
                        "images": [str(img_path)],
                    }],
                )
                text = response["message"]["content"]
                last_raw = text
                bibs, notes, ok = parse_response(text)
                if ok:
                    break
            except Exception as e:
                last_raw = f"request failed: {e}"
                ok = False

        if ok:
            rows.append([img_path.name, bibs, notes])
        else:
            detail = last_raw.replace("\n", " ")[:200]
            rows.append([img_path.name, "parse_error", detail])
            if args.quiet:
                # The inline progress line is hidden, so failures still need a voice.
                print(f"parse_error: {img_path.name}: {detail}", file=sys.stderr)

        # ETA from the average time per photo so far, which smooths out the
        # variation between a quick photo and a slow, crowded one.
        photo_secs = time.monotonic() - photo_start
        elapsed = time.monotonic() - run_start
        remaining = len(images) - i
        summary = bibs if ok else "parse_error"
        if remaining:
            eta = (elapsed / i) * remaining
            info(f"{summary} [{photo_secs:.1f}s, elapsed {format_duration(elapsed)}, "
                 f"ETA {format_duration(eta)}]")
        else:
            info(f"{summary} [{photo_secs:.1f}s, elapsed {format_duration(elapsed)}]")

    total_secs = time.monotonic() - run_start

    output_path = Path(args.output)
    if output_path.suffix.lower() == ".xlsx":
        write_xlsx(rows, output_path)
    else:
        write_csv(rows, output_path)

    detected = sum(1 for r in rows if r[1] not in ("none", "parse_error"))
    errors = sum(1 for r in rows if r[1] == "parse_error")
    skipped = total_found - len(rows)
    info(f"\nDone. {detected}/{len(rows)} photos had a plausible bib number "
         f"({errors} parse errors). Wrote results to {output_path}")
    if skipped:
        info(f"Reminder: --limit was set, so {skipped} of the {total_found} photo(s) "
             f"found were not processed.")
    info(f"Total time: {format_duration(total_secs)} "
         f"({total_secs / len(rows):.1f}s per photo average)")


if __name__ == "__main__":
    main()
