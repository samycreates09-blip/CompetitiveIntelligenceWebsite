from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.database import engine

router = APIRouter()


@router.get("/health")
def health() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "service": "boost-competitive-intelligence-api", "database": "connected"}
    except Exception:
        return {"status": "error", "service": "boost-competitive-intelligence-api", "database": "disconnected"}
