from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.engine import Connection

from app.deps import get_db
from app.services.change_service import get_change_by_id, get_changes

router = APIRouter(prefix="/api/v1")


@router.get("/changes")
def list_changes(
    competitor_id: Optional[int] = Query(default=None),
    change_type: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    record_origin: Optional[str] = Query(default=None, pattern="^(synthetic_seeded|system_detected)$"),
    from_date: Optional[date] = Query(default=None),
    to_date: Optional[date] = Query(default=None),
    conn: Connection = Depends(get_db),
):
    if competitor_id is not None and competitor_id <= 0:
        raise HTTPException(status_code=400, detail="competitor_id must be greater than 0")
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date cannot be later than to_date")
    if severity is not None and severity not in {"low", "medium", "high"}:
        raise HTTPException(status_code=400, detail="severity must be one of: low, medium, high")
    return get_changes(
        conn,
        competitor_id=competitor_id,
        change_type=change_type,
        entity_type=entity_type,
        severity=severity,
        record_origin=record_origin,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/changes/{change_id}")
def get_change(
    change_id: int,
    conn: Connection = Depends(get_db),
):
    if change_id <= 0:
        raise HTTPException(status_code=400, detail="change_id must be greater than 0")
    change = get_change_by_id(conn, change_id)
    if change is None:
        raise HTTPException(status_code=404, detail=f"Change with id {change_id} was not found.")
    return change
