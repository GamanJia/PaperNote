from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import httpx
from fastapi import APIRouter, Query

from app.core.dependencies import get_connectors, get_file_storage, get_runtime_config

router = APIRouter(prefix="/api", tags=["sources"])

_venues_cache_payload: dict[str, list[str]] | None = None
_venues_cache_expires_at: datetime | None = None
_venue_query_aliases: dict[str, str] = {
    "neurips": "Neural Information Processing Systems",
    "nips": "Neural Information Processing Systems",
    "icml": "International Conference on Machine Learning",
    "iclr": "International Conference on Learning Representations",
    "iccv": "International Conference on Computer Vision",
    "cvpr": "Conference on Computer Vision and Pattern Recognition",
    "eccv": "European Conference on Computer Vision",
    "aaai": "AAAI Conference on Artificial Intelligence",
    "acl": "Annual Meeting of the Association for Computational Linguistics",
    "asplos": "Architectural Support for Programming Languages and Operating Systems",
}


def _unique_items(values: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in values:
        normalized = item.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def _expand_query_terms(keyword: str | None) -> list[str]:
    normalized = (keyword or "").strip()
    if not normalized:
        return []
    terms = [normalized]
    alias = _venue_query_aliases.get(normalized.lower())
    if alias:
        terms.append(alias)
    return _unique_items(terms)


def _cache_file_path() -> Path:
    runtime = get_runtime_config()
    return runtime.cache_dir / "venue_options_cache.json"


def _load_disk_cache() -> dict[str, list[str]] | None:
    payload = get_file_storage().read_json(_cache_file_path(), default=None)
    if not isinstance(payload, dict):
        return None
    conferences = payload.get("conferences")
    journals = payload.get("journals")
    if not isinstance(conferences, list) or not isinstance(journals, list):
        return None
    result = {
        "conferences": _unique_items(str(item) for item in conferences),
        "journals": _unique_items(str(item) for item in journals),
    }
    return result


def _save_disk_cache(payload: dict[str, list[str]]) -> None:
    get_file_storage().write_json_atomic(_cache_file_path(), payload)


def _filter_cached_venues(payload: dict[str, list[str]], keyword: str | None) -> dict[str, list[str]]:
    normalized = (keyword or "").strip().lower()
    if not normalized:
        return payload
    terms = [item.lower() for item in _expand_query_terms(keyword)] or [normalized]

    def pick(rows: list[str]) -> list[str]:
        result: list[str] = []
        for row in rows:
            lowered = row.lower()
            if any(term in lowered for term in terms):
                result.append(row)
        return result

    return {"conferences": pick(payload.get("conferences", [])), "journals": pick(payload.get("journals", []))}

async def _fetch_openalex_venues(
    kind: str,
    limit: int,
    trust_env_proxy: bool,
    keyword: str | None = None,
) -> list[str]:
    endpoint = "https://api.openalex.org/sources"
    headers = {"User-Agent": "PaperNote/0.1 (VenueOptions)"}
    bounded_limit = max(20, min(limit, 500))

    async with httpx.AsyncClient(timeout=12, trust_env=trust_env_proxy, headers=headers) as client:
        names: list[str] = []
        seen: set[str] = set()
        page = 1
        per_page = min(200, bounded_limit)

        while len(names) < bounded_limit:
            params: dict[str, str | int] = {
                "filter": f"type:{kind},works_count:>0",
                "per-page": per_page,
                "page": page,
            }
            if keyword:
                params["search"] = keyword
            else:
                params["sort"] = "works_count:desc"

            resp = await client.get(endpoint, params=params)
            resp.raise_for_status()
            payload = resp.json()
            rows = payload.get("results") or []
            if not rows:
                break

            for item in rows:
                name = str(item.get("display_name") or "").strip()
                if not name:
                    continue
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                names.append(name)
                if len(names) >= bounded_limit:
                    break

            if keyword:
                break
            page += 1

    return names[:bounded_limit]


async def _fetch_openalex_venues_multi(
    kind: str,
    limit: int,
    trust_env_proxy: bool,
    keyword: str | None,
) -> list[str]:
    terms = _expand_query_terms(keyword)
    if not terms:
        return await _fetch_openalex_venues(kind, limit, trust_env_proxy, keyword=None)

    per_term_limit = max(20, min(limit, 200))
    results = await asyncio.gather(
        *[
            _fetch_openalex_venues(
                kind=kind,
                limit=per_term_limit,
                trust_env_proxy=trust_env_proxy,
                keyword=term,
            )
            for term in terms
        ],
        return_exceptions=True,
    )

    merged: list[str] = []
    for item in results:
        if isinstance(item, Exception):
            continue
        merged.extend(item)
    return _unique_items(merged)[:limit]


async def _list_venue_options(keyword: str | None, limit: int) -> dict[str, list[str]]:
    global _venues_cache_payload, _venues_cache_expires_at

    normalized_keyword = (keyword or "").strip()
    cacheable = not normalized_keyword
    now = datetime.now(timezone.utc)
    if (
        cacheable
        and _venues_cache_payload
        and _venues_cache_expires_at
        and now < _venues_cache_expires_at
    ):
        return _venues_cache_payload

    runtime = get_runtime_config()
    try:
        conferences, journals = await asyncio.gather(
            _fetch_openalex_venues_multi(
                kind="conference",
                limit=limit,
                trust_env_proxy=runtime.openalex_trust_env_proxy,
                keyword=normalized_keyword or None,
            ),
            _fetch_openalex_venues_multi(
                kind="journal",
                limit=limit,
                trust_env_proxy=runtime.openalex_trust_env_proxy,
                keyword=normalized_keyword or None,
            ),
        )
        result = {"conferences": conferences, "journals": journals}
    except Exception:
        # 仅返回历史已从数据源获取到的缓存，避免注入无法验证可检索性的硬编码选项。
        if _venues_cache_payload:
            return _filter_cached_venues(_venues_cache_payload, normalized_keyword)
        disk_cache = _load_disk_cache()
        if disk_cache:
            return _filter_cached_venues(disk_cache, normalized_keyword)
        return {"conferences": [], "journals": []}

    if cacheable:
        _venues_cache_payload = result
        _venues_cache_expires_at = now + timedelta(hours=12)
        _save_disk_cache(result)
    return result


@router.get("/sources")
async def list_sources() -> list[dict[str, str]]:
    connectors = get_connectors()
    return [
        {"id": connector.source_key, "name": connector.source_name}
        for connector in connectors.values()
    ]


@router.get("/venue-options")
async def list_venue_options(
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=300, ge=20, le=500),
) -> dict[str, list[str]]:
    return await _list_venue_options(keyword=q, limit=limit)
