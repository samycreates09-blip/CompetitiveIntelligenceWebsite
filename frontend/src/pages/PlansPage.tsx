import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { DataState } from '../components/DataState';
import { PageHeader } from '../components/PageHeader';
import { PriceHistoryChart } from '../components/PriceHistoryChart';
import { api } from '../lib/api';
import { formatCurrency, formatDate } from '../lib/format';

export default function PlansPage() {
  const [competitorId, setCompetitorId] = useState('all');
  const [category, setCategory] = useState('all');
  const [planType, setPlanType] = useState('all');
  const [expandedPlanId, setExpandedPlanId] = useState<number | null>(null);
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  const plansQuery = useQuery({ queryKey: ['plans-current'], queryFn: () => api.getCurrentPlanOffers() });
  const competitorsQuery = useQuery({ queryKey: ['competitors'], queryFn: api.getCompetitors });
  const historyQuery = useQuery({
    queryKey: ['plan-history', expandedPlanId, fromDate, toDate],
    queryFn: () => api.getPlanHistory(expandedPlanId as number, {
      from_date: fromDate || undefined,
      to_date: toDate || undefined,
      order: 'asc',
    }),
    enabled: expandedPlanId !== null,
  });

  const plans = plansQuery.data ?? [];
  const categories = [...new Set(plans.map((plan) => plan.plan_category))].sort();
  const planTypes = [...new Set(plans.map((plan) => plan.plan_type))].sort();
  const filteredPlans = useMemo(() => plans.filter((plan) =>
    (competitorId === 'all' || plan.competitor_id === Number(competitorId)) &&
    (category === 'all' || plan.plan_category === category) &&
    (planType === 'all' || plan.plan_type === planType),
  ), [plans, competitorId, category, planType]);

  if (plansQuery.isPending || competitorsQuery.isPending) {
    return <DataState status="loading" message="Loading plan offers" detail="Retrieving current competitor pricing from the API." />;
  }
  if (plansQuery.isError) {
    return <DataState status="error" message="Plan offers unavailable" detail="The plan pricing endpoint could not be reached." />;
  }

  return (
    <div className="dashboard-page">
      <PageHeader eyebrow="Plans" title="Plan comparison" note="Current prices are resolved from the latest captured history record." />
      <section className="filter-bar" aria-label="Plan filters">
        <label>Competitor
          <select value={competitorId} onChange={(event) => setCompetitorId(event.target.value)}>
            <option value="all">All competitors</option>
            {(competitorsQuery.data ?? []).map((competitor) => <option key={competitor.competitor_id} value={competitor.competitor_id}>{competitor.name}</option>)}
          </select>
        </label>
        <label>Category
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="all">All categories</option>
            {categories.map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label>Plan type
          <select value={planType} onChange={(event) => setPlanType(event.target.value)}>
            <option value="all">All types</option>
            {planTypes.map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <span className="filter-count">{filteredPlans.length} offers</span>
      </section>

      {filteredPlans.length === 0 ? (
        <DataState status="empty" message="No plans match these filters" detail="Adjust the competitor, category, or plan type selection." />
      ) : (
        <section className="plan-comparison-list" aria-label="Current plans">
          {filteredPlans.map((plan) => {
            const expanded = expandedPlanId === plan.plan_id;
            return (
              <article key={plan.plan_id} className="panel plan-detail-card">
                <div className="plan-summary-row">
                  <div className="plan-identity">
                    <p className="plan-competitor">{plan.competitor_name}</p>
                    <h3>{plan.plan_name}</h3>
                    <div className="meta-line"><span>{plan.plan_category}</span><span>{plan.plan_type}</span><span>Effective {formatDate(plan.effective_date)}</span></div>
                  </div>
                  <div className="plan-current-price">
                    <span>Monthly price</span>
                    <strong>{formatCurrency(plan.price_usd)}</strong>
                    {plan.promotional_price_usd != null ? <small>{formatCurrency(plan.promotional_price_usd)} promotional price</small> : <small>No promotional price listed</small>}
                    {plan.promo_terms ? <em>{plan.promo_terms}</em> : null}
                  </div>
                  <button
                    type="button"
                    className="secondary-button"
                    aria-expanded={expanded}
                    onClick={() => setExpandedPlanId(expanded ? null : plan.plan_id)}
                  >
                    {expanded ? 'Hide history' : 'Price history'}
                  </button>
                </div>
                {expanded ? (
                  <div className="history-detail">
                    <div className="panel-header">
                      <div><h4>Captured price history</h4><p className="subtle-copy">Historical price snapshots from the existing API.</p></div>
                      <div className="date-filters">
                        <label>From<input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} /></label>
                        <label>To<input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} /></label>
                      </div>
                    </div>
                    {historyQuery.isPending ? <DataState status="loading" message="Loading plan history" /> : null}
                    {historyQuery.isError ? <DataState status="error" message="Plan history unavailable" detail="Try adjusting the selected date range." /> : null}
                    {historyQuery.isSuccess && historyQuery.data.length === 0 ? <DataState status="empty" message="No history in this date range" /> : null}
                    {historyQuery.isSuccess && historyQuery.data.length > 0 ? (
                      <>
                        <PriceHistoryChart series={[
                          { label: 'Standard price', color: '#60a5fa', values: historyQuery.data.map((entry) => ({ date: entry.source_snapshot_date, value: entry.price_usd })) },
                          { label: 'Promotional price', color: '#c084fc', values: historyQuery.data.map((entry) => ({ date: entry.source_snapshot_date, value: entry.promotional_price_usd })) },
                        ]} />
                        <div className="table-scroll">
                          <table className="data-table">
                            <thead><tr><th>Snapshot</th><th>Effective</th><th>Standard</th><th>Promo</th><th>Terms</th></tr></thead>
                            <tbody>{historyQuery.data.map((entry) => (
                              <tr key={`${entry.source_snapshot_date}-${entry.captured_at}`}>
                                <td>{formatDate(entry.source_snapshot_date)}</td><td>{formatDate(entry.effective_date)}</td>
                                <td>{formatCurrency(entry.price_usd)}</td><td>{formatCurrency(entry.promotional_price_usd)}</td><td>{entry.promo_terms ?? '—'}</td>
                              </tr>
                            ))}</tbody>
                          </table>
                        </div>
                      </>
                    ) : null}
                  </div>
                ) : null}
              </article>
            );
          })}
        </section>
      )}
    </div>
  );
}
