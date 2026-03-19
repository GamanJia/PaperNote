from __future__ import annotations

import json
import re
from typing import Any


def extract_json_candidate(raw_text: str) -> str:
    text = raw_text.strip()
    if not text:
        return "{}"

    fenced = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, flags=re.S)
    if fenced:
        return fenced.group(1).strip()

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        return text[first_brace : last_brace + 1]

    first_bracket = text.find("[")
    last_bracket = text.rfind("]")
    if first_bracket >= 0 and last_bracket > first_bracket:
        return text[first_bracket : last_bracket + 1]

    return text


def safe_json_loads(raw_text: str, fallback: Any) -> Any:
    candidate = extract_json_candidate(raw_text)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        repaired = candidate.replace("\n", " ").replace("\t", " ")
        repaired = re.sub(r",\s*}", "}", repaired)
        repaired = re.sub(r",\s*]", "]", repaired)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            return fallback
