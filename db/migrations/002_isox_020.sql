-- Migration for an existing ISO-X 0.1.0 SQLite user database.
-- Run once only if its kernel_watermark table predates v0.2.0.
ALTER TABLE kernel_watermark ADD COLUMN module_version TEXT NOT NULL DEFAULT '0.3.1';
ALTER TABLE kernel_watermark ADD COLUMN module_sha256 TEXT;
ALTER TABLE kernel_watermark ADD COLUMN signing_cert_fingerprint TEXT;
ALTER TABLE kernel_watermark ADD COLUMN verification_state TEXT NOT NULL DEFAULT 'unconfigured'
  CHECK (verification_state IN ('unconfigured','signed','verified','failed'));
CREATE TABLE IF NOT EXISTS local_app_usage (
    usage_id INTEGER PRIMARY KEY,
    app_id TEXT NOT NULL,
    hour_of_day INTEGER NOT NULL CHECK (hour_of_day BETWEEN 0 AND 23),
    used_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_local_app_usage_recent ON local_app_usage(used_at);
INSERT OR IGNORE INTO privacy_settings(setting_key, setting_value) VALUES ('preload_enabled', 'disabled');
INSERT OR IGNORE INTO schema_migrations(version) VALUES ('0.2.0');

-- Replace the 0.1.0 trigger that blocked every metadata change: attribution remains
-- immutable, while release hash/fingerprint/status may be refreshed by trusted tooling.
DROP TRIGGER IF EXISTS kernel_watermark_no_update;
DROP TRIGGER IF EXISTS kernel_watermark_no_delete;
CREATE TRIGGER kernel_watermark_no_update
BEFORE UPDATE OF watermark_key, watermark_value ON kernel_watermark BEGIN
  SELECT RAISE(ABORT, 'ISO-X developer attribution is read-only');
END;
CREATE TRIGGER kernel_watermark_no_delete
BEFORE DELETE ON kernel_watermark BEGIN
  SELECT RAISE(ABORT, 'ISO-X developer watermark is read-only');
END;
INSERT OR IGNORE INTO privacy_settings(setting_key,setting_value) VALUES
  ('remote_telemetry','disabled'),
  ('background_metrics','disabled'),
  ('user_triggered_local_metrics','enabled'),
  ('preload_enabled','disabled');
INSERT OR IGNORE INTO schema_migrations(version) VALUES ('0.2.0');
