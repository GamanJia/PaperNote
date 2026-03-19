from __future__ import annotations

import re
from collections.abc import Iterable
from uuid import uuid4

import httpx

from app.connectors.base import BaseConnector, ConnectorQuery
from app.schemas.paper import Paper
from app.utils.text_utils import normalize_doi


class OpenAlexConnector(BaseConnector):
    source_key = "openalex"
    source_name = "OpenAlex"
    endpoint = "https://api.openalex.org/works"
    venue_aliases = {
        "iclr": "international conference on learning representations",
        "icml": "international conference on machine learning",
        "neurips": "neural information processing systems",
        "nips": "neural information processing systems",
        "aaai": "aaai conference on artificial intelligence",
        "acl": "annual meeting of the association for computational linguistics",
        "cvpr": "conference on computer vision and pattern recognition",
        "eccv": "european conference on computer vision",
        "iccv": "international conference on computer vision",
    }
    keyword_hints = {
        "大语言模型": "large language model",
        "大型语言模型": "large language model",
        "多智能体": "multi-agent",
        "智能体": "agent",
        "记忆": "memory",
        "协作": "collaboration",
        "推理": "reasoning",
    }
    core_semantic_tokens = ("llm", "language model", "agent", "memory")
    llm_semantic_tokens = ("llm", "large language model", "language model")
    agent_memory_tokens = ("multi-agent", "multi agent", "agent", "memory", "collaborative")
    conference_source_ids = {
        "iclr": "S4306419637",
        "neurips": "S4306420609",
        "nips": "S4306420609",
        "aaai": "S4210191458",
    }

    def _reconstruct_abstract(self, inverted_index: dict | None) -> str:
        if not inverted_index:
            return ""
        token_positions: dict[int, str] = {}
        for token, positions in inverted_index.items():
            for position in positions:
                token_positions[position] = token
        return " ".join(token_positions[idx] for idx in sorted(token_positions))

    def _extract_arxiv_id(self, raw_item: dict) -> str | None:
        ids = raw_item.get("ids") or {}
        arxiv_url = ids.get("arxiv")
        if not arxiv_url:
            return None
        return arxiv_url.rstrip("/").split("/")[-1]

    def _extract_venue_texts(self, raw_item: dict) -> list[str]:
        values: list[str] = []
        primary_location = raw_item.get("primary_location") or {}
        primary_source = primary_location.get("source") or {}
        primary_name = (primary_source.get("display_name") or "").strip()
        if primary_name:
            values.append(primary_name)

        locations = raw_item.get("locations") or []
        for location in locations:
            source = (location or {}).get("source") or {}
            name = (source.get("display_name") or "").strip()
            if name:
                values.append(name)

        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(value)
        return deduped

    def _iter_normalized_targets(self, journals: list[str], conferences: list[str]) -> Iterable[str]:
        for target in journals + conferences:
            normalized = target.lower().strip()
            if normalized:
                yield normalized

    def _matches_venue(self, venue_texts: list[str], journals: list[str], conferences: list[str]) -> bool:
        targets = [item for item in journals + conferences if item]
        if not targets:
            return True

        normalized_venues = [value.lower() for value in venue_texts]
        for normalized in self._iter_normalized_targets(journals, conferences):
            alias = self.venue_aliases.get(normalized)
            for venue_text in normalized_venues:
                if normalized in venue_text:
                    return True
                if alias and alias in venue_text:
                    return True
        return False

    def _pick_display_venue(
        self,
        primary_venue: str | None,
        venue_texts: list[str],
        journals: list[str],
        conferences: list[str],
    ) -> str | None:
        if not venue_texts:
            return primary_venue

        for normalized in self._iter_normalized_targets(journals, conferences):
            alias = self.venue_aliases.get(normalized)
            for venue in venue_texts:
                lowered = venue.lower()
                if normalized in lowered:
                    return venue
                if alias and alias in lowered:
                    return venue

        return primary_venue or venue_texts[0]

    def _expand_terms(self, terms: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for term in terms:
            normalized = re.sub(r"\s+", " ", (term or "").strip())
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered not in seen:
                seen.add(lowered)
                result.append(normalized)

            for key, mapped in self.keyword_hints.items():
                if key in normalized:
                    mapped_lower = mapped.lower()
                    if mapped_lower not in seen:
                        seen.add(mapped_lower)
                        result.append(mapped)
        return result

    def _build_search_queries(self, query: ConnectorQuery) -> list[str | None]:
        priority_terms = self._expand_terms(query.conferences + query.journals)
        terms = query.keywords[:]
        if not terms and query.research_direction:
            terms.append(query.research_direction)
        if not terms and query.paper_description:
            terms.append(query.paper_description)
        terms.extend(priority_terms)

        if not terms:
            return [None]

        expanded_terms = self._expand_terms(terms)
        priority_set = set(priority_terms)
        ordered_terms = priority_terms + [item for item in expanded_terms if item not in priority_set]
        english_terms = [item for item in ordered_terms if re.search(r"[A-Za-z]", item)]
        selected_terms = english_terms[:8] if english_terms else ordered_terms[:8]

        queries: list[str] = []
        if selected_terms:
            queries.append(" ".join(selected_terms))

        core_terms = [
            term
            for term in selected_terms
            if any(token in term.lower() for token in self.core_semantic_tokens)
        ]
        for conf in query.conferences[:4]:
            normalized_conf = re.sub(r"\s+", " ", conf.strip())
            if not normalized_conf:
                continue
            merged = [normalized_conf] + core_terms[:4]
            query_text = " ".join(merged).strip()
            if query_text:
                queries.append(query_text)

        deduped_queries: list[str | None] = []
        seen: set[str] = set()
        for item in queries:
            key = item.lower().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped_queries.append(item)

        return deduped_queries or [None]

    def _build_core_semantic_query(self, query: ConnectorQuery) -> str | None:
        terms = query.keywords[:]
        if query.research_direction:
            terms.append(query.research_direction)
        if query.paper_description:
            terms.append(query.paper_description)
        expanded = self._expand_terms(terms)
        english = [item for item in expanded if re.search(r"[A-Za-z]", item)]
        core = [
            item
            for item in english
            if any(token in item.lower() for token in self.core_semantic_tokens)
        ]
        selected = core[:6] if core else english[:6]
        if not selected:
            return None
        return " ".join(selected)

    def _raw_item_key(self, item: dict) -> str:
        doi = normalize_doi(item.get("doi"))
        if doi:
            return f"doi:{doi}"

        item_id = (item.get("id") or "").strip().lower()
        if item_id:
            return f"id:{item_id}"

        title = re.sub(r"\s+", " ", (item.get("display_name") or item.get("title") or "").strip().lower())
        if title:
            return f"title:{title}"
        return ""

    def _raw_item_text(self, item: dict) -> str:
        title = (item.get("display_name") or item.get("title") or "").lower()
        abstract = self._reconstruct_abstract(item.get("abstract_inverted_index")).lower()
        return f"{title} {abstract}".strip()

    def _matches_semantic_focus(self, item: dict, query: ConnectorQuery) -> bool:
        text = self._raw_item_text(item)
        if not text:
            return False

        llm_hit = any(token in text for token in self.llm_semantic_tokens)
        agent_memory_hit = any(token in text for token in self.agent_memory_tokens)
        if llm_hit and agent_memory_hit:
            return True

        # 对非典型表达保留兜底：只要命中核心词即可。
        return any(token in text for token in self.core_semantic_tokens)

    async def search(self, query: ConnectorQuery) -> list[Paper]:
        base_params: dict[str, str | int] = {
            # OpenAlex 默认相关性排序较宽泛，适当提高抓取上限以避免漏召回。
            "per-page": max(100, min(query.max_results * 3, 200)),
        }
        search_queries = self._build_search_queries(query)

        filters: list[str] = []
        if query.date_start:
            filters.append(f"from_publication_date:{query.date_start}")
        elif query.year_start:
            filters.append(f"from_publication_date:{query.year_start}-01-01")

        if query.date_end:
            filters.append(f"to_publication_date:{query.date_end}")
        elif query.year_end:
            filters.append(f"to_publication_date:{query.year_end}-12-31")
        if filters:
            base_params["filter"] = ",".join(filters)

        raw_items: list[dict] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for search_query in search_queries:
                params = base_params.copy()
                if search_query:
                    params["search"] = search_query
                response = await client.get(self.endpoint, params=params)
                response.raise_for_status()
                payload = response.json()
                raw_items.extend(payload.get("results", []))

            conference_source_ids: set[str] = set()
            for conf in query.conferences:
                normalized = conf.lower().strip()
                source_id = self.conference_source_ids.get(normalized)
                if source_id:
                    conference_source_ids.add(source_id)

            targeted_query = self._build_core_semantic_query(query)
            for source_id in conference_source_ids:
                params = base_params.copy()
                filters_text = str(params.get("filter") or "")
                source_filter = f"locations.source.id:https://openalex.org/{source_id}"
                params["filter"] = f"{source_filter},{filters_text}" if filters_text else source_filter
                if targeted_query:
                    params["search"] = targeted_query
                response = await client.get(self.endpoint, params=params)
                response.raise_for_status()
                payload = response.json()
                raw_items.extend(payload.get("results", []))

                if targeted_query:
                    fallback_params = base_params.copy()
                    fallback_filters_text = str(fallback_params.get("filter") or "")
                    fallback_params["filter"] = (
                        f"{source_filter},{fallback_filters_text}"
                        if fallback_filters_text
                        else source_filter
                    )
                    fallback_response = await client.get(self.endpoint, params=fallback_params)
                    fallback_response.raise_for_status()
                    fallback_payload = fallback_response.json()
                    for fallback_item in fallback_payload.get("results", []):
                        if self._matches_semantic_focus(fallback_item, query):
                            raw_items.append(fallback_item)

        deduped_raw_items: list[dict] = []
        seen_item_keys: set[str] = set()
        for item in raw_items:
            key = self._raw_item_key(item)
            if key and key in seen_item_keys:
                continue
            if key:
                seen_item_keys.add(key)
            deduped_raw_items.append(item)

        papers: list[Paper] = []
        for item in deduped_raw_items:
            location = item.get("primary_location") or {}
            source = location.get("source") or {}
            primary_venue = source.get("display_name")
            venue_texts = self._extract_venue_texts(item)

            if not self._matches_venue(venue_texts, query.journals, query.conferences):
                continue

            venue = self._pick_display_venue(primary_venue, venue_texts, query.journals, query.conferences)
            doi = normalize_doi(item.get("doi"))
            abstract = self._reconstruct_abstract(item.get("abstract_inverted_index"))
            concepts = item.get("concepts") or []
            keywords = [concept.get("display_name", "") for concept in concepts[:8] if concept.get("display_name")]

            papers.append(
                Paper(
                    id=str(uuid4()),
                    title=item.get("display_name") or item.get("title") or "",
                    authors=[
                        authorship.get("author", {}).get("display_name", "")
                        for authorship in (item.get("authorships") or [])
                        if authorship.get("author", {}).get("display_name")
                    ],
                    abstract=abstract,
                    year=item.get("publication_year"),
                    published_date=item.get("publication_date"),
                    venue=venue,
                    source=self.source_name,
                    doi=doi or None,
                    url=location.get("landing_page_url") or item.get("id"),
                    pdf_url=(item.get("best_oa_location") or {}).get("pdf_url"),
                    keywords=keywords,
                    citation_count=int(item.get("cited_by_count") or 0),
                    arxiv_id=self._extract_arxiv_id(item),
                )
            )

        upper_bound = max(5, query.max_results)
        return papers[:upper_bound]
