-- 05_device_price_history.sql
-- Append-only historical price snapshots for devices.

CREATE TABLE device_price_history (
    device_price_history_id BIGSERIAL PRIMARY KEY,
    device_id BIGINT NOT NULL,
    effective_date DATE,
    retail_price_usd NUMERIC(10,2) NOT NULL,
    promo_price_usd NUMERIC(10,2),
    promotion_terms TEXT,
    financing_terms TEXT,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_snapshot_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_device_price_history_device
        FOREIGN KEY (device_id)
        REFERENCES devices (device_id)
        ON DELETE RESTRICT,
    CONSTRAINT chk_device_price_history_retail_nonnegative
        CHECK (retail_price_usd >= 0),
    CONSTRAINT chk_device_price_history_promo_nonnegative
        CHECK (promo_price_usd IS NULL OR promo_price_usd >= 0)
);

CREATE INDEX idx_device_price_history_device_id ON device_price_history (device_id);
CREATE INDEX idx_device_price_history_effective_date ON device_price_history (effective_date);
CREATE INDEX idx_device_price_history_captured_at ON device_price_history (captured_at);
CREATE INDEX idx_device_price_history_source_snapshot_date ON device_price_history (source_snapshot_date);
CREATE INDEX idx_device_price_history_device_date ON device_price_history (device_id, effective_date, captured_at);
