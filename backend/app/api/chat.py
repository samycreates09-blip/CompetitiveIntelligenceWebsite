from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import Connection

from app.deps import get_db
from app.models.schemas import ChatRequest, ChatResponse
from app.services.agent_service import answer_chat_question_with_tools
from app.services.briefing_service import BriefingConfigurationError, BriefingContextError, BriefingGenerationError
from app.services.chat_service import answer_chat_question

router = APIRouter(prefix="/api/v1/ai")


@router.post("/chat", response_model=ChatResponse)
def chat(message: ChatRequest, conn: Connection = Depends(get_db)):
    """Deterministic-router chat path, retained for comparison and test coverage.
    The Ask AI UI calls /agent-chat (below); see docs/future_unstructured_data.md."""
    try:
        return answer_chat_question(conn, message.message.strip())
    except BriefingConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except BriefingContextError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except BriefingGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None


@router.post("/agent-chat", response_model=ChatResponse)
def agent_chat(message: ChatRequest, conn: Connection = Depends(get_db)):
    """Gemini selects and calls tools (backed by the same services as /chat
    and the RAG retrieval index) in a bounded loop, rather than a deterministic
    keyword router deciding which categories to retrieve."""
    try:
        return answer_chat_question_with_tools(conn, message.message.strip())
    except BriefingConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except BriefingGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
