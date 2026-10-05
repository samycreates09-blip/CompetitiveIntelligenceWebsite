from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List

from sqlalchemy.engine import Connection

from app.config import settings
from app.services.change_service import get_changes
from app.services.competitor_service import get_competitors
from app.services.device_service import get_device_history, get_devices
from app.services.embedding_provider import EmbeddingProviderError
from app.services.plan_service import get_current_plan_prices, get_plan_history
from app.services.promotion_service import get_promotions
from app.services.retrieval_service import embed_query, search_chunks

ROUTE_CATEGORIES = ("plans", "plan_history", "devices", "device_history", "promotions", "changes", "documents")


def route_question(message: str, competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Small deterministic intent/entity router; it never delegates routing to Gemini."""
    text = message.lower()
    competitor_ids = [
        int(competitor["competitor_id"])
        for competitor in competitors
        if competitor["name"].lower() in text or competitor["short_name"].lower() in text
    ]
    categories = set()
    comparison = any(term in text for term in ("compare", "comparison", "versus", " vs ", "which competitor"))
    mentions_plan = any(term in text for term in ("plan", "plans", "essentials", "unlimited", "monthly", "price", "pricing", "cost"))
    explicit_plan = any(term in text for term in ("plan", "plans", "essentials", "unlimited", "monthly"))
    mentions_history = any(term in text for term in ("history", "historical", "changed", "change", "increased", "increase", "reduced", "decreased", "before", "recently", "recent"))
    mentions_device = any(term in text for term in ("device", "phone", "iphone", "galaxy", "pixel", "samsung", "apple"))
    mentions_promotion = any(term in text for term in ("promotion", "promotions", "promo", "offer", "discount", "trade-in", "trade in", "bill credit", "bundle"))
    mentions_change = any(term in text for term in ("what changed", "change log", "changes", "recently", "recent", "increased", "increase", "decreased", "reduced"))
    mentions_unstructured = any(term in text for term in (
        "eligib", "requir", "condition", "qualify", "qualifies", "fine print", "terms",
        "restriction", "exclusion",
    ))

    if comparison or (mentions_plan and (not mentions_device or explicit_plan)):
        categories.add("plans")
    if mentions_history and (mentions_plan or comparison):
        categories.add("plan_history")
        categories.add("changes")
    if mentions_device:
        categories.add("devices")
        if mentions_history:
            categories.add("device_history")
    if mentions_promotion:
        categories.add("promotions")
    if mentions_change:
        categories.add("changes")
    if mentions_unstructured:
        categories.add("documents")
    unsupported_topic = any(term in text for term in ("satellite", "network coverage", "5g speed", "coverage map", "roaming rate"))
    if unsupported_topic:
        categories.clear()
    return {
        "categories": [category for category in ROUTE_CATEGORIES if category in categories],
        "include_device_history": "device_history" in categories,
        "competitor_ids": sorted(set(competitor_ids)),
        "comparison": comparison,
    }


def _money(value: Any) -> str:
    return "not recorded" if value is None else "${:,.2f}".format(float(value))


def _entity_match(question: str, name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", question.lower())
    words = [word for word in re.sub(r"[^a-z0-9]+", " ", name.lower()).split() if len(word) > 2]
    return bool(words) and all(word in normalized for word in words)


def assemble_chat_context(conn: Connection, message: str) -> Dict[str, Any]:
    competitors = get_competitors(conn, is_active=True)
    route = route_question(message, competitors)
    selected_competitors = route["competitor_ids"]
    sources: List[Dict[str, Any]] = []
    records: Dict[str, List[Dict[str, Any]]] = {category: [] for category in ROUTE_CATEGORIES}

    if not route["categories"]:
        return {
            "question": message,
            "data_notice": "The requested topic is not represented by tracked structured data.",
            "as_of_date": date.today().isoformat(),
            "route": route,
            "records": records,
            "sources": [],
            "sufficient": False,
            "data_scope": {
                "requested_categories": [],
                "available_categories": [],
                "competitors": [],
                "source_count": 0,
                "synthetic_change_records_included": False,
            },
        }

    if "plans" in route["categories"] or "plan_history" in route["categories"]:
        all_plans = get_current_plan_prices(conn)
        plans = [plan for plan in all_plans if not selected_competitors or plan["competitor_id"] in selected_competitors]
        named_plans = [plan for plan in plans if _entity_match(message, plan["plan_name"])]
        if named_plans:
            plans = named_plans
        for plan in plans:
            source_id = "PLAN-{}".format(plan["plan_id"])
            records["plans"].append(plan)
            sources.append({
                "source_id": source_id,
                "category": "current_plan",
                "summary": "{} — {} current listed {}, promo {} (effective {}).".format(
                    plan["competitor_name"], plan["plan_name"], _money(plan["price_usd"]),
                    _money(plan["promotional_price_usd"]), plan["effective_date"] or "date not recorded",
                ),
                "record_origin": "structured_observation",
            })
            if "plan_history" in route["categories"]:
                history = get_plan_history(conn, plan_id=plan["plan_id"], order="asc")
                records["plan_history"].extend(history)
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

    if "devices" in route["categories"]:
        devices = get_devices(conn)
        if selected_competitors:
            devices = [device for device in devices if device["competitor_id"] in selected_competitors]
        matching_devices = [
            device for device in devices
            if _entity_match(message, device["model_name"])
            or _entity_match(message, device["manufacturer"])
            or str(device["device_id"]) in message
        ]
        if matching_devices:
            devices = matching_devices
        for device in devices:
            history = get_device_history(conn, device_id=device["device_id"], order="asc")
            if route["include_device_history"]:
                relevant_history = history
            else:
                relevant_history = history[-1:]
            records["devices"].append({"device": device, "price_history": relevant_history})
            if route["include_device_history"]:
                records["device_history"].extend(relevant_history)
            for index, entry in enumerate(relevant_history, 1):
                source_id = "DEVICE-{}-{}".format(device["device_id"], index)
                sources.append({
                    "source_id": source_id,
                    "category": "device_price",
                    "summary": "{} {} latest observed {}: retail {}, promo {}. {}".format(
                        device["competitor_name"], device["model_name"], entry["source_snapshot_date"],
                        _money(entry["retail_price_usd"]), _money(entry["promo_price_usd"]),
                        entry["promotion_terms"] or "No promotion terms recorded.",
                    ),
                    "record_origin": "structured_observation",
                })

    if "promotions" in route["categories"]:
        active_only = not any(word in message.lower() for word in ("ended", "expired", "history", "historical"))
        promotions = get_promotions(conn, active_only=active_only)
        if selected_competitors:
            promotions = [promotion for promotion in promotions if promotion["competitor_id"] in selected_competitors]
        for promotion in promotions:
            records["promotions"].append(promotion)
            sources.append({
                "source_id": "PROMOTION-{}".format(promotion["promotion_id"]),
                "category": "promotion",
                "summary": "{}: {} ({}), {} through {}. {}".format(
                    promotion["competitor_name"], promotion["promotion_title"], promotion["target_type"],
                    promotion["start_date"] or "start unspecified", promotion["end_date"] or "end unspecified",
                    promotion["description"],
                ),
                "record_origin": "structured_observation",
            })

    if "changes" in route["categories"]:
        changes = get_changes(conn)
        if selected_competitors:
            changes = [change for change in changes if change["competitor_id"] in selected_competitors]
        changes = changes[:10]
        for change in changes:
            records["changes"].append(change)
            origin = change.get("record_origin", "synthetic_seeded")
            sources.append({
                "source_id": "CHANGE-{}".format(change["change_id"]),
                "category": "competitor_change",
                "summary": "{} [{}]: {} ({}): {} -> {}. {}".format(
                    change["competitor_name"], origin, change["change_type"], change["effective_date"],
                    change["previous_value"] or "not recorded", change["new_value"] or "not recorded",
                    change["summary_text"],
                ),
                "record_origin": origin,
            })

    if "documents" in route["categories"]:
        chunks: List[Dict[str, Any]] = []
        if settings.gemini_api_key:
            try:
                query_vector = embed_query(message, settings.gemini_api_key, settings.gemini_embedding_model)
                chunks = search_chunks(conn, query_vector, competitor_ids=selected_competitors or None)
            except EmbeddingProviderError:
                chunks = []
        for chunk in chunks:
            records["documents"].append(chunk)
            sources.append({
                "source_id": "DOC-{}-{}".format(chunk["document_id"], chunk["chunk_index"]),
                "category": "document_chunk",
                "summary": "{} — {} ({}, {}): {}".format(
                    chunk["competitor_name"], chunk["title"], chunk["document_type"],
                    chunk["captured_date"], chunk["chunk_text"],
                ),
                "record_origin": "synthetic_document",
            })

    usable_categories = [category for category in route["categories"] if records.get(category)]
    sufficient = bool(sources)
    competitor_names = {plan["competitor_name"] for plan in records["plans"]}
    competitor_names.update(plan["competitor_name"] for plan in records["plan_history"])
    competitor_names.update(device["device"]["competitor_name"] for device in records["devices"])
    for category in ("promotions", "changes", "documents"):
        competitor_names.update(record["competitor_name"] for record in records[category])
    return {
        "question": message,
        "data_notice": "Structured facts come only from tracked PostgreSQL observations. Seeded change records and retrieved document excerpts are synthetic demo data, not live or automatically detected content.",
        "as_of_date": date.today().isoformat(),
        "route": route,
        "records": records,
        "sources": sources,
        "sufficient": sufficient,
        "data_scope": {
            "requested_categories": route["categories"],
            "available_categories": usable_categories,
            "competitors": sorted(competitor_names),
            "source_count": len(sources),
            "synthetic_change_records_included": any(source.get("record_origin") == "synthetic_seeded" for source in sources),
            "document_sources_included": any(source.get("category") == "document_chunk" for source in sources),
        },
    }
