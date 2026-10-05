import type {
  ChangeRecord,
  BriefingResponse,
  ChatResponse,
  Competitor,
  CurrentPlanOffer,
  DeviceHistoryEntry,
  DeviceRecord,
  HealthStatus,
  PlanHistoryEntry,
  Promotion,
  ObservationResult,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

type DateRange = { from_date?: string; to_date?: string; order?: 'asc' | 'desc' };

function queryString(params: Record<string, string | number | boolean | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') query.set(key, String(value));
  });
  return query.toString();
}

function withQuery(path: string, params: Record<string, string | number | boolean | undefined>) {
  const query = queryString(params);
  return query ? `${path}?${query}` : path;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API request failed for ${path}: ${response.status} ${errorBody}`);
  }

  return (await response.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const message = payload?.error?.message ?? `Request failed (${response.status}).`;
    throw new Error(message);
  }
  return (await response.json()) as T;
}

async function postJsonErrorSafe<T>(path: string, body: unknown): Promise<T> {
  return postJson<T>(path, body);
}

export const api = {
  getHealth: () => getJson<HealthStatus>('/health'),
  generateAiBriefing: () => postJson<BriefingResponse>('/api/v1/ai/briefing', {}),
  askAi: (message: string) => postJsonErrorSafe<ChatResponse>('/api/v1/ai/agent-chat', { message }),
  submitPlanPriceObservation: (observation: {
    plan_id: number;
    price_usd: number;
    promotional_price_usd?: number | null;
    promo_terms?: string;
    source_snapshot_date: string;
  }) => postJsonErrorSafe<ObservationResult>('/api/v1/observations/plan-price', observation),
  getCompetitors: () => getJson<Competitor[]>('/api/v1/competitors'),
  getCurrentPlanOffers: (params?: { competitor_id?: number; plan_category?: string; plan_type?: string }) =>
    getJson<CurrentPlanOffer[]>(withQuery('/api/v1/plans/current', params ?? {})),
  getPlanHistory: (planId: number, params?: DateRange) =>
    getJson<PlanHistoryEntry[]>(withQuery(`/api/v1/plans/${planId}/history`, params ?? {})),
  getDevices: (params?: { competitor_id?: number; manufacturer?: string; device_type?: string }) =>
    getJson<DeviceRecord[]>(withQuery('/api/v1/devices', params ?? {})),
  getDevice: (deviceId: number) => getJson<DeviceRecord>(`/api/v1/devices/${deviceId}`),
  getDeviceHistory: (deviceId: number, params?: DateRange) =>
    getJson<DeviceHistoryEntry[]>(withQuery(`/api/v1/devices/${deviceId}/history`, params ?? {})),
  getPromotions: (params?: {
    competitor_id?: number;
    target_type?: string;
    start_date?: string;
    end_date?: string;
    active_only?: boolean;
  }) => getJson<Promotion[]>(withQuery('/api/v1/promotions', params ?? {})),
  getPromotion: (promotionId: number) => getJson<Promotion>(`/api/v1/promotions/${promotionId}`),
  getChanges: (params?: {
    competitor_id?: number;
    change_type?: string;
    entity_type?: string;
    severity?: string;
    record_origin?: string;
    from_date?: string;
    to_date?: string;
  }) => getJson<ChangeRecord[]>(withQuery('/api/v1/changes', params ?? {})),
  getChange: (changeId: number) => getJson<ChangeRecord>(`/api/v1/changes/${changeId}`),
};
