from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from app.connectors.base import BaseConnector, ConnectorQuery
from app.repositories.cache_repository import CacheRepository
from app.schemas.paper import Paper
from app.schemas.search import ParsedQuery, SearchRequest
from app.utils.text_utils import normalize_doi, normalize_title, split_keywords


class PaperSearchService:
    logger = logging.getLogger(__name__)

    def __init__(self, connectors: dict[str, BaseConnector], cache_repository: CacheRepository) -> None:
        self.connectors = connectors
        self.cache_repository = cache_repository
        # 单数据源硬超时，避免前端长时间无响应。
        self.source_timeout_seconds = 25

    def _deduplicate(self, papers: list[Paper]) -> list[Paper]:
        seen: set[str] = set()
        deduped: list[Paper] = []

        for paper in papers:
            key = ""
            doi = normalize_doi(paper.doi)
            if doi:
                key = f"doi:{doi}"
            elif paper.arxiv_id:
                key = f"arxiv:{paper.arxiv_id.lower()}"
            elif paper.title:
                key = f"title:{normalize_title(paper.title)}"
            elif paper.url:
                key = f"url:{paper.url.strip().lower()}"

            if key and key in seen:
                continue
            if key:
                seen.add(key)
            deduped.append(paper)

        return deduped

    def _apply_excludes(self, papers: list[Paper], parsed_query: ParsedQuery) -> list[Paper]:
        excludes = [item.lower() for item in parsed_query.exclude_keywords if item]
        if not excludes:
            return papers

        result: list[Paper] = []
        for paper in papers:
            text = f"{paper.title} {paper.abstract}".lower()
            if any(token in text for token in excludes):
                continue
            result.append(paper)
        return result

    def _sort_papers(self, papers: list[Paper], sort_by: str) -> list[Paper]:
        if sort_by == "date_desc":
            return sorted(
                papers,
                key=lambda item: item.published_date or "",
                reverse=True,
            )
        if sort_by == "year_desc":
            return sorted(
                papers,
                key=lambda item: item.year or 0,
                reverse=True,
            )
        return papers

    async def _search_one_source(
        self,
        source_key: str,
        connector: BaseConnector,
        query: ConnectorQuery,
        ttl_seconds: int,
    ) -> list[Paper]:
        cache_key = (
            f"source:{source_key}:v11:"
            f"{json.dumps(query.model_dump(mode='json'), ensure_ascii=False, sort_keys=True)}"
        )
        cached = self.cache_repository.get(cache_key)
        if cached:
            return [Paper.model_validate(item) for item in cached]

        papers = await asyncio.wait_for(
            connector.search(query),
            timeout=self.source_timeout_seconds,
        )
        self.cache_repository.set(cache_key, [item.model_dump() for item in papers], ttl_seconds=ttl_seconds)
        return papers

    async def search(self, request: SearchRequest, parsed_query: ParsedQuery) -> tuple[list[Paper], dict[str, Any]]:
        keywords = split_keywords(request.query.keywords + parsed_query.keywords)
        if request.params.enable_keyword_expansion:
            keywords = split_keywords(keywords + parsed_query.expanded_keywords)

        query = ConnectorQuery(
            keywords=keywords,
            research_direction=request.query.research_direction,
            paper_description=request.query.paper_description,
            journals=request.filters.journals,
            conferences=request.filters.conferences,
            year_start=request.filters.year_start,
            year_end=request.filters.year_end,
            date_start=request.filters.date_start,
            date_end=request.filters.date_end,
            max_results=max(request.params.max_results * 2, request.params.max_results),
        )

        selected_sources = [item.lower() for item in request.params.sources if item]
        if not selected_sources:
            selected_sources = list(self.connectors.keys())

        ttl_seconds = request.params.cache_ttl_minutes * 60
        fallback_date_relaxed = False

        async def fetch_from_sources(connector_query: ConnectorQuery) -> tuple[list[Paper], dict[str, int], list[str]]:
            local_source_counts: dict[str, int] = {}
            local_failed_sources: list[str] = []
            local_merged: list[Paper] = []

            tasks: list[tuple[str, asyncio.Task[list[Paper]]]] = []
            for source_key in selected_sources:
                connector = self.connectors.get(source_key)
                if not connector:
                    local_failed_sources.append(source_key)
                    continue
                task = asyncio.create_task(
                    self._search_one_source(
                        source_key=source_key,
                        connector=connector,
                        query=connector_query,
                        ttl_seconds=ttl_seconds,
                    )
                )
                tasks.append((source_key, task))

            for source_key, task in tasks:
                try:
                    source_papers = await task
                    local_source_counts[source_key] = len(source_papers)
                    local_merged.extend(source_papers)
                except asyncio.TimeoutError:
                    self.logger.warning(
                        "source %s timeout after %ss",
                        source_key,
                        self.source_timeout_seconds,
                    )
                    local_failed_sources.append(source_key)
                except Exception:
                    local_failed_sources.append(source_key)

            return local_merged, local_source_counts, local_failed_sources

        merged, source_counts, failed_sources = await fetch_from_sources(query)

        # 若用户仅选择了单日窗口且无结果，则自动放宽到整年范围重试一次。
        if (
            not merged
            and query.date_start
            and query.date_end
            and query.date_start == query.date_end
            and len(query.date_start) >= 4
        ):
            year = query.date_start[:4]
            if year.isdigit():
                relaxed_query = query.model_copy(deep=True)
                relaxed_query.date_start = f"{year}-01-01"
                relaxed_query.date_end = f"{year}-12-31"
                merged, source_counts, failed_sources = await fetch_from_sources(relaxed_query)
                fallback_date_relaxed = True

        total_candidates = len(merged)
        deduped = self._deduplicate(merged)
        deduped = self._apply_excludes(deduped, parsed_query)
        deduped = self._sort_papers(deduped, request.params.sort_by)

        max_candidates = max(request.params.max_results * 3, request.params.max_results)
        deduped = deduped[:max_candidates]

        stats = {
            "source_counts": source_counts,
            "failed_sources": failed_sources,
            "total_candidates": total_candidates,
            "deduped_candidates": len(deduped),
            "searched_at": datetime.utcnow().isoformat(),
            "fallback_date_relaxed": fallback_date_relaxed,
        }
        return deduped, stats
