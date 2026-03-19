from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.dependencies import get_export_service, get_runtime_config, get_search_history_repository
from app.schemas.export import ExportRequest, ExportResponse
from app.schemas.paper import PaperResult

router = APIRouter(prefix="/api", tags=["export"])


@router.post("/export", response_model=ExportResponse)
async def export_results(request: ExportRequest) -> ExportResponse:
    repo = get_search_history_repository()
    rows: list[PaperResult] = []

    if request.search_id:
        record = repo.get_search(request.search_id)
        if not record:
            raise HTTPException(status_code=404, detail="search record not found")
        rows = [PaperResult.model_validate(item) for item in record.get("results", [])]
    elif request.results:
        rows = request.results
    else:
        raise HTTPException(status_code=400, detail="search_id or results is required")

    exporter = get_export_service()
    metadata = exporter.export_results(rows, request.format, request.file_prefix)
    if request.search_id:
        repo.add_export_record(
            request.search_id,
            {
                "file_name": metadata["file_name"],
                "format": metadata["format"],
                "row_count": metadata["row_count"],
                "created_at": metadata["created_at"].isoformat(),
            },
        )

    return ExportResponse(
        file_name=metadata["file_name"],
        format=metadata["format"],
        row_count=metadata["row_count"],
        created_at=metadata["created_at"],
        download_url=f"/api/exports/{metadata['file_name']}",
        absolute_path=metadata["absolute_path"],
    )


@router.get("/exports/{file_name}")
async def download_export(file_name: str) -> FileResponse:
    config = get_runtime_config()
    output_path = config.exports_dir / file_name
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="export file not found")

    suffix = output_path.suffix.lower()
    media_type = "application/octet-stream"
    if suffix == ".csv":
        media_type = "text/csv"
    elif suffix == ".xlsx":
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif suffix == ".md":
        media_type = "text/markdown"

    return FileResponse(path=Path(output_path), filename=file_name, media_type=media_type)
