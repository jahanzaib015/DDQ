from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from .models import QuestionRow, Finding


YES_PAT = re.compile(r"\b(ja|yes|y|bestätigt|confirmed)\b", re.I)
NO_PAT = re.compile(r"\b(nein|no|n)\b", re.I)
EMAIL_PAT = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PAT = re.compile(r"[0-9].*[0-9].*[0-9].*[0-9].*[0-9].*[0-9].*[0-9]")
URL_PAT = re.compile(r"(https?://|www\.)\S+", re.I)
FILENAME_PAT = re.compile(r"\b[\w\-.]+\.(pdf|docx|doc|xlsx|xls|pptx|ppt|zip|png|jpg|jpeg|csv)\b", re.I)
REFUSAL_PAT = re.compile(r"\b(refusal|refuse|decline|not to answer|no answer)\b", re.I)
SIGNATURE_PAT = re.compile(
    r"(signature|signatur|unterschrift|name\s*&\s*position|name\s*and\s*position|"
    r"ort\s*/\s*datum|place\s*/\s*date)",
    re.I,
)
REFERENCE_PAT = re.compile(
    r"(see|refer|reference|attached|attachment|annex|section|chapter|appendix|"
    r"siehe|vgl\.|verweis|anhang|beigefügt|abschnitt|kapitel|ziffer)"
    r"|\b\d+(?:\.\d+){1,}\b",  # e.g. 4.1.9
    re.I,
)


@dataclass
class RuleConfig:
    forbidden_tokens: List[str]
    min_len_descriptive: int = 20

    @staticmethod
    def default() -> "RuleConfig":
        return RuleConfig(
            forbidden_tokens=[
                "n/a",
                "n.a",
                "na",
                "not applicable",
                "tbd",
                "to be defined",
                "later",
                "unknown",
                "k.a",
                "keine angabe",
            ],
            min_len_descriptive=20,
        )


def looks_like_question(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    # Most DDQ questions start with these verbs
    starters = ("bitte", "please", "sofern", "gab", "wurde", "hat", "ist", "nutzen", "wird")
    if t.lower().startswith(starters):
        return True
    if "?" in t:
        return True
    # Many questions contain these verbs
    if re.search(r"\b(beschreiben|erläutern|bestätigen|informieren|detaillieren|teilen)\b", t, re.I):
        return True
    return False


def looks_like_note(expected: str, question_text: str) -> bool:
    """Heuristic to ignore guidance lines that are not meant to be answered."""

    e = (expected or "").strip().lower()
    q = (question_text or "").strip().lower()
    if not e:
        return False

    note_starters = (
        "please note",
        "bitte beachten",
        "hinweis",
        "note:",
        "the following documents",
    )
    if e.startswith(note_starters):
        return True
    # Many sheets have a section heading like "Prozesse" and the expected text is only a note.
    if q in {"prozesse", "dokumentation", "outsourcing"} and any(s in e for s in ["please note", "bitte", "note"]):
        return True
    return False


def is_signature_row(row: QuestionRow) -> bool:
    q = (row.question_text or "").lower()
    e = (row.expected_text or "").lower()
    return bool(SIGNATURE_PAT.search(q) or SIGNATURE_PAT.search(e))


def is_allgemeiner_sheet(sheet: str) -> bool:
    s = (sheet or "").lower()
    return "allgemein" in s or "general" in s


def is_fondsmanagement_sheet(sheet: str) -> bool:
    s = (sheet or "").lower()
    return "fondsmanagement" in s or "fund management" in s


def is_innenrevision_sheet(sheet: str) -> bool:
    s = (sheet or "").lower()
    return "innenrevision" in s


def is_regta_sheet(sheet: str) -> bool:
    s = (sheet or "").lower()
    return "regta" in s


def is_zv_fobu_sheet(sheet: str) -> bool:
    s = (sheet or "").lower()
    return "zv" in s and "fobu" in s


def is_verwahrstelle_sheet(sheet: str) -> bool:
    s = (sheet or "").lower()
    return "verwahrstelle" in s


def expected_requires_filename(expected: str) -> bool:
    e = (expected or "").lower()
    return any(k in e for k in ["name of a file", "name of file", "dateiname"])


def expected_requires_number_and_text(expected: str) -> bool:
    e = (expected or "").lower()
    return "number and text obligatory" in e or "nummer und text" in e


def expected_content_not_relevant(expected: str) -> bool:
    e = (expected or "").lower()
    return "content not relevant" in e or "fields must only be filled" in e


def expected_disallow_reference(expected: str) -> bool:
    e = (expected or "").lower()
    return (
        "reference to a document is not acceptable" in e
        or "reference to another document is not acceptable" in e
        or "only reference to another document is also not acceptable" in e
    )


def expected_disallow_refusal(expected: str) -> bool:
    e = (expected or "").lower()
    return (
        "refusal is not acceptable" in e
        or "any sort of refusal is not acceptable" in e
        or ("not acceptable" in e and "n/a" in e)
    )


def looks_like_email(answer: str) -> bool:
    return bool(EMAIL_PAT.match((answer or "").strip()))


def looks_like_phone(answer: str) -> bool:
    return bool(PHONE_PAT.search(answer or ""))


def looks_like_url(answer: str) -> bool:
    a = (answer or "").strip()
    return bool(URL_PAT.search(a)) or ("." in a and " " not in a and len(a) >= 4)


def looks_like_filename(answer: str) -> bool:
    return bool(FILENAME_PAT.search(answer or ""))


def has_number_and_text(answer: str) -> bool:
    a = (answer or "").strip()
    return bool(re.search(r"[0-9]", a)) and bool(re.search(r"[A-Za-zÄÖÜäöü]", a))


def should_validate(row: QuestionRow) -> bool:
    """Decide whether a row is intended to be answered."""

    expected = (row.expected_text or "")
    if looks_like_note(expected, row.question_text):
        return False

    if is_signature_row(row):
        return True

    # Validate if it looks like an actual question
    if looks_like_question(row.question_text):
        return True

    # Or if the reference workbook explicitly defines expected behavior
    e_lower = expected.lower()
    if "[text]" in e_lower:
        return True
    if any(k in e_lower for k in ["obligatory", "not acceptable", "must", "fields must only be filled", "number and text obligatory"]):
        return True
    if expected_yes_no(expected) is not None:
        return True

    return False


def is_mandatory(row: QuestionRow) -> bool:
    e = (row.expected_text or "").lower()
    q = (row.question_text or "").lower()
    if "obligatory" in e or "not acceptable" in e or "must" in e:
        return True
    # If we have any expected text at all, assume it's mandatory/checked.
    if e.strip():
        return True
    # Contact / identification-like fields in this DDQ are typically mandatory
    if q.startswith("name der") or q.startswith("e-mail") or q.startswith("telefon"):
        return True
    return False


def detect_reference(answer: str) -> bool:
    return bool(REFERENCE_PAT.search(answer or ""))


def contains_forbidden(answer: str, cfg: RuleConfig) -> Optional[str]:
    a = (answer or "").strip().lower()
    if not a:
        return None
    for tok in cfg.forbidden_tokens:
        if tok in a:
            return tok
    return None


def expected_yes_no(expected: str) -> Optional[str]:
    e = (expected or "").lower()
    # Typical model answers in your file: "Ja" / "Nein" or "JA; Bestätigt..."
    if "ja" in e and "nein" not in e:
        return "YES"
    if "nein" in e and "ja" not in e:
        return "NO"
    return None


def validate_row(row: QuestionRow, cfg: RuleConfig) -> Optional[Finding]:
    """Return a Finding for flagged rows only. OK rows return None."""

    # Skip headings/titles or pure guidance lines
    if not should_validate(row):
        return None

    answer = (row.answer_text or "").strip()
    expected = (row.expected_text or "").strip()
    mandatory = is_mandatory(row)

    if is_signature_row(row):
        forbidden = contains_forbidden(answer, cfg)
        if not answer or forbidden:
            return Finding(
                sheet=row.sheet,
                row_idx=row.row_idx,
                question_id=row.question_id,
                question_text=row.question_text,
                answer_text=row.answer_text,
                expected_text=row.expected_text,
                status="INCOMPLETE",
                reason="Signature/name/date is missing.",
                details={"expected": "signature"},
            )
        return None

    if not answer:
        if mandatory:
            return Finding(
                sheet=row.sheet,
                row_idx=row.row_idx,
                question_id=row.question_id,
                question_text=row.question_text,
                answer_text=row.answer_text,
                expected_text=row.expected_text,
                status="REJECTED",
                reason="Mandatory field is empty.",
                details={"mandatory": True},
            )
        return None

    forbidden = contains_forbidden(answer, cfg)
    if forbidden and mandatory:
        return Finding(
            sheet=row.sheet,
            row_idx=row.row_idx,
            question_id=row.question_id,
            question_text=row.question_text,
            answer_text=row.answer_text,
            expected_text=row.expected_text,
            status="REJECTED",
            reason=f"Answer contains forbidden placeholder: '{forbidden}'.",
            details={"forbidden": forbidden},
        )

    if expected_requires_filename(expected) and not looks_like_filename(answer):
        return Finding(
            sheet=row.sheet,
            row_idx=row.row_idx,
            question_id=row.question_id,
            question_text=row.question_text,
            answer_text=row.answer_text,
            expected_text=row.expected_text,
            status="INCOMPLETE",
            reason="Expected a filename (e.g., .pdf/.docx) but none found.",
            details={"expected": "filename"},
        )

    if is_allgemeiner_sheet(row.sheet):
        q_lower = (row.question_text or "").lower()
        e_lower = expected.lower()

        if expected_requires_number_and_text(expected) and not has_number_and_text(answer):
            return Finding(
                sheet=row.sheet,
                row_idx=row.row_idx,
                question_id=row.question_id,
                question_text=row.question_text,
                answer_text=row.answer_text,
                expected_text=row.expected_text,
                status="INCOMPLETE",
                reason="Expected both a number and descriptive text.",
                details={"expected": "number+text"},
            )

        if "e-mail" in q_lower or "email" in q_lower or "e-mail" in e_lower:
            if not looks_like_email(answer):
                return Finding(
                    sheet=row.sheet,
                    row_idx=row.row_idx,
                    question_id=row.question_id,
                    question_text=row.question_text,
                    answer_text=row.answer_text,
                    expected_text=row.expected_text,
                    status="INCOMPLETE",
                    reason="Expected a valid email address.",
                    details={"expected": "email"},
                )

        if "telefon" in q_lower or "phone" in q_lower or "telefon" in e_lower:
            if not looks_like_phone(answer):
                return Finding(
                    sheet=row.sheet,
                    row_idx=row.row_idx,
                    question_id=row.question_id,
                    question_text=row.question_text,
                    answer_text=row.answer_text,
                    expected_text=row.expected_text,
                    status="INCOMPLETE",
                    reason="Expected a valid phone number.",
                    details={"expected": "phone"},
                )

        if "website" in q_lower or "web" in q_lower:
            if not looks_like_url(answer):
                return Finding(
                    sheet=row.sheet,
                    row_idx=row.row_idx,
                    question_id=row.question_id,
                    question_text=row.question_text,
                    answer_text=row.answer_text,
                    expected_text=row.expected_text,
                    status="INCOMPLETE",
                    reason="Expected a website/URL.",
                    details={"expected": "url"},
                )

        if expected_content_not_relevant(expected):
            # For content-not-relevant fields, any non-empty answer is acceptable.
            return None

    if is_fondsmanagement_sheet(row.sheet):
        # Disallow "see attachment" style references unless it is explicitly a policy reference.
        if expected_disallow_reference(expected):
            if detect_reference(answer) and "policy" not in answer.lower():
                return Finding(
                    sheet=row.sheet,
                    row_idx=row.row_idx,
                    question_id=row.question_id,
                    question_text=row.question_text,
                    answer_text=row.answer_text,
                    expected_text=row.expected_text,
                    status="REJECTED",
                    reason="Reference-only answers are not acceptable; provide substantive text.",
                    details={"reference_only": True},
                )

        # Disallow refusal-style answers where the template says refusal is not acceptable.
        if expected_disallow_refusal(expected) and REFUSAL_PAT.search(answer):
            return Finding(
                sheet=row.sheet,
                row_idx=row.row_idx,
                question_id=row.question_id,
                question_text=row.question_text,
                answer_text=row.answer_text,
                expected_text=row.expected_text,
                status="REJECTED",
                reason="Refusal-style answers are not acceptable for this question.",
                details={"refusal": True},
            )

    if is_regta_sheet(row.sheet):
        if expected_disallow_reference(expected) and detect_reference(answer):
            return Finding(
                sheet=row.sheet,
                row_idx=row.row_idx,
                question_id=row.question_id,
                question_text=row.question_text,
                answer_text=row.answer_text,
                expected_text=row.expected_text,
                status="REJECTED",
                reason="Reference-only answers are not acceptable; provide substantive text.",
                details={"reference_only": True},
            )

        if expected_disallow_refusal(expected) and REFUSAL_PAT.search(answer):
            return Finding(
                sheet=row.sheet,
                row_idx=row.row_idx,
                question_id=row.question_id,
                question_text=row.question_text,
                answer_text=row.answer_text,
                expected_text=row.expected_text,
                status="REJECTED",
                reason="Refusal-style answers are not acceptable for this question.",
                details={"refusal": True},
            )

    if is_zv_fobu_sheet(row.sheet):
        if expected_disallow_reference(expected) and detect_reference(answer):
            return Finding(
                sheet=row.sheet,
                row_idx=row.row_idx,
                question_id=row.question_id,
                question_text=row.question_text,
                answer_text=row.answer_text,
                expected_text=row.expected_text,
                status="REJECTED",
                reason="Reference-only answers are not acceptable; provide substantive text.",
                details={"reference_only": True},
            )

        if expected_disallow_refusal(expected) and REFUSAL_PAT.search(answer):
            return Finding(
                sheet=row.sheet,
                row_idx=row.row_idx,
                question_id=row.question_id,
                question_text=row.question_text,
                answer_text=row.answer_text,
                expected_text=row.expected_text,
                status="REJECTED",
                reason="Refusal-style answers are not acceptable for this question.",
                details={"refusal": True},
            )

    if is_verwahrstelle_sheet(row.sheet):
        if expected_disallow_reference(expected) and detect_reference(answer):
            return Finding(
                sheet=row.sheet,
                row_idx=row.row_idx,
                question_id=row.question_id,
                question_text=row.question_text,
                answer_text=row.answer_text,
                expected_text=row.expected_text,
                status="REJECTED",
                reason="Reference-only answers are not acceptable; provide substantive text.",
                details={"reference_only": True},
            )

        if expected_disallow_refusal(expected) and REFUSAL_PAT.search(answer):
            return Finding(
                sheet=row.sheet,
                row_idx=row.row_idx,
                question_id=row.question_id,
                question_text=row.question_text,
                answer_text=row.answer_text,
                expected_text=row.expected_text,
                status="REJECTED",
                reason="Refusal-style answers are not acceptable for this question.",
                details={"refusal": True},
            )

    if is_innenrevision_sheet(row.sheet):
        if expected_requires_number_and_text(expected) and not has_number_and_text(answer):
            return Finding(
                sheet=row.sheet,
                row_idx=row.row_idx,
                question_id=row.question_id,
                question_text=row.question_text,
                answer_text=row.answer_text,
                expected_text=row.expected_text,
                status="INCOMPLETE",
                reason="Expected both a number and descriptive text.",
                details={"expected": "number+text"},
            )

    if detect_reference(answer):
        return Finding(
            sheet=row.sheet,
            row_idx=row.row_idx,
            question_id=row.question_id,
            question_text=row.question_text,
            answer_text=row.answer_text,
            expected_text=row.expected_text,
            status="NEEDS_EVIDENCE",
            reason="Answer references an attachment/section; requires document evidence retrieval.",
            details={"reference_detected": True},
        )

    yn = expected_yes_no(expected)
    if yn == "YES" and not YES_PAT.search(answer):
        return Finding(
            sheet=row.sheet,
            row_idx=row.row_idx,
            question_id=row.question_id,
            question_text=row.question_text,
            answer_text=row.answer_text,
            expected_text=row.expected_text,
            status="INCOMPLETE",
            reason="Expected a 'Yes/Confirmed' style answer based on model answer.",
            details={"expected": "YES"},
        )
    if yn == "NO" and not NO_PAT.search(answer):
        return Finding(
            sheet=row.sheet,
            row_idx=row.row_idx,
            question_id=row.question_id,
            question_text=row.question_text,
            answer_text=row.answer_text,
            expected_text=row.expected_text,
            status="INCOMPLETE",
            reason="Expected a 'No' style answer based on model answer.",
            details={"expected": "NO"},
        )

    # Descriptive answers
    if ("[text]" in expected.lower()) or re.search(r"\b(beschreiben|erläutern|detaillieren)\b", row.question_text, re.I):
        if len(answer) < cfg.min_len_descriptive:
            return Finding(
                sheet=row.sheet,
                row_idx=row.row_idx,
                question_id=row.question_id,
                question_text=row.question_text,
                answer_text=row.answer_text,
                expected_text=row.expected_text,
                status="INCOMPLETE",
                reason=f"Answer is too short for a descriptive question (min {cfg.min_len_descriptive} chars).",
                details={"min_len": cfg.min_len_descriptive, "actual_len": len(answer)},
            )

    return None
