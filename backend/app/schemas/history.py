from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.search import ParsedQuery


class HistorySummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    total_candidates: int
    final_results: int


class HistoryDetail(BaseModel):
    id: str
    title: str
    created_at: datetime
    request: dict[str, Any]
    parsed_query: ParsedQuery
    stats: dict[str, Any] = Field(default_factory=dict)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    results: list[dict[str, Any]] = Field(default_factory=list)
    exports: list[dict[str, Any]] = Field(default_factory=list)
