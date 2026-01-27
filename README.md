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

