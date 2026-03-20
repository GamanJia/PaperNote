from __future__ import annotations

from datetime import datetime
import re
from uuid import uuid4
from xml.etree import ElementTree as ET

import httpx

from app.connectors.base import BaseConnector, ConnectorQuery
from app.schemas.paper import Paper


class ArxivConnector(BaseConnector):
    source_key = "arxiv"
    source_name = "arXiv"
    endpoint = "https://export.arxiv.org/api/query"
    venue_aliases = {
        "iclr": "international conference on learning representations",
        "icml": "international conference on machine learning",
        "neurips": "neural information processing systems",
        "nips": "neural information processing systems",
        "aaai": "aaai conference on artificial intelligence",
        "acl": "annual meeting of the association for computational linguistics",
        "emnlp": "empirical methods in natural language processing",
        "aamas": "international conference on autonomous agents and multiagent systems",
        "ijcai": "international joint conference on artificial intelligence",
        "asplos": "architectural support for programming languages and operating systems",
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

    namespace = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

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

    def _build_query(self, query: ConnectorQuery) -> str:
        priority_terms = self._expand_terms(query.conferences + query.journals)
        terms = query.keywords[:]
        if not terms and query.research_direction:
            terms.append(query.research_direction)
        if not terms and query.paper_description:
            terms.append(query.paper_description)
        terms.extend(priority_terms)
        if not terms:
            terms = ["machine learning"]

        expanded_terms = self._expand_terms(terms)
        priority_set = set(priority_terms)
        ordered_terms = priority_terms + [item for item in expanded_terms if item not in priority_set]
        english_terms = [item for item in ordered_terms if re.search(r"[A-Za-z]", item)]
        selected_terms = english_terms[:8] if english_terms else ordered_terms[:8]
        if not selected_terms:
            selected_terms = ["machine learning"]

        # arXiv 对多关键词 AND 很容易变成 0 结果，这里默认 OR 扩大召回。
        return " OR ".join(f'all:"{term}"' for term in selected_terms)

    def _extract_pdf_link(self, entry: ET.Element) -> str | None:
        for link in entry.findall("atom:link", self.namespace):
            if link.attrib.get("title") == "pdf":
                return link.attrib.get("href")
        return None

    def _matches_venue(self, venue_texts: list[str], journals: list[str], conferences: list[str]) -> bool:
        targets = [item for item in journals + conferences if item]
        if not targets:
            return True

        merged_text = " ".join(venue_texts).lower()
        for target in targets:
            normalized = target.lower().strip()
            if not normalized:
                continue
            if normalized in merged_text:
                return True
            alias = self.venue_aliases.get(normalized)
            if alias and alias in merged_text:
                return True
        return False

    def _within_year_range(self, published_date: str, year_start: int | None, year_end: int | None) -> bool:
        if not published_date:
            return True
        try:
            published_year = datetime.fromisoformat(published_date.replace("Z", "+00:00")).year
        except ValueError:
            return True
        if year_start and published_year < year_start:
            return False
        if year_end and published_year > year_end:
            return False
        return True

    def _within_date_range(
        self,
        published_date: str,
        date_start: str | None,
        date_end: str | None,
    ) -> bool:
        if not published_date:
            return True
        try:
            value = datetime.fromisoformat(published_date.replace("Z", "+00:00")).date()
        except ValueError:
            return True

        if date_start:
            try:
                if value < datetime.fromisoformat(date_start).date():
                    return False
            except ValueError:
                pass
        if date_end:
            try:
                if value > datetime.fromisoformat(date_end).date():
                    return False
            except ValueError:
                pass
        return True

    async def search(self, query: ConnectorQuery) -> list[Paper]:
        params = {
            "search_query": self._build_query(query),
            "start": 0,
            "max_results": max(5, min(query.max_results, 100)),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self.endpoint, params=params)
            response.raise_for_status()
            content = response.text

        root = ET.fromstring(content)
        papers: list[Paper] = []

        for entry in root.findall("atom:entry", self.namespace):
            title = (entry.findtext("atom:title", default="", namespaces=self.namespace) or "").strip()
            abstract = (entry.findtext("atom:summary", default="", namespaces=self.namespace) or "").strip()
            url = (entry.findtext("atom:id", default="", namespaces=self.namespace) or "").strip()
            published_date = (
                entry.findtext("atom:published", default="", namespaces=self.namespace) or ""
            ).strip()
            journal_ref = (
                entry.findtext("arxiv:journal_ref", default="", namespaces=self.namespace) or ""
            ).strip()
            comment = (entry.findtext("arxiv:comment", default="", namespaces=self.namespace) or "").strip()

            if not self._within_year_range(published_date, query.year_start, query.year_end):
                continue
            if not self._within_date_range(published_date, query.date_start, query.date_end):
                continue

            if not self._matches_venue(
                venue_texts=[journal_ref, comment],
                journals=query.journals,
                conferences=query.conferences,
            ):
                continue

            authors = [
                (node.findtext("atom:name", default="", namespaces=self.namespace) or "").strip()
                for node in entry.findall("atom:author", self.namespace)
                if (node.findtext("atom:name", default="", namespaces=self.namespace) or "").strip()
            ]
            categories = [
                node.attrib.get("term", "")
                for node in entry.findall("atom:category", self.namespace)
                if node.attrib.get("term")
            ]

            doi = (
                entry.findtext("arxiv:doi", default="", namespaces=self.namespace) or ""
            ).strip() or None
            arxiv_id = url.rstrip("/").split("/")[-1] if url else None
            year = None
            if published_date:
                try:
                    year = datetime.fromisoformat(published_date.replace("Z", "+00:00")).year
                except ValueError:
                    year = None

            venue = journal_ref or "arXiv"

            papers.append(
                Paper(
                    id=str(uuid4()),
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    year=year,
                    published_date=published_date[:10] if published_date else None,
                    venue=venue,
                    source=self.source_name,
                    doi=doi,
                    url=url or None,
                    pdf_url=self._extract_pdf_link(entry),
                    keywords=categories[:8],
                    citation_count=0,
                    arxiv_id=arxiv_id,
                )
            )

        return papers
