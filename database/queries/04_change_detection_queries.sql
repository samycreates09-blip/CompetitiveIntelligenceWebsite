-- 04_change_detection_queries.sql
-- Example queries for reviewing change events.

SELECT
    c.name AS competitor_name,
    cc.change_type,
    cc.entity_type,
    cc.entity_id,
    cc.summary_text,
    cc.effective_date,
    cc.severity,
    cc.change_detected_at
FROM competitor_changes cc
JOIN competitors c
    ON c.competitor_id = cc.competitor_id
WHERE cc.change_detected_at >= NOW() - INTERVAL '30 days'
ORDER BY cc.change_detected_at DESC;

-- Query to compare the latest two plan observations for a specific plan.
SELECT
    sp.plan_name,
    pph_old.source_snapshot_date AS previous_snapshot_date,
    pph_old.price_usd AS previous_price_usd,
    pph_new.source_snapshot_date AS current_snapshot_date,
    pph_new.price_usd AS current_price_usd
FROM service_plans sp
JOIN plan_price_history pph_new
    ON pph_new.plan_id = sp.plan_id
LEFT JOIN LATERAL (
    SELECT pph.*
    FROM plan_price_history pph
    WHERE pph.plan_id = sp.plan_id
      AND pph.captured_at < pph_new.captured_at
    ORDER BY pph.captured_at DESC
    LIMIT 1
) pph_old ON TRUE
WHERE sp.plan_name = 'T-Mobile Essentials'
  AND pph_new.captured_at = (
      SELECT MAX(inner_pph.captured_at)
      FROM plan_price_history inner_pph
      WHERE inner_pph.plan_id = sp.plan_id
  );
