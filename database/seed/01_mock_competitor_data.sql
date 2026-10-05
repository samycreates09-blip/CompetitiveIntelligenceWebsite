-- 01_mock_competitor_data.sql
-- Synthetic competitor seed data.

INSERT INTO competitors (competitor_id, name, short_name, brand_type, is_active, created_at, updated_at)
VALUES
    (1, 'Boost Mobile', 'Boost', 'MVNO', TRUE, NOW(), NOW()),
    (2, 'T-Mobile', 'T-Mobile', 'Major Carrier', TRUE, NOW(), NOW()),
    (3, 'Verizon', 'Verizon', 'Major Carrier', TRUE, NOW(), NOW());
