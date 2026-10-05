import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { DataState } from '../components/DataState';
import { PageHeader } from '../components/PageHeader';
import { api } from '../lib/api';
import { formatDate } from '../lib/format';

export default function PromotionsPage() {
  const [competitorId, setCompetitorId] = useState('all');
  const [targetType, setTargetType] = useState('all');
  const [activity, setActivity] = useState('all');
  const [startsAfter, setStartsAfter] = useState('');
  const [endsBefore, setEndsBefore] = useState('');
  const [selectedPromotionId, setSelectedPromotionId] = useState<number | null>(null);

  const competitorsQuery = useQuery({ queryKey: ['competitors'], queryFn: api.getCompetitors });
  const promotionsQuery = useQuery({
    queryKey: ['promotions', competitorId, targetType, activity, startsAfter, endsBefore],
    queryFn: () => api.getPromotions({
      competitor_id: competitorId === 'all' ? undefined : Number(competitorId),
      target_type: targetType === 'all' ? undefined : targetType,
      active_only: activity === 'active' ? true : undefined,
      start_date: startsAfter || undefined,
      end_date: endsBefore || undefined,
    }),
  });
  const detailQuery = useQuery({
    queryKey: ['promotion', selectedPromotionId],
    queryFn: () => api.getPromotion(selectedPromotionId as number),
    enabled: selectedPromotionId !== null,
  });

  if (competitorsQuery.isPending || promotionsQuery.isPending) return <DataState status="loading" message="Loading promotions" detail="Retrieving competitor offers from the promotions API." />;
  if (promotionsQuery.isError) return <DataState status="error" message="Promotions unavailable" detail="The promotions endpoint could not be reached." />;

  const promotions = promotionsQuery.data ?? [];
  return (
    <div className="dashboard-page">
      <PageHeader eyebrow="Promotions" title="Promotion tracker" note="Dates and offer details are sourced from captured competitor records." />
      <section className="filter-bar" aria-label="Promotion filters">
        <label>Competitor
          <select value={competitorId} onChange={(event) => setCompetitorId(event.target.value)}>
            <option value="all">All competitors</option>
            {(competitorsQuery.data ?? []).map((competitor) => <option key={competitor.competitor_id} value={competitor.competitor_id}>{competitor.name}</option>)}
          </select>
        </label>
        <label>Target
          <select value={targetType} onChange={(event) => setTargetType(event.target.value)}>
            <option value="all">All targets</option><option value="plan">Plan</option><option value="device">Device</option><option value="bundle">Bundle</option>
          </select>
        </label>
        <label>Activity
          <select value={activity} onChange={(event) => setActivity(event.target.value)}><option value="all">All offers</option><option value="active">Active now</option></select>
        </label>
        <label>Starts on/after<input type="date" value={startsAfter} onChange={(event) => setStartsAfter(event.target.value)} /></label>
        <label>Ends on/before<input type="date" value={endsBefore} onChange={(event) => setEndsBefore(event.target.value)} /></label>
        <span className="filter-count">{promotions.length} offers</span>
      </section>

      {promotions.length === 0 ? <DataState status="empty" message="No promotions match these filters" detail="Try broadening the selected competitor, target, activity, or dates." /> : (
        <section className="promotion-grid" aria-label="Promotions">
          {promotions.map((promotion) => (
            <article key={promotion.promotion_id} className="panel promotion-card">
              <div className="change-head">
                <p className="plan-competitor">{promotion.competitor_name}</p>
                <span className="target-badge">{promotion.target_type}</span>
              </div>
              <h3>{promotion.promotion_title}</h3>
              <p className="promotion-description">{promotion.description}</p>
              <div className="promotion-dates">
                <div><small>Starts</small><strong>{formatDate(promotion.start_date)}</strong></div>
                <div><small>Ends</small><strong>{formatDate(promotion.end_date)}</strong></div>
              </div>
              <div className="promotion-card-footer">
                <small>{promotion.promotion_type} offer · captured {formatDate(promotion.captured_at)}</small>
                <button type="button" className="text-button" onClick={() => setSelectedPromotionId(promotion.promotion_id)}>Details</button>
              </div>
            </article>
          ))}
        </section>
      )}

      {selectedPromotionId !== null ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedPromotionId(null); }}>
          <section className="detail-modal" role="dialog" aria-modal="true" aria-labelledby="promotion-detail-title">
            <div className="panel-header"><div><p className="eyebrow">Promotion detail</p><h3 id="promotion-detail-title">{detailQuery.data?.promotion_title ?? 'Offer details'}</h3></div><button type="button" className="icon-button" aria-label="Close details" onClick={() => setSelectedPromotionId(null)}>×</button></div>
            {detailQuery.isPending ? <DataState status="loading" message="Loading offer details" /> : null}
            {detailQuery.isError ? <DataState status="error" message="Offer details unavailable" /> : null}
            {detailQuery.isSuccess ? (
              <div className="detail-fields">
                <p>{detailQuery.data.description}</p>
                <dl>
                  <div><dt>Competitor</dt><dd>{detailQuery.data.competitor_name}</dd></div>
                  <div><dt>Offer type</dt><dd>{detailQuery.data.promotion_type}</dd></div>
                  <div><dt>Target</dt><dd>{detailQuery.data.target_type}{detailQuery.data.target_plan_id ? ` · plan #${detailQuery.data.target_plan_id}` : ''}{detailQuery.data.target_device_id ? ` · device #${detailQuery.data.target_device_id}` : ''}</dd></div>
                  <div><dt>Valid dates</dt><dd>{formatDate(detailQuery.data.start_date)} – {formatDate(detailQuery.data.end_date)}</dd></div>
                  <div><dt>Captured</dt><dd>{new Date(detailQuery.data.captured_at).toLocaleString()}</dd></div>
                </dl>
              </div>
            ) : null}
          </section>
        </div>
      ) : null}
    </div>
  );
}
