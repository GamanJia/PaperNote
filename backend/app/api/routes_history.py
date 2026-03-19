from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.dependencies import get_search_history_repository, get_search_orchestrator_service
from app.schemas.history import HistoryDetail, HistorySummary
from app.schemas.search import SearchRequest, SearchResponse

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=list[HistorySummary])
async def list_history() -> list[HistorySummary]:
    repo = get_search_history_repository()
    return repo.list_history()


@router.get("/{search_id}", response_model=HistoryDetail)
async def get_history_detail(search_id: str) -> HistoryDetail:
    repo = get_search_history_repository()
    record = repo.get_search(search_id)
    if not record:
        raise HTTPException(status_code=404, detail="search record not found")
    return HistoryDetail.model_validate(record)


@router.delete("/{search_id}")
async def delete_history(search_id: str) -> dict[str, bool]:
    repo = get_search_history_repository()
    deleted = repo.delete_search(search_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="search record not found")
    return {"ok": True}


@router.post("/{search_id}/rerun", response_model=SearchResponse)
async def rerun_history(search_id: str) -> SearchResponse:
    repo = get_search_history_repository()
    record = repo.get_search(search_id)
    if not record:
        raise HTTPException(status_code=404, detail="search record not found")

    try:
        request = SearchRequest.model_validate(record.get("request") or {})
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid stored request: {exc}") from exc

    orchestrator = get_search_orchestrator_service()
    return await orchestrator.execute_search(request, persist=True)
