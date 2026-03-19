from __future__ import annotations

import re
from typing import Iterable, List


def normalize_text(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text or "").strip().lower()
    return collapsed


def normalize_title(title: str) -> str:
    value = normalize_text(title)
    return re.sub(r"[^a-z0-9]+", "", value)


def normalize_doi(doi: str | None) -> str:
    if not doi:
        return ""
    lowered = doi.strip().lower()
    prefixes = ["https://doi.org/", "http://doi.org/", "doi:"]
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return lowered[len(prefix) :]
    return lowered


def split_keywords(raw_values: Iterable[str] | str | None) -> List[str]:
    keywords: List[str] = []
    seen = set()

    if raw_values is None:
        return keywords
    if isinstance(raw_values, str):
        iterator: Iterable[str] = [raw_values]
    else:
        iterator = raw_values

    for item in iterator:
        if not item:
            continue
        parts = [piece.strip() for piece in str(item).split(",")]
        for part in parts:
            if not part:
                continue
            lowered = part.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            keywords.append(part)

    return keywords


def short_text(text: str, limit: int = 140) -> str:
    value = normalize_text(text)
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."
