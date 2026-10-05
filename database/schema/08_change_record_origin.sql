-- 08_change_record_origin.sql
-- Additive migration: preserve legacy/seeded rows as demo provenance and allow
-- the deterministic observation service to label new rows as system-detected.

ALTER TABLE competitor_changes
    ADD COLUMN IF NOT EXISTS record_origin VARCHAR(30) NOT NULL DEFAULT 'synthetic_seeded';

UPDATE competitor_changes
SET record_origin = 'synthetic_seeded'
WHERE record_origin IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_competitor_changes_record_origin'
          AND conrelid = 'competitor_changes'::regclass
    ) THEN
        ALTER TABLE competitor_changes
            ADD CONSTRAINT chk_competitor_changes_record_origin
            CHECK (record_origin IN ('synthetic_seeded', 'system_detected'));
    END IF;
END $$;