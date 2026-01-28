import os
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from ddq_validator.extract import load_questions, load_questions_pdf
from ddq_validator.llm import llm_refine_findings
from ddq_validator.models import Finding
from ddq_validator.redact import redact_rows
from ddq_validator.report import write_report
from ddq_validator.rules import RuleConfig, should_validate, validate_row


load_dotenv()

app = FastAPI(title="DDQ Validator API", version="1.0.0")

allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed_origins.split(",")] if allowed_origins else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = (Path(__file__).parent / "frontend").resolve()


@app.get("/health")
def health():
    return {"status": "ok"}


def _validate_rows(rows, use_llm: bool, llm_model: str) -> List[Finding]:
    cfg = RuleConfig.default()
    findings: List[Finding] = []
    results: List[Finding] = []

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
        results = [
            refined_map.get((r.sheet, r.row_idx, r.question_id), r)
            for r in results
        ]

    return results


@app.post("/validate")
async def validate(
    file: UploadFile = File(...),
    use_llm: bool = Form(False),
    llm_model: str = Form("gpt-5.2"),
    max_rows_per_sheet: int = Form(0),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".xlsx", ".pdf"}:
        raise HTTPException(status_code=400, detail="Only XLSX or PDF files are supported.")

    max_rows: Optional[int] = None if max_rows_per_sheet <= 0 else max_rows_per_sheet

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        filled_path = tmp_path / f"filled{suffix}"
        filled_path.write_bytes(await file.read())

        if suffix == ".pdf":
            rows = load_questions_pdf(
                filled_path=str(filled_path),
                max_rows_per_sheet=max_rows,
            )
        else:
            rows = load_questions(
                filled_path=str(filled_path),
                max_rows_per_sheet=max_rows,
            )
        rows = redact_rows(rows)

        if not rows:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No rows were extracted. Check that the filled file uses the expected "
                    "column layout (A=ID, B=Question, C=Answer)."
                ),
            )

        results = _validate_rows(rows, use_llm=use_llm, llm_model=llm_model)
        report_result = write_report(results, tmp_path)
        report_csv = Path(report_result["report_csv"]).read_text(encoding="utf-8")
        summary_json = Path(report_result["summary_json"]).read_text(encoding="utf-8")

        return {
            "summary": report_result["summary"],
            "report": [r.to_dict() for r in results],
            "report_csv": report_csv,
            "summary_json": summary_json,
        }


@app.get("/")
def index():
    if not frontend_dir.exists():
        raise HTTPException(status_code=404, detail="Frontend not found.")
    return FileResponse(frontend_dir / "index.html")


if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
