# vision-based vs Local OCR vs Gemma e2b
Running the full three-way comparison against the vision-based ground truth.
Ran the three-way comparison against the vision-based read (ground truth).
Both local methods land around 60-65% exact match, but they fail in opposite directions:

**Local OCR (EasyOCR):** 60.2% exact match. Missed 66 photos vision caught, invented bibs on 61 photos vision said had none. Conservative but sloppy — 190 distinct "bibs" found, only 89 confirmed by vision.

**Gemma (gemma4:e4b):** 64.8% exact match — slightly better overall, and much better recall (missed only 23 photos vision caught, vs. OCR's 66). But it hallucinates far more: 326 distinct "bibs" found, only 116 confirmed by vision. On 69 photos where vision found nothing at all, Gemma invented numbers anyway — including one case (`_5D_0473.JPG`) where it listed eight different single/double-digit "bibs" out of thin air.

The pattern: Gemma rarely says "I don't see a bib," even when there genuinely isn't one (especially in the cycling-race frames with no pinned bibs) — it guesses instead. OCR misses more real bibs but invents less. Neither is a reliable stand-in for the vision-based pass; `bib_comparison_3way.csv` has the full row-by-row breakdown (`ocr_vs_vision` / `gemma_vs_vision` columns) if you want to dig into specific photos.

# vision-based vs Local OCR vs Gemma e2b vs Gemma 12b
Both files have all 566 rows. Running the four-way comparison against the vision-based ground truth.Full results, all against the vision-based ground truth (566 photos, 150 true distinct bibs):

| Method | Exact match | Recall (found vision's bibs) | Precision (found bibs confirmed) | Full disagreements |
|---|---|---|---|---|
| Local OCR | 60.2% | 59.3% | 46.8% | 46 |
| Gemma e2b | 64.8% | 77.3% | 35.6% | 55 |
| Gemma 12b | 65.7% | 48.7% | 34.4% | 101 |

The bigger model isn't simply "better" — it trades in a different direction. 12b is far more conservative (says "none" on 333/566 photos vs. e2b's 277), so it rarely invents a bib out of thin air (only 13 false-positive-all cases vs. e2b's 69). But when it does commit to a number, it's wrong more often — 101 photos where it and vision found bibs but shared zero overlap (e.g. `_5D_0028.JPG`: vision saw `1034/1048/1119/1134/1144`, 12b confidently said `1305`). Its recall actually drops to 48.7%, worse than both OCR and e2b, because it says "none" on real bibs more often too.

e2b's failure mode is the opposite: it almost always finds *something* (best recall at 77.3%), but roughly 2 out of 3 numbers it reports turn out to be fabricated.

Bottom line: none of the three local methods is trustworthy as a standalone source — each has a different bias (OCR: undershoots; e2b: overshoots with hallucinations; 12b: overconfident wrong reads when it does commit). `bib_comparison_4way.csv` has every photo's readings side by side with a per-method agreement label if you want to inspect specific cases or try blending methods (e.g., only trusting a number when two of the three agree).