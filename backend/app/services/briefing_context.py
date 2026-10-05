from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from sqlalchemy.engine import Connection

from app.services.change_service import get_changes
from app.services.device_service import get_device_history, get_devices
from app.services.plan_service import get_current_plan_prices, get_plan_history
from app.services.promotion_service import get_promotions


def _money(value: Any) -> str:
    return "not recorded" if value is None else "${:,.2f}".format(float(value))


def assemble_briefing_context(conn: Connection) -> Dict[str, Any]:
    """Build deterministic, compact facts by reusing the existing read services."""
    today = date.today()
    plans = get_current_plan_prices(conn)
    plan_context: List[Dict[str, Any]] = []
    facts: List[Dict[str, str]] = []

    for plan in plans:
        history = get_plan_history(conn, plan_id=plan["plan_id"], order="desc")[:3]
        history = list(reversed(history))
        current_fact_id = "F{}".format(len(facts) + 1)
        current_text = (
            "{} {}: current listed price {}, promotional price {}, effective {}. Terms: {}."
        ).format(
            plan["competitor_name"], plan["plan_name"], _money(plan["price_usd"]),
            _money(plan["promotional_price_usd"]), plan["effective_date"] or "not recorded",
            plan["promo_terms"] or "none recorded",
        )
        facts.append({"id": current_fact_id, "category": "current_plan", "text": current_text})
        history_rows = []
        if len(history) > 1:
            hist_fact_id = "F{}".format(len(facts) + 1)
            history_text = "{} {} price history: {}.".format(
                plan["competitor_name"], plan["plan_name"],
                "; ".join("{} listed {}, promo {}".format(
                    row["source_snapshot_date"], _money(row["price_usd"]), _money(row["promotional_price_usd"])
                ) for row in history),
            )
            facts.append({"id": hist_fact_id, "category": "plan_history", "text": history_text})
            history_rows = history
        plan_context.append({"current": plan, "recent_history": history_rows})

    devices = get_devices(conn)
    device_context: List[Dict[str, Any]] = []
    for device in devices:
        history = get_device_history(conn, device_id=device["device_id"], order="desc")
        if not history:
            continue
        latest = history[0]
        fact_id = "F{}".format(len(facts) + 1)
        facts.append({
            "id": fact_id,
            "category": "current_device_price",
            "text": "{} {} {} latest observed on {}: retail {}, promotional {}. Terms: {}.".format(
                device["competitor_name"], device["manufacturer"], device["model_name"],
                latest["source_snapshot_date"], _money(latest["retail_price_usd"]),
                _money(latest["promo_price_usd"]), latest["promotion_terms"] or "none recorded",
            ),
        })
        device_context.append({"device": device, "latest_price": latest})

    active_promotions = get_promotions(conn, active_only=True)
    promotion_context = []
    for promotion in active_promotions:
        fact_id = "F{}".format(len(facts) + 1)
        facts.append({
            "id": fact_id,
            "category": "active_promotion",
            "text": "{} promotion '{}': {} target; dates {} through {}. {}".format(
                promotion["competitor_name"], promotion["promotion_title"], promotion["target_type"],
                promotion["start_date"] or "unspecified", promotion["end_date"] or "unspecified",
                promotion["description"],
            ),
        })
        promotion_context.append(promotion)

    changes = get_changes(conn)[:8]
    change_context = []
    for change in changes:
        fact_id = "F{}".format(len(facts) + 1)
        facts.append({
            "id": fact_id,
            "category": "synthetic_seeded_change",
            "text": "SYNTHETIC SEEDED RECORD (not automatically detected): {}; {}; {}; effective {}; {} -> {}. {}".format(
                change["competitor_name"], change["change_type"], change["entity_type"],
                change["effective_date"], change["previous_value"] or "not recorded",
                change["new_value"] or "not recorded", change["summary_text"],
            ),
        })
        change_context.append({"record": change, "fact_id": fact_id})

    competitors = sorted({plan["competitor_name"] for plan in plans})
    return {
        "data_notice": "Structured local seeded demo data. Change records are synthetic and are not automatically detected.",
        "as_of_date": today.isoformat(),
        "plans": plan_context,
        "latest_device_prices": device_context,
        "active_promotions": promotion_context,
        "synthetic_seeded_change_records": change_context,
        "facts": facts,
        "data_scope": {
            "competitors": competitors,
            "plan_count": len(plans),
            "device_count": len(devices),
            "device_price_history_count": len(device_context),
            "active_promotion_count": len(promotion_context),
            "synthetic_change_record_count": len(change_context),
            "synthetic_change_records": True,
            "as_of_date": today,
        },
    }