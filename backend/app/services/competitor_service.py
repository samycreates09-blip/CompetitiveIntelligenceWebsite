from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.engine import Connection

from app.database import competitors


def get_competitors(conn: Connection, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
    query = select(competitors).order_by(competitors.c.name.asc())
    if is_active is not None:
        query = query.where(competitors.c.is_active == is_active)
    return [dict(row) for row in conn.execute(query).mappings()]


def get_competitor_by_id(conn: Connection, competitor_id: int) -> Optional[dict]:
    query = select(competitors).where(competitors.c.competitor_id == competitor_id)
    row = conn.execute(query).mappings().first()
    if row is None:
        return None
    return dict(row)
