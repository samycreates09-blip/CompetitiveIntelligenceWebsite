from __future__ import annotations

import re

from google.genai.errors import APIError


def safe_model_name(model: str) -> str:
    if isinstance(model, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,100}", model):
        return model
    return "<invalid-model-name>"


def safe_api_error_message(error: APIError) -> str:
    """Sanitize the SDK's provider message before emitting it to application logs."""
    message = getattr(error, "message", "")
    if not isinstance(message, str):
        return "Provider returned an error without a readable message."
    message = re.sub(
        r"(?i)(authorization\s*[:=]\s*(?:bearer|basic)\s+)[^\s,;]+",
        r"\1[REDACTED]",
        message,
    )
    message = re.sub(
        r"(?i)(?:api[_-]?key|key)\s*[:=]\s*[\"']?[^\s\"',;&]+",
        "credential=[REDACTED]",
        message,
    )
    message = re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[REDACTED]", message)
    message = re.sub(r"\b[A-Za-z0-9_-]{48,}\b", "[REDACTED]", message)
    message = " ".join(message.split())
    return message[:300] or "Provider returned an empty error message."


def safe_status(error: Exception) -> int | None:
    status = getattr(error, "code", None)
    if not isinstance(status, int):
        status = getattr(error, "status_code", None)
    return status if isinstance(status, int) and 100 <= status <= 599 else None
