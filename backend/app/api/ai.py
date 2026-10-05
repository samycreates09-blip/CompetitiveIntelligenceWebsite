from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import Connection

from app.deps import get_db
from app.models.schemas import BriefingRequest, BriefingResponse
from app.services.briefing_service import (
    BriefingConfigurationError,
    BriefingContextError,
    BriefingGenerationError,
    create_briefing,
)

router = APIRouter(prefix="/api/v1/ai")


@router.post("/briefing", response_model=BriefingResponse)
def generate_ai_briefing(
    request: BriefingRequest,
    conn: Connection = Depends(get_db),
):
    del request
    try:
        return create_briefing(conn)
    except BriefingConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except BriefingContextError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except BriefingGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None