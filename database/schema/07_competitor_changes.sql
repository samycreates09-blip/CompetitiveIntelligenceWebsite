-- 07_competitor_changes.sql
-- Change log created by deterministic comparison logic.
-- This table is append-only and should not be manually maintained by users.

CREATE TABLE competitor_changes (
    change_id BIGSERIAL PRIMARY KEY,
    competitor_id BIGINT NOT NULL,
    change_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    previous_value TEXT,
    new_value TEXT,
    previous_snapshot_captured_at TIMESTAMPTZ,
    new_snapshot_captured_at TIMESTAMPTZ,
    change_detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effective_date DATE,
    severity VARCHAR(50) NOT NULL DEFAULT 'medium',
    summary_text TEXT NOT NULL,
    source_snapshot_from DATE,
    source_snapshot_to DATE,
    record_origin VARCHAR(30) NOT NULL DEFAULT 'synthetic_seeded',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_competitor_changes_competitor
        FOREIGN KEY (competitor_id)
        REFERENCES competitors (competitor_id)
        ON DELETE RESTRICT,
    CONSTRAINT chk_change_severity
        CHECK (severity IN ('low', 'medium', 'high')),
    CONSTRAINT chk_competitor_changes_record_origin
        CHECK (record_origin IN ('synthetic_seeded', 'system_detected'))
);

CREATE INDEX idx_competitor_changes_competitor_id ON competitor_changes (competitor_id);
CREATE INDEX idx_competitor_changes_change_type ON competitor_changes (change_type);
CREATE INDEX idx_competitor_changes_entity_type ON competitor_changes (entity_type, entity_id);
CREATE INDEX idx_competitor_changes_detected_at ON competitor_changes (change_detected_at);
CREATE INDEX idx_competitor_changes_effective_date ON competitor_changes (effective_date);
