-- 06_mock_promotion_data.sql
-- Synthetic promotional offers.

INSERT INTO promotions (
    promotion_id,
    competitor_id,
    promotion_title,
    promotion_type,
    description,
    target_type,
    target_plan_id,
    target_device_id,
    start_date,
    end_date,
    captured_at,
    created_at
)
VALUES
    (3001, 2, 'T-Mobile 5G Home and Mobile Combo', 'bundle', 'Get a $150 bill credit when you add a new phone line.', 'bundle', 201, NULL, '2026-09-05', '2026-10-05', TIMESTAMPTZ '2026-09-05 09:00:00+00', TIMESTAMPTZ '2026-09-05 09:00:00+00'),
    (3002, 3, 'Verizon Trade-In Bonus', 'trade_in', 'Save up to $300 with eligible trade-in on select devices.', 'device', NULL, 7001, '2026-09-10', '2026-09-30', TIMESTAMPTZ '2026-09-10 09:00:00+00', TIMESTAMPTZ '2026-09-10 09:00:00+00'),
    (3003, 1, 'Boost Unlimited Launch Offer', 'service', 'Get $5 off monthly for the first 3 months with AutoPay.', 'plan', 101, NULL, '2026-09-15', '2026-10-15', TIMESTAMPTZ '2026-09-15 09:00:00+00', TIMESTAMPTZ '2026-09-15 09:00:00+00');
