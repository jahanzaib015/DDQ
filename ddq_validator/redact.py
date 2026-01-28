from __future__ import annotations

import re
from typing import Iterable, List

from .models import QuestionRow


_NAME_LABEL_RE = re.compile(
    r"(?i)\b(name|contact|prepared by|author|signed by|signatory|respondent)\b\s*[:\-]\s*"
    r"([A-Z][a-z]+(?:[\s\-'\.][A-Z][a-z]+){0,3})"
)
_TITLE_RE = re.compile(
    r"\b(Mr|Ms|Mrs|Dr|Prof)\.?\s+([A-Z][a-z]+(?:[\s\-'\.][A-Z][a-z]+){0,3})"
)
_BY_FROM_RE = re.compile(
    r"(?i)\b(by|from|attn|attention)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})"
)


def redact_names(text: str) -> str:
    if not text:
        return text

    text = _NAME_LABEL_RE.sub(lambda m: f"{m.group(1)}: [REDACTED]", text)
    text = _TITLE_RE.sub(lambda m: f"{m.group(1)} [REDACTED]", text)
    text = _BY_FROM_RE.sub(lambda m: f"{m.group(1)} [REDACTED]", text)
    return text


def redact_rows(rows: Iterable[QuestionRow]) -> List[QuestionRow]:
    redacted: List[QuestionRow] = []
    for row in rows:
        redacted.append(
            QuestionRow(
                sheet=row.sheet,
                row_idx=row.row_idx,
                question_id=row.question_id,
                question_text=redact_names(row.question_text),
                answer_text=redact_names(row.answer_text),
                expected_text=redact_names(row.expected_text),
            )
        )
    return redacted
