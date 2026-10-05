-- 04_devices.sql
-- Device catalog by competitor.

CREATE TABLE devices (
    device_id BIGSERIAL PRIMARY KEY,
    competitor_id BIGINT NOT NULL,
    manufacturer VARCHAR(150) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    device_type VARCHAR(100) NOT NULL,
    storage_variant VARCHAR(100),
    color VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_devices_competitor
        FOREIGN KEY (competitor_id)
        REFERENCES competitors (competitor_id)
        ON DELETE RESTRICT
);

CREATE INDEX idx_devices_competitor_id ON devices (competitor_id);
CREATE INDEX idx_devices_model_name ON devices (model_name);
CREATE INDEX idx_devices_manufacturer ON devices (manufacturer);
