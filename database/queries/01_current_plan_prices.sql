-- 01_current_plan_prices.sql
-- Example query to return the latest observed price for each plan.

SELECT
    c.name AS competitor_name,
    sp.plan_name,
    latest.price_usd AS current_price_usd,
    latest.effective_date,
    latest.captured_at AS last_observed_at
FROM service_plans sp
JOIN competitors c
    ON c.competitor_id = sp.competitor_id
JOIN LATERAL (
    SELECT pph.price_usd, pph.effective_date, pph.captured_at
    FROM plan_price_history pph
    WHERE pph.plan_id = sp.plan_id
    ORDER BY pph.captured_at DESC, pph.source_snapshot_date DESC
    LIMIT 1
) latest ON TRUE
ORDER BY c.name, sp.plan_name;
