from __future__ import annotations

import json
import os
from typing import List

from openai import OpenAI

from .models import Finding


SYSTEM_PROMPT = (
    "You are an internal due-diligence questionnaire (DDQ) validator. "
    "Be strict, factual, and concise. Do not cite regulations unless they are explicitly provided in the expected/model text. "
    "Return ONLY valid JSON matching the requested schema."
)


def llm_refine_findings(findings: List[Finding], model: str = "gpt-5.2", max_items: int = 30) -> List[Finding]:
    """Refine flagged items with an LLM (gated; do NOT call for all rows).

    - Only runs if OPENAI_API_KEY is set.
    - Only processes up to `max_items` findings to keep costs controlled.
    """

    if not os.environ.get("OPENAI_API_KEY"):
        return findings

    client = OpenAI()

    for f in findings[:max_items]:
        if f.status == "NEEDS_EVIDENCE" or (f.details or {}).get("reference_detected"):
            continue
        prompt = {
            "question": f.question_text,
            "customer_answer": f.answer_text,
            "expected": f.expected_text,
            "current_status": f.status,
            "current_reason": f.reason,
            "task": "Refine the assessment and suggest what exactly the customer must add/fix.",
            "output_schema": {
                "status": "OK | INCOMPLETE | REJECTED | NEEDS_EVIDENCE",
                "reason": "short explanation",
                "missing_points": ["..."],
                "customer_request": "one short instruction to the customer"
            }
        }

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            temperature=0,
        )

        content = (resp.choices[0].message.content or "").strip()
        try:
            data = json.loads(content)
            f.status = data.get("status", f.status)
            f.reason = data.get("reason", f.reason)
            f.details = (f.details or {}) | {
                "missing_points": data.get("missing_points", []),
                "customer_request": data.get("customer_request", ""),
                "llm": True,
                "llm_model": model,
            }
        except Exception:
            # If the model responds with non-JSON, keep deterministic result and store raw output
            f.details = (f.details or {}) | {"llm_raw": content, "llm": True, "llm_model": model}

    return findings
