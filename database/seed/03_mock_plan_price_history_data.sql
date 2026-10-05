-- 03_mock_plan_price_history_data.sql
-- Historical plan pricing snapshots for Boost, T-Mobile, and Verizon.

INSERT INTO plan_price_history (
    plan_price_history_id,
    plan_id,
    effective_date,
    price_usd,
    promotional_price_usd,
    promo_terms,
    features_snapshot,
    captured_at,
    source_snapshot_date,
    created_at
)
VALUES
    (1001, 101, '2026-08-15', 60.00, NULL, NULL, 'Unlimited talk, text, and data; mobile hotspot included', TIMESTAMPTZ '2026-08-15 09:00:00+00', '2026-08-15', TIMESTAMPTZ '2026-08-15 09:00:00+00'),
    (1002, 101, '2026-09-01', 60.00, NULL, NULL, 'Unlimited talk, text, and data; mobile hotspot included', TIMESTAMPTZ '2026-09-01 09:00:00+00', '2026-09-01', TIMESTAMPTZ '2026-09-01 09:00:00+00'),
    (1003, 101, '2026-09-20', 50.00, 40.00, 'Launch offer: $5 off for first 3 months with AutoPay', 'Unlimited talk, text, and data; mobile hotspot included', TIMESTAMPTZ '2026-09-20 09:00:00+00', '2026-09-20', TIMESTAMPTZ '2026-09-20 09:00:00+00'),

    (2001, 201, '2026-08-20', 60.00, NULL, NULL, 'Unlimited data; basic coverage features', TIMESTAMPTZ '2026-08-20 09:00:00+00', '2026-08-20', TIMESTAMPTZ '2026-08-20 09:00:00+00'),
    (2002, 201, '2026-09-01', 60.00, NULL, NULL, 'Unlimited data; basic coverage features', TIMESTAMPTZ '2026-09-01 09:00:00+00', '2026-09-01', TIMESTAMPTZ '2026-09-01 09:00:00+00'),
    (2003, 201, '2026-09-15', 65.00, NULL, NULL, 'Unlimited data; enhanced access tier', TIMESTAMPTZ '2026-09-15 09:00:00+00', '2026-09-15', TIMESTAMPTZ '2026-09-15 09:00:00+00'),

    (3001, 301, '2026-08-22', 70.00, NULL, NULL, 'Unlimited data with standard features', TIMESTAMPTZ '2026-08-22 09:00:00+00', '2026-08-22', TIMESTAMPTZ '2026-08-22 09:00:00+00'),
    (3002, 301, '2026-09-05', 70.00, 55.00, 'Promo pricing for first 6 months', 'Unlimited data with standard features and stream access', TIMESTAMPTZ '2026-09-05 09:00:00+00', '2026-09-05', TIMESTAMPTZ '2026-09-05 09:00:00+00');
