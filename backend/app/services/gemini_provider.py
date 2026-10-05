from __future__ import annotations

import logging
import re

from google import genai
from google.genai.errors import APIError
from google.genai import types

from app.services.provider_safety import safe_api_error_message, safe_model_name, safe_status


SYSTEM_INSTRUCTION = """You are a concise competitive-intelligence analyst writing for product, pricing, and business stakeholders.
Use ONLY the supplied structured context. Do not invent competitors, prices, promotions, devices, dates, or changes. Distinguish facts from interpretation, and omit any claim the context cannot support. Identify important competitive movements only when supported by supplied facts. If you cite or use any synthetic_seeded_change fact, explicitly identify that change in the same bullet as synthetic, seeded, or demo data, and state that it was not automatically detected. Do not apply this qualification to ordinary plan, device, or promotion facts. Do not claim access to external or current market information.
Return a short, useful business briefing with a few concise bullets and a practical implication. Cite every factual bullet with one or more exact supplied fact IDs using the form [F1]. Keep the response between 40 and 250 words. Do not repeat raw JSON."""

CHAT_SYSTEM_INSTRUCTION = """You are the Boost Competitive Intelligence Assistant for product managers.
Answer the user's question using ONLY the supplied context. Exact prices, dates, and historical movements must come from the structured records in that context, never from document excerpts or outside/current market knowledge. Document excerpts (sources marked document_chunk / synthetic_document) are retrieved passages from synthetic demo competitor documents (promotion terms, eligibility conditions, plan descriptions); use them only for the qualitative conditions, eligibility, and terms they actually state, and label anything drawn from them as coming from a synthetic/demo document. If the supplied context — structured or document-based — does not contain the specific detail the question asks for, say plainly that the tracked data does not contain enough information instead of guessing or filling the gap with general knowledge. Never invent missing facts. Distinguish current observed facts from interpretation. Cite factual statements using the exact source_id strings supplied in the context. Sources marked synthetic_seeded are demo change records, not live or automatically detected changes; label them as synthetic/demo when discussing them. Keep the answer concise and conversational."""

AGENT_SYSTEM_INSTRUCTION = """You are the Boost Competitive Intelligence Assistant for product managers, with access to tools backed by the tracked PostgreSQL database and a retrieval index of synthetic demo competitor documents.
Call tools to gather the evidence you need before answering; never answer from memory or general/outside knowledge. You may call more than one tool, including the same tool for different competitors, when a question needs it — for example, comparing two competitors' prices, or combining a price with that competitor's promotion terms.
Tool results are the only source of truth. Never state a price, date, promotion detail, competitor fact, or historical change that is not present in a tool's returned evidence. If the tools you called do not return enough evidence to answer the question, say plainly that the tracked data does not contain enough information instead of guessing.
Evidence returned by search_competitor_documents comes from synthetic/demo competitor documents, not live or scraped sources; label any claim drawn from it as coming from a synthetic/demo document. Likewise, a change record whose origin is synthetic_seeded is a demo record, not a live or automatically detected change; label it as such if you discuss it.
Once you have enough evidence, stop calling tools and give a concise, conversational final answer. Cite the exact source_id values returned by the tools, for example [PLAN-201] or [DOC-3-1]."""


class GeminiProviderError(Exception):
    """Safe provider failure that never carries secret configuration values."""


logger = logging.getLogger(__name__)


def _log_provider_failure(exc: Exception, safe_model: str) -> None:
    # Never log repr(exc), exc_info, headers, or configuration. APIError.message
    # is useful for model/auth/quota diagnosis after credential-pattern cleanup.
    if isinstance(exc, APIError):
        safe_message = safe_api_error_message(exc)
    else:
        safe_message = "Provider client or transport failed before an API response."
    logger.warning(
        "Gemini request failed model=%s exception_type=%s http_status=%s message=%s",
        safe_model,
        re.sub(r"[^A-Za-z0-9_.-]", "", type(exc).__name__)[:80] or "UnknownError",
        safe_status(exc),
        safe_message,
    )


def _generate_text(contents: str, system_instruction: str, api_key: str, model: str) -> str:
    if not api_key:
        raise GeminiProviderError("Gemini is not configured.")
    safe_model = safe_model_name(model)
    client = None
    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                max_output_tokens=650,
            ),
        )
        text = response.text
        if not isinstance(text, str) or not text.strip():
            raise GeminiProviderError("Gemini returned an empty or malformed response.")
        return text.strip()
    except GeminiProviderError:
        raise
    except Exception as exc:
        _log_provider_failure(exc, safe_model)
        raise GeminiProviderError("Gemini could not generate a briefing.") from None
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                # Closing an SDK client must not mask generation results/errors.
                pass


def generate_briefing(context_json: str, api_key: str, model: str) -> str:
    return _generate_text(
        "Produce a competitive briefing using this context only:\n" + context_json,
        SYSTEM_INSTRUCTION,
        api_key,
        model,
    )


def generate_chat_answer(question: str, context_json: str, api_key: str, model: str) -> str:
    contents = "User question:\n{}\n\nTrusted structured context:\n{}".format(question, context_json)
    return _generate_text(contents, CHAT_SYSTEM_INSTRUCTION, api_key, model)


class GeminiToolSession:
    """A multi-turn function-calling session. All raw SDK interaction for tool
    calling is confined here, mirroring how `_generate_text` is the sole
    SDK touchpoint for single-turn generation."""

    def __init__(self, client: "genai.Client", chat, safe_model: str):
        self._client = client
        self._chat = chat
        self._safe_model = safe_model

    def send(self, message):
        try:
            return self._chat.send_message(message)
        except Exception as exc:
            _log_provider_failure(exc, self._safe_model)
            raise GeminiProviderError("Gemini tool-calling turn failed.") from None

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            # Closing an SDK client must not mask the session's results/errors.
            pass


def create_tool_session(
    tool_declarations: list[dict],
    api_key: str,
    model: str,
    system_instruction: str = AGENT_SYSTEM_INSTRUCTION,
) -> GeminiToolSession:
    if not api_key:
        raise GeminiProviderError("Gemini is not configured.")
    safe_model = safe_model_name(model)
    tool = types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name=declaration["name"],
            description=declaration["description"],
            parameters_json_schema=declaration["parameters"],
        )
        for declaration in tool_declarations
    ])
    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        chat = client.chats.create(
            model=model,
            config=types.GenerateContentConfig(
                tools=[tool],
                system_instruction=system_instruction,
                temperature=0.1,
                max_output_tokens=700,
            ),
        )
    except Exception as exc:
        _log_provider_failure(exc, safe_model)
        raise GeminiProviderError("Gemini tool-calling session could not be created.") from None
    return GeminiToolSession(client, chat, safe_model)


def extract_function_calls(response) -> list[dict]:
    """Return [{"name": ..., "args": {...}}, ...] for every function call in
    the response's first candidate (there can be more than one per turn)."""
    content = getattr(response.candidates[0], "content", None) if response.candidates else None
    parts = getattr(content, "parts", None) or []
    calls = []
    for part in parts:
        call = getattr(part, "function_call", None)
        if call is not None:
            calls.append({"name": call.name, "args": dict(call.args or {})})
    return calls


def extract_text(response) -> str:
    text = getattr(response, "text", None)
    return text.strip() if isinstance(text, str) and text.strip() else ""


def build_function_response_part(name: str, response: dict):
    return types.Part.from_function_response(name=name, response=response)