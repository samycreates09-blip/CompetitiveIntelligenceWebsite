-- 05_mock_device_price_history_data.sql
-- Historical device pricing snapshots.

INSERT INTO device_price_history (
    device_price_history_id,
    device_id,
    effective_date,
    retail_price_usd,
    promo_price_usd,
    promotion_terms,
    financing_terms,
    captured_at,
    source_snapshot_date,
    created_at
)
VALUES
    (9001, 5001, '2026-08-20', 799.00, NULL, NULL, NULL, TIMESTAMPTZ '2026-08-20 09:00:00+00', '2026-08-20', TIMESTAMPTZ '2026-08-20 09:00:00+00'),
    (9002, 5001, '2026-09-18', 799.00, 699.00, 'Trade-in bonus up to $200', '24-month financing available', TIMESTAMPTZ '2026-09-18 09:00:00+00', '2026-09-18', TIMESTAMPTZ '2026-09-18 09:00:00+00'),

    (9003, 6001, '2026-09-05', 799.00, 749.00, 'Prepaid bundle offer', NULL, TIMESTAMPTZ '2026-09-05 09:00:00+00', '2026-09-05', TIMESTAMPTZ '2026-09-05 09:00:00+00'),
    (9004, 6001, '2026-09-19', 799.00, 699.00, 'Limited-time discount with eligible trade-in', '0% APR for 24 months', TIMESTAMPTZ '2026-09-19 09:00:00+00', '2026-09-19', TIMESTAMPTZ '2026-09-19 09:00:00+00'),

    (9005, 7001, '2026-09-10', 999.00, 899.00, 'Bill credit on select unlimited plans', '0% APR for 24 months', TIMESTAMPTZ '2026-09-10 09:00:00+00', '2026-09-10', TIMESTAMPTZ '2026-09-10 09:00:00+00'),
    (9006, 7001, '2026-09-25', 999.00, 849.00, 'Upgrade bonus with trade-in', '0% APR for 30 months', TIMESTAMPTZ '2026-09-25 09:00:00+00', '2026-09-25', TIMESTAMPTZ '2026-09-25 09:00:00+00');
