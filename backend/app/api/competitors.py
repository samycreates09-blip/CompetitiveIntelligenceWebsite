from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.engine import Connection

from app.deps import get_db
from app.services.competitor_service import get_competitor_by_id, get_competitors

router = APIRouter(prefix="/api/v1")


@router.get("/competitors")
def list_competitors(
    is_active: Optional[bool] = Query(default=None),
    conn: Connection = Depends(get_db),
):
    return get_competitors(conn, is_active=is_active)


@router.get("/competitors/{competitor_id}")
def get_competitor(
    competitor_id: int,
    conn: Connection = Depends(get_db),
):
    if competitor_id <= 0:
        raise HTTPException(status_code=400, detail="competitor_id must be greater than 0")
    competitor = get_competitor_by_id(conn, competitor_id)
    if competitor is None:
        raise HTTPException(status_code=404, detail=f"Competitor with id {competitor_id} was not found.")
    return competitor
