from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str
    service: str
    database: str


class CompetitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    competitor_id: int
    name: str
    short_name: str
    brand_type: str
    is_active: bool


class PlanCurrentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: int
    competitor_id: int
    competitor_name: str
    plan_name: str
    plan_category: str
    plan_type: str
    price_usd: Optional[float] = None
    promotional_price_usd: Optional[float] = None
    promo_terms: Optional[str] = None
    effective_date: Optional[date] = None
    captured_at: Optional[datetime] = None


class PlanHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: int
    competitor_id: int
    competitor_name: str
    plan_name: str
    effective_date: Optional[date] = None
    price_usd: float
    promotional_price_usd: Optional[float] = None
    promo_terms: Optional[str] = None
    captured_at: datetime
    source_snapshot_date: date


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: int
    competitor_id: int
    competitor_name: str
    manufacturer: str
    model_name: str
    device_type: str
    storage_variant: Optional[str] = None
    color: Optional[str] = None
    is_active: bool


class DeviceHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: int
    competitor_id: int
    competitor_name: str
    manufacturer: str
    model_name: str
    effective_date: Optional[date] = None
    retail_price_usd: float
    promo_price_usd: Optional[float] = None
    promotion_terms: Optional[str] = None
    financing_terms: Optional[str] = None
    captured_at: datetime
    source_snapshot_date: date


class PromotionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    promotion_id: int
    competitor_id: int
    competitor_name: str
    promotion_title: str
    promotion_type: str
    description: str
    target_type: str
    target_plan_id: Optional[int] = None
    target_device_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    captured_at: datetime


class ChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    change_id: int
    competitor_id: int
    competitor_name: str
    change_type: str
    entity_type: str
    entity_id: int
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    effective_date: Optional[date] = None
    severity: str
    summary_text: str
    source_snapshot_from: Optional[date] = None
    source_snapshot_to: Optional[date] = None
    record_origin: str = "synthetic_seeded"
    change_detected_at: datetime


class BriefingRequest(BaseModel):
    pass


class EvaluationDimension(BaseModel):
    score: float
    passed: bool
    reason: str


class BriefingEvaluation(BaseModel):
    status: str
    dimensions: Dict[str, EvaluationDimension]
    manual_review_required: bool
    limitation: str


class BriefingDataScope(BaseModel):
    competitors: List[str]
    plan_count: int
    device_count: int
    device_price_history_count: int
    active_promotion_count: int
    synthetic_change_record_count: int
    synthetic_change_records: bool
    as_of_date: date


class BriefingResponse(BaseModel):
    briefing: str
    model: str
    generated_at: datetime
    data_scope: BriefingDataScope
    evaluation: BriefingEvaluation


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ChatSource(BaseModel):
    source_id: str
    category: str
    summary: str
    record_origin: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    model: str
    sources: List[ChatSource]
    data_scope: Dict[str, Any]


class PlanPriceObservationRequest(BaseModel):
    plan_id: int = Field(gt=0)
    price_usd: float = Field(ge=0)
    promotional_price_usd: Optional[float] = Field(default=None, ge=0)
    promo_terms: Optional[str] = None
    effective_date: Optional[date] = None
    source_snapshot_date: date = Field(default_factory=date.today)


class DevicePriceObservationRequest(BaseModel):
    device_id: int = Field(gt=0)
    retail_price_usd: float = Field(ge=0)
    promo_price_usd: Optional[float] = Field(default=None, ge=0)
    promotion_terms: Optional[str] = None
    financing_terms: Optional[str] = None
    effective_date: Optional[date] = None
    source_snapshot_date: date = Field(default_factory=date.today)


class PromotionObservationRequest(BaseModel):
    competitor_id: int = Field(gt=0)
    promotion_title: str = Field(min_length=1, max_length=255)
    promotion_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    target_type: str = Field(pattern="^(plan|device|bundle)$")
    target_plan_id: Optional[int] = Field(default=None, gt=0)
    target_device_id: Optional[int] = Field(default=None, gt=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    source_snapshot_date: date = Field(default_factory=date.today)


class MockEmailAlert(BaseModel):
    provider: str = "mock"
    status: str = "recorded_not_sent"
    recipient: str
    subject: str
    body: str


class ObservationResponse(BaseModel):
    observation_type: str
    observation_appended: bool
    change_detected: bool
    change: Optional[ChangeOut] = None
    alert_important: bool = False
    email_alert: Optional[MockEmailAlert] = None
