from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy.engine import Connection

from app.config import settings
from app.services.briefing_context import assemble_briefing_context
from app.services.briefing_evaluation import evaluate_briefing
from app.services.gemini_provider import GeminiProviderError, generate_briefing


class BriefingConfigurationError(Exception):
    pass


class BriefingContextError(Exception):
    pass


class BriefingGenerationError(Exception):
    pass


@dataclass(frozen=True)
class BriefingConfiguration:
    api_key: str = field(repr=False)
    model: str


def load_briefing_configuration() -> BriefingConfiguration:
    """Return runtime provider configuration with the credential excluded from repr."""
    return BriefingConfiguration(api_key=settings.gemini_api_key, model=settings.gemini_model)


def create_briefing(conn: Connection) -> Dict[str, Any]:
    try:
        context = assemble_briefing_context(conn)
    except Exception:
        raise BriefingContextError("Competitive context could not be retrieved.") from None

    configuration = load_briefing_configuration()
    if not configuration.api_key:
        raise BriefingConfigurationError("AI briefing is unavailable because the provider is not configured.")

    try:
        briefing = generate_briefing(
            json.dumps(context, default=str, separators=(",", ":")),
            configuration.api_key,
            configuration.model,
        )
    except GeminiProviderError:
        raise BriefingGenerationError("The AI provider could not generate a briefing.") from None

    return {
        "briefing": briefing,
        "model": configuration.model,
        "generated_at": datetime.now(timezone.utc),
        "data_scope": context["data_scope"],
        "evaluation": evaluate_briefing(briefing, context),
    }