from __future__ import annotations

import json
from typing import Any, Dict

from sqlalchemy.engine import Connection

from app.services.briefing_service import (
    BriefingConfiguration,
    BriefingConfigurationError,
    BriefingContextError,
    BriefingGenerationError,
    load_briefing_configuration,
)
from app.services.chat_context import assemble_chat_context
from app.services.gemini_provider import GeminiProviderError, generate_chat_answer


INSUFFICIENT_DATA_ANSWER = "The tracked competitive-intelligence data is insufficient to answer that question reliably. Try asking about tracked plan prices, device prices, promotions, or recorded changes."


def answer_chat_question(conn: Connection, message: str) -> Dict[str, Any]:
    try:
        context = assemble_chat_context(conn, message)
    except Exception:
        raise BriefingContextError("Competitive context could not be retrieved.") from None

    if not context["sufficient"]:
        return {
            "answer": INSUFFICIENT_DATA_ANSWER,
            "model": load_chat_configuration().model,
            "sources": [],
            "data_scope": context["data_scope"],
        }

    configuration = load_chat_configuration()
    if not configuration.api_key:
        raise BriefingConfigurationError("AI assistant is unavailable because the provider is not configured.")

    try:
        answer = generate_chat_answer(
            context["question"],
            json.dumps(context, default=str, separators=(",", ":")),
            configuration.api_key,
            configuration.model,
        )
    except GeminiProviderError:
        raise BriefingGenerationError("The AI provider could not answer this question.") from None

    return {
        "answer": answer,
        "model": configuration.model,
        "sources": context["sources"],
        "data_scope": context["data_scope"],
    }


def load_chat_configuration() -> BriefingConfiguration:
    return load_briefing_configuration()
