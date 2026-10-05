from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional, Protocol

from sqlalchemy import insert, select
from sqlalchemy.engine import Connection

from app.config import settings
from app.database import (
    competitor_changes,
    competitors,
    device_price_history,
    devices,
    plan_price_history,
    promotions,
    service_plans,
)
from app.models.schemas import DevicePriceObservationRequest, PlanPriceObservationRequest, PromotionObservationRequest

logger = logging.getLogger(__name__)
IMPORTANT_CHANGE_TYPES = {"plan_price", "promotion", "device_price", "device_promotion", "promotion_new", "promotion_ended", "promotion_terms_changed"}


class EmailProvider(Protocol):
    def send(self, subject: str, body: str, recipient: Optional[str] = None) -> Dict[str, str]:
        ...


def detect_observation_change(entity_type: str, previous: Optional[Dict[str, Any]], current: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Pure, deterministic field comparison shared by observation ingestion paths."""
    if not previous:
        return None
    fields = {
        "plan": (
            ("price_usd", "plan_price"),
            ("promotional_price_usd", "promotion"),
            ("promo_terms", "promotion"),
        ),
        "device": (
            ("retail_price_usd", "device_price"),
            ("promo_price_usd", "device_promotion"),
            ("promotion_terms", "device_promotion"),
            ("financing_terms", "device_promotion"),
        ),
    }.get(entity_type, ())
    changed = [(field, change_type) for field, change_type in fields if previous.get(field) != current.get(field)]
    if not changed:
        return None
    change_type = "plan_price" if entity_type == "plan" and any(field == "price_usd" for field, _ in changed) else changed[0][1]
    return {"change_type": change_type, "changed_fields": [field for field, _ in changed]}


def should_alert(change_type: str) -> bool:
    return change_type in IMPORTANT_CHANGE_TYPES


class MockEmailProvider:
    """Development provider: records messages in memory and never sends email."""

    def __init__(self):
        self.sent_messages = []

    def send(self, subject: str, body: str, recipient: Optional[str] = None) -> Dict[str, str]:
        message = {
            "provider": "mock",
            "status": "recorded_not_sent",
            "recipient": recipient or settings.alert_email_recipient,
            "subject": subject,
            "body": body,
        }
        self.sent_messages.append(message)
        logger.info("Mock email alert recorded recipient=%s subject=%s", message["recipient"], subject)
        return message


mock_email_provider = MockEmailProvider()


def _begin_write(conn: Connection):
    return conn.begin_nested() if conn.in_transaction() else conn.begin()


def _fmt(value: Any) -> str:
    return "not recorded" if value is None else "${:,.2f}".format(float(value))


def _severity(previous: Any, current: Any) -> str:
    if previous is not None and current is not None and float(previous) != 0:
        if abs(float(current) - float(previous)) / abs(float(previous)) >= 0.10:
            return "high"
    return "medium"


def _persist_change(
    conn: Connection,
    *,
    competitor_id: int,
    competitor_name: str,
    change_type: str,
    entity_type: str,
    entity_id: int,
    previous_value: Optional[str],
    new_value: Optional[str],
    effective_date: date,
    previous_snapshot_captured_at: Optional[datetime],
    new_snapshot_captured_at: datetime,
    severity: str,
    summary_text: str,
    source_snapshot_from: Optional[date],
    source_snapshot_to: date,
) -> Dict[str, Any]:
    statement = insert(competitor_changes).values(
        competitor_id=competitor_id,
        change_type=change_type,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_value=previous_value,
        new_value=new_value,
        previous_snapshot_captured_at=previous_snapshot_captured_at,
        new_snapshot_captured_at=new_snapshot_captured_at,
        change_detected_at=new_snapshot_captured_at,
        effective_date=effective_date,
        severity=severity,
        summary_text=summary_text,
        source_snapshot_from=source_snapshot_from,
        source_snapshot_to=source_snapshot_to,
        record_origin="system_detected",
        created_at=new_snapshot_captured_at,
    ).returning(competitor_changes.c.change_id)
    change_id = conn.execute(statement).scalar_one()
    return {
        "change_id": change_id,
        "competitor_id": competitor_id,
        "competitor_name": competitor_name,
        "change_type": change_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "previous_value": previous_value,
        "new_value": new_value,
        "effective_date": effective_date,
        "severity": severity,
        "summary_text": summary_text,
        "source_snapshot_from": source_snapshot_from,
        "source_snapshot_to": source_snapshot_to,
        "record_origin": "system_detected",
        "change_detected_at": new_snapshot_captured_at,
    }


def _email_for_change(change: Dict[str, Any], competitor_name: str) -> Dict[str, str]:
    subject = "Competitive Alert: {} {} Change".format(competitor_name, change["change_type"].replace("_", " ").title())
    body = (
        "{}\n\nChange: {}\nPrevious: {}\nNew: {}\nObserved: {}\n\n"
        "This alert was generated from the competitive intelligence tracking system."
    ).format(
        change["summary_text"], change["change_type"], change["previous_value"] or "Not recorded",
        change["new_value"] or "Not recorded", change["effective_date"],
    )
    return mock_email_provider.send(subject, body)


def submit_plan_price_observation(conn: Connection, request: PlanPriceObservationRequest) -> Dict[str, Any]:
    with _begin_write(conn):
        plan_row = conn.execute(
            select(service_plans.c.plan_id, service_plans.c.plan_name, service_plans.c.competitor_id, competitors.c.name.label("competitor_name"))
            .select_from(service_plans.join(competitors, competitors.c.competitor_id == service_plans.c.competitor_id))
            .where(service_plans.c.plan_id == request.plan_id)
        ).mappings().first()
        if plan_row is None:
            raise ValueError("Plan was not found.")
        previous = conn.execute(
            select(plan_price_history)
            .where(plan_price_history.c.plan_id == request.plan_id)
            .order_by(plan_price_history.c.captured_at.desc(), plan_price_history.c.plan_price_history_id.desc())
            .limit(1)
        ).mappings().first()
        previous = dict(previous) if previous else None
        current = {
            "price_usd": request.price_usd,
            "promotional_price_usd": request.promotional_price_usd,
            "promo_terms": request.promo_terms,
        }
        detected = detect_observation_change("plan", previous, current)
        captured_at = datetime.now(timezone.utc)
        effective_date = request.effective_date or request.source_snapshot_date
        conn.execute(insert(plan_price_history).values(
            plan_id=request.plan_id,
            effective_date=effective_date,
            price_usd=request.price_usd,
            promotional_price_usd=request.promotional_price_usd,
            promo_terms=request.promo_terms,
            features_snapshot=None,
            captured_at=captured_at,
            source_snapshot_date=request.source_snapshot_date,
            created_at=captured_at,
        ))
        if not detected:
            return {"observation_type": "plan_price", "observation_appended": True, "change_detected": False, "change": None, "alert_important": False, "email_alert": None}

        previous_value = "{} (promo {})".format(_fmt(previous["price_usd"]), _fmt(previous["promotional_price_usd"]))
        new_value = "{} (promo {})".format(_fmt(request.price_usd), _fmt(request.promotional_price_usd))
        summary = "{} {} changed from {} to {}.".format(plan_row["competitor_name"], plan_row["plan_name"], previous_value, new_value)
        change = _persist_change(
            conn,
            competitor_id=plan_row["competitor_id"], competitor_name=plan_row["competitor_name"], change_type=detected["change_type"], entity_type="plan",
            entity_id=request.plan_id, previous_value=previous_value, new_value=new_value,
            effective_date=effective_date, previous_snapshot_captured_at=previous["captured_at"],
            new_snapshot_captured_at=captured_at,
            severity=_severity(previous["price_usd"], request.price_usd), summary_text=summary,
            source_snapshot_from=previous["source_snapshot_date"], source_snapshot_to=request.source_snapshot_date,
        )
        alert = should_alert(change["change_type"])
        email = _email_for_change(change, plan_row["competitor_name"]) if alert else None
        return {"observation_type": "plan_price", "observation_appended": True, "change_detected": True, "change": change, "alert_important": alert, "email_alert": email}


def submit_device_price_observation(conn: Connection, request: DevicePriceObservationRequest) -> Dict[str, Any]:
    with _begin_write(conn):
        device_row = conn.execute(
            select(devices.c.device_id, devices.c.model_name, devices.c.competitor_id, competitors.c.name.label("competitor_name"))
            .select_from(devices.join(competitors, competitors.c.competitor_id == devices.c.competitor_id))
            .where(devices.c.device_id == request.device_id)
        ).mappings().first()
        if device_row is None:
            raise ValueError("Device was not found.")
        previous = conn.execute(
            select(device_price_history)
            .where(device_price_history.c.device_id == request.device_id)
            .order_by(device_price_history.c.captured_at.desc(), device_price_history.c.device_price_history_id.desc())
            .limit(1)
        ).mappings().first()
        previous = dict(previous) if previous else None
        current = {
            "retail_price_usd": request.retail_price_usd,
            "promo_price_usd": request.promo_price_usd,
            "promotion_terms": request.promotion_terms,
            "financing_terms": request.financing_terms,
        }
        detected = detect_observation_change("device", previous, current)
        captured_at = datetime.now(timezone.utc)
        effective_date = request.effective_date or request.source_snapshot_date
        conn.execute(insert(device_price_history).values(
            device_id=request.device_id,
            effective_date=effective_date,
            retail_price_usd=request.retail_price_usd,
            promo_price_usd=request.promo_price_usd,
            promotion_terms=request.promotion_terms,
            financing_terms=request.financing_terms,
            captured_at=captured_at,
            source_snapshot_date=request.source_snapshot_date,
            created_at=captured_at,
        ))
        if not detected:
            return {"observation_type": "device_price", "observation_appended": True, "change_detected": False, "change": None, "alert_important": False, "email_alert": None}

        previous_value = "retail {} (promo {})".format(_fmt(previous["retail_price_usd"]), _fmt(previous["promo_price_usd"]))
        new_value = "retail {} (promo {})".format(_fmt(request.retail_price_usd), _fmt(request.promo_price_usd))
        summary = "{} {} pricing changed from {} to {}.".format(device_row["competitor_name"], device_row["model_name"], previous_value, new_value)
        change = _persist_change(
            conn,
            competitor_id=device_row["competitor_id"], competitor_name=device_row["competitor_name"], change_type=detected["change_type"], entity_type="device",
            entity_id=request.device_id, previous_value=previous_value, new_value=new_value,
            effective_date=effective_date, previous_snapshot_captured_at=previous["captured_at"],
            new_snapshot_captured_at=captured_at,
            severity=_severity(previous["promo_price_usd"] or previous["retail_price_usd"], request.promo_price_usd or request.retail_price_usd),
            summary_text=summary, source_snapshot_from=previous["source_snapshot_date"], source_snapshot_to=request.source_snapshot_date,
        )
        alert = should_alert(change["change_type"])
        email = _email_for_change(change, device_row["competitor_name"]) if alert else None
        return {"observation_type": "device_price", "observation_appended": True, "change_detected": True, "change": change, "alert_important": alert, "email_alert": email}


def detect_promotion_change(previous: Optional[Dict[str, Any]], current: Dict[str, Any], observed_on: date) -> Optional[str]:
    if previous is None:
        return "promotion_new"
    was_active = previous.get("end_date") is None or previous["end_date"] >= observed_on
    is_ended = current.get("end_date") is not None and current["end_date"] <= observed_on
    if was_active and is_ended:
        return "promotion_ended"
    compare_fields = ("promotion_type", "description", "target_type", "target_plan_id", "target_device_id", "start_date", "end_date")
    if any(previous.get(field) != current.get(field) for field in compare_fields):
        return "promotion_terms_changed"
    return None


def submit_promotion_observation(conn: Connection, request: PromotionObservationRequest) -> Dict[str, Any]:
    with _begin_write(conn):
        competitor = conn.execute(select(competitors).where(competitors.c.competitor_id == request.competitor_id)).mappings().first()
        if competitor is None:
            raise ValueError("Competitor was not found.")
        previous = conn.execute(
            select(promotions)
            .where(promotions.c.competitor_id == request.competitor_id)
            .where(promotions.c.promotion_title.ilike(request.promotion_title))
            .order_by(promotions.c.captured_at.desc(), promotions.c.promotion_id.desc())
            .limit(1)
        ).mappings().first()
        previous = dict(previous) if previous else None
        current = request.model_dump()
        change_type = detect_promotion_change(previous, current, request.source_snapshot_date)
        captured_at = datetime.now(timezone.utc)
        promotion_id = conn.execute(insert(promotions).values(
            competitor_id=request.competitor_id,
            promotion_title=request.promotion_title,
            promotion_type=request.promotion_type,
            description=request.description,
            target_type=request.target_type,
            target_plan_id=request.target_plan_id,
            target_device_id=request.target_device_id,
            start_date=request.start_date,
            end_date=request.end_date,
            captured_at=captured_at,
            created_at=captured_at,
        ).returning(promotions.c.promotion_id)).scalar_one()
        if change_type is None:
            return {"observation_type": "promotion", "observation_appended": True, "change_detected": False, "change": None, "alert_important": False, "email_alert": None}
        previous_value = "{} ({} through {})".format(previous["description"], previous["start_date"] or "unspecified", previous["end_date"] or "unspecified") if previous else "No previously tracked promotion"
        new_value = "{} ({} through {})".format(request.description, request.start_date or "unspecified", request.end_date or "unspecified")
        summary = "{} promotion '{}' {}.".format(competitor["name"], request.promotion_title, change_type.replace("_", " "))
        change = _persist_change(
            conn,
            competitor_id=request.competitor_id,
            competitor_name=competitor["name"],
            change_type=change_type,
            entity_type=request.target_type,
            entity_id=request.target_plan_id or request.target_device_id or promotion_id,
            previous_value=previous_value,
            new_value=new_value,
            effective_date=request.source_snapshot_date,
            previous_snapshot_captured_at=previous["captured_at"] if previous else None,
            new_snapshot_captured_at=captured_at,
            severity="high" if change_type in {"promotion_new", "promotion_ended"} else "medium",
            summary_text=summary,
            source_snapshot_from=previous["start_date"] if previous else None,
            source_snapshot_to=request.source_snapshot_date,
        )
        alert = should_alert(change_type)
        email = _email_for_change(change, competitor["name"]) if alert else None
        return {"observation_type": "promotion", "observation_appended": True, "change_detected": True, "change": change, "alert_important": alert, "email_alert": email}
