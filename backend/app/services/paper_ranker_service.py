from __future__ import annotations

import asyncio
import json
from datetime import datetime

from app.repositories.cache_repository import CacheRepository
from app.schemas.paper import Paper, PaperResult
from app.schemas.search import ParsedQuery, SearchRequest
from app.services.llm_service import LLMService
from app.utils.text_utils import short_text, split_keywords


class PaperRankerService:
    def __init__(self, llm_service: LLMService, cache_repository: CacheRepository) -> None:
        self.llm_service = llm_service
        self.cache_repository = cache_repository

    def _heuristic_analysis(self, parsed_query: ParsedQuery, paper: Paper) -> dict:
        all_keywords = split_keywords(parsed_query.keywords + parsed_query.expanded_keywords)
        lowered_text = f"{paper.title} {paper.abstract}".lower()
        matched = [word for word in all_keywords if word.lower() in lowered_text]
        match_count = len(set(item.lower() for item in matched))

        score = 40 + match_count * 12
        if paper.year and paper.year >= datetime.utcnow().year - 2:
            score += 5
        score = max(0, min(100, score))

        return {
            "is_relevant": bool(match_count > 0 or not all_keywords),
            "relevance_score": score,
            "tags": matched[:5],
            "summary": short_text(paper.abstract or paper.title, limit=140),
            "reason": "基于关键词匹配的本地降级分析结果。",
            "innovation": "",
            "match_points": matched[:5],
        }

    async def _analyze_one(self, request: SearchRequest, parsed_query: ParsedQuery, paper: Paper) -> PaperResult:
        cache_key = "llm:" + json.dumps(
            {
                "provider": request.model.provider_type.value,
                "base_url": request.model.base_url,
                "model": request.model.model_name,
                "topic": parsed_query.topic,
                "keywords": parsed_query.keywords,
                "paper": {
                    "title": paper.title,
                    "abstract": paper.abstract,
                    "year": paper.year,
                    "source": paper.source,
                },
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        cached = self.cache_repository.get(cache_key)
        if cached:
            analysis = cached
        else:
            try:
                analysis = await self.llm_service.analyze_paper(request.model, parsed_query, paper)
            except Exception:
                analysis = self._heuristic_analysis(parsed_query, paper)
            self.cache_repository.set(cache_key, analysis, ttl_seconds=86400)

        return PaperResult(
            **paper.model_dump(),
            is_relevant=bool(analysis.get("is_relevant", True)),
            relevance_score=int(max(0, min(100, int(analysis.get("relevance_score", 0) or 0)))),
            tags=split_keywords(analysis.get("tags") or []),
            summary=str(analysis.get("summary") or ""),
            reason=str(analysis.get("reason") or ""),
            innovation=str(analysis.get("innovation") or ""),
            match_points=split_keywords(analysis.get("match_points") or []),
        )

    def _sort_results(self, request: SearchRequest, results: list[PaperResult]) -> list[PaperResult]:
        if request.params.sort_by == "date_desc":
            return sorted(results, key=lambda item: item.published_date or "", reverse=True)
        if request.params.sort_by == "year_desc":
            return sorted(results, key=lambda item: item.year or 0, reverse=True)
        return sorted(results, key=lambda item: item.relevance_score, reverse=True)

    async def rank(
        self,
        request: SearchRequest,
        parsed_query: ParsedQuery,
        papers: list[Paper],
    ) -> list[PaperResult]:
        if not papers:
            return []

        if not request.params.enable_llm_filter:
            results = [
                PaperResult(**paper.model_dump(), **self._heuristic_analysis(parsed_query, paper))
                for paper in papers
            ]
            return self._sort_results(request, results)[: request.params.max_results]

        semaphore = asyncio.Semaphore(request.params.llm_concurrency)

        async def guarded(paper: Paper) -> PaperResult:
            async with semaphore:
                return await self._analyze_one(request, parsed_query, paper)

        tasks = [guarded(paper) for paper in papers]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[PaperResult] = []
        for idx, item in enumerate(raw_results):
            if isinstance(item, Exception):
                results.append(
                    PaperResult(
                        **papers[idx].model_dump(),
                        **self._heuristic_analysis(parsed_query, papers[idx]),
                    )
                )
                continue
            results.append(item)

        relevant = [item for item in results if item.is_relevant]
        if not relevant:
            ranked = self._sort_results(request, results)
            return ranked[: request.params.max_results]

        ranked_relevant = self._sort_results(request, relevant)
        min_kept = min(request.params.max_results, max(5, request.params.max_results // 3))
        if len(ranked_relevant) >= min_kept:
            return ranked_relevant[: request.params.max_results]

        ranked_all = self._sort_results(request, results)
        kept_ids = {item.id for item in ranked_relevant}
        supplements: list[PaperResult] = []
        for item in ranked_all:
            if item.id in kept_ids:
                continue
            supplements.append(item)
            kept_ids.add(item.id)
            if len(ranked_relevant) + len(supplements) >= min_kept:
                break

        blended = ranked_relevant + supplements
        blended = self._sort_results(request, blended)
        return blended[: request.params.max_results]
