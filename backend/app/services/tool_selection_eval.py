from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, FrozenSet, List

from sqlalchemy.engine import Connection

from app.services.agent_service import answer_chat_question_with_tools
from app.services.rag_evaluation import evaluate_chat_groundedness

AnswerFn = Callable[[Connection, str], Dict[str, Any]]


@dataclass(frozen=True)
class ToolSelectionCase:
    question: str
    expected_tools: FrozenSet[str]
    # Most questions only need one matching tool; the multi-step example needs
    # at least this many *distinct* tools actually called to count as a pass.
    min_distinct_tools: int = 1


def evaluate_tool_selection(
    conn: Connection,
    cases: List[ToolSelectionCase],
    answer_fn: AnswerFn = answer_chat_question_with_tools,
) -> Dict[str, Any]:
    """Run each case through the real (or injected) agent and score five things:
    tool-selection accuracy, whether enough distinct tools were used, tool
    execution success (evidence came back or the model correctly declined),
    RAG retrieval when search_competitor_documents was expected, and citation
    groundedness of the final answer. `answer_fn` is injected so a live run
    (scripts/run_tool_selection_eval.py) and a mocked test can share this logic."""
    results = []
    correct = 0
    for case in cases:
        try:
            response = answer_fn(conn, case.question)
        except Exception as exc:
            # A transient provider error (e.g. a 503) shouldn't abort the whole
            # evaluation run; record it as a failed case and keep going.
            results.append({
                "question": case.question,
                "expected_tools": sorted(case.expected_tools),
                "tools_used": [],
                "tool_selection_ok": False,
                "execution_ok": False,
                "rag_ok": False,
                "grounded_ok": False,
                "passed": False,
                "answer": "ERROR: {}".format(exc),
            })
            continue
        tools_used = set(response["data_scope"].get("tools_used", []))
        sources = response.get("sources", [])
        answer = response.get("answer", "")

        tool_selection_ok = bool(tools_used & case.expected_tools) and len(tools_used) >= case.min_distinct_tools
        execution_ok = bool(sources) or "insufficient" in answer.lower() or "does not contain" in answer.lower()
        rag_ok = True
        if "search_competitor_documents" in case.expected_tools:
            rag_ok = any(source.get("category") == "document_chunk" for source in sources)
        grounded = evaluate_chat_groundedness(answer, sources)
        case_pass = tool_selection_ok and execution_ok and rag_ok and grounded["passed"]
        correct += int(case_pass)
        results.append({
            "question": case.question,
            "expected_tools": sorted(case.expected_tools),
            "tools_used": sorted(tools_used),
            "tool_selection_ok": tool_selection_ok,
            "execution_ok": execution_ok,
            "rag_ok": rag_ok,
            "grounded_ok": grounded["passed"],
            "passed": case_pass,
            "answer": answer,
        })
    total = len(cases)
    return {
        "correct": correct,
        "total": total,
        "accuracy": round(correct / total, 2) if total else 1.0,
        "passed": (correct / total >= 0.8) if total else True,
        "cases": results,
    }
