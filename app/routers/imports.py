"""[API-24] CSV import. The body is the raw CSV bytes (Content-Type: text/csv)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from app.config import CSV_MAX_BYTES
from app.dependencies import get_import_service
from app.errors import AppError, ErrorCode
from app.routers.common import error_responses
from app.schemas.csv_import import ImportReportOut
from app.services.import_service import ImportService

router = APIRouter(prefix="/api/imports", tags=["imports"])
Service = Annotated[ImportService, Depends(get_import_service)]

_OPENAPI_BODY = {
    "requestBody": {
        "required": True,
        "description": "CSV file bytes (UTF-8, UTF-8 with BOM, or Shift_JIS). Max 1 MB / 5,000 rows.",
        "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}},
    }
}


async def _read_limited(request: Request, limit: int) -> bytes:
    """[CSV-03] Stop reading at limit + 1 bytes so huge bodies never sit in memory."""
    buffer = bytearray()
    async for chunk in request.stream():
        buffer.extend(chunk)
        if len(buffer) > limit:
            raise AppError(ErrorCode.CSV_TOO_LARGE, 413, "The file exceeds 1 MB.")
    return bytes(buffer)


@router.post(
    "/expenses",
    response_model=ImportReportOut,
    responses=error_responses(400, 413, 415),
    openapi_extra=_OPENAPI_BODY,
    summary="Import expenses from CSV",
)
async def import_expenses(request: Request, service: Service) -> ImportReportOut:
    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type != "text/csv":
        raise AppError(ErrorCode.CSV_UNSUPPORTED_MEDIA_TYPE, 415, "Content-Type must be text/csv.")
    raw = await _read_limited(request, CSV_MAX_BYTES)
    # File I/O and the store lock are blocking: keep them off the event loop.
    return await run_in_threadpool(service.import_csv, raw)
