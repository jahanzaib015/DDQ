from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any

from .models import Finding


def write_report(results: List[Finding], out_dir: str) -> Dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    report_path = out / "report.csv"
    summary_path = out / "summary.json"

    # Flatten data for CSV
    fieldnames = [
        "sheet",
        "row_idx",
        "question_id",
        "question_text",
        "answer_text",
        "expected_text",
        "status",
        "reason",
        "details_json",
    ]

    with report_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for item in results:
            d = item.to_dict()
            d["details_json"] = json.dumps(d.get("details", {}), ensure_ascii=False)
            w.writerow({k: d.get(k, "") for k in fieldnames})

    counts = Counter([f.status for f in results])
    flagged_statuses = {k for k in counts.keys() if k not in {"OK", "SKIPPED"}}
    total_flagged = sum(v for k, v in counts.items() if k in flagged_statuses)
    summary = {
        "total_rows": len(results),
        "total_flagged": total_flagged,
        "by_status": dict(counts),
    }

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "report_csv": str(report_path),
        "summary_json": str(summary_path),
        "summary": summary,
    }
