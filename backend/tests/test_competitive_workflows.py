import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.database import engine
from app.deps import get_write_db
from app.main import app
from app.services import chat_context, chat_service, change_detection_service
from app.services.briefing_service import BriefingConfiguration
from app.services.plan_service import get_plan_history

client = TestClient(app)


@pytest.fixture(autouse=True)
def rollback_observation_writes(monkeypatch):
    """Isolate simulation POST tests so seeded/historical DB state remains unchanged."""
    def transactional_connection():
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                yield connection
            finally:
                if transaction.is_active:
                    transaction.rollback()

    app.dependency_overrides[get_write_db] = transactional_connection
    change_detection_service.mock_email_provider.sent_messages[:] = []
    yield
    app.dependency_overrides.pop(get_write_db, None)
    change_detection_service.mock_email_provider.sent_messages[:] = []


def test_deterministic_question_routing_for_requested_categories():
    competitors = [
        {"competitor_id": 1, "name": "Boost Mobile", "short_name": "Boost"},
        {"competitor_id": 2, "name": "T-Mobile", "short_name": "T-Mobile"},
        {"competitor_id": 3, "name": "Verizon", "short_name": "Verizon"},
    ]
    assert chat_context.route_question("What is T-Mobile Essentials currently priced at?", competitors)["categories"] == ["plans"]
    assert chat_context.route_question("How has T-Mobile Essentials pricing changed?", competitors)["categories"] == ["plans", "plan_history", "changes"]
    assert chat_context.route_question("Compare Boost and T-Mobile plan pricing", competitors)["competitor_ids"] == [1, 2]
    assert chat_context.route_question("What promotions does Verizon have?", competitors)["categories"] == ["promotions"]
    assert chat_context.route_question("Tell me about Verizon iPhone 15 Pro pricing", competitors)["categories"] == ["devices"]
    assert chat_context.route_question("What changed recently?", competitors)["categories"] == ["changes"]


def test_chat_context_retrieves_structured_plan_and_history_facts():
    with engine.connect() as conn:
        context = chat_context.assemble_chat_context(conn, "How has T-Mobile Essentials pricing changed?")
    assert context["sufficient"]
    assert context["route"]["categories"] == ["plans", "plan_history", "changes"]
    assert context["data_scope"]["competitors"] == ["T-Mobile"]
    assert any("$65.00" in source["summary"] for source in context["sources"])
    assert any(source["category"] == "plan_history" and "$60.00" in source["summary"] for source in context["sources"])


def test_chat_response_uses_mocked_gemini_and_source_context(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "load_chat_configuration",
        lambda: BriefingConfiguration(api_key="not-a-real-test-key", model="test-model"),
    )
    captured = {}

    def fake_answer(question, context_json, _key, model):
        context = json.loads(context_json)
        captured["question"] = question
        captured["context"] = context
        captured["model"] = model
        plan = next(source for source in context["sources"] if source["category"] == "current_plan")
        return "T-Mobile Essentials currently costs $65.00 per month [PLAN-201]."

    monkeypatch.setattr(chat_service, "generate_chat_answer", fake_answer)
    response = client.post("/api/v1/ai/chat", json={"message": "What is T-Mobile Essentials currently priced at?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "test-model"
    assert "65.00" in payload["answer"]
    assert payload["sources"][0]["source_id"] == "PLAN-201"
    assert captured["question"].startswith("What is")
    assert captured["model"] == "test-model"
    assert "$65.00" in json.dumps(captured["context"])
    assert "not-a-real-test-key" not in response.text


def test_chat_insufficient_database_data_does_not_call_gemini(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "load_chat_configuration",
        lambda: BriefingConfiguration(api_key="", model="test-model"),
    )
    called = []
    monkeypatch.setattr(chat_service, "generate_chat_answer", lambda *_args: called.append(True))
    response = client.post("/api/v1/ai/chat", json={"message": "What satellite texting price does Boost Mobile offer?"})
    assert response.status_code == 200
    assert "insufficient" in response.json()["answer"].lower()
    assert called == []


def test_price_change_detection_is_deterministic():
    previous = {"price_usd": 65, "promotional_price_usd": None, "promo_terms": None}
    unchanged = {"price_usd": 65, "promotional_price_usd": None, "promo_terms": None}
    changed = {"price_usd": 70, "promotional_price_usd": None, "promo_terms": None}
    assert change_detection_service.detect_observation_change("plan", previous, unchanged) is None
    result = change_detection_service.detect_observation_change("plan", previous, changed)
    assert result["change_type"] == "plan_price"
    assert change_detection_service.should_alert(result["change_type"]) is True
    assert change_detection_service.should_alert("color_change") is False


def test_plan_observation_appends_history_detects_change_and_records_mock_email():
    with engine.connect() as conn:
        before = len(get_plan_history(conn, 201))

    response = client.post("/api/v1/observations/plan-price", json={
        "plan_id": 201,
        "price_usd": 70.0,
        "source_snapshot_date": "2026-10-03",
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["observation_appended"] is True
    assert payload["change_detected"] is True
    assert payload["change"]["record_origin"] == "system_detected"
    assert payload["change"]["previous_value"].startswith("$65.00")
    assert payload["change"]["new_value"].startswith("$70.00")
    assert payload["alert_important"] is True
    assert payload["email_alert"]["provider"] == "mock"
    assert payload["email_alert"]["status"] == "recorded_not_sent"
    assert "T-Mobile Essentials" in payload["email_alert"]["body"]

    with engine.connect() as conn:
        assert len(get_plan_history(conn, 201)) == before


def test_promotion_detection_new_changed_and_ended_cases():
    current = {"promotion_type": "service", "description": "Offer", "target_type": "plan", "target_plan_id": 201, "target_device_id": None, "start_date": None, "end_date": None}
    assert change_detection_service.detect_promotion_change(None, current, date(2026, 10, 3)) == "promotion_new"
    prior = dict(current)
    updated = dict(current, description="Updated terms")
    assert change_detection_service.detect_promotion_change(prior, updated, date(2026, 10, 3)) == "promotion_terms_changed"
    ended = dict(current, end_date=date(2026, 10, 3))
    assert change_detection_service.detect_promotion_change(prior, ended, date(2026, 10, 3)) == "promotion_ended"


def test_changes_records_expose_seeded_provenance():
    response = client.get("/api/v1/changes")
    assert response.status_code == 200
    assert len(response.json()) == 3
    assert all(change["record_origin"] == "synthetic_seeded" for change in response.json())


def test_device_observation_detects_promo_price_change_and_alerts():
    response = client.post("/api/v1/observations/device-price", json={
        "device_id": 7001,
        "retail_price_usd": 999,
        "promo_price_usd": 799,
        "promotion_terms": "New trade-in offer",
        "financing_terms": "0% APR",
        "source_snapshot_date": "2026-10-03",
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["change_detected"] is True
    assert payload["change"]["change_type"] == "device_promotion"
    assert payload["change"]["record_origin"] == "system_detected"
    assert payload["alert_important"] is True
    assert payload["email_alert"]["status"] == "recorded_not_sent"


def test_new_promotion_observation_creates_change_and_mock_email():
    response = client.post("/api/v1/observations/promotion", json={
        "competitor_id": 2,
        "promotion_title": "Workflow Test Bundle",
        "promotion_type": "bundle",
        "description": "A new synthetic test promotion.",
        "target_type": "bundle",
        "start_date": "2026-10-03",
        "end_date": "2026-10-10",
        "source_snapshot_date": "2026-10-03",
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["change_detected"] is True
    assert payload["change"]["change_type"] == "promotion_new"
    assert payload["change"]["record_origin"] == "system_detected"
    assert payload["alert_important"] is True
    assert payload["email_alert"]["provider"] == "mock"
    assert payload["email_alert"]["status"] == "recorded_not_sent"


def test_change_origin_filter_separates_seeded_from_system_records():
    response = client.get("/api/v1/changes?record_origin=synthetic_seeded")
    assert response.status_code == 200
    assert len(response.json()) == 3
    assert all(item["record_origin"] == "synthetic_seeded" for item in response.json())
