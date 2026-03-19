from __future__ import annotations

from pydantic import BaseModel, Field


class Paper(BaseModel):
    id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    year: int | None = None
    published_date: str | None = None
    venue: str | None = None
    source: str
    doi: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    keywords: list[str] = Field(default_factory=list)
    citation_count: int = 0
    arxiv_id: str | None = None


class PaperResult(Paper):
    is_relevant: bool = True
    relevance_score: int = Field(default=0, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    reason: str = ""
    innovation: str = ""
    match_points: list[str] = Field(default_factory=list)
