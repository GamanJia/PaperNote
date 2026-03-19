from __future__ import annotations

import asyncio
import re

from app.schemas.search import ParsedQuery, SearchRequest
from app.services.llm_service import LLMService
from app.utils.text_utils import split_keywords


class QueryParserService:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service
        # 关键词扩展使用的 LLM 解析超时，超时后直接降级到本地解析。
        self.llm_parse_timeout_seconds = 6

    async def parse(self, request: SearchRequest) -> ParsedQuery:
        keywords = split_keywords(request.query.keywords)
        topic = (request.query.research_direction or request.query.paper_description or "").strip()
        venue_hints = split_keywords(request.filters.journals + request.filters.conferences)
        if not keywords and topic:
            derived = [item.strip() for item in re.split(r"[，,、；;。/\s]+", topic) if item.strip()]
            keywords = split_keywords(derived[:8])

        fallback = ParsedQuery(
            topic=topic or (", ".join(keywords[:3]) if keywords else "paper search"),
            keywords=keywords,
            expanded_keywords=[],
            exclude_keywords=[],
            venue_hints=venue_hints,
        )

        if not request.params.enable_keyword_expansion:
            return fallback

        if not request.query.research_direction and not request.query.paper_description:
            return fallback

        try:
            parsed = await asyncio.wait_for(
                self.llm_service.parse_query(
                    model_config=request.model,
                    keywords=keywords,
                    research_direction=request.query.research_direction,
                    paper_description=request.query.paper_description,
                ),
                timeout=self.llm_parse_timeout_seconds,
            )
            if not parsed.venue_hints and venue_hints:
                parsed.venue_hints = venue_hints
            if not parsed.keywords:
                parsed.keywords = keywords
            return parsed
        except Exception:
            return fallback
