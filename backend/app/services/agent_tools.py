from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional

from sqlalchemy.engine import Connection

from app.config import settings
from app.services import change_service, competitor_service, device_service, plan_service, promotion_service
from app.services.embedding_provider import EmbeddingProviderError
from app.services.retrieval_service import embed_query, search_chunks

TOOL_DECLARATIONS = [
    {
        "name": "get_current_plan_prices",
        "description": (
            "Get currently listed monthly prices for tracked wireless plans, optionally filtered by "
            "competitor and/or plan name. Use for questions about current/latest plan pricing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "competitor": {"type": "string", "description": "Competitor name, e.g. 'T-Mobile', 'Verizon', 'Boost Mobile'. Omit to search all competitors."},
                "plan_name": {"type": "string", "description": "Plan name or partial name, e.g. 'Essentials'. Omit to include all plans."},
            },
        },
    },
    {
        "name": "get_plan_price_history",
        "description": (
            "Get the historical sequence of observed prices for a tracked plan, showing how its price "
            "has changed over time. Use for questions about price changes or price history for a plan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "competitor": {"type": "string", "description": "Competitor name."},
                "plan_name": {"type": "string", "description": "Plan name or partial name."},
            },
        },
    },
    {
        "name": "get_device_price_history",
        "description": (
            "Get the historical sequence of observed retail/promo prices for a tracked device. Use for "
            "questions about device price changes or device price history."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "competitor": {"type": "string", "description": "Competitor name."},
                "model_name": {"type": "string", "description": "Device model name or partial name, e.g. 'iPhone 15 Pro'."},
            },
        },
    },
    {
        "name": "get_promotions",
        "description": (
            "Get tracked promotions (headline offer, target, active window), optionally filtered by "
            "competitor. Use for questions about current or past promotions/offers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "competitor": {"type": "string", "description": "Competitor name."},
                "active_only": {"type": "boolean", "description": "If true (default), only return promotions currently active. Set false to include expired/historical promotions."},
            },
        },
    },
    {
        "name": "get_recent_changes",
        "description": (
            "Get recently recorded competitive changes (price changes, new/ended promotions), optionally "
            "filtered by competitor. Use for 'what changed' / 'what's new' questions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "competitor": {"type": "string", "description": "Competitor name."},
                "limit": {"type": "integer", "description": "Maximum number of changes to return (default 10)."},
            },
        },
    },
    {
        "name": "search_competitor_documents",
        "description": (
            "Semantically search unstructured competitor documents (promotion fine print, eligibility "
            "conditions, plan descriptions) for passages relevant to a query. Use for questions about "
            "eligibility, conditions, terms, or restrictions that structured records don't fully capture."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for, e.g. 'trade-in eligibility requirements'."},
                "competitor": {"type": "string", "description": "Competitor name to restrict the search to. Omit to search all competitors' documents."},
            },
            "required": ["query"],
        },
    },
]


def _name_matches(query: str, candidate: str) -> bool:
    q = query.strip().lower()
    c = candidate.strip().lower()
    return bool(q) and bool(c) and (q in c or c in q)


def _word_match(query: str, candidate: str) -> bool:
    """True when every significant word of `query` appears in `candidate` —
    e.g. query "iPhone 15 Pro" matches candidate "iPhone 15 Pro" but not the
    separate "iPhone 15" device, because "pro" is absent from the latter."""
    normalized_candidate = re.sub(r"[^a-z0-9]+", " ", candidate.lower())
    words = [word for word in re.sub(r"[^a-z0-9]+", " ", query.lower()).split() if len(word) > 2]
    return bool(words) and all(word in normalized_candidate for word in words)


def _money(value: Any) -> str:
    return "not recorded" if value is None else "${:,.2f}".format(float(value))


def get_current_plan_prices(conn: Connection, competitor: Optional[str] = None, plan_name: Optional[str] = None) -> Dict[str, Any]:
    plans = plan_service.get_current_plan_prices(conn)
    if competitor:
        plans = [p for p in plans if _name_matches(competitor, p["competitor_name"])]
    if plan_name:
        matched = [p for p in plans if _word_match(plan_name, p["plan_name"])]
        if matched:
            plans = matched
    sources = [{
        "source_id": "PLAN-{}".format(p["plan_id"]),
        "category": "current_plan",
        "summary": "{} — {} current listed {}, promo {} (effective {}).".format(
            p["competitor_name"], p["plan_name"], _money(p["price_usd"]),
            _money(p["promotional_price_usd"]), p["effective_date"] or "date not recorded",
        ),
        "record_origin": "structured_observation",
    } for p in plans]
    return {"sources": sources, "count": len(sources)}


def get_plan_price_history(conn: Connection, competitor: Optional[str] = None, plan_name: Optional[str] = None) -> Dict[str, Any]:
    plans = plan_service.get_current_plan_prices(conn)
    if competitor:
        plans = [p for p in plans if _name_matches(competitor, p["competitor_name"])]
    if plan_name:
        matched = [p for p in plans if _word_match(plan_name, p["plan_name"])]
        if matched:
            plans = matched
    sources = []
    for plan in plans:
        history = plan_service.get_plan_history(conn, plan_id=plan["plan_id"], order="asc")
        for index, entry in enumerate(history, 1):
            sources.append({
                "source_id": "PLAN-HISTORY-{}-{}".format(plan["plan_id"], index),
                "category": "plan_history",
                "summary": "{} {}: {} price {}, promo {}.".format(
                    entry["source_snapshot_date"], entry["plan_name"], entry["competitor_name"],
                    _money(entry["price_usd"]), _money(entry["promotional_price_usd"]),
                ),
                "record_origin": "structured_observation",
            })
    return {"sources": sources, "count": len(sources)}


def get_device_price_history(conn: Connection, competitor: Optional[str] = None, model_name: Optional[str] = None) -> Dict[str, Any]:
    devices = device_service.get_devices(conn)
    if competitor:
        devices = [d for d in devices if _name_matches(competitor, d["competitor_name"])]
    if model_name:
        matched = [d for d in devices if _word_match(model_name, d["model_name"]) or _word_match(model_name, d["manufacturer"])]
        if matched:
            devices = matched
    sources = []
    for device in devices:
        history = device_service.get_device_history(conn, device_id=device["device_id"], order="asc")
        for index, entry in enumerate(history, 1):
            sources.append({
                "source_id": "DEVICE-{}-{}".format(device["device_id"], index),
                "category": "device_price",
                "summary": "{} {} {}: retail {}, promo {}. {}".format(
                    device["competitor_name"], device["model_name"], entry["source_snapshot_date"],
                    _money(entry["retail_price_usd"]), _money(entry["promo_price_usd"]),
                    entry["promotion_terms"] or "No promotion terms recorded.",
                ),
                "record_origin": "structured_observation",
            })
    return {"sources": sources, "count": len(sources)}


def get_promotions(conn: Connection, competitor: Optional[str] = None, active_only: bool = True) -> Dict[str, Any]:
    promotions = promotion_service.get_promotions(conn, active_only=active_only)
    if competitor:
        promotions = [p for p in promotions if _name_matches(competitor, p["competitor_name"])]
    sources = [{
        "source_id": "PROMOTION-{}".format(p["promotion_id"]),
        "category": "promotion",
        "summary": "{}: {} ({}), {} through {}. {}".format(
            p["competitor_name"], p["promotion_title"], p["target_type"],
            p["start_date"] or "start unspecified", p["end_date"] or "end unspecified", p["description"],
        ),
        "record_origin": "structured_observation",
    } for p in promotions]
    return {"sources": sources, "count": len(sources)}


def get_recent_changes(conn: Connection, competitor: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    changes = change_service.get_changes(conn)
    if competitor:
        changes = [c for c in changes if _name_matches(competitor, c["competitor_name"])]
    bounded_limit = max(1, min(int(limit or 10), 25))
    changes = changes[:bounded_limit]
    sources = [{
        "source_id": "CHANGE-{}".format(c["change_id"]),
        "category": "competitor_change",
        "summary": "{} [{}]: {} ({}): {} -> {}. {}".format(
            c["competitor_name"], c.get("record_origin", "synthetic_seeded"), c["change_type"], c["effective_date"],
            c["previous_value"] or "not recorded", c["new_value"] or "not recorded", c["summary_text"],
        ),
        "record_origin": c.get("record_origin", "synthetic_seeded"),
    } for c in changes]
    return {"sources": sources, "count": len(sources)}


def search_competitor_documents(conn: Connection, query: str, competitor: Optional[str] = None) -> Dict[str, Any]:
    if not settings.gemini_api_key:
        return {"sources": [], "count": 0, "error": "Document search is not configured."}
    competitor_ids = None
    if competitor:
        competitors = competitor_service.get_competitors(conn, is_active=True)
        matched_ids = [
            c["competitor_id"] for c in competitors
            if _name_matches(competitor, c["name"]) or _name_matches(competitor, c["short_name"])
        ]
        competitor_ids = matched_ids or None
    try:
        vector = embed_query(query, settings.gemini_api_key, settings.gemini_embedding_model)
        chunks = search_chunks(conn, vector, competitor_ids=competitor_ids)
    except EmbeddingProviderError:
        return {"sources": [], "count": 0, "error": "Document search is temporarily unavailable."}
    sources = [{
        "source_id": "DOC-{}-{}".format(c["document_id"], c["chunk_index"]),
        "category": "document_chunk",
        "summary": "{} — {} ({}, {}): {}".format(
            c["competitor_name"], c["title"], c["document_type"], c["captured_date"], c["chunk_text"],
        ),
        "record_origin": "synthetic_document",
    } for c in chunks]
    return {"sources": sources, "count": len(sources)}


TOOL_DISPATCH: Dict[str, Callable[..., Dict[str, Any]]] = {
    "get_current_plan_prices": get_current_plan_prices,
    "get_plan_price_history": get_plan_price_history,
    "get_device_price_history": get_device_price_history,
    "get_promotions": get_promotions,
    "get_recent_changes": get_recent_changes,
    "search_competitor_documents": search_competitor_documents,
}
