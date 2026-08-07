"""Liveness/readiness endpoints for orchestration & load balancers."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from worldview.db import get_db

router = APIRouter(tags=["ops"])


@router.get("/healthz", summary="Liveness probe")
def healthz() -> dict[str, str]:
    """Process is up and able to serve requests."""
    return {"status": "ok"}


@router.get("/readyz", summary="Readiness probe (DB connectivity)")
def readyz(db: Session = Depends(get_db)) -> dict[str, str]:
    """Service can reach its backing database."""
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
