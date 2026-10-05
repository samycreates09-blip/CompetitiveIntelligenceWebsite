from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.engine import Connection

from app.services import agent_tools
from app.services.briefing_service import (
    BriefingConfigurationError,
    BriefingGenerationError,
    load_briefing_configuration,
)
from app.services.gemini_provider import (
    GeminiProviderError,
    build_function_response_part,
    create_tool_session,
    extract_function_calls,
    extract_text,
)

# Bounded, not open-ended: a handful of rounds is enough for the multi-tool
# examples this prototype demonstrates (e.g. compare-two-competitors-and-
# explain-terms needs 3 tool calls), without letting the model loop forever.
MAX_TOOL_CALL_STEPS = 4

INSUFFICIENT_DATA_ANSWER = (
    "The tracked competitive-intelligence data is insufficient to answer that question reliably. "
    "Try asking about tracked plan prices, device prices, promotions, recorded changes, or promotion terms/eligibility."
)
TOOL_STEP_LIMIT_ANSWER = (
    "This question needed more tool calls than this assistant allows in a single turn. "
    "Try asking a narrower question."
)


def _execute_tool(conn: Connection, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    tool_fn = agent_tools.TOOL_DISPATCH.get(name)
    if tool_fn is None:
        return {"sources": [], "count": 0, "error": "Unknown tool '{}'.".format(name)}
    try:
        return tool_fn(conn, **args)
    except TypeError as exc:
        return {"sources": [], "count": 0, "error": "Invalid arguments for {}: {}".format(name, exc)}
    except Exception:
        return {"sources": [], "count": 0, "error": "{} failed to execute.".format(name)}


def _dedupe_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for source in sources:
        source_id = source.get("source_id")
        if source_id in seen:
            continue
        seen.add(source_id)
        deduped.append(source)
    return deduped


def _build_response(answer: str, model: str, sources: List[Dict[str, Any]], tool_call_log: List[Dict[str, Any]]) -> Dict[str, Any]:
    deduped = _dedupe_sources(sources)
    return {
        "answer": answer,
        "model": model,
        "sources": deduped,
        "data_scope": {
            "tools_used": sorted({call["tool"] for call in tool_call_log}),
            "tool_call_count": len(tool_call_log),
            "source_count": len(deduped),
            "synthetic_change_records_included": any(s.get("record_origin") == "synthetic_seeded" for s in deduped),
            "document_sources_included": any(s.get("category") == "document_chunk" for s in deduped),
        },
    }


def answer_chat_question_with_tools(conn: Connection, message: str) -> Dict[str, Any]:
    configuration = load_briefing_configuration()
    if not configuration.api_key:
        raise BriefingConfigurationError("AI assistant is unavailable because the provider is not configured.")

    try:
        session = create_tool_session(agent_tools.TOOL_DECLARATIONS, configuration.api_key, configuration.model)
    except GeminiProviderError:
        raise BriefingGenerationError("The AI provider could not answer this question.") from None

    all_sources: List[Dict[str, Any]] = []
    tool_call_log: List[Dict[str, Any]] = []
    try:
        response = session.send(message)
        for _step in range(MAX_TOOL_CALL_STEPS):
            calls = extract_function_calls(response)
            if not calls:
                break
            response_parts = []
            for call in calls:
                result = _execute_tool(conn, call["name"], call["args"])
                all_sources.extend(result.get("sources", []))
                tool_call_log.append({"tool": call["name"], "args": call["args"], "result_count": result.get("count", 0)})
                tool_response: Dict[str, Any] = {"count": result.get("count", 0), "sources": result.get("sources", [])}
                if "error" in result:
                    tool_response["error"] = result["error"]
                response_parts.append(build_function_response_part(call["name"], tool_response))
            response = session.send(response_parts)
        else:
            if extract_function_calls(response):
                return _build_response(TOOL_STEP_LIMIT_ANSWER, configuration.model, all_sources, tool_call_log)

        final_text = extract_text(response) or INSUFFICIENT_DATA_ANSWER
    except GeminiProviderError:
        raise BriefingGenerationError("The AI provider could not answer this question.") from None
    finally:
        session.close()

    return _build_response(final_text, configuration.model, all_sources, tool_call_log)
