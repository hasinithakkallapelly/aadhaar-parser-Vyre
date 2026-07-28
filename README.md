# Aadhaar Document Parser & Verification

OCR-based Aadhaar card parsing pipeline with a FastAPI backend and MySQL
lookup for new-vs-returning-user detection.

## Pipeline

1. Upload an Aadhaar card image (`/upload` or `/recognise` endpoint, or run
   `main.py`/`parser/aadhaar_parser.py` directly from the CLI).
2. **Document-type validation** (`parser/document_validator.py`) -- checks
   whether the OCR text actually looks like an Aadhaar card before running
   full field extraction. See "Document-type validation" section below for
   what this does and doesn't cover.
3. **Preprocessing** (`parser/aadhaar_parser.py`) -- grayscale conversion,
   2x upscaling, and Otsu thresholding to improve OCR accuracy.
4. **OCR** via Tesseract (`pytesseract`).
5. **Field extraction** -- regex for Aadhaar number and DOB, keyword/heuristic
   scoring to identify the name line near the DOB.
6. **Database check** -- looks up the extracted Aadhaar number in MySQL to
   determine new vs. returning user; inserts new records.

## Document-type validation

Added a basic check (`parser/document_validator.py`) that runs before full
field extraction: it looks for Aadhaar-specific text markers (government/
Aadhaar boilerplate, a 12-digit-shaped number) and rejects uploads that
instead match known markers for other Indian ID documents (PAN card, voter
ID, driving license), or that don't look like any recognizable ID at all.

**What this catches**: wrong document type entirely (e.g. uploading a PAN
card), and unreadable/garbage uploads. Verified end-to-end with real
Tesseract OCR against a synthetic PAN card image -- correctly rejected,
see `test_document_validator.py`.

**What this does NOT catch -- stated honestly**: a well-made forged
Aadhaar card that includes correct-looking boilerplate text and a
plausible 12-digit number would pass this check. This is keyword/structure
validation, not forgery detection. Real forgery detection would need:
- **QR code cross-validation** -- Aadhaar cards issued since ~2018 carry a
  UIDAI-signed secure QR code encoding the same data printed on the card;
  decoding it and comparing against OCR text is the standard real approach.
- **Tamper/forensic analysis** -- Error Level Analysis or copy-move
  forgery detection to catch digitally edited images.

Neither is implemented here -- that's a meaningfully larger project.

## Tested results (real, not simulated)

Two things were conflated in initial testing, then separated out:

**1. A real regex bug — fixed.** The Aadhaar number regex required exact
`\d{4}\s\d{4}\s\d{4}` spacing. If OCR dropped or misplaced a single space,
the match failed entirely and `aadhaar_number` came back `None` even
though the digits were mostly present in the text. Fixed by adding a
per-line fallback that strips whitespace and looks for 12 consecutive
digits (checked line-by-line, not across the whole document, to avoid
accidentally concatenating digits from unrelated fields into a false
match).

**2. An OCR image-quality issue — not a code bug, isolated by testing.**
The first test used a synthetic image rendered with PIL's default tiny
bitmap font, which produced real digit misreads (5→6, 9→8) that no
regex or parsing logic can fix — Tesseract itself read the wrong
character. Re-testing with a normal-resolution font isolated this:

```
Low-quality font/resolution:
  {'aadhaar_number': '123466788012', 'dob': '16/06/1898', 'gender': 'FEMALE', 'name': 'Jane Test Doe'}
  (regex fix means aadhaar_number is no longer None, but digits are still OCR-misread)

Normal-quality font/resolution:
  {'aadhaar_number': '123456789012', 'dob': '15/06/1998', 'gender': 'FEMALE', 'name': 'Jane Test Doe'}
  (exact match on every field)
```

Conclusion: the parsing pipeline itself is correct and was verified
end-to-end with Tesseract (not simulated). Real-world accuracy on actual
Aadhaar cards will depend on scan/photo quality, which hasn't been tested
against a real card. Don't claim a specific accuracy number without
testing against real (or better-simulated) card images first.

## Fixes made to the original code

- **Fixed a real runtime bug**: several API responses returned Python
  `set` literals (e.g. `{"some string"}`) instead of dicts. Sets are not
  JSON-serializable, so these lines would have thrown a 500 error instead
  of returning the intended error message. Confirmed with
  `json.dumps({"x"})` before fixing. All response bodies are now proper
  dicts.
- **Removed hardcoded MySQL credentials** (`password="cjbe8302"`) from
  both `api.py` and `parser/aadhaar_parser.py` -- now read from environment
  variables via `.env` (see `.env.example`). If this password was ever used
  on a real database, rotate it; it was exposed in a public repo.
- **Removed a `.git`-tracked Python virtual environment** -- the original
  repo had an entire venv (hundreds of thousands of files, including
  compiled numpy/OpenCV binaries) committed. Added a proper `.gitignore`
  so this can't happen again.
- **Removed ~5 stacked iterations of commented-out dead code** in
  `parser/aadhaar_parser.py` -- only the final, active implementation
  remains. Git history is what git history is for.
- **Deduplicated `requirements.txt`** (several packages were listed twice).
- **Clarified the two CLI entry points** -- `main.py` (single image) and
  `parser/aadhaar_parser.py` run directly (batch folder + DB insert) did
  overlapping but different things with no explanation. Both still exist,
  now documented.

## Known limitations

- OCR accuracy on digit fields (DOB, Aadhaar number) is unverified against
  real cards and shown above to be imperfect even on a clean synthetic
  image.
- No authentication/authorization on any API endpoint.
- Name-extraction heuristic is keyword/pattern based, not ML-based --
  works well when a DOB line anchors the search, weaker otherwise.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your DB_PASSWORD
python main.py [image_path]                 # single image, CLI
python parser/aadhaar_parser.py             # batch process images/ folder
uvicorn api:app --reload                    # run the API
```

Requires Tesseract installed separately:
- macOS: `brew install tesseract`
- Ubuntu: `sudo apt install tesseract-ocr`
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
