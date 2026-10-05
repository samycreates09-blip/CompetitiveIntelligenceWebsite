from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.engine import Connection

from app.services.retrieval_service import search_chunks

CITATION_GROUP_RE = re.compile(r"\[((?:[A-Z]+-[\w-]+)(?:\s*,\s*[A-Z]+-[\w-]+)*)\]")
CITATION_ID_RE = re.compile(r"[A-Z]+-[\w-]+")
INSUFFICIENT_PHRASES = (
    "does not contain enough information",
    "insufficient",
    "not contain that information",
    "tracked data does not",
    "don't have that information",
    "do not have that information",
)


@dataclass(frozen=True)
class RetrievalEvalCase:
    """One known question -> expected-source pair for deterministic retrieval scoring."""

    question: str
    expected_document_title: str
    competitor_ids: Optional[List[int]] = None


def evaluate_retrieval(
    conn: Connection,
    cases: List[RetrievalEvalCase],
    embed_fn: Callable[[str], List[float]],
    top_k: int = 3,
) -> Dict[str, Any]:
    """Deterministic retrieval hit-rate/recall: for each case, does the expected
    document appear anywhere in the top-k retrieved chunks? `embed_fn` is injected
    so tests can supply a mocked embedding function with zero live API calls."""
    case_results = []
    hits = 0
    for case in cases:
        query_vector = embed_fn(case.question)
        matches = search_chunks(conn, query_vector, top_k=top_k, competitor_ids=case.competitor_ids)
        retrieved_titles = [match["title"] for match in matches]
        hit = case.expected_document_title in retrieved_titles
        hits += int(hit)
        case_results.append({
            "question": case.question,
            "expected_document_title": case.expected_document_title,
            "retrieved_titles": retrieved_titles,
            "hit": hit,
            "top_distance": matches[0]["distance"] if matches else None,
        })
    recall_at_k = hits / len(cases) if cases else 1.0
    return {
        "recall_at_k": round(recall_at_k, 2),
        "hits": hits,
        "total": len(cases),
        "passed": recall_at_k >= 0.8,
        "cases": case_results,
    }


def evaluate_chat_groundedness(answer: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check that every cited source_id in the answer actually exists among the
    sources supplied to the model. An answer with zero citations is not flagged
    as ungrounded by this check alone (short/declined answers are legitimate);
    it only catches citations that point at facts never supplied, i.e. the
    class of hallucination a citation check can actually detect deterministically."""
    known_ids = {source["source_id"] for source in sources}
    citation_groups = CITATION_GROUP_RE.findall(answer)
    cited_ids = [citation for group in citation_groups for citation in CITATION_ID_RE.findall(group)]
    invalid_citations = sorted(set(citation for citation in cited_ids if citation not in known_ids))
    return {
        "cited_ids": sorted(set(cited_ids)),
        "invalid_citations": invalid_citations,
        "passed": not invalid_citations,
        "reason": (
            "All cited source IDs exist in the supplied context."
            if not invalid_citations
            else f"Answer cites source ID(s) not present in supplied context: {invalid_citations}."
        ),
    }


def evaluate_unsupported_refusal(answer: str) -> Dict[str, Any]:
    """For cases where retrieval found nothing relevant, confirm the answer says
    so instead of fabricating a response from outside knowledge."""
    declined = any(phrase in answer.lower() for phrase in INSUFFICIENT_PHRASES)
    return {
        "declined_to_guess": declined,
        "passed": declined,
        "reason": (
            "Answer states tracked data is insufficient."
            if declined
            else "Answer does not acknowledge missing context; risk of fabricated content."
        ),
    }
