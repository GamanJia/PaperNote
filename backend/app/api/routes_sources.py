from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Query

from app.core.dependencies import get_connectors, get_runtime_config

router = APIRouter(prefix="/api", tags=["sources"])

_venues_cache_payload: dict[str, list[str]] | None = None
_venues_cache_expires_at: datetime | None = None

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
            _fetch_openalex_venues(
                kind="conference",
                limit=limit,
                trust_env_proxy=runtime.openalex_trust_env_proxy,
                keyword=normalized_keyword or None,
            ),
            _fetch_openalex_venues(
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
            return _venues_cache_payload
        return {"conferences": [], "journals": []}

    if cacheable:
        _venues_cache_payload = result
        _venues_cache_expires_at = now + timedelta(hours=12)
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
