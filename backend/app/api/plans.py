from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.engine import Connection

from app.deps import get_db
from app.services.plan_service import get_current_plan_prices, get_plan_history

router = APIRouter(prefix="/api/v1")


@router.get("/plans/current")
def list_current_plan_prices(
    competitor_id: Optional[int] = Query(default=None),
    plan_category: Optional[str] = Query(default=None),
    plan_type: Optional[str] = Query(default=None),
    conn: Connection = Depends(get_db),
):
    if competitor_id is not None and competitor_id <= 0:
        raise HTTPException(status_code=400, detail="competitor_id must be greater than 0")
    return get_current_plan_prices(
        conn,
        competitor_id=competitor_id,
        plan_category=plan_category,
        plan_type=plan_type,
    )


@router.get("/plans/{plan_id}/history")
def get_plan_history_by_id(
    plan_id: int,
    from_date: Optional[date] = Query(default=None),
    to_date: Optional[date] = Query(default=None),
    order: str = Query(default="asc"),
    conn: Connection = Depends(get_db),
):
    if plan_id <= 0:
        raise HTTPException(status_code=400, detail="plan_id must be greater than 0")
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date cannot be later than to_date")
    if order.lower() not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="order must be either asc or desc")

    query_result = get_plan_history(conn, plan_id=plan_id, from_date=from_date, to_date=to_date, order=order)
    if not query_result:
        raise HTTPException(status_code=404, detail=f"Plan history for plan_id {plan_id} was not found.")
    return query_result
