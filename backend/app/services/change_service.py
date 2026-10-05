from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.engine import Connection

from app.database import competitor_changes, competitors


def get_changes(
    conn: Connection,
    competitor_id: Optional[int] = None,
    change_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    severity: Optional[str] = None,
    record_origin: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    query = (
        select(
            competitor_changes.c.change_id,
            competitor_changes.c.competitor_id,
            competitors.c.name.label("competitor_name"),
            competitor_changes.c.change_type,
            competitor_changes.c.entity_type,
            competitor_changes.c.entity_id,
            competitor_changes.c.previous_value,
            competitor_changes.c.new_value,
            competitor_changes.c.effective_date,
            competitor_changes.c.severity,
            competitor_changes.c.summary_text,
            competitor_changes.c.source_snapshot_from,
            competitor_changes.c.source_snapshot_to,
            competitor_changes.c.record_origin,
            competitor_changes.c.change_detected_at,
        )
        .select_from(competitor_changes)
        .join(competitors, competitors.c.competitor_id == competitor_changes.c.competitor_id)
    )

    if competitor_id is not None:
        query = query.where(competitor_changes.c.competitor_id == competitor_id)
    if change_type is not None:
        query = query.where(competitor_changes.c.change_type == change_type)
    if entity_type is not None:
        query = query.where(competitor_changes.c.entity_type == entity_type)
    if severity is not None:
        query = query.where(competitor_changes.c.severity == severity)
    if record_origin is not None:
        query = query.where(competitor_changes.c.record_origin == record_origin)
    if from_date is not None:
        query = query.where(competitor_changes.c.effective_date >= from_date)
    if to_date is not None:
        query = query.where(competitor_changes.c.effective_date <= to_date)

    query = query.order_by(competitor_changes.c.change_detected_at.desc())
    return [dict(row) for row in conn.execute(query).mappings()]


def get_change_by_id(conn: Connection, change_id: int) -> Optional[dict]:
    query = (
        select(
            competitor_changes.c.change_id,
            competitor_changes.c.competitor_id,
            competitors.c.name.label("competitor_name"),
            competitor_changes.c.change_type,
            competitor_changes.c.entity_type,
            competitor_changes.c.entity_id,
            competitor_changes.c.previous_value,
            competitor_changes.c.new_value,
            competitor_changes.c.effective_date,
            competitor_changes.c.severity,
            competitor_changes.c.summary_text,
            competitor_changes.c.source_snapshot_from,
            competitor_changes.c.source_snapshot_to,
            competitor_changes.c.record_origin,
            competitor_changes.c.change_detected_at,
        )
        .select_from(competitor_changes)
        .join(competitors, competitors.c.competitor_id == competitor_changes.c.competitor_id)
        .where(competitor_changes.c.change_id == change_id)
    )
    row = conn.execute(query).mappings().first()
    if row is None:
        return None
    return dict(row)
