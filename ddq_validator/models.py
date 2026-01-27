from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class QuestionRow:
    """Canonical representation of one DDQ row."""

    sheet: str
    row_idx: int
    question_id: Optional[str]
    question_text: str
    answer_text: str
    expected_text: str


@dataclass
class Finding:
    """Validation result for one DDQ row."""

    sheet: str
    row_idx: int
    question_id: Optional[str]
    question_text: str
    answer_text: str
    expected_text: str
    status: str  # OK / INCOMPLETE / REJECTED / NEEDS_EVIDENCE
    reason: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Flatten details if missing
        if d.get("details") is None:
            d["details"] = {}
        return d
