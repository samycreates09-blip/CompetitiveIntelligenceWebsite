from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import Connection

from app.deps import get_write_db
from app.models.schemas import (
    DevicePriceObservationRequest,
    ObservationResponse,
    PlanPriceObservationRequest,
    PromotionObservationRequest,
)
from app.services.change_detection_service import (
    submit_device_price_observation,
    submit_plan_price_observation,
    submit_promotion_observation,
)

router = APIRouter(prefix="/api/v1/observations")


def _submit(operation, conn: Connection, request):
    try:
        return operation(conn, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.post("/plan-price", response_model=ObservationResponse)
def observe_plan_price(request: PlanPriceObservationRequest, conn: Connection = Depends(get_write_db)):
    return _submit(submit_plan_price_observation, conn, request)


@router.post("/device-price", response_model=ObservationResponse)
def observe_device_price(request: DevicePriceObservationRequest, conn: Connection = Depends(get_write_db)):
    return _submit(submit_device_price_observation, conn, request)


@router.post("/promotion", response_model=ObservationResponse)
def observe_promotion(request: PromotionObservationRequest, conn: Connection = Depends(get_write_db)):
    return _submit(submit_promotion_observation, conn, request)
