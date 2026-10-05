-- 04_mock_device_data.sql
-- Synthetic device catalog seed data.

INSERT INTO devices (device_id, competitor_id, manufacturer, model_name, device_type, storage_variant, color, is_active, created_at, updated_at)
VALUES
    (5001, 1, 'Apple', 'iPhone 15', 'smartphone', '128GB', 'Black', TRUE, NOW(), NOW()),
    (5002, 1, 'Samsung', 'Galaxy A35', 'smartphone', '128GB', 'Blue', TRUE, NOW(), NOW()),
    (6001, 2, 'Samsung', 'Galaxy S24', 'smartphone', '256GB', 'Gray', TRUE, NOW(), NOW()),
    (6002, 2, 'Google', 'Pixel 9', 'smartphone', '128GB', 'Obsidian', TRUE, NOW(), NOW()),
    (7001, 3, 'Apple', 'iPhone 15 Pro', 'smartphone', '128GB', 'Natural Titanium', TRUE, NOW(), NOW()),
    (7002, 3, 'Samsung', 'Galaxy S24 Ultra', 'smartphone', '256GB', 'Titanium Gray', TRUE, NOW(), NOW());
