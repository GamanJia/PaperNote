from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.dependencies import get_llm_service, get_settings_repository
from app.schemas.settings import AppSettings, LLMTestRequest, LLMTestResponse

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=AppSettings)
async def get_settings() -> AppSettings:
    repo = get_settings_repository()
    return repo.load_settings()


@router.put("", response_model=AppSettings)
async def update_settings(settings: AppSettings) -> AppSettings:
    repo = get_settings_repository()
    sanitized = settings.model_copy(deep=True)
    sanitized.default_model.api_key = None
    return repo.save_settings(sanitized)


@router.post("/llm/test", response_model=LLMTestResponse)
async def test_llm_connection(request: LLMTestRequest) -> LLMTestResponse:
    llm_service = get_llm_service()
    result = await llm_service.test_connection(request.model)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("detail") or "llm unavailable")
    return LLMTestResponse(ok=True, detail=str(result.get("detail") or "ok"))
