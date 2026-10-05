-- 06_promotions.sql
-- Time-bounded promotions tied to plans, devices, or bundles.

CREATE TABLE promotions (
    promotion_id BIGSERIAL PRIMARY KEY,
    competitor_id BIGINT NOT NULL,
    promotion_title VARCHAR(255) NOT NULL,
    promotion_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_plan_id BIGINT,
    target_device_id BIGINT,
    start_date DATE,
    end_date DATE,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_promotions_competitor
        FOREIGN KEY (competitor_id)
        REFERENCES competitors (competitor_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_promotions_plan
        FOREIGN KEY (target_plan_id)
        REFERENCES service_plans (plan_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_promotions_device
        FOREIGN KEY (target_device_id)
        REFERENCES devices (device_id)
        ON DELETE RESTRICT,
    CONSTRAINT chk_target_type
        CHECK (target_type IN ('plan', 'device', 'bundle'))
);

CREATE INDEX idx_promotions_competitor_id ON promotions (competitor_id);
CREATE INDEX idx_promotions_start_date ON promotions (start_date);
CREATE INDEX idx_promotions_end_date ON promotions (end_date);
CREATE INDEX idx_promotions_target_plan_id ON promotions (target_plan_id);
CREATE INDEX idx_promotions_target_device_id ON promotions (target_device_id);
