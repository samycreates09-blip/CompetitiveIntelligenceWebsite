from fastapi.testclient import TestClient

from app.database import engine
from app.main import app
from app.services import agent_service, agent_tools
from app.services.briefing_service import BriefingConfiguration

client = TestClient(app)


# ---- Tool wrappers: real read-only queries against the dev DB, no mocking needed ----

def test_get_current_plan_prices_filters_by_competitor_and_plan_name():
    with engine.connect() as conn:
        result = agent_tools.get_current_plan_prices(conn, competitor="T-Mobile")
    assert result["count"] >= 1
    assert all("T-Mobile" in s["summary"] for s in result["sources"])

    with engine.connect() as conn:
        result = agent_tools.get_current_plan_prices(conn, plan_name="Essentials")
    assert result["count"] == 1
    assert result["sources"][0]["source_id"] == "PLAN-201"


def test_get_plan_price_history_returns_ordered_observations():
    with engine.connect() as conn:
        result = agent_tools.get_plan_price_history(conn, competitor="T-Mobile", plan_name="Essentials")
    assert result["count"] >= 2
    assert any("$60.00" in s["summary"] for s in result["sources"])
    assert any("$65.00" in s["summary"] for s in result["sources"])


def test_get_device_price_history_filters_by_model_name():
    with engine.connect() as conn:
        result = agent_tools.get_device_price_history(conn, model_name="iPhone 15 Pro")
    assert result["count"] >= 1
    assert all("iPhone 15 Pro" in s["summary"] for s in result["sources"])


def test_get_promotions_filters_by_competitor():
    with engine.connect() as conn:
        result = agent_tools.get_promotions(conn, competitor="Boost", active_only=False)
    assert result["count"] >= 1
    assert all(s["source_id"].startswith("PROMOTION-") for s in result["sources"])


def test_get_recent_changes_respects_limit_and_competitor():
    with engine.connect() as conn:
        result = agent_tools.get_recent_changes(conn, competitor="T-Mobile", limit=1)
    assert result["count"] == 1
    assert "T-Mobile" in result["sources"][0]["summary"]


def test_search_competitor_documents_returns_document_chunks_with_real_embeddings():
    with engine.connect() as conn:
        result = agent_tools.search_competitor_documents(conn, query="trade-in eligibility requirements", competitor="Verizon")
    assert result["count"] >= 1
    assert all(s["category"] == "document_chunk" for s in result["sources"])
    assert all(s["record_origin"] == "synthetic_document" for s in result["sources"])
    assert any("Verizon" in s["summary"] for s in result["sources"])


def test_search_competitor_documents_returns_empty_without_configured_key(monkeypatch):
    import dataclasses
    monkeypatch.setattr(agent_tools, "settings", dataclasses.replace(agent_tools.settings, gemini_api_key=""))
    with engine.connect() as conn:
        result = agent_tools.search_competitor_documents(conn, query="anything")
    assert result == {"sources": [], "count": 0, "error": "Document search is not configured."}


# ---- Bounded agent loop: fully mocked Gemini tool-calling session ----

class FakeToolSession:
    """Scripted stand-in for gemini_provider.GeminiToolSession: returns one
    canned response per call in order, so the loop's control flow (execute
    tool -> feed result back -> ask again) is tested without any network."""

    def __init__(self, responses):
        self._responses = iter(responses)
        self.sent_messages = []
        self.closed = False

    def send(self, message):
        self.sent_messages.append(message)
        return next(self._responses)

    def close(self):
        self.closed = True


def _fake_response(calls=None, text=None):
    return {"calls": calls or [], "text": text}


def test_agent_answers_simple_single_tool_question(monkeypatch):
    session = FakeToolSession([
        _fake_response(calls=[{"name": "get_current_plan_prices", "args": {"plan_name": "Essentials"}}]),
        _fake_response(text="T-Mobile Essentials is $65.00/month [PLAN-201]."),
    ])
    monkeypatch.setattr(agent_service, "create_tool_session", lambda *_a, **_k: session)
    monkeypatch.setattr(agent_service, "extract_function_calls", lambda resp: resp["calls"])
    monkeypatch.setattr(agent_service, "extract_text", lambda resp: resp["text"])
    monkeypatch.setattr(agent_service, "build_function_response_part", lambda name, response: {"name": name, "response": response})
    monkeypatch.setattr(
        agent_service, "load_briefing_configuration",
        lambda: BriefingConfiguration(api_key="not-a-real-test-key", model="test-model"),
    )

    with engine.connect() as conn:
        result = agent_service.answer_chat_question_with_tools(conn, "What is T-Mobile Essentials currently priced at?")

    assert "65.00" in result["answer"]
    assert result["data_scope"]["tools_used"] == ["get_current_plan_prices"]
    assert result["data_scope"]["tool_call_count"] == 1
    assert any(s["source_id"] == "PLAN-201" for s in result["sources"])
    assert session.closed is True


def test_agent_supports_multi_tool_call_in_one_turn(monkeypatch):
    session = FakeToolSession([
        _fake_response(calls=[
            {"name": "get_plan_price_history", "args": {"competitor": "T-Mobile"}},
            {"name": "get_current_plan_prices", "args": {"competitor": "Boost"}},
            {"name": "search_competitor_documents", "args": {"competitor": "T-Mobile", "query": "promotion conditions"}},
        ]),
        _fake_response(text="T-Mobile rose from $60 to $65 [PLAN-HISTORY-201-2]; Boost is $50 [PLAN-101]. T-Mobile's bundle requires a new line [DOC-2-2]."),
    ])
    monkeypatch.setattr(agent_service, "create_tool_session", lambda *_a, **_k: session)
    monkeypatch.setattr(agent_service, "extract_function_calls", lambda resp: resp["calls"])
    monkeypatch.setattr(agent_service, "extract_text", lambda resp: resp["text"])
    monkeypatch.setattr(agent_service, "build_function_response_part", lambda name, response: {"name": name, "response": response})
    monkeypatch.setattr(
        agent_service, "load_briefing_configuration",
        lambda: BriefingConfiguration(api_key="not-a-real-test-key", model="test-model"),
    )

    with engine.connect() as conn:
        result = agent_service.answer_chat_question_with_tools(
            conn, "Compare T-Mobile's recent price change with Boost and explain T-Mobile's promotion conditions."
        )

    assert sorted(result["data_scope"]["tools_used"]) == [
        "get_current_plan_prices", "get_plan_price_history", "search_competitor_documents",
    ]
    assert result["data_scope"]["tool_call_count"] == 3
    categories = {s["category"] for s in result["sources"]}
    assert "plan_history" in categories
    assert "current_plan" in categories
    assert "document_chunk" in categories


def test_agent_stops_calling_tools_and_returns_insufficient_when_none_match(monkeypatch):
    session = FakeToolSession([
        _fake_response(calls=[{"name": "get_promotions", "args": {"competitor": "Boost"}}]),
        _fake_response(text=""),
    ])
    monkeypatch.setattr(agent_service, "create_tool_session", lambda *_a, **_k: session)
    monkeypatch.setattr(agent_service, "extract_function_calls", lambda resp: resp["calls"])
    monkeypatch.setattr(agent_service, "extract_text", lambda resp: resp["text"])
    monkeypatch.setattr(agent_service, "build_function_response_part", lambda name, response: {"name": name, "response": response})
    monkeypatch.setattr(
        agent_service, "load_briefing_configuration",
        lambda: BriefingConfiguration(api_key="not-a-real-test-key", model="test-model"),
    )

    with engine.connect() as conn:
        result = agent_service.answer_chat_question_with_tools(conn, "What satellite texting price does Boost Mobile offer?")

    assert "insufficient" in result["answer"].lower()


def test_agent_returns_bounded_fallback_when_step_limit_exceeded(monkeypatch):
    # Every turn keeps requesting another tool call, never producing final text.
    endless_calls = [_fake_response(calls=[{"name": "get_recent_changes", "args": {}}]) for _ in range(agent_service.MAX_TOOL_CALL_STEPS + 1)]
    session = FakeToolSession(endless_calls)
    monkeypatch.setattr(agent_service, "create_tool_session", lambda *_a, **_k: session)
    monkeypatch.setattr(agent_service, "extract_function_calls", lambda resp: resp["calls"])
    monkeypatch.setattr(agent_service, "extract_text", lambda resp: resp["text"])
    monkeypatch.setattr(agent_service, "build_function_response_part", lambda name, response: {"name": name, "response": response})
    monkeypatch.setattr(
        agent_service, "load_briefing_configuration",
        lambda: BriefingConfiguration(api_key="not-a-real-test-key", model="test-model"),
    )

    with engine.connect() as conn:
        result = agent_service.answer_chat_question_with_tools(conn, "What changed recently?")

    assert result["answer"] == agent_service.TOOL_STEP_LIMIT_ANSWER
    assert result["data_scope"]["tool_call_count"] == agent_service.MAX_TOOL_CALL_STEPS


def test_unknown_tool_name_is_handled_without_crashing(monkeypatch):
    session = FakeToolSession([
        _fake_response(calls=[{"name": "delete_all_competitors", "args": {}}]),
        _fake_response(text="I could not find that information."),
    ])
    monkeypatch.setattr(agent_service, "create_tool_session", lambda *_a, **_k: session)
    monkeypatch.setattr(agent_service, "extract_function_calls", lambda resp: resp["calls"])
    monkeypatch.setattr(agent_service, "extract_text", lambda resp: resp["text"])
    monkeypatch.setattr(agent_service, "build_function_response_part", lambda name, response: {"name": name, "response": response})
    monkeypatch.setattr(
        agent_service, "load_briefing_configuration",
        lambda: BriefingConfiguration(api_key="not-a-real-test-key", model="test-model"),
    )

    with engine.connect() as conn:
        result = agent_service.answer_chat_question_with_tools(conn, "irrelevant")

    assert result["sources"] == []


def test_agent_chat_endpoint_requires_configured_provider(monkeypatch):
    monkeypatch.setattr(
        agent_service, "load_briefing_configuration",
        lambda: BriefingConfiguration(api_key="", model="test-model"),
    )
    response = client.post("/api/v1/ai/agent-chat", json={"message": "What is T-Mobile Essentials currently priced at?"})
    assert response.status_code == 503


# ---- Tool-selection evaluation: deterministic, mocked, no live calls ----

TOOL_SELECTION_CASES = [
    ("What is T-Mobile Essentials currently priced at?", {"get_current_plan_prices"}),
    ("How has T-Mobile Essentials pricing changed?", {"get_plan_price_history"}),
    ("What changed recently?", {"get_recent_changes"}),
    ("What are Verizon's promotion conditions?", {"search_competitor_documents", "get_promotions"}),
    ("Compare T-Mobile's recent price change with Boost and explain T-Mobile's promotion conditions.",
     {"get_plan_price_history", "get_current_plan_prices", "search_competitor_documents"}),
]


def test_tool_declaration_names_match_dispatch_table():
    declared_names = {decl["name"] for decl in agent_tools.TOOL_DECLARATIONS}
    assert declared_names == set(agent_tools.TOOL_DISPATCH.keys())
