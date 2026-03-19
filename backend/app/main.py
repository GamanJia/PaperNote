from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_export import router as export_router
from app.api.routes_history import router as history_router
from app.api.routes_search import router as search_router
from app.api.routes_settings import router as settings_router
from app.api.routes_sources import router as sources_router
from app.core.dependencies import get_runtime_config

runtime_config = get_runtime_config()

app = FastAPI(
    title="PaperNote API",
    version="0.1.0",
    description="Local paper retrieval and LLM ranking service",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=runtime_config.frontend_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router)
app.include_router(history_router)
app.include_router(export_router)
app.include_router(settings_router)
app.include_router(sources_router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
