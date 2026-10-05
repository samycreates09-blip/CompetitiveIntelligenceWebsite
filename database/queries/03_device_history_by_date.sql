-- 03_device_history_by_date.sql
-- Example query to review device pricing and promos over time.

SELECT
    c.name AS competitor_name,
    d.model_name,
    dph.effective_date,
    dph.retail_price_usd,
    dph.promo_price_usd,
    dph.promotion_terms,
    dph.financing_terms,
    dph.source_snapshot_date,
    dph.captured_at
FROM device_price_history dph
JOIN devices d
    ON d.device_id = dph.device_id
JOIN competitors c
    ON c.competitor_id = d.competitor_id
WHERE d.model_name = 'iPhone 15 Pro'
  AND dph.source_snapshot_date BETWEEN '2026-09-01' AND '2026-09-30'
ORDER BY dph.source_snapshot_date ASC, dph.captured_at ASC;
