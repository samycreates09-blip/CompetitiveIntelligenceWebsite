-- 01_competitors.sql
-- Master list of tracked competitors.

CREATE TABLE competitors (
    competitor_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    short_name VARCHAR(100) NOT NULL,
    brand_type VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_competitors_name ON competitors (name);
CREATE INDEX idx_competitors_is_active ON competitors (is_active);
