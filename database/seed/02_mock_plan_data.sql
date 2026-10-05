-- 02_mock_plan_data.sql
-- Synthetic plan seed data.

INSERT INTO service_plans (plan_id, competitor_id, plan_name, plan_category, plan_type, description, is_active, created_at, updated_at)
VALUES
    (101, 1, 'Boost Unlimited Plan', 'Unlimited', 'Monthly', 'Unlimited talk, text, and data with mobile hotspot access.', TRUE, NOW(), NOW()),
    (102, 1, 'Boost 5G Prepaid', 'Prepaid', 'Prepaid', 'Prepaid unlimited option with flexible monthly billing.', TRUE, NOW(), NOW()),
    (201, 2, 'T-Mobile Essentials', 'Unlimited', 'Monthly', 'Entry-level unlimited plan with basic coverage and data features.', TRUE, NOW(), NOW()),
    (202, 2, 'T-Mobile Experience More', 'Unlimited', 'Monthly', 'Premium unlimited plan with more hotspot and streaming features.', TRUE, NOW(), NOW()),
    (301, 3, 'Verizon Unlimited Welcome', 'Unlimited', 'Monthly', 'Basic unlimited access with standard features.', TRUE, NOW(), NOW()),
    (302, 3, 'Verizon Unlimited Plus', 'Unlimited', 'Monthly', 'Higher-tier unlimited plan with enhanced perks.', TRUE, NOW(), NOW());
