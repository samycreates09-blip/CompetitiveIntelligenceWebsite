import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import briefing_context, briefing_evaluation, briefing_service
from app.services import gemini_provider
from app.services.gemini_provider import GeminiProviderError
from google.genai.errors import APIError

client = TestClient(app)


def _mock_grounded_briefing(context_json):
    context = json.loads(context_json)
    fact_by_category = {}
    for fact in context["facts"]:
        fact_by_category.setdefault(fact["category"], []).append(fact["id"])
    change_ids = [item["fact_id"] for item in context["synthetic_seeded_change_records"]]
    return "\n".join([
        "- Boost Mobile's Unlimited Plan is listed at $50.00 with an observed $40.00 promotional price [{}].".format(
            fact_by_category["current_plan"][0]
        ),
        "- T-Mobile Essentials moved from $60.00 to $65.00 in a synthetic seeded record, not an automatically detected event [{}].".format(
            change_ids[1]
        ),
        "- Verizon's synthetic seeded record describes a $300 trade-in bonus for the iPhone 15 Pro; it is not automatic detection [{}].".format(
            change_ids[2]
        ),
        "- These supplied records suggest reviewing the limited-time Boost offer against competitors; this is an interpretation, not an external market assessment [{}].".format(
            fact_by_category["active_promotion"][0]
        ),
        "- Treat the displayed prices and promotion details as the local seeded dataset, and validate commercial decisions against approved current sources [{}].".format(
            fact_by_category["current_plan"][0]
        ),
    ])


def test_context_assembly_uses_existing_seeded_data():
    from app.database import engine

    with engine.connect() as conn:
        context = briefing_context.assemble_briefing_context(conn)

    assert context["data_scope"]["plan_count"] == 3
    assert context["data_scope"]["device_count"] == 6
    assert context["data_scope"]["active_promotion_count"] == 2
    assert context["data_scope"]["synthetic_change_record_count"] == 3
    assert context["data_scope"]["synthetic_change_records"] is True
    assert any("Boost Mobile Boost Unlimited Plan" in fact["text"] and "$50.00" in fact["text"] for fact in context["facts"])
    assert any("SYNTHETIC SEEDED RECORD" in fact["text"] and "not automatically detected" in fact["text"] for fact in context["facts"])


def test_successful_briefing_endpoint_with_mocked_gemini(monkeypatch):
    monkeypatch.setattr(
        briefing_service,
        "load_briefing_configuration",
        lambda: briefing_service.BriefingConfiguration(api_key="test-key-not-real", model="gemini-test-model"),
    )
    captured = {}

    def fake_generate(context_json, api_key, model):
        captured["context"] = json.loads(context_json)
        captured["api_key_passed"] = api_key
        captured["model"] = model
        return _mock_grounded_briefing(context_json)

    monkeypatch.setattr("app.services.briefing_service.generate_briefing", fake_generate)
    response = client.post("/api/v1/ai/briefing", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "gemini-test-model"
    assert payload["briefing"]
    assert payload["data_scope"]["plan_count"] == 3
    assert payload["data_scope"]["synthetic_change_records"] is True
    assert payload["evaluation"]["status"] == "pass"
    assert payload["evaluation"]["manual_review_required"] is True
    assert captured["model"] == "gemini-test-model"
    assert "$50.00" in json.dumps(captured["context"])
    assert "test-key-not-real" not in response.text


def test_missing_gemini_configuration_returns_safe_503(monkeypatch):
    monkeypatch.setattr(
        briefing_service,
        "load_briefing_configuration",
        lambda: briefing_service.BriefingConfiguration(api_key="", model="gemini-test-model"),
    )
    response = client.post("/api/v1/ai/briefing", json={})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "HTTP_ERROR"
    assert "not configured" in response.json()["error"]["message"]


def test_provider_failure_returns_sanitized_502(monkeypatch):
    monkeypatch.setattr(
        briefing_service,
        "load_briefing_configuration",
        lambda: briefing_service.BriefingConfiguration(api_key="test-key-not-real", model="gemini-test-model"),
    )

    def fail_generation(*_args):
        raise GeminiProviderError("Gemini could not generate a briefing.")

    monkeypatch.setattr("app.services.briefing_service.generate_briefing", fail_generation)
    response = client.post("/api/v1/ai/briefing", json={})

    assert response.status_code == 502
    assert "could not generate" in response.json()["error"]["message"]
    assert "test-key-not-real" not in response.text


def test_context_failure_returns_safe_503(monkeypatch):
    monkeypatch.setattr(
        briefing_service,
        "load_briefing_configuration",
        lambda: briefing_service.BriefingConfiguration(api_key="test-key-not-real", model="gemini-test-model"),
    )

    def fail_context(_conn):
        raise RuntimeError("sensitive database detail")

    monkeypatch.setattr(briefing_service, "assemble_briefing_context", fail_context)
    response = client.post("/api/v1/ai/briefing", json={})

    assert response.status_code == 503
    assert "could not be retrieved" in response.json()["error"]["message"]
    assert "sensitive database detail" not in response.text


def test_provider_configuration_repr_hides_credentials():
    from app.config import settings

    configuration = briefing_service.BriefingConfiguration(api_key="test-key-not-real", model="test-model")
    assert "test-key-not-real" not in repr(configuration)
    assert "gemini_api_key" not in repr(settings)


def test_empty_provider_response_is_rejected_without_live_call(monkeypatch):
    class FakeModels:
        def generate_content(self, **_kwargs):
            return type("Response", (), {"text": None})()

    class FakeClient:
        def __init__(self, **_kwargs):
            self.models = FakeModels()

    monkeypatch.setattr(gemini_provider.genai, "Client", FakeClient)
    with pytest.raises(GeminiProviderError, match="empty or malformed"):
        gemini_provider.generate_briefing("{}", "test-key-not-real", "test-model")


def test_provider_api_error_logs_safe_diagnostics_only(monkeypatch, caplog):
    credential_like_value = "AIza" + ("X" * 32)

    class FakeModels:
        def generate_content(self, **_kwargs):
            raise APIError(
                code=403,
                response_json={
                    "error": {
                        "message": "permission denied; api_key={}".format(credential_like_value)
                    }
                },
            )

    class FakeClient:
        def __init__(self, **_kwargs):
            self.models = FakeModels()

        def close(self):
            pass

    monkeypatch.setattr(gemini_provider.genai, "Client", FakeClient)
    with caplog.at_level("WARNING", logger="app.services.gemini_provider"):
        with pytest.raises(GeminiProviderError):
            gemini_provider.generate_briefing("{}", "not-a-real-key", "gemini-test-model")

    output = caplog.text
    assert "model=gemini-test-model" in output
    assert "exception_type=APIError" in output
    assert "http_status=403" in output
    assert "permission denied" in output
    assert "[REDACTED]" in output
    assert credential_like_value not in output
    assert "not-a-real-key" not in output


def test_non_api_provider_error_does_not_log_raw_exception(monkeypatch, caplog):
    class FakeModels:
        def generate_content(self, **_kwargs):
            raise RuntimeError("transport failure with Authorization: Bearer sensitive-token")

    class FakeClient:
        def __init__(self, **_kwargs):
            self.models = FakeModels()

        def close(self):
            pass

    monkeypatch.setattr(gemini_provider.genai, "Client", FakeClient)
    with caplog.at_level("WARNING", logger="app.services.gemini_provider"):
        with pytest.raises(GeminiProviderError):
            gemini_provider.generate_briefing("{}", "not-a-real-key", "gemini-test-model")

    assert "exception_type=RuntimeError" in caplog.text
    assert "Provider client or transport failed" in caplog.text
    assert "sensitive-token" not in caplog.text
    assert "transport failure with Authorization" not in caplog.text


def test_evaluation_flags_unsupported_amount_and_missing_change_coverage():
    context = {
        "facts": [
            {"id": "F1", "category": "current_plan", "text": "Boost Mobile plan costs $50.00."},
            {"id": "F2", "category": "synthetic_seeded_change", "text": "Synthetic change: $60.00 to $65.00."},
        ],
        "data_scope": {"competitors": ["Boost Mobile"], "synthetic_change_records": True},
        "synthetic_seeded_change_records": [{"fact_id": "F2"}],
    }
    briefing = "- Boost Mobile plan is $50.00 [F1].\n- Boost Mobile rose to $99.00 [F2]."

    evaluation = briefing_evaluation.evaluate_briefing(briefing, context)

    assert evaluation["status"] == "review"
    assert evaluation["dimensions"]["factual_accuracy"]["passed"] is False
    assert evaluation["dimensions"]["hallucination_risk"]["passed"] is False
    assert evaluation["dimensions"]["important_fact_coverage"]["score"] == 1.0
    assert evaluation["manual_review_required"] is True


def test_invalid_citations_fail_groundedness():
    context = {
        "facts": [{"id": "F1", "category": "current_plan", "text": "Boost Mobile costs $50."}],
        "data_scope": {"competitors": ["Boost Mobile"]},
        "synthetic_seeded_change_records": [],
    }
    evaluation = briefing_evaluation.evaluate_briefing(
        "- " + ("This is a factual statement that makes a claim. " * 8) + "[F99]", context
    )
    assert evaluation["dimensions"]["groundedness"]["passed"] is False
    assert evaluation["dimensions"]["hallucination_risk"]["passed"] is False


@pytest.mark.parametrize("citation", ["[F1, F2, F12]", "[F1,F2,F12]"])
def test_grouped_citations_resolve_every_fact_id(citation):
    context = {
        "facts": [
            {"id": "F1", "category": "current_plan", "text": "Boost Mobile plan costs $50.00."},
            {"id": "F2", "category": "plan_history", "text": "Boost Mobile plan was $60.00 before."},
            {"id": "F12", "category": "synthetic_seeded_change", "text": "Synthetic seeded change, not auto detected."},
        ],
        "data_scope": {"competitors": ["Boost Mobile"], "synthetic_change_records": True},
        "synthetic_seeded_change_records": [{"fact_id": "F12"}],
    }
    briefing = "\n".join([
        "- Boost Mobile's plan currently costs $50.00 [F1, F2].",
        "- The historical listing was $60.00 [F2].",
        "- This synthetic seeded demo change record was not automatically detected [F12].",
        "- These supplied listings offer stakeholders a comparison based only on locally captured structured records [F1].",
        "- Further conclusions should remain limited to the supported plan prices and recorded snapshot history [F2].",
    ]).replace("[F1, F2].", citation + ".", 1)

    evaluation = briefing_evaluation.evaluate_briefing(briefing, context)

    assert evaluation["dimensions"]["groundedness"]["passed"] is True
    assert evaluation["dimensions"]["important_fact_coverage"]["score"] == 1.0
    assert evaluation["dimensions"]["important_fact_coverage"]["passed"] is True
    assert evaluation["dimensions"]["hallucination_risk"]["passed"] is True


@pytest.mark.parametrize("amount", ["$50", "$50.00"])
def test_numeric_amount_normalization_accepts_supported_equivalent_formats(amount):
    context = {
        "facts": [{"id": "F1", "category": "current_plan", "text": "Boost Mobile plan is $50.00 monthly."}],
        "data_scope": {"competitors": ["Boost Mobile"]},
        "synthetic_seeded_change_records": [],
    }
    briefing = "- Boost Mobile lists its plan at {} [F1].\n- The supplied plan listing can inform a focused product review [F1].\n- This summary is restricted to the provided competitive facts [F1].".format(amount)

    evaluation = briefing_evaluation.evaluate_briefing(briefing, context)

    assert evaluation["dimensions"]["factual_accuracy"]["passed"] is True
    assert evaluation["dimensions"]["hallucination_risk"]["passed"] is True


def test_record_specific_discount_amount_is_supported():
    context = {
        "facts": [{"id": "F1", "category": "current_device_price", "text": "Device retail $799 and promo $699."}],
        "latest_device_prices": [{"latest_price": {"retail_price_usd": 799, "promo_price_usd": 699}}],
        "data_scope": {"competitors": ["Boost Mobile"]},
        "synthetic_seeded_change_records": [],
    }
    briefing = "- Boost Mobile offers a $100 promotional discount against this device's $799 retail price [F1].\n- This comparison comes from the same captured retail and promotional price record [F1].\n- Stakeholders can review the observed discount alongside the source snapshot details [F1]."

    evaluation = briefing_evaluation.evaluate_briefing(briefing, context)

    assert evaluation["dimensions"]["factual_accuracy"]["passed"] is True
    assert evaluation["dimensions"]["hallucination_risk"]["passed"] is True


def test_genuinely_invented_monetary_amount_fails():
    context = {
        "facts": [{"id": "F1", "category": "current_plan", "text": "Boost Mobile plan is $50.00 monthly."}],
        "data_scope": {"competitors": ["Boost Mobile"]},
        "synthetic_seeded_change_records": [],
    }
    briefing = "- Boost Mobile lists its plan at $99.00 [F1].\n- The supplied plan record is the only reference for this summary [F1].\n- Stakeholders should confirm pricing against approved snapshots [F1]."

    evaluation = briefing_evaluation.evaluate_briefing(briefing, context)

    assert evaluation["dimensions"]["factual_accuracy"]["passed"] is False
    assert evaluation["dimensions"]["hallucination_risk"]["passed"] is False


@pytest.mark.parametrize("qualification", ["", "This is a synthetic seeded demo record, not automatically detected. "])
def test_cited_synthetic_change_requires_explicit_qualification(qualification):
    context = {
        "facts": [
            {"id": "F1", "category": "synthetic_seeded_change", "text": "T-Mobile Essentials moved from $60.00 to $65.00."},
            {"id": "F2", "category": "current_plan", "text": "T-Mobile Essentials is currently $65.00."},
            {"id": "F3", "category": "active_promotion", "text": "T-Mobile offers a $150 bill credit."},
        ],
        "data_scope": {"competitors": ["T-Mobile"], "synthetic_change_records": True},
        "synthetic_seeded_change_records": [{"fact_id": "F1"}],
    }
    briefing = "\n".join([
        "- T-Mobile Essentials moved from $60.00 to $65.00. {}[F1]".format(qualification),
        "- The supplied current plan record lists T-Mobile Essentials at $65.00 [F2].",
        "- A separate supplied promotion record describes a $150 bill credit [F3].",
        "- These structured observations can inform pricing review, without adding external market claims [F2].",
        "- Interpretations should remain distinct from the recorded competitor facts [F2].",
    ])

    evaluation = briefing_evaluation.evaluate_briefing(briefing, context)

    assert evaluation["manual_review_required"] is True
    assert evaluation["dimensions"]["instruction_following"]["passed"] is bool(qualification)
    if qualification:
        assert evaluation["status"] == "pass"
    else:
        assert evaluation["status"] == "review"
