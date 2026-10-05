export type Competitor = {
  competitor_id: number;
  name: string;
  short_name: string;
  brand_type: string;
  is_active: boolean;
};

export type CurrentPlanOffer = {
  plan_id: number;
  competitor_id: number;
  competitor_name: string;
  plan_name: string;
  plan_category: string;
  plan_type: string;
  price_usd: number | null;
  promotional_price_usd: number | null;
  promo_terms: string | null;
  effective_date: string | null;
  captured_at: string;
};

export type PlanHistoryEntry = {
  plan_id: number;
  competitor_id: number;
  competitor_name: string;
  plan_name: string;
  effective_date: string;
  price_usd: number;
  promotional_price_usd: number | null;
  promo_terms: string | null;
  captured_at: string;
  source_snapshot_date: string;
};

export type DeviceRecord = {
  device_id: number;
  competitor_id: number;
  competitor_name: string;
  manufacturer: string;
  model_name: string;
  device_type: string;
  storage_variant: string | null;
  color: string | null;
  is_active: boolean;
};

export type DeviceHistoryEntry = {
  device_id: number;
  competitor_id: number;
  competitor_name: string;
  manufacturer: string;
  model_name: string;
  effective_date: string;
  retail_price_usd: number;
  promo_price_usd: number | null;
  promotion_terms: string | null;
  financing_terms: string | null;
  captured_at: string;
  source_snapshot_date: string;
};

export type Promotion = {
  promotion_id: number;
  competitor_id: number;
  competitor_name: string;
  promotion_title: string;
  promotion_type: string;
  description: string;
  target_type: string;
  target_plan_id: number | null;
  target_device_id: number | null;
  start_date: string | null;
  end_date: string | null;
  captured_at: string;
};

export type ChangeRecord = {
  change_id: number;
  competitor_id: number;
  competitor_name: string;
  change_type: string;
  entity_type: string;
  entity_id: number;
  previous_value: string | null;
  new_value: string | null;
  effective_date: string;
  severity: 'low' | 'medium' | 'high';
  summary_text: string;
  source_snapshot_from: string | null;
  source_snapshot_to: string | null;
  record_origin: 'synthetic_seeded' | 'system_detected';
  change_detected_at: string;
};

export type ChatSource = {
  source_id: string;
  category: string;
  summary: string;
  record_origin: string | null;
};

export type ChatResponse = {
  answer: string;
  model: string;
  sources: ChatSource[];
  data_scope: {
    requested_categories?: string[];
    available_categories?: string[];
    competitors?: string[];
    source_count: number;
    synthetic_change_records_included: boolean;
    document_sources_included: boolean;
    tools_used?: string[];
    tool_call_count?: number;
  };
};

export type ObservationResult = {
  observation_type: string;
  observation_appended: boolean;
  change_detected: boolean;
  change: ChangeRecord | null;
  alert_important: boolean;
  email_alert: {
    provider: 'mock';
    status: 'recorded_not_sent';
    recipient: string;
    subject: string;
    body: string;
  } | null;
};

export type HealthStatus = {
  status: string;
  service: string;
  database: string;
};

export type BriefingEvaluationDimension = {
  score: number;
  passed: boolean;
  reason: string;
};

export type BriefingResponse = {
  briefing: string;
  model: string;
  generated_at: string;
  data_scope: {
    competitors: string[];
    plan_count: number;
    device_count: number;
    device_price_history_count: number;
    active_promotion_count: number;
    synthetic_change_record_count: number;
    synthetic_change_records: boolean;
    as_of_date: string;
  };
  evaluation: {
    status: string;
    dimensions: Record<string, BriefingEvaluationDimension>;
    manual_review_required: boolean;
    limitation: string;
  };
};
