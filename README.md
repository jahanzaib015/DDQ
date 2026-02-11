# DDQ Validator (Excel-first MVP)

This is an MVP tool to **validate filled Due Diligence Questionnaires (DDQs)** against a **reference/template with model answers**.

It is designed for the provided 2026 DDQ Excel structure:
- **Column A**: question ID / numbering (e.g., `2.2.1`)
- **Column B**: question text
- **Column C**: customer answer (filled questionnaire)
- **Column D**: model answer / expected logic (reference workbook)

## What it does (MVP)

✅ Deterministic checks:
- empty / whitespace answers
- forbidden placeholders (e.g., `N/A`, `tbd`, `later`)
- too-short answers for descriptive questions
- detects cross-references ("see attached", "section 4.1.9", "siehe Anhang")

✅ Output:
- `output/report.csv` (all flagged rows)
- `output/summary.json` (counts per status)

Optional (later stage):
- document ingestion + evidence retrieval for "see attached" cases
- LLM-based quality assessment (only on flagged/critical rows)

## Quick start

1) Create a virtualenv and install deps:

```bash
pip install -r requirements.txt
```

2) Run validation:

```bash
python -m ddq_validator.cli \
  --filled "/path/to/FILLED_DDQ.xlsx" \
  --reference "/path/to/2026_Due Diligence Questionnaire_template_wirh model answer.xlsx" \
  --out-dir "output"
```

Outputs:
- `output/report.csv`
- `output/summary.json`

## PDFs that open in Adobe but fail

Some PDFs are scanned/flattened or XFA forms without a text layer. For those, the validator cannot extract any text.

Options:
- Export to a text-based PDF (e.g., Acrobat "Recognize Text"/OCR).
- Export to XLSX and upload that.
- Enable OCR extraction (optional):

```bash
pip install pdf2image pytesseract pillow
```

You will also need system tools:
- Windows: install Tesseract OCR and Poppler, then add them to PATH.

## Web app on VDI / corporate networks

If the deployed app works on your PC but shows "Validation failed" immediately on a VDI (e.g. Omnissa) or behind a corporate proxy:

- **Proxy / SSL inspection** – Traffic may be intercepted; the browser can get an HTML error page instead of the API response, so the app shows a generic failure. After the latest update, the UI shows the real HTTP status and a hint when a network error occurs.
- **Timeouts** – Proxies or firewalls may close long-running requests (e.g. large PDFs or LLM validation). Try a smaller file or XLSX instead of PDF.
- **Upload size limits** – Some gateways cap request body size; try a smaller file.
- **403 Forbidden** – Often a corporate proxy or WAF (shared IP, SSL inspection, bot rules). The app retries once automatically; the message suggests asking IT to whitelist the app URL and allow POST to `/validate`. If the request never reaches the server, Render logs will show no "validate request" line for that attempt—meaning the block happened upstream (proxy/WAF).
- **What to check** – Browser Network tab (F12): check `/validate` status and response body. In Render logs, successful or app-received requests show a line with `origin`, `referer`, `user_agent`, `forwarded` for diagnostics to share with IT.

## Optional: enable LLM checks

Set your API key:

```bash
export OPENAI_API_KEY="..."
```

Then run with:

```bash
python -m ddq_validator.cli --filled ... --reference ... --use-llm
```

Notes:
- The tool uses a **gating strategy**: the LLM is called only for rows that are already flagged by deterministic rules.
- If you do not set `OPENAI_API_KEY`, the tool will still run (LLM steps are skipped).

## Adapting to your future formats

If the questionnaire layout changes (different columns, extra sheets, etc.), update:
- `ddq_validator/extract.py` (column mapping)
- `ddq_validator/rules.py` (heuristics and forbidden tokens)

