from __future__ import annotations

import json
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich import print

from .extract import load_questions, load_questions_pdf
from .models import Finding
from .rules import RuleConfig, should_validate, validate_row
from .llm import llm_refine_findings
from .report import write_report

load_dotenv()
app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def validate(
    filled: str = typer.Option(..., help="Path to the filled DDQ Excel or PDF file"),
    out_dir: str = typer.Option("output", help="Output directory for report.csv and summary.json"),
    use_llm: bool = typer.Option(False, help="Refine flagged rows using an LLM (requires OPENAI_API_KEY)"),
    llm_model: str = typer.Option("gpt-5.2", help="OpenAI model name"),
    max_rows_per_sheet: int = typer.Option(0, help="Debug: limit max rows per sheet (0 = no limit)"),
):
    """Validate a filled DDQ against a reference workbook with model answers."""

    filled_path = Path(filled)
    if not filled_path.exists():
        raise typer.BadParameter(f"Filled file not found: {filled}")

    max_rows = None if max_rows_per_sheet <= 0 else max_rows_per_sheet

    if filled_path.suffix.lower() == ".pdf":
        rows = load_questions_pdf(
            filled_path=str(filled_path),
            max_rows_per_sheet=max_rows,
        )
    else:
        rows = load_questions(
            filled_path=str(filled_path),
            max_rows_per_sheet=max_rows,
        )
    if not rows:
        raise RuntimeError(
            "No rows were extracted. Check that the filled file uses the expected "
            "column layout (A=ID, B=Question, C=Answer)."
        )

    cfg = RuleConfig.default()

    findings = []
    results = []
    for row in rows:
        if not should_validate(row):
            results.append(
                Finding(
                    sheet=row.sheet,
                    row_idx=row.row_idx,
                    question_id=row.question_id,
                    question_text=row.question_text,
                    answer_text=row.answer_text,
                    expected_text=row.expected_text,
                    status="SKIPPED",
                    reason="Row is not a question or validation rule does not apply.",
                    details={"validated": False},
                )
            )
            continue

        fnd = validate_row(row, cfg)
        if fnd is not None:
            findings.append(fnd)
            results.append(fnd)
        else:
            results.append(
                Finding(
                    sheet=row.sheet,
                    row_idx=row.row_idx,
                    question_id=row.question_id,
                    question_text=row.question_text,
                    answer_text=row.answer_text,
                    expected_text=row.expected_text,
                    status="OK",
                    reason="Passed rule checks.",
                    details={"validated": True},
                )
            )

    if use_llm and findings:
        refined = llm_refine_findings(findings, model=llm_model)
        refined_map = {(f.sheet, f.row_idx, f.question_id): f for f in refined}
        findings = refined
        results = [
            refined_map.get((r.sheet, r.row_idx, r.question_id), r)
            for r in results
        ]

    result = write_report(results, out_dir)

    print("\n[bold]DDQ Validation Complete[/bold]")
    print(f"Flagged rows: [bold]{result['summary']['total_flagged']}[/bold]")
    print("By status:")
    for k, v in result["summary"]["by_status"].items():
        print(f"  - {k}: {v}")
    print("\nOutputs:")
    print(f"  - {result['report_csv']}")
    print(f"  - {result['summary_json']}")


if __name__ == "__main__":
    app()
