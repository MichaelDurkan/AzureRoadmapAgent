"""Liveness / readiness probes."""
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Health"])


@router.get("/", include_in_schema=False)
def root():
    return {"name": "Azure Roadmap Agent API", "version": "1.0.0", "docs": "/docs"}


@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/ready", summary="Readiness probe")
def ready():
    return JSONResponse(content={"status": "ready"}, status_code=200)
