from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.llm import LLMConfig
from app.schemas.paper import PaperResult


class SearchFilters(BaseModel):
    journals: list[str] = Field(default_factory=list)
    conferences: list[str] = Field(default_factory=list)
    year_start: int | None = None
    year_end: int | None = None
    date_start: str | None = None
    date_end: str | None = None


class SearchQueryInput(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    research_direction: str | None = None
    paper_description: str | None = None


class SearchParams(BaseModel):
    max_results: int = Field(default=50, ge=1, le=200)
    enable_llm_filter: bool = True
    enable_keyword_expansion: bool = True
    sort_by: Literal["relevance", "date_desc", "year_desc"] = "relevance"
    sources: list[str] = Field(default_factory=lambda: ["openalex", "arxiv"])
    llm_concurrency: int = Field(default=4, ge=1, le=20)
    cache_ttl_minutes: int = Field(default=120, ge=1, le=1440)


class ParsedQuery(BaseModel):
    topic: str = ""
    keywords: list[str] = Field(default_factory=list)
    expanded_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    venue_hints: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    filters: SearchFilters = Field(default_factory=SearchFilters)
    query: SearchQueryInput = Field(default_factory=SearchQueryInput)
    params: SearchParams = Field(default_factory=SearchParams)
    model: LLMConfig = Field(default_factory=LLMConfig)


class SearchStats(BaseModel):
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    total_candidates: int
    deduped_candidates: int
    final_results: int
    source_counts: dict[str, int] = Field(default_factory=dict)
    failed_sources: list[str] = Field(default_factory=list)
    venue_filtered_out: int = 0
    fallback_date_relaxed: bool = False


class SearchResponse(BaseModel):
    search_id: str
    parsed_query: ParsedQuery
    total_candidates: int
    results: list[PaperResult]
    stats: SearchStats
