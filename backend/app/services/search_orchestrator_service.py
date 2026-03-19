from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.repositories.search_history_repository import SearchHistoryRepository
from app.schemas.search import SearchRequest, SearchResponse, SearchStats
from app.services.paper_ranker_service import PaperRankerService
from app.services.paper_search_service import PaperSearchService
from app.services.query_parser_service import QueryParserService


class SearchOrchestratorService:
    def __init__(
        self,
        query_parser_service: QueryParserService,
        paper_search_service: PaperSearchService,
        paper_ranker_service: PaperRankerService,
        history_repository: SearchHistoryRepository,
    ) -> None:
        self.query_parser_service = query_parser_service
        self.paper_search_service = paper_search_service
        self.paper_ranker_service = paper_ranker_service
        self.history_repository = history_repository

    async def execute_search(
        self,
        request: SearchRequest,
        persist: bool = True,
    ) -> SearchResponse:
        started = datetime.now(timezone.utc)

        parsed_query = await self.query_parser_service.parse(request)
        candidates, source_stats = await self.paper_search_service.search(request, parsed_query)
        ranked_results = await self.paper_ranker_service.rank(request, parsed_query, candidates)

        finished = datetime.now(timezone.utc)
        duration_ms = int((finished - started).total_seconds() * 1000)

        stats = SearchStats(
            started_at=started,
            finished_at=finished,
            duration_ms=duration_ms,
            total_candidates=source_stats.get("total_candidates", len(candidates)),
            deduped_candidates=source_stats.get("deduped_candidates", len(candidates)),
            final_results=len(ranked_results),
            source_counts=source_stats.get("source_counts", {}),
            failed_sources=source_stats.get("failed_sources", []),
        )

        search_id = self.history_repository.generate_search_id()
        if persist:
            request_dump = request.model_dump(mode="json")
            request_dump["model"]["api_key"] = None
            record: dict[str, Any] = {
                "id": search_id,
                "created_at": started.isoformat(),
                "request": request_dump,
                "parsed_query": parsed_query.model_dump(mode="json"),
                "candidates": [item.model_dump(mode="json") for item in candidates],
                "results": [item.model_dump(mode="json") for item in ranked_results],
                "stats": stats.model_dump(mode="json"),
                "exports": [],
            }
            summary = self.history_repository.save_search(record)
            search_id = summary.id

        return SearchResponse(
            search_id=search_id,
            parsed_query=parsed_query,
            total_candidates=stats.total_candidates,
            results=ranked_results,
            stats=stats,
        )
