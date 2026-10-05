from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.engine import Connection

from app.deps import get_db
from app.services.promotion_service import get_promotion_by_id, get_promotions

router = APIRouter(prefix="/api/v1")


@router.get("/promotions")
def list_promotions(
    competitor_id: Optional[int] = Query(default=None),
    target_type: Optional[str] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    active_only: bool = Query(default=False),
    conn: Connection = Depends(get_db),
):
    if competitor_id is not None and competitor_id <= 0:
        raise HTTPException(status_code=400, detail="competitor_id must be greater than 0")
    if target_type is not None and target_type not in {"plan", "device", "bundle"}:
        raise HTTPException(status_code=400, detail="target_type must be one of: plan, device, bundle")
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be later than end_date")
    return get_promotions(
        conn,
        competitor_id=competitor_id,
        target_type=target_type,
        start_date=start_date,
        end_date=end_date,
        active_only=active_only,
    )


@router.get("/promotions/{promotion_id}")
def get_promotion(
    promotion_id: int,
    conn: Connection = Depends(get_db),
):
    if promotion_id <= 0:
        raise HTTPException(status_code=400, detail="promotion_id must be greater than 0")
    promotion = get_promotion_by_id(conn, promotion_id)
    if promotion is None:
        raise HTTPException(status_code=404, detail=f"Promotion with id {promotion_id} was not found.")
    return promotion
