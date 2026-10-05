-- 02_plan_history_by_date.sql
-- Example query to review plan history for a date range.

SELECT
    c.name AS competitor_name,
    sp.plan_name,
    pph.effective_date,
    pph.price_usd,
    pph.promotional_price_usd,
    pph.promo_terms,
    pph.source_snapshot_date,
    pph.captured_at
FROM plan_price_history pph
JOIN service_plans sp
    ON sp.plan_id = pph.plan_id
JOIN competitors c
    ON c.competitor_id = sp.competitor_id
WHERE sp.plan_name = 'T-Mobile Essentials'
  AND pph.source_snapshot_date BETWEEN '2026-08-15' AND '2026-09-30'
ORDER BY pph.source_snapshot_date ASC, pph.captured_at ASC;
