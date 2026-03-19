from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from app.schemas.paper import Paper


class ConnectorQuery(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    research_direction: str | None = None
    paper_description: str | None = None
    journals: list[str] = Field(default_factory=list)
    conferences: list[str] = Field(default_factory=list)
    year_start: int | None = None
    year_end: int | None = None
    date_start: str | None = None
    date_end: str | None = None
    max_results: int = 50


class BaseConnector(ABC):
    source_key: str
    source_name: str

    @abstractmethod
    async def search(self, query: ConnectorQuery) -> list[Paper]:
        raise NotImplementedError
