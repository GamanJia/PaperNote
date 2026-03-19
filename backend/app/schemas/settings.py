from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.llm import LLMConfig


class AppSettings(BaseModel):
    default_model: LLMConfig = Field(default_factory=LLMConfig)
    enabled_sources: list[str] = Field(default_factory=lambda: ["openalex", "arxiv"])
    default_export_format: Literal["csv", "xlsx", "markdown"] = "csv"


class LLMTestRequest(BaseModel):
    model: LLMConfig


class LLMTestResponse(BaseModel):
    ok: bool
    detail: str
