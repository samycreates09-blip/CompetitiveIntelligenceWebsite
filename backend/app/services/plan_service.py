from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import select, true
from sqlalchemy.engine import Connection

from app.database import competitors, plan_price_history, service_plans


def get_current_plan_prices(
    conn: Connection,
    competitor_id: Optional[int] = None,
    plan_category: Optional[str] = None,
    plan_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    latest = (
        select(
            plan_price_history.c.plan_id,
            plan_price_history.c.price_usd,
            plan_price_history.c.promotional_price_usd,
            plan_price_history.c.promo_terms,
            plan_price_history.c.effective_date,
            plan_price_history.c.captured_at,
            plan_price_history.c.plan_price_history_id,
        )
        .where(plan_price_history.c.plan_id == service_plans.c.plan_id)
        .order_by(
            plan_price_history.c.captured_at.desc(),
            plan_price_history.c.plan_price_history_id.desc(),
        )
        .limit(1)
        .correlate(service_plans)
        .subquery()
        .lateral()
    )

    query = (
        select(
            service_plans.c.plan_id,
            competitors.c.competitor_id,
            competitors.c.name.label("competitor_name"),
            service_plans.c.plan_name,
            service_plans.c.plan_category,
            service_plans.c.plan_type,
            latest.c.price_usd,
            latest.c.promotional_price_usd,
            latest.c.promo_terms,
            latest.c.effective_date,
            latest.c.captured_at,
        )
        .select_from(service_plans)
        .join(competitors, competitors.c.competitor_id == service_plans.c.competitor_id)
        .join(latest, true())
    )

    if competitor_id is not None:
        query = query.where(competitors.c.competitor_id == competitor_id)
    if plan_category is not None:
        query = query.where(service_plans.c.plan_category == plan_category)
    if plan_type is not None:
        query = query.where(service_plans.c.plan_type == plan_type)

    query = query.order_by(competitors.c.name.asc(), service_plans.c.plan_name.asc())
    return [dict(row) for row in conn.execute(query).mappings()]


def get_plan_by_id(conn: Connection, plan_id: int) -> Optional[dict]:
    query = select(service_plans).where(service_plans.c.plan_id == plan_id)
    row = conn.execute(query).mappings().first()
    if row is None:
        return None
    return dict(row)


def get_plan_history(
    conn: Connection,
    plan_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    order: str = "asc",
) -> List[Dict[str, Any]]:
    query = (
        select(
            service_plans.c.plan_id,
            competitors.c.competitor_id,
            competitors.c.name.label("competitor_name"),
            service_plans.c.plan_name,
            plan_price_history.c.effective_date,
            plan_price_history.c.price_usd,
            plan_price_history.c.promotional_price_usd,
            plan_price_history.c.promo_terms,
            plan_price_history.c.captured_at,
            plan_price_history.c.source_snapshot_date,
        )
        .select_from(plan_price_history)
        .join(service_plans, service_plans.c.plan_id == plan_price_history.c.plan_id)
        .join(competitors, competitors.c.competitor_id == service_plans.c.competitor_id)
        .where(plan_price_history.c.plan_id == plan_id)
    )

    if from_date is not None:
        query = query.where(plan_price_history.c.source_snapshot_date >= from_date)
    if to_date is not None:
        query = query.where(plan_price_history.c.source_snapshot_date <= to_date)

    if order.lower() == "desc":
        query = query.order_by(plan_price_history.c.source_snapshot_date.desc(), plan_price_history.c.captured_at.desc())
    else:
        query = query.order_by(plan_price_history.c.source_snapshot_date.asc(), plan_price_history.c.captured_at.asc())

    return [dict(row) for row in conn.execute(query).mappings()]
