from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.engine import Connection

from app.database import competitors, promotions, service_plans, devices


def get_promotions(
    conn: Connection,
    competitor_id: Optional[int] = None,
    target_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    active_only: bool = False,
) -> List[Dict[str, Any]]:
    query = (
        select(
            promotions.c.promotion_id,
            promotions.c.competitor_id,
            competitors.c.name.label("competitor_name"),
            promotions.c.promotion_title,
            promotions.c.promotion_type,
            promotions.c.description,
            promotions.c.target_type,
            promotions.c.target_plan_id,
            promotions.c.target_device_id,
            promotions.c.start_date,
            promotions.c.end_date,
            promotions.c.captured_at,
        )
        .select_from(promotions)
        .join(competitors, competitors.c.competitor_id == promotions.c.competitor_id)
        .outerjoin(service_plans, service_plans.c.plan_id == promotions.c.target_plan_id)
        .outerjoin(devices, devices.c.device_id == promotions.c.target_device_id)
    )

    if competitor_id is not None:
        query = query.where(promotions.c.competitor_id == competitor_id)
    if target_type is not None:
        query = query.where(promotions.c.target_type == target_type)
    if start_date is not None:
        query = query.where(promotions.c.start_date >= start_date)
    if end_date is not None:
        query = query.where(promotions.c.end_date <= end_date)
    if active_only:
        today = datetime.utcnow().date()
        query = query.where((promotions.c.start_date.is_(None)) | (promotions.c.start_date <= today))
        query = query.where((promotions.c.end_date.is_(None)) | (promotions.c.end_date >= today))

    query = query.order_by(promotions.c.start_date.desc().nullslast(), promotions.c.captured_at.desc())
    return [dict(row) for row in conn.execute(query).mappings()]


def get_promotion_by_id(conn: Connection, promotion_id: int) -> Optional[dict]:
    query = (
        select(
            promotions.c.promotion_id,
            promotions.c.competitor_id,
            competitors.c.name.label("competitor_name"),
            promotions.c.promotion_title,
            promotions.c.promotion_type,
            promotions.c.description,
            promotions.c.target_type,
            promotions.c.target_plan_id,
            promotions.c.target_device_id,
            promotions.c.start_date,
            promotions.c.end_date,
            promotions.c.captured_at,
        )
        .select_from(promotions)
        .join(competitors, competitors.c.competitor_id == promotions.c.competitor_id)
        .where(promotions.c.promotion_id == promotion_id)
    )
    row = conn.execute(query).mappings().first()
    if row is None:
        return None
    return dict(row)
