-- 03_plan_price_history.sql
-- Append-only historical price snapshots for service plans.
-- Current price is derived from the newest applicable historical record.

CREATE TABLE plan_price_history (
    plan_price_history_id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT NOT NULL,
    effective_date DATE,
    price_usd NUMERIC(10,2) NOT NULL,
    promotional_price_usd NUMERIC(10,2),
    promo_terms TEXT,
    features_snapshot TEXT,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_snapshot_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_plan_price_history_plan
        FOREIGN KEY (plan_id)
        REFERENCES service_plans (plan_id)
        ON DELETE RESTRICT,
    CONSTRAINT chk_plan_price_history_price_nonnegative
        CHECK (price_usd >= 0),
    CONSTRAINT chk_plan_price_history_promotional_price_nonnegative
        CHECK (promotional_price_usd IS NULL OR promotional_price_usd >= 0)
);

CREATE INDEX idx_plan_price_history_plan_id ON plan_price_history (plan_id);
CREATE INDEX idx_plan_price_history_effective_date ON plan_price_history (effective_date);
CREATE INDEX idx_plan_price_history_captured_at ON plan_price_history (captured_at);
CREATE INDEX idx_plan_price_history_source_snapshot_date ON plan_price_history (source_snapshot_date);
CREATE INDEX idx_plan_price_history_plan_date ON plan_price_history (plan_id, effective_date, captured_at);
