import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { DataState } from '../components/DataState';
import { PageHeader } from '../components/PageHeader';
import { api } from '../lib/api';
import { formatDate } from '../lib/format';

export default function ChangesPage() {
  const queryClient = useQueryClient();
  const [competitorId, setCompetitorId] = useState('all');
  const [severity, setSeverity] = useState('all');
  const [origin, setOrigin] = useState('all');
  const [entityType, setEntityType] = useState('all');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [selectedChangeId, setSelectedChangeId] = useState<number | null>(null);
  const [simulationPlanId, setSimulationPlanId] = useState('201');
  const [simulationPrice, setSimulationPrice] = useState('70');
  const [simulationResult, setSimulationResult] = useState<Awaited<ReturnType<typeof api.submitPlanPriceObservation>> | null>(null);

  const competitorsQuery = useQuery({ queryKey: ['competitors'], queryFn: api.getCompetitors });
  const changesQuery = useQuery({
    queryKey: ['changes', origin],
    queryFn: () => api.getChanges({ record_origin: origin === 'all' ? undefined : origin }),
  });
  const plansQuery = useQuery({ queryKey: ['plans-current'], queryFn: () => api.getCurrentPlanOffers() });
  const observationMutation = useMutation({
    mutationFn: api.submitPlanPriceObservation,
    onSuccess: async (result) => {
      setSimulationResult(result);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['changes'] }),
        queryClient.invalidateQueries({ queryKey: ['plans-current'] }),
        queryClient.invalidateQueries({ queryKey: ['plan-history'] }),
      ]);
    },
  });
  const detailQuery = useQuery({
    queryKey: ['change', selectedChangeId],
    queryFn: () => api.getChange(selectedChangeId as number),
    enabled: selectedChangeId !== null,
  });

  const changes = changesQuery.data ?? [];
  const plans = plansQuery.data ?? [];
  const entityTypes = [...new Set(changes.map((change) => change.entity_type))].sort();
  const filteredChanges = useMemo(() => changes.filter((change) =>
    (competitorId === 'all' || change.competitor_id === Number(competitorId)) &&
    (severity === 'all' || change.severity === severity) &&
    (entityType === 'all' || change.entity_type === entityType) &&
    (!fromDate || change.effective_date >= fromDate) &&
    (!toDate || change.effective_date <= toDate),
  ), [changes, competitorId, severity, entityType, fromDate, toDate]);

  if (competitorsQuery.isPending || changesQuery.isPending) return <DataState status="loading" message="Loading change log" detail="Retrieving captured change records." />;
  if (changesQuery.isError) return <DataState status="error" message="Change log unavailable" detail="The competitor changes endpoint could not be reached." />;

  return (
    <div className="dashboard-page">
      <PageHeader eyebrow="Changes" title="Competitive change log" note="Seeded changes are demos; new system-detected records come only from submitted observations." />
      <section className="panel observation-simulator">
        <div className="panel-header">
          <div><p className="eyebrow">Development simulator</p><h3>Submit a plan price observation</h3><p className="subtle-copy">Appends a price-history record, compares it deterministically with the previous snapshot, and records a mock alert when important.</p></div>
          <span className="panel-tag">No scraping · No Gemini</span>
        </div>
        <form className="filter-bar simulator-form" onSubmit={(event) => {
          event.preventDefault();
          observationMutation.mutate({
            plan_id: Number(simulationPlanId),
            price_usd: Number(simulationPrice),
            source_snapshot_date: new Date().toISOString().slice(0, 10),
          });
        }}>
          <label>Tracked plan
            <select value={simulationPlanId} onChange={(event) => setSimulationPlanId(event.target.value)}>
              {plans.map((plan) => <option key={plan.plan_id} value={plan.plan_id}>{plan.competitor_name} · {plan.plan_name} ({formatDate(plan.effective_date)})</option>)}
            </select>
          </label>
          <label>New observed monthly price (USD)
            <input type="number" min="0" step="0.01" required value={simulationPrice} onChange={(event) => setSimulationPrice(event.target.value)} />
          </label>
          <button className="primary-button" type="submit" disabled={!plans.length || observationMutation.isPending}>
            {observationMutation.isPending ? 'Comparing…' : 'Submit observation'}
          </button>
        </form>
        {observationMutation.isPending ? <DataState status="loading" message="Appending observation and checking prior history" /> : null}
        {observationMutation.isError ? <DataState status="error" message="Observation was not accepted" detail={observationMutation.error.message} /> : null}
        {simulationResult ? (
          <div className={`simulation-result ${simulationResult.change_detected ? 'detected' : 'unchanged'}`} aria-live="polite">
            <strong>{simulationResult.change_detected ? 'System-detected change' : 'Observation appended; no material change detected'}</strong>
            <span>Historical observation appended: {simulationResult.observation_appended ? 'yes' : 'no'}</span>
            {simulationResult.change ? <span>{simulationResult.change.summary_text} · {simulationResult.change.previous_value} → {simulationResult.change.new_value}</span> : null}
            <span>Alert importance: {simulationResult.alert_important ? 'important' : 'not alert-worthy'}</span>
            {simulationResult.email_alert ? (
              <div className="mock-email-card">
                <span className="origin-badge system-origin">Mock email · not sent</span>
                <strong>{simulationResult.email_alert.subject}</strong>
                <small>To: {simulationResult.email_alert.recipient}</small>
                <p>{simulationResult.email_alert.body}</p>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>
      <section className="filter-bar" aria-label="Change log filters">
        <label>Competitor
          <select value={competitorId} onChange={(event) => setCompetitorId(event.target.value)}>
            <option value="all">All competitors</option>
            {(competitorsQuery.data ?? []).map((competitor) => <option key={competitor.competitor_id} value={competitor.competitor_id}>{competitor.name}</option>)}
          </select>
        </label>
        <label>Severity
          <select value={severity} onChange={(event) => setSeverity(event.target.value)}><option value="all">All severities</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select>
        </label>
        <label>Record origin
          <select value={origin} onChange={(event) => setOrigin(event.target.value)}>
            <option value="all">All origins</option>
            <option value="synthetic_seeded">Synthetic / seeded demo</option>
            <option value="system_detected">System-detected</option>
          </select>
        </label>
        <label>Entity
          <select value={entityType} onChange={(event) => setEntityType(event.target.value)}><option value="all">All entities</option>{entityTypes.map((value) => <option key={value}>{value}</option>)}</select>
        </label>
        <label>Effective from<input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} /></label>
        <label>Effective to<input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} /></label>
        <span className="filter-count">{filteredChanges.length} records</span>
      </section>

      {filteredChanges.length === 0 ? <DataState status="empty" message="No change records match these filters" detail="Try a different competitor, severity, origin, entity, or date range." /> : (
        <section className="change-timeline" aria-label="Competitive changes">
          {filteredChanges.map((change) => (
            <article className="change-entry panel" key={change.change_id}>
              <div className="timeline-marker" aria-hidden="true" />
              <div className="change-entry-content">
                <div className="change-entry-top">
                  <div><p className="plan-competitor">{change.competitor_name}</p><h3>{change.summary_text}</h3><span className={`origin-badge ${change.record_origin === 'system_detected' ? 'system-origin' : 'synthetic-origin'}`}>{change.record_origin === 'system_detected' ? 'System-detected' : 'Synthetic / seeded demo'}</span></div>
                  <span className={`severity ${change.severity}`}>{change.severity}</span>
                </div>
                <div className="change-values"><span>{change.previous_value ?? 'No previous value'}</span><b aria-hidden="true">→</b><span>{change.new_value ?? 'No new value'}</span></div>
                <div className="meta-line"><span>{change.change_type}</span><span>{change.entity_type} #{change.entity_id}</span><span>Effective {formatDate(change.effective_date)}</span></div>
                <button type="button" className="text-button" onClick={() => setSelectedChangeId(change.change_id)}>View record detail</button>
              </div>
            </article>
          ))}
        </section>
      )}

      {selectedChangeId !== null ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedChangeId(null); }}>
          <section className="detail-modal" role="dialog" aria-modal="true" aria-labelledby="change-detail-title">
            <div className="panel-header"><div><p className="eyebrow">{detailQuery.data?.record_origin === 'system_detected' ? 'System-detected observation' : 'Synthetic seeded demo record'}</p><h3 id="change-detail-title">Change detail</h3></div><button type="button" className="icon-button" aria-label="Close details" onClick={() => setSelectedChangeId(null)}>×</button></div>
            {detailQuery.isPending ? <DataState status="loading" message="Loading change detail" /> : null}
            {detailQuery.isError ? <DataState status="error" message="Change detail unavailable" /> : null}
            {detailQuery.isSuccess ? (
              <div className="detail-fields">
                <p>{detailQuery.data.summary_text}</p>
                <dl>
                  <div><dt>Competitor</dt><dd>{detailQuery.data.competitor_name}</dd></div>
                  <div><dt>Change</dt><dd>{detailQuery.data.change_type} · {detailQuery.data.entity_type} #{detailQuery.data.entity_id}</dd></div>
                  <div><dt>Severity</dt><dd><span className={`severity ${detailQuery.data.severity}`}>{detailQuery.data.severity}</span></dd></div>
                  <div><dt>Record origin</dt><dd>{detailQuery.data.record_origin === 'system_detected' ? 'System-detected from submitted observation' : 'Synthetic seeded demo record (not automatically detected)'}</dd></div>
                  <div><dt>Previous</dt><dd>{detailQuery.data.previous_value ?? 'Not recorded'}</dd></div>
                  <div><dt>New</dt><dd>{detailQuery.data.new_value ?? 'Not recorded'}</dd></div>
                  <div><dt>Effective date</dt><dd>{formatDate(detailQuery.data.effective_date)}</dd></div>
                  <div><dt>Source snapshot window</dt><dd>{formatDate(detailQuery.data.source_snapshot_from)} – {formatDate(detailQuery.data.source_snapshot_to)}</dd></div>
                  <div><dt>Record captured</dt><dd>{new Date(detailQuery.data.change_detected_at).toLocaleString()}</dd></div>
                </dl>
              </div>
            ) : null}
          </section>
        </div>
      ) : null}
    </div>
  );
}
