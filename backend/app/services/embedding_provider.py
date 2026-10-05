from __future__ import annotations

import logging
import re
from typing import List

from google import genai
from google.genai.errors import APIError
from google.genai import types

from app.services.provider_safety import safe_api_error_message, safe_model_name, safe_status


class EmbeddingProviderError(Exception):
    """Safe provider failure that never carries secret configuration values."""


logger = logging.getLogger(__name__)


def embed_texts(
    texts: List[str],
    api_key: str,
    model: str,
    task_type: str,
    output_dimensionality: int = 768,
) -> List[List[float]]:
    """Embed a batch of texts with the configured Gemini embedding model.

    `task_type` should be "RETRIEVAL_DOCUMENT" when embedding chunks at ingestion
    time and "RETRIEVAL_QUERY" when embedding a user question, matching the
    asymmetric retrieval optimization the embedding model supports.
    """
    if not api_key:
        raise EmbeddingProviderError("Embedding provider is not configured.")
    if not texts:
        return []
    safe_model = safe_model_name(model)
    client = None
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.embed_content(
            model=model,
            contents=texts,
            config=types.EmbedContentConfig(
                output_dimensionality=output_dimensionality,
                task_type=task_type,
            ),
        )
        embeddings = response.embeddings or []
        vectors = [list(embedding.values) for embedding in embeddings]
        if len(vectors) != len(texts) or any(not vector for vector in vectors):
            raise EmbeddingProviderError("Embedding provider returned a malformed response.")
        return vectors
    except EmbeddingProviderError:
        raise
    except Exception as exc:
        if isinstance(exc, APIError):
            safe_message = safe_api_error_message(exc)
        else:
            safe_message = "Provider client or transport failed before an API response."
        logger.warning(
            "Embedding request failed model=%s exception_type=%s http_status=%s message=%s",
            safe_model,
            re.sub(r"[^A-Za-z0-9_.-]", "", type(exc).__name__)[:80] or "UnknownError",
            safe_status(exc),
            safe_message,
        )
        raise EmbeddingProviderError("Embeddings could not be generated.") from None
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
