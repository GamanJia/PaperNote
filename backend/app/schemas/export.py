from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.paper import PaperResult


class ExportRequest(BaseModel):
    search_id: str | None = None
    results: list[PaperResult] | None = None
    format: Literal["csv", "xlsx", "markdown"] = "csv"
    file_prefix: str | None = None


class ExportResponse(BaseModel):
    file_name: str
    format: str
    row_count: int
    created_at: datetime
    download_url: str
    absolute_path: str


class ExportRecord(BaseModel):
    file_name: str
    format: str
    row_count: int
    created_at: datetime
