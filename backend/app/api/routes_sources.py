from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import get_connectors

router = APIRouter(prefix="/api", tags=["sources"])


@router.get("/sources")
async def list_sources() -> list[dict[str, str]]:
    connectors = get_connectors()
    return [
        {"id": connector.source_key, "name": connector.source_name}
        for connector in connectors.values()
    ]
