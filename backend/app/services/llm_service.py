from __future__ import annotations

import json
from typing import Any

from app.core.config import RuntimeConfig
from app.schemas.llm import LLMConfig, LLMProviderType
from app.schemas.paper import Paper
from app.schemas.search import ParsedQuery
from app.services.llm.providers import BaseLLMProvider, OllamaProvider, OpenAICompatibleProvider
from app.utils.text_utils import split_keywords


class LLMService:
    def __init__(self, runtime_config: RuntimeConfig) -> None:
        self.runtime_config = runtime_config

    def resolve_config(self, raw_config: LLMConfig) -> LLMConfig:
        config = raw_config.model_copy(deep=True)

        if config.provider_type == LLMProviderType.OPENAI_COMPATIBLE:
            config.base_url = config.base_url or self.runtime_config.openai_base_url
            if not config.api_key:
                config.api_key = self.runtime_config.openai_api_key or None
            config.model_name = config.model_name or self.runtime_config.default_model_name
        else:
            config.base_url = config.base_url or self.runtime_config.ollama_base_url
            config.model_name = config.model_name or "llama3.1"
            config.api_key = None

        return config

    def _build_provider(self, model_config: LLMConfig) -> BaseLLMProvider:
        resolved = self.resolve_config(model_config)
        if resolved.provider_type == LLMProviderType.OLLAMA:
            return OllamaProvider(resolved)
        return OpenAICompatibleProvider(resolved)

    async def test_connection(self, model_config: LLMConfig) -> dict[str, Any]:
        provider = self._build_provider(model_config)
        return await provider.health_check()

    async def parse_query(
        self,
        model_config: LLMConfig,
        keywords: list[str],
        research_direction: str | None,
        paper_description: str | None,
    ) -> ParsedQuery:
        provider = self._build_provider(model_config)
        prompt = f"""
请把用户需求解析为 JSON，只返回 JSON：
{{
  "topic": "string",
  "keywords": ["string"],
  "expanded_keywords": ["string"],
  "exclude_keywords": ["string"],
  "venue_hints": ["string"]
}}

用户关键词: {keywords}
研究方向: {research_direction or ""}
论文描述: {paper_description or ""}
"""
        system_prompt = "你是论文检索助手。输出必须是合法 JSON，不要解释。"
        payload = await provider.generate_json(prompt=prompt, system_prompt=system_prompt)

        if not isinstance(payload, dict):
            payload = {}

        result = ParsedQuery(
            topic=str(payload.get("topic") or research_direction or ""),
            keywords=split_keywords(payload.get("keywords") or keywords),
            expanded_keywords=split_keywords(payload.get("expanded_keywords") or []),
            exclude_keywords=split_keywords(payload.get("exclude_keywords") or []),
            venue_hints=split_keywords(payload.get("venue_hints") or []),
        )

        if not result.keywords:
            result.keywords = split_keywords(keywords)
        if not result.topic:
            result.topic = (research_direction or paper_description or "paper search").strip()
        return result

    async def analyze_paper(
        self,
        model_config: LLMConfig,
        parsed_query: ParsedQuery,
        paper: Paper,
    ) -> dict[str, Any]:
        provider = self._build_provider(model_config)
        prompt = f"""
你需要判断论文是否与检索目标相关。请只输出 JSON：
{{
  "is_relevant": true,
  "relevance_score": 0-100,
  "tags": ["string"],
  "summary": "string",
  "reason": "string",
  "innovation": "string",
  "match_points": ["string"]
}}

检索主题:
{json.dumps(parsed_query.model_dump(mode="json"), ensure_ascii=False, indent=2)}

论文信息:
{json.dumps(paper.model_dump(mode="json"), ensure_ascii=False, indent=2)}
"""
        system_prompt = "你是学术论文分析助手。仅返回合法 JSON。"
        payload = await provider.generate_json(prompt=prompt, system_prompt=system_prompt)
        if not isinstance(payload, dict):
            payload = {}

        return {
            "is_relevant": bool(payload.get("is_relevant", True)),
            "relevance_score": int(max(0, min(100, int(payload.get("relevance_score", 0) or 0)))),
            "tags": split_keywords(payload.get("tags") or []),
            "summary": str(payload.get("summary") or ""),
            "reason": str(payload.get("reason") or ""),
            "innovation": str(payload.get("innovation") or ""),
            "match_points": split_keywords(payload.get("match_points") or []),
        }
