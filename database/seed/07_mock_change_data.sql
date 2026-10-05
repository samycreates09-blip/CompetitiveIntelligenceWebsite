-- 07_mock_change_data.sql
-- Example change records for testing and demonstrations.
-- In production, this table should be populated by deterministic comparison logic.

INSERT INTO competitor_changes (
    change_id,
    competitor_id,
    change_type,
    entity_type,
    entity_id,
    previous_value,
    new_value,
    previous_snapshot_captured_at,
    new_snapshot_captured_at,
    change_detected_at,
    effective_date,
    severity,
    summary_text,
    source_snapshot_from,
    source_snapshot_to,
    record_origin,
    created_at
)
VALUES
    (4001, 2, 'plan_price', 'plan', 201, '60.00', '65.00', TIMESTAMPTZ '2026-09-01 09:00:00+00', TIMESTAMPTZ '2026-09-15 09:00:00+00', TIMESTAMPTZ '2026-09-15 09:00:00+00', '2026-09-15', 'medium', 'T-Mobile Essentials increased from $60 to $65.', '2026-09-01', '2026-09-15', 'synthetic_seeded', TIMESTAMPTZ '2026-09-15 09:00:00+00'),
    (4002, 3, 'device_promotion', 'device', 7001, 'No trade-in bonus', '$300 trade-in bonus', TIMESTAMPTZ '2026-09-01 09:00:00+00', TIMESTAMPTZ '2026-09-10 09:00:00+00', TIMESTAMPTZ '2026-09-10 09:00:00+00', '2026-09-10', 'high', 'Verizon added a $300 trade-in bonus for the iPhone 15 Pro.', '2026-09-01', '2026-09-10', 'synthetic_seeded', TIMESTAMPTZ '2026-09-10 09:00:00+00'),
    (4003, 1, 'promotion', 'plan', 101, 'No launch offer', '$5 off for first 3 months with AutoPay', TIMESTAMPTZ '2026-09-01 09:00:00+00', TIMESTAMPTZ '2026-09-20 09:00:00+00', TIMESTAMPTZ '2026-09-20 09:00:00+00', '2026-09-20', 'low', 'Boost launched a limited-time monthly discount on its Unlimited Plan.', '2026-09-01', '2026-09-20', 'synthetic_seeded', TIMESTAMPTZ '2026-09-20 09:00:00+00');
