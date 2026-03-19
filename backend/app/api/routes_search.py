from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import get_search_orchestrator_service, get_settings_repository
from app.schemas.search import SearchRequest, SearchResponse
from app.schemas.settings import AppSettings

router = APIRouter(prefix="/api", tags=["search"])


def _merge_with_settings(request: SearchRequest, settings: AppSettings) -> SearchRequest:
    merged = request.model_copy(deep=True)

    if not merged.params.sources:
        merged.params.sources = settings.enabled_sources
    if not merged.model.base_url:
        merged.model.base_url = settings.default_model.base_url
    if not merged.model.model_name:
        merged.model.model_name = settings.default_model.model_name
    if merged.model.temperature is None:
        merged.model.temperature = settings.default_model.temperature
    if merged.model.max_tokens is None:
        merged.model.max_tokens = settings.default_model.max_tokens
    return merged


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    settings_repo = get_settings_repository()
    settings = settings_repo.load_settings()
    merged = _merge_with_settings(request, settings)

    orchestrator = get_search_orchestrator_service()
    return await orchestrator.execute_search(merged, persist=True)
