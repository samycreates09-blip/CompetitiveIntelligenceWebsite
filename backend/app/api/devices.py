from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.engine import Connection

from app.deps import get_db
from app.services.device_service import get_device_by_id, get_device_history, get_devices

router = APIRouter(prefix="/api/v1")


@router.get("/devices")
def list_devices(
    competitor_id: Optional[int] = Query(default=None),
    manufacturer: Optional[str] = Query(default=None),
    device_type: Optional[str] = Query(default=None),
    conn: Connection = Depends(get_db),
):
    if competitor_id is not None and competitor_id <= 0:
        raise HTTPException(status_code=400, detail="competitor_id must be greater than 0")
    return get_devices(conn, competitor_id=competitor_id, manufacturer=manufacturer, device_type=device_type)


@router.get("/devices/{device_id}")
def get_device(
    device_id: int,
    conn: Connection = Depends(get_db),
):
    if device_id <= 0:
        raise HTTPException(status_code=400, detail="device_id must be greater than 0")
    device = get_device_by_id(conn, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail=f"Device with id {device_id} was not found.")
    return device


@router.get("/devices/{device_id}/history")
def get_device_history_by_id(
    device_id: int,
    from_date: Optional[date] = Query(default=None),
    to_date: Optional[date] = Query(default=None),
    order: str = Query(default="asc"),
    conn: Connection = Depends(get_db),
):
    if device_id <= 0:
        raise HTTPException(status_code=400, detail="device_id must be greater than 0")
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date cannot be later than to_date")
    if order.lower() not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="order must be either asc or desc")

    query_result = get_device_history(conn, device_id=device_id, from_date=from_date, to_date=to_date, order=order)
    if not query_result:
        raise HTTPException(status_code=404, detail=f"Device history for device_id {device_id} was not found.")
    return query_result
