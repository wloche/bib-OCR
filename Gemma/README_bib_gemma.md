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

# Quick trial run over just the first 10 photos
python bib_gemma.py --input /path/to/photos --limit 10 --output sample.csv

# Silent run — only errors are reported (for cron jobs and scripts)
python bib_gemma.py --input /path/to/photos --quiet --output out.csv

# Discard readings outside the race's actual number range
python bib_gemma.py --input /path/to/photos --bib-range 1000-1699 --output out.csv

# Tune the prompt to the discipline
python bib_gemma.py --input ./running-photos --race-type runners  --output run.csv
python bib_gemma.py --input ./cycling-photos --race-type cyclists --output ride.csv

# Also record each person's team, matched against the teams you know are racing
python bib_gemma.py --input /path/to/photos --teams "xXx, 606" --output out.csv
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
| `--limit` | *(all)* | Only process the first N photos found |
| `--quiet` | off | Report only errors and warnings, on stderr |
| `--min-digits` | off | Discard readings with fewer than N digits |
| `--bib-range` | off | Discard readings outside `LOW-HIGH`, e.g. `1000-1699` |
| `--race-type` | `mixed` | Tune the prompt: `runners`, `cyclists` or `mixed` |
| `--teams` | off | Add a `team` column; optionally pass the known team names |

## Progress and timing

Each photo prints a line as it finishes, showing what was found, how long that photo took, the total elapsed time, and an ETA for the rest of the run:

```
Found 566 photo(s). Using model 'gemma4:e4b' via Ollama at http://localhost:11434.
[1/566] _5D_0004.JPG ... 129;1171 [9.1s, elapsed 9s, ETA 1h 25m 44s]
[2/566] _5D_0005.JPG ... none [7.8s, elapsed 17s, ETA 1h 20m 08s]
[3/566] _5D_0006.JPG ... 482;217 [8.4s, elapsed 25s, ETA 1h 18m 52s]
...
[566/566] _5D_0570.JPG ... 903 [8.2s, elapsed 1h 19m 12s]

Done. 498/566 photos had a plausible bib number (3 parse errors). Wrote results to bib_numbers_gemma.csv
Total time: 1h 19m 12s (8.4s per photo average)
```

The ETA is the average time per photo so far multiplied by the number of photos remaining, so it settles down after the first handful and drifts as it goes if some photos are much slower than others. The final `Total time` line also reports the per-photo average — useful for estimating a larger batch or comparing `e2b` against `e4b` against `12b` on the same folder.

## Trial runs with `--limit`

Before committing to a multi-hour run over a full shoot, `--limit N` processes only the first N photos (in the same sorted order the script would otherwise use). It's the quickest way to sanity-check the setup, eyeball accuracy on a sample, or time a model on your hardware.

```bash
python bib_gemma.py --input /path/to/photos --limit 10 --output sample.csv
```

The script is explicit about the fact that the run is partial, both up front and again at the end, so a truncated output file doesn't get mistaken for a complete one:

```
NOTE: --limit 10 is set — only the first 10 of 566 photo(s) found will be processed. The output file will cover those 10 photo(s) only.
Processing 10 photo(s). Using model 'gemma4:e4b' via Ollama at http://localhost:11434.
[1/10] _5D_0004.JPG ... 129;1171 [9.1s, elapsed 9s, ETA 1m 22s]
...
Done. 9/10 photos had a plausible bib number (0 parse errors). Wrote results to sample.csv
Reminder: --limit was set, so 556 of the 566 photo(s) found were not processed.
Total time: 1m 24s (8.4s per photo average)
```

Notes:

- Write trial runs to a separate output file (`sample.csv` above). Pointing `--limit` at your real output path overwrites it with the partial results.
- If `--limit` is greater than or equal to the number of photos found, it has no effect and no disclaimer is shown.
- Multiply the reported per-photo average by your full photo count to estimate the real run: `8.4s × 566 ≈ 1h 20m`.

## Quiet mode

`--quiet` turns off everything described above — progress lines, per-photo timings, the ETA, the `--limit` notice and the final summary — and reports **only errors and warnings, on stderr**. A successful run prints absolutely nothing:

```bash
python bib_gemma.py --input /path/to/photos --quiet --output out.csv
```

What still gets reported in quiet mode:

- One line per photo the model failed on: `parse_error: _5D_0200.JPG: <raw response, truncated>`
- The pre-flight warning when `--model` isn't in `ollama list`
- All fatal errors (bad `--input`, unreachable Ollama, missing `ollama`/`openpyxl` package, no JPGs found), each still exiting non-zero

Because everything lands on stderr, this suits cron jobs and scripts — redirect stderr to a log and no news is good news:

```bash
python bib_gemma.py --input ./photos --quiet --output out.csv 2>>bib_errors.log
```

The output CSV/XLSX is byte-for-byte the same as a normal run; `--quiet` only affects the console. Note that `parse_error` rows are already recorded in the output file with their raw response, so the stderr lines are a convenience, not the only record.

## Output format

CSV/XLSX with four columns:

| filename | bib_numbers | colors | notes |
|---|---|---|---|
| `_5D_0004.JPG` | `129;1171` | black on white; black on white | |
| `_5D_0100.JPG` | `none` | | riders in team kit, no number visible |
| `_5D_0120.JPG` | `852;illegible` | black on white; unclear | second bib too small to read |
| `_5D_0140.JPG` | `illegible` | unclear | heavily motion-blurred |
| `_5D_0150.JPG` | `1204` | black on white | distant runners \| filtered out: 45, 7 |
| `_5D_0200.JPG` | `parse_error` | | *(raw model response, truncated)* |

- Multiple bibs in one photo are semicolon-separated.
- `colors` is the model's own description of each bib it reported, in the same order — `black on white`, `white on blue`, or `unclear`. It's recorded for analysis, never used to filter (see below).
- `none` means there was no bib in the photo at all — or that every number reported was removed by a filter, in which case `notes` says which.
- `illegible` means a bib was visible but couldn't be read. It appears on its own, or alongside numbers (`852;illegible`) when only some bibs in the frame were readable. See below for why this matters.
- `parse_error` means the model's reply didn't follow the expected format even after retries — the raw response is kept in `notes` so you can see what happened, rather than the script silently guessing.

In XLSX output these are colour-coded in the bib column: grey for `none`, amber for `illegible` (worth a manual look), red for `parse_error`.

A fifth column, `team`, appears between `colors` and `notes` when you pass `--teams` — see below. Without that flag the schema is exactly the four columns above.

## Team column

`--teams` adds a `team` column holding the club or team name on each person's kit, in the same order as their bibs:

```bash
# Read whatever team name is visible on the kit
python bib_gemma.py --input ./photos --teams --output out.csv

# Match against the teams you know are competing
python bib_gemma.py --input ./photos --teams "xXx, 606" --output out.csv
```

| filename | bib_numbers | colors | team | notes |
|---|---|---|---|---|
| `_5D_0004.JPG` | `1129;1171` | black on white; black on white | xXx; 606 | |
| `_5D_0120.JPG` | `852;illegible` | black on white; unclear | 606; unknown | second bib too small to read |
| `_5D_0150.JPG` | `1204` | black on white | Riverside Runners | *(a team not on the list)* |
| `_5D_0180.JPG` | `45` | unclear | unknown | distant |

How the known-team list is used:

- A case-insensitive match is normalised to **your** spelling, so a model that writes `xxx` or `XXX` lands in the column as `xXx` and the column groups cleanly in a pivot table.
- A team that **isn't** on your list is kept verbatim, not rewritten to the nearest listed name and not dropped. A name the model saw that you didn't list is information — maybe a guest rider, maybe your list is incomplete — so it stays visible.
- Passing `--teams` with no usable names (e.g. `--teams ","`) is an error rather than a silent fall-through to free-form mode.
- The end-of-run summary reports coverage: `A team was identified on 3/5 photos (the rest are blank or 'unknown').`

Expect a lot of `unknown`, and treat that as the feature working. The prompt asks for `unknown` explicitly and tells the model **not** to infer a team from kit colours alone, because on a small or blurry jersey that inference is exactly the kind of confident guess that produced the fabricated bib numbers in the first place.

One caution worth keeping in mind: the team list is given to the model as context, which is the same priming risk described under [colors](#why-colors-are-recorded-but-not-filtered-on) — a model told that `xXx` is racing is more likely to report `xXx`. Nothing is filtered on the team value, so a wrong team can't remove a real bib, but treat the column as a lead to verify rather than a fact. If you want to measure the effect, the `--teams`-free run is the control.

## `illegible`: giving the model a way to admit uncertainty

The original prompt offered a binary — a number, or `none`. A model facing a bib it can see but can't read had no way to say so, and both Gemma sizes resolve that by inventing a plausible number. Against the hosted vision read, which marked 31 photos `illegible`, `e2b` produced a confident number on 14 of them. Those readings are wrong by construction, not by bad luck.

So `illegible` is now a first-class answer, and the prompt says outright that it beats a guess:

> Do not guess at digits you cannot make out. "illegible" is a better answer than a number you are unsure of, and "none" is a better answer than a bib that isn't there.

Practical notes:

- `illegible` is never removed by `--min-digits`/`--bib-range` — there's no number to judge.
- Repeated `illegible` markers in one reply collapse to one. The count of unreadable bibs in a frame isn't something a small model reports reliably.
- The end-of-run summary counts these separately, so they don't inflate the detection rate: `3/5 photos yielded a bib number (1 bib seen but unreadable, 0 parse errors)`.
- These rows are the best candidates for a manual pass — the model is telling you exactly where it needed a closer look.

## Race type

`--race-type` changes what the model is told to look for. This matters more than it sounds, because the default `mixed` prompt has to serve both disciplines at once, and that compromise is measurably expensive.

On the 566-photo reference set the shoot splits into a running block and a cycling block:

| | running block (192 photos) | cycling block (374 photos) |
|---|---|---|
| vision read a number | 173 (90%) | 45 (12%) |
| vision saw a bib but couldn't read it | 5 | 26 |
| vision found no bib at all | 14 (7%) | 303 (81%) |
| **`e2b` fabricated readings** | **0 photos, 0 readings** | **57 photos, 104 readings** |

Every fabricated-from-nothing reading in the entire run falls in the cycling block. The reason is a single clause the `mixed` prompt needs in order to cover runners whose number is printed on their kit — it permits numbers *"printed directly on a jersey"*. Harmless in a running photo; in a cycling photo, where team kit is covered in sponsor lettering and most riders have no visible number, it's an invitation.

```bash
python bib_gemma.py --input ./running-photos --race-type runners  --output run.csv
python bib_gemma.py --input ./cycling-photos --race-type cyclists --output ride.csv
```

| | what the prompt says |
|---|---|
| `runners` | Bib is a card pinned to the **front torso**, large digits; nearly every runner has one, so keep looking if a torso is visible. Ignore timing clocks, road signs, banners, vehicles, brand graphics. |
| `cyclists` | Number is **small**, on the hip, lower back or side of the jersey, or a plate on the frame — often creased, curved or hidden by the rider's arm. `none` is a common correct answer. Sponsor lettering, jersey logos and bike model numbers are **not** bibs. |
| `mixed` | The original prompt, covering both. Still the default, so existing runs are unaffected apart from `illegible` now being available. |

Run each block of photos separately with the matching race type where you can — separate folders, one invocation each.

**The cyclists prompt is deliberately not "expect nothing".** Riders at these events do wear numbers: the vision read finds 45 real ones in the cycling block, including a clean run of `852`/`859`/`1065` across frames 883–944, and calls 26 more illegible. A prompt that assumed no bibs would trade 45 real detections for the 104 fabrications, which is not obviously a win. It's written to reach for `illegible` instead.

## Filtering out implausible readings

Both local models hallucinate far more than they miss: on the 566-photo reference set, `e2b` reported 326 distinct bibs and only 116 were confirmed by the hosted vision read. But the fabrications have a recognisable shape — they're mostly short numbers:

| digits | real bibs (151 distinct) | `e2b`'s 210 unconfirmed reads |
|---|---|---|
| 1–2 | 3 | 43 |
| 3 | 13 | 137 |
| 4 | 134 | 30 |

Real bibs at that event were overwhelmingly 4-digit in the 1000–1699 band, so the race's own numbering is a much stronger filter than anything the model can self-report:

```bash
# Drop anything shorter than 3 digits
python bib_gemma.py --input ./photos --min-digits 3 --output out.csv

# Strongest filter: only keep numbers the race actually issued
python bib_gemma.py --input ./photos --bib-range 1000-1699 --output out.csv

# Both together
python bib_gemma.py --input ./photos --min-digits 4 --bib-range 1000-1699 --output out.csv
```

Filters run per reading, after parsing. **Nothing is discarded silently** — the removed numbers are appended to that row's `notes` as `filtered out: 45, 7`, and the run reports a total at the end:

```
Filtering readings: keeping only numbers at least 3 digit(s) and within 1000-1699. Discarded numbers are listed in the notes column.
...
Filters discarded 58 reading(s) as implausible (see the notes column for which).
```

So if you set the range too tight, it's visible in the output file rather than invisible. On the reference data, dropping every ≤2-digit reading removes 58 of `e2b`'s 497 readings at the cost of three real ones (`14`, `45`, `1`).

### Why colors are recorded but not filtered on

If you know the bibs are black-on-white it's tempting to have the script reject anything else. Two reasons it doesn't:

1. **Race lighting wrecks apparent color.** Backlighting, shade, motion blur and mixed white balance shift a yellow bib to olive and a white bib to grey. Filtering on color would cost real detections in exactly the hard photos you most want to catch.
2. **A small vision model tends to agree with you.** Tell it what color the bibs are and the likely outcome isn't that it rejects a hallucinated number — it's that it keeps the number and describes it in the color you suggested. That's why the prompt asks it to report what it sees and to write `unclear` rather than guess, and doesn't state an expected scheme.

Recording the color instead lets you check offline whether it actually correlates with correctness — group the `colors` column against a known-good read and see whether off-scheme rows really are the wrong ones — without paying for another multi-hour run to change your mind.

## How it works internally

Each photo is sent to the model with a fixed prompt asking it to reply in exactly this shape:

```
BIBS: <comma-separated numbers, "illegible" per unreadable bib, or "none">
COLORS: <"<digit color> on <background color>" per bib, same order, or "unclear">
TEAM: <team name per bib, same order, or "unknown">     <-- only with --teams
NOTES: <one short phrase, optional>
```

Only the opening "what to look for" paragraph changes between race types; this response block is shared, so parsing is identical whichever one you pick. The `TEAM:` line and its guidance are added only when `--teams` is passed — every extra instruction is a chance for a small model to drift, so the default prompt stays as short as it was.

Internally each bib and its per-bib fields are carried as one record rather than three parallel lists, so colours and teams can't drift out of alignment with their bib when duplicates are collapsed or a filter drops a reading.

The script regex-parses that fixed format rather than relying on free-form text, which keeps results consistent across runs. Duplicate numbers in one reply are collapsed, keeping the color given for the first occurrence; a reply that omits the `COLORS:` line still parses with the column left blank; and `unreadable` / `can't read` / `not legible` are accepted as synonyms for `illegible`. Any `--min-digits` / `--bib-range` filtering happens after this parse, in Python, so the model never knows what numbering you expect.

## Performance

This runs entirely on your machine's CPU/GPU — no internet connection or API key needed once the model is downloaded. Without a GPU, expect roughly a few seconds to tens of seconds per photo depending on model size; processing 566 photos on `e4b` on CPU alone could take anywhere from ~30 minutes to a few hours. A GPU will be dramatically faster. If speed matters more than accuracy, try `--model gemma4:e2b`.

You don't have to guess where a given run will land: the per-photo ETA (see [Progress and timing](#progress-and-timing)) gives you a real estimate for *your* hardware within the first few photos.

## Limitations

Smaller local vision models are still not as reliable as a top-tier hosted model — expect some misses on very small, heavily motion-blurred, or steeply angled bibs. It should still substantially outperform `../local-OCR/bib_ocr.py` on the same photos, since it can reason about context instead of just transcribing text. Compare its output against `../local-OCR/bib_ocr.py`'s to see where the two disagree, and spot-check `none`/`parse_error` rows manually.

`--min-digits`/`--bib-range` improve precision but can't fix recall: they remove junk the model reported, and do nothing about bibs it never saw. The likely root cause of the misses is resolution — a bib a few dozen pixels tall in a full frame — so cropping candidate regions before inference would probably help more than any prompt or filter change. The `colors` and `illegible` fields exist partly to test that theory: if `unclear`/`illegible` cluster on the photos where readings are wrong, the model is telling you it couldn't resolve the bib.

Two caveats on the numbers quoted above:

- They're agreement with a hosted vision model's read, not human-verified ground truth.
- The running/cycling split was inferred from the pattern of no-bib photos plus the note about team kit in `../README.md`, not from inspecting the photos. Worth eyeballing the boundary frames before treating the block sizes as exact.

`--race-type` is also untested against ground truth so far — the reasoning for it is sound and the failure it targets is precisely located, but no before/after measurement has been run. The cycling block is the natural test bed: frames from ~950 onward are essentially 100% no-bib, so any number the model reports there is unambiguously wrong, and a `--limit 40` run with and without `--race-type cyclists` will show the difference in a couple of minutes.
