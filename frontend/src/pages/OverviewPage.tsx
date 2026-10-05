import { useMutation, useQueries, useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import type { DeviceHistoryEntry, Promotion } from '../lib/types';
import { DataState } from '../components/DataState';

function formatCurrency(value: number | null | undefined) {
  if (value == null) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function getLatestDevicePrice(history: DeviceHistoryEntry[] | undefined) {
  if (!history || history.length === 0) return null;
  const sorted = [...history].sort(
    (a, b) => new Date(b.source_snapshot_date).getTime() - new Date(a.source_snapshot_date).getTime(),
  );
  return sorted[0];
}

export default function OverviewPage() {
  const plansQuery = useQuery({
    queryKey: ['plans-current'],
    queryFn: () => api.getCurrentPlanOffers(),
  });

  const promotionsQuery = useQuery({
    queryKey: ['promotions-active'],
    queryFn: () => api.getPromotions({ active_only: true }),
  });

  const changesQuery = useQuery({
    queryKey: ['changes'],
    queryFn: () => api.getChanges(),
  });

  const devicesQuery = useQuery({
    queryKey: ['devices'],
    queryFn: () => api.getDevices(),
  });

  const briefingMutation = useMutation({ mutationFn: api.generateAiBriefing });

  const deviceIds = [7001, 6001, 5001];

  const deviceHistoryQueries = useQueries({
    queries: deviceIds.map((id) => ({
      queryKey: ['device-history', id],
      queryFn: () => api.getDeviceHistory(id),
      enabled: !!devicesQuery.data,
    })),
  });

  const deviceSummary = deviceIds
    .map((deviceId, index) => {
      const history = deviceHistoryQueries[index]?.data;
      const latest = getLatestDevicePrice(history);
      const device = devicesQuery.data?.find((entry) => entry.device_id === deviceId);

      if (!device || !latest) return null;

      return {
        deviceId,
        modelName: device.model_name,
        competitorName: device.competitor_name,
        latestPrice: latest.promo_price_usd ?? latest.retail_price_usd,
        promoTerms: latest.promotion_terms ?? 'Historical device price snapshot',
        sourceDate: latest.source_snapshot_date,
      };
    })
    .filter(Boolean) as Array<{
      deviceId: number;
      modelName: string;
      competitorName: string;
      latestPrice: number;
      promoTerms: string;
      sourceDate: string;
    }>;

  const activePromotions = (promotionsQuery.data ?? []).filter((promotion: Promotion) => {
    if (!promotion.start_date || !promotion.end_date) return true;
    const start = new Date(promotion.start_date).getTime();
    const end = new Date(promotion.end_date).getTime();
    const now = Date.now();
    return now >= start && now <= end;
  });

  const currentPlans = plansQuery.data ?? [];
  const currentChanges = changesQuery.data ?? [];

  // One headline plan per competitor, taken in the order the API already
  // returns them (by competitor_id) — no hardcoded competitor list, so this
  // adapts automatically if the tracked competitor set ever changes.
  const accentClasses = ['accent-blue', 'accent-purple', 'accent-amber', 'accent-green'];
  const headlinePlans = currentPlans.reduce<typeof currentPlans>((acc, plan) => {
    if (!acc.some((existing) => existing.competitor_id === plan.competitor_id)) acc.push(plan);
    return acc;
  }, []);

  if (plansQuery.isLoading || promotionsQuery.isLoading || changesQuery.isLoading || devicesQuery.isLoading) {
    return <DataState status="loading" message="Loading overview data" detail="Fetching current plan pricing, promotions and change events." />;
  }

  if (
    plansQuery.isError ||
    promotionsQuery.isError ||
    changesQuery.isError ||
    devicesQuery.isError ||
    !currentPlans.length
  ) {
    return (
      <DataState
        status="error"
        message="Overview data unavailable"
        detail="The local FastAPI backend is not responding with the expected seeded competitive data."
      />
    );
  }

  return (
    <div className="overview-page">
      <section className="page-header-row">
        <div>
          <p className="eyebrow">Overview</p>
          <h2>Competitive Intelligence Overview</h2>
        </div>
        <div className="page-note">Seeded competitor data • synthetic demo records</div>
      </section>

      <section className="competitor-grid" aria-label="Current competitor pricing">
        {headlinePlans.map((plan, index) => (
          <div key={plan.competitor_id} className={`competitor-card ${accentClasses[index % accentClasses.length]}`}>
            <span className="competitor-card-name">{plan.competitor_name}</span>
            <strong className="competitor-card-price">{formatCurrency(plan.price_usd)}</strong>
            <small className="competitor-card-plan">{plan.plan_name}</small>
          </div>
        ))}
      </section>

      <section className="panel" aria-labelledby="recent-changes-title">
        <div className="panel-header">
          <h3 id="recent-changes-title">Recent Competitive Changes</h3>
          <span className="panel-tag">Synthetic seeded changes</span>
        </div>
        <div className="stack-list compact">
          {currentChanges.length > 0 ? (
            currentChanges.slice(0, 4).map((change) => (
              <article key={change.change_id} className="mini-card">
                <div className="change-head">
                  <p className="plan-competitor">{change.competitor_name}</p>
                  <span className={`severity ${change.severity}`}>{change.severity}</span>
                </div>
                <h4>{change.summary_text}</h4>
                <small>{change.previous_value ?? '—'} → {change.new_value ?? '—'}</small>
                <div className="meta-line">
                  <span>{change.entity_type}</span>
                  <span>{change.effective_date}</span>
                </div>
              </article>
            ))
          ) : (
            <DataState status="empty" message="No seeded change data" detail="The synthetic competitor-changes dataset is empty." />
          )}
        </div>
      </section>

      <section className="panel ai-briefing-panel" aria-labelledby="ai-briefing-title">
        <div className="panel-header ai-briefing-header">
          <div>
            <p className="eyebrow">AI-generated · synthetic/demo data</p>
            <h3 id="ai-briefing-title">AI Competitive Briefing</h3>
            <p className="subtle-copy">Generated on request from structured local competitor records. No external market data is used.</p>
          </div>
          <button
            type="button"
            className="primary-button"
            onClick={() => briefingMutation.mutate()}
            disabled={briefingMutation.isPending}
          >
            {briefingMutation.isPending ? 'Generating…' : briefingMutation.data ? 'Generate again' : 'Generate AI Briefing'}
          </button>
        </div>
        {briefingMutation.isPending ? (
          <DataState status="loading" message="Generating briefing" detail="The backend is assembling trusted facts and requesting a concise Gemini response." />
        ) : null}
        {briefingMutation.isError ? (
          <DataState status="error" message="AI briefing unavailable" detail={`${briefingMutation.error.message} Check backend provider configuration and connectivity, then try again.`} />
        ) : null}
        {briefingMutation.data ? (
          <div className="ai-briefing-result">
            <div className="briefing-result-meta">
              <span className="ai-status-pill">AI-generated · {briefingMutation.data.model}</span>
              <span className="synthetic-status-pill">Synthetic/demo data</span>
              <span className={`evaluation-status ${briefingMutation.data.evaluation.status}`}>
                Evaluation: {briefingMutation.data.evaluation.status === 'pass' ? 'Checks passed' : 'Review recommended'}
              </span>
            </div>
            <p className="briefing-text">{briefingMutation.data.briefing}</p>
            <div className="briefing-scope">
              Context as of {briefingMutation.data.data_scope.as_of_date}: {briefingMutation.data.data_scope.plan_count} plans, {briefingMutation.data.data_scope.device_count} catalog devices ({briefingMutation.data.data_scope.device_price_history_count} with price history), {briefingMutation.data.data_scope.active_promotion_count} active promotions, and {briefingMutation.data.data_scope.synthetic_change_record_count} synthetic change records.
            </div>
            <div className="evaluation-grid" aria-label="Briefing evaluation results">
              {Object.entries(briefingMutation.data.evaluation.dimensions).map(([dimension, result]) => (
                <div className="evaluation-item" key={dimension}>
                  <span className={result.passed ? 'evaluation-check passed' : 'evaluation-check failed'} aria-hidden="true">{result.passed ? '✓' : '!'}</span>
                  <div><strong>{dimension.replace(/_/g, ' ')}</strong><small>{result.reason}</small></div>
                </div>
              ))}
            </div>
            <p className="evaluation-limitation">
              Human review required: {briefingMutation.data.evaluation.limitation}
            </p>
            <small className="generated-at">Generated {new Date(briefingMutation.data.generated_at).toLocaleString()}</small>
          </div>
        ) : null}
      </section>

      <section className="content-grid two-up">
        <div className="panel">
          <div className="panel-header">
            <h3>Current plan offers</h3>
            <span className="panel-tag">Current state</span>
          </div>

          <div className="stack-list">
            {currentPlans.map((plan) => (
              <article key={plan.plan_id} className="plan-row">
                <div>
                  <p className="plan-competitor">{plan.competitor_name}</p>
                  <h4>{plan.plan_name}</h4>
                  <div className="meta-line">
                    <span>{plan.plan_category}</span>
                    <span>{plan.plan_type}</span>
                  </div>
                </div>
                <div className="plan-price-box">
                  <strong>{formatCurrency(plan.price_usd)}</strong>
                  {plan.promotional_price_usd ? (
                    <small>{formatCurrency(plan.promotional_price_usd)} promo</small>
                  ) : (
                    <small>No promo price</small>
                  )}
                  {plan.promo_terms ? <em>{plan.promo_terms}</em> : null}
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h3>Latest observed device pricing</h3>
            <span className="panel-tag">Historical device-price API</span>
          </div>

          <div className="stack-list compact">
            {deviceSummary.length > 0 ? (
              deviceSummary.map((device) => (
                <article key={device.deviceId} className="device-row">
                  <div>
                    <p className="plan-competitor">{device.competitorName}</p>
                    <h4>{device.modelName}</h4>
                    <small>Observed on {device.sourceDate}</small>
                  </div>
                  <div className="plan-price-box">
                    <strong>{formatCurrency(device.latestPrice)}</strong>
                    <em>{device.promoTerms}</em>
                  </div>
                </article>
              ))
            ) : (
              <DataState status="empty" message="No device history available" />
            )}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h3>Active promotions</h3>
          <span className="panel-tag">Seeded offers</span>
        </div>

        <div className="stack-list compact">
          {activePromotions.length > 0 ? (
            activePromotions.map((promotion) => (
              <article key={promotion.promotion_id} className="mini-card">
                <p className="plan-competitor">{promotion.competitor_name}</p>
                <h4>{promotion.promotion_title}</h4>
                <small>{promotion.target_type}</small>
                <p>{promotion.description}</p>
                <div className="meta-line">
                  <span>{promotion.start_date}</span>
                  <span>→</span>
                  <span>{promotion.end_date}</span>
                </div>
              </article>
            ))
          ) : (
            <DataState status="empty" message="No active promotions" detail="The seeded promotion dataset does not currently show an active offer." />
          )}
        </div>
      </section>
    </div>
  );
}
