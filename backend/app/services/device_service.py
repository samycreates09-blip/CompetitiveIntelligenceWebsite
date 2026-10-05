from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.engine import Connection

from app.database import competitors, device_price_history, devices


def get_devices(conn: Connection, competitor_id: Optional[int] = None, manufacturer: Optional[str] = None, device_type: Optional[str] = None) -> List[Dict[str, Any]]:
    query = (
        select(
            devices.c.device_id,
            devices.c.competitor_id,
            competitors.c.name.label("competitor_name"),
            devices.c.manufacturer,
            devices.c.model_name,
            devices.c.device_type,
            devices.c.storage_variant,
            devices.c.color,
            devices.c.is_active,
        )
        .select_from(devices)
        .join(competitors, competitors.c.competitor_id == devices.c.competitor_id)
    )

    if competitor_id is not None:
        query = query.where(devices.c.competitor_id == competitor_id)
    if manufacturer is not None:
        query = query.where(devices.c.manufacturer == manufacturer)
    if device_type is not None:
        query = query.where(devices.c.device_type == device_type)

    query = query.order_by(competitors.c.name.asc(), devices.c.model_name.asc())
    return [dict(row) for row in conn.execute(query).mappings()]


def get_device_by_id(conn: Connection, device_id: int) -> Optional[dict]:
    query = (
        select(
            devices.c.device_id,
            devices.c.competitor_id,
            competitors.c.name.label("competitor_name"),
            devices.c.manufacturer,
            devices.c.model_name,
            devices.c.device_type,
            devices.c.storage_variant,
            devices.c.color,
            devices.c.is_active,
        )
        .select_from(devices)
        .join(competitors, competitors.c.competitor_id == devices.c.competitor_id)
        .where(devices.c.device_id == device_id)
    )
    row = conn.execute(query).mappings().first()
    if row is None:
        return None
    return dict(row)


def get_device_history(
    conn: Connection,
    device_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    order: str = "asc",
) -> List[Dict[str, Any]]:
    query = (
        select(
            devices.c.device_id,
            devices.c.competitor_id,
            competitors.c.name.label("competitor_name"),
            devices.c.manufacturer,
            devices.c.model_name,
            device_price_history.c.effective_date,
            device_price_history.c.retail_price_usd,
            device_price_history.c.promo_price_usd,
            device_price_history.c.promotion_terms,
            device_price_history.c.financing_terms,
            device_price_history.c.captured_at,
            device_price_history.c.source_snapshot_date,
        )
        .select_from(device_price_history)
        .join(devices, devices.c.device_id == device_price_history.c.device_id)
        .join(competitors, competitors.c.competitor_id == devices.c.competitor_id)
        .where(device_price_history.c.device_id == device_id)
    )

    if from_date is not None:
        query = query.where(device_price_history.c.source_snapshot_date >= from_date)
    if to_date is not None:
        query = query.where(device_price_history.c.source_snapshot_date <= to_date)

    if order.lower() == "desc":
        query = query.order_by(device_price_history.c.source_snapshot_date.desc(), device_price_history.c.captured_at.desc())
    else:
        query = query.order_by(device_price_history.c.source_snapshot_date.asc(), device_price_history.c.captured_at.asc())

    return [dict(row) for row in conn.execute(query).mappings()]
