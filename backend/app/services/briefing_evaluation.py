from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List


CITATION_GROUP_RE = re.compile(r"\[((?:F\d+)(?:\s*,\s*F\d+)*)\]")
CITATION_ID_RE = re.compile(r"F\d+")
MONEY_RE = re.compile(
    r"(?:\$\s*((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)|"
    r"(?<![\w])((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(?:USD|dollars?)\b)",
    re.IGNORECASE,
)
SYNTHETIC_QUALIFIER_RE = re.compile(r"\b(?:synthetic|seeded|demo)\b", re.IGNORECASE)


def _amounts(text: str) -> set:
    amounts = set()
    for match in MONEY_RE.findall(text):
        raw_value = next((value for value in match if value), None)
        if raw_value is None:
            continue
        try:
            amounts.add(Decimal(raw_value.replace(",", "")).normalize())
        except InvalidOperation:
            continue
    return amounts


def _record_discount_amounts(context: Dict[str, Any]) -> set:
    """Accept a discount only when retail and promo prices coexist on one record."""
    differences = set()
    records = [
        plan.get("current", {})
        for plan in context.get("plans", [])
    ]
    records.extend(
        device.get("latest_price", {})
        for device in context.get("latest_device_prices", [])
    )
    for record in records:
        retail = record.get("price_usd", record.get("retail_price_usd"))
        promo = record.get("promotional_price_usd", record.get("promo_price_usd"))
        if retail is None or promo is None:
            continue
        try:
            difference = (Decimal(str(retail)) - Decimal(str(promo))).normalize()
        except InvalidOperation:
            continue
        if difference > 0:
            differences.add(difference)
    return differences


def evaluate_briefing(briefing: str, context: Dict[str, Any]) -> Dict[str, Any]:
    facts = context.get("facts", [])
    fact_ids = {fact["id"] for fact in facts}
    citation_groups = CITATION_GROUP_RE.findall(briefing)
    citations = [citation for group in citation_groups for citation in CITATION_ID_RE.findall(group)]
    valid_citations = [citation for citation in citations if citation in fact_ids]
    invalid_citations = sorted(set(citation for citation in citations if citation not in fact_ids))

    lines = [line.strip() for line in briefing.splitlines() if line.strip()]
    claim_lines = [line for line in lines if not (line.startswith("#") or (len(line) < 60 and line.endswith(":")))]
    cited_claim_lines = [line for line in claim_lines if CITATION_GROUP_RE.search(line)]
    groundedness = len(cited_claim_lines) / len(claim_lines) if claim_lines else 0.0

    context_text = " ".join(fact.get("text", "") for fact in facts)
    supported_money = _amounts(context_text) | _record_discount_amounts(context)
    output_money = _amounts(briefing)
    unsupported_money = sorted(output_money - supported_money)

    known_competitors = set(context.get("data_scope", {}).get("competitors", []))
    candidate_competitors = {"Boost Mobile", "T-Mobile", "Verizon"}
    unsupported_competitors = sorted(
        name for name in candidate_competitors
        if re.search(r"\b{}\b".format(re.escape(name)), briefing, re.IGNORECASE) and name not in known_competitors
    )

    changes = context.get("synthetic_seeded_change_records", [])
    important_change_ids = {item["fact_id"] for item in changes}
    covered_change_ids = important_change_ids.intersection(valid_citations)
    coverage = len(covered_change_ids) / len(important_change_ids) if important_change_ids else 1.0
    synthetic_fact_ids = {
        fact["id"] for fact in facts if fact.get("category") == "synthetic_seeded_change"
    }
    synthetic_claim_lines = [
        line for line in claim_lines
        if synthetic_fact_ids.intersection(CITATION_ID_RE.findall(line))
    ]
    unqualified_synthetic_lines = [
        line for line in synthetic_claim_lines if not SYNTHETIC_QUALIFIER_RE.search(line)
    ]
    words = re.findall(r"\b[\w$.,%-]+\b", briefing)
    length_and_format_ok = 40 <= len(words) <= 250 and bool(claim_lines)
    instruction_following = length_and_format_ok and not unqualified_synthetic_lines
    factual_accuracy = not unsupported_money and not unsupported_competitors
    hallucination_risk = bool(unsupported_money or unsupported_competitors or invalid_citations)
    grounded_pass = groundedness >= 0.75 and not invalid_citations
    coverage_pass = coverage >= 0.5
    dimensions = {
        "groundedness": {
            "score": round(groundedness, 2), "passed": grounded_pass,
            "reason": "{}/{} content lines cite supplied fact IDs; {} invalid citations.".format(
                len(cited_claim_lines), len(claim_lines), len(invalid_citations)
            ),
        },
        "factual_accuracy": {
            "score": 1.0 if factual_accuracy else 0.0, "passed": factual_accuracy,
            "reason": "No unsupported currency amounts or competitor names." if factual_accuracy else
            "Unsupported amounts: {}; competitor names: {}.".format(unsupported_money, unsupported_competitors),
        },
        "hallucination_risk": {
            "score": 0.0 if not hallucination_risk else 1.0, "passed": not hallucination_risk,
            "reason": "No unsupported checked entities, amounts, or citations detected." if not hallucination_risk else
            "Detected unsupported amounts, names, or citation IDs; review before use.",
        },
        "instruction_following": {
            "score": 1.0 if instruction_following else 0.0, "passed": instruction_following,
            "reason": (
                "Briefing contains {} words (target 40–250); synthetic seeded change claims are explicitly qualified."
            ).format(len(words)) if instruction_following else (
                "Briefing contains {} words (target 40–250); {} cited synthetic seeded change claim(s) lack a synthetic/seeded/demo qualifier."
            ).format(len(words), len(unqualified_synthetic_lines)),
        },
        "important_fact_coverage": {
            "score": round(coverage, 2), "passed": coverage_pass,
            "reason": "Cited {} of {} synthetic seeded change records.".format(len(covered_change_ids), len(important_change_ids)),
        },
    }
    return {
        "status": "pass" if all(dimension["passed"] for dimension in dimensions.values()) else "review",
        "dimensions": dimensions,
        "manual_review_required": True,
        "limitation": "Heuristic checks verify citations and selected factual tokens; they do not establish semantic entailment. Human review is required.",
    }