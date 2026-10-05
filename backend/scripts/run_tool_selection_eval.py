"""Run the tool-selection evaluation against the real agent (real Gemini tool
calls, real PostgreSQL/pgvector retrieval). This is a manual validation step,
like run_rag_evaluation.py, not part of the pytest suite:

    cd backend && source ../.venv/bin/activate && python -m scripts.run_tool_selection_eval
"""
from __future__ import annotations

from app.database import engine
from app.services.tool_selection_eval import ToolSelectionCase, evaluate_tool_selection

CASES = [
    ToolSelectionCase("What is T-Mobile Essentials currently priced at?", frozenset({"get_current_plan_prices"})),
    ToolSelectionCase("What is Verizon's current plan price?", frozenset({"get_current_plan_prices"})),
    ToolSelectionCase("How has T-Mobile Essentials pricing changed?", frozenset({"get_plan_price_history"})),
    ToolSelectionCase("Has the Boost Unlimited Plan price changed over time?", frozenset({"get_plan_price_history"})),
    ToolSelectionCase("Has Verizon changed iPhone 15 Pro pricing?", frozenset({"get_device_price_history"})),
    ToolSelectionCase("What promotions does Verizon have?", frozenset({"get_promotions"})),
    ToolSelectionCase("What are Verizon's promotion conditions?", frozenset({"search_competitor_documents", "get_promotions"})),
    ToolSelectionCase("What changed recently?", frozenset({"get_recent_changes"})),
    ToolSelectionCase("What changed for Boost recently?", frozenset({"get_recent_changes"})),
    ToolSelectionCase("Summarize T-Mobile's promotion terms.", frozenset({"search_competitor_documents"})),
    ToolSelectionCase("Does Verizon's trade-in bonus require a new line?", frozenset({"search_competitor_documents"})),
    ToolSelectionCase(
        "Compare T-Mobile's recent price change with Boost and explain T-Mobile's promotion conditions.",
        frozenset({"get_recent_changes", "get_plan_price_history", "get_current_plan_prices", "search_competitor_documents"}),
        min_distinct_tools=2,
    ),
]


def main() -> None:
    with engine.connect() as conn:
        report = evaluate_tool_selection(conn, CASES)

    print(f"Tool-selection accuracy: {report['correct']}/{report['total']} ({report['accuracy']}), passed={report['passed']}")
    for case in report["cases"]:
        mark = "PASS" if case["passed"] else "FAIL"
        print(f"  [{mark}] {case['question']}")
        print(f"         expected one of: {case['expected_tools']}")
        print(f"         tools used: {case['tools_used']}")
        if not case["passed"]:
            print(f"         tool_selection_ok={case['tool_selection_ok']} execution_ok={case['execution_ok']} rag_ok={case['rag_ok']} grounded_ok={case['grounded_ok']}")
            print(f"         answer: {case['answer'][:200]}")


if __name__ == "__main__":
    main()
