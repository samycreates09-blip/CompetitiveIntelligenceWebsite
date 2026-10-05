-- 02_service_plans.sql
-- The stable identity of a plan offered by a competitor.

CREATE TABLE service_plans (
    plan_id BIGSERIAL PRIMARY KEY,
    competitor_id BIGINT NOT NULL,
    plan_name VARCHAR(255) NOT NULL,
    plan_category VARCHAR(100) NOT NULL,
    plan_type VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_service_plans_competitor
        FOREIGN KEY (competitor_id)
        REFERENCES competitors (competitor_id)
        ON DELETE RESTRICT
);

CREATE INDEX idx_service_plans_competitor_id ON service_plans (competitor_id);
CREATE INDEX idx_service_plans_plan_name ON service_plans (plan_name);
CREATE INDEX idx_service_plans_category ON service_plans (plan_category);
