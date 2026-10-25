PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    system_username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user','admin')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
-- No passwords, password hashes, biometrics, or authentication secrets are stored here.
-- PAM / the Linux login manager owns OS account authentication.

CREATE TABLE IF NOT EXISTS app_registry (
    app_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    version TEXT,
    state TEXT NOT NULL DEFAULT 'available' CHECK (state IN ('available','installed','external-runtime','optional-runtime','disabled')),
    executable_path TEXT,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS installed_app_permissions (
    permission_id INTEGER PRIMARY KEY,
    app_id TEXT NOT NULL REFERENCES app_registry(app_id) ON DELETE CASCADE,
    permission TEXT NOT NULL,
    decision TEXT NOT NULL DEFAULT 'ask' CHECK (decision IN ('allow','deny','ask')),
    changed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(app_id, permission)
);

CREATE TABLE IF NOT EXISTS fs_index (
    path TEXT PRIMARY KEY,
    basename TEXT NOT NULL,
    parent_path TEXT,
    file_type TEXT NOT NULL CHECK (file_type IN ('file','directory','symlink','other')),
    size_bytes INTEGER,
    modified_at TEXT,
    indexed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_fs_index_basename ON fs_index(basename COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_fs_index_parent ON fs_index(parent_path);

CREATE TABLE IF NOT EXISTS perf_logs (
    metric_id INTEGER PRIMARY KEY,
    metric_name TEXT NOT NULL,
    metric_value TEXT NOT NULL,
    unit TEXT,
    source TEXT NOT NULL DEFAULT 'user-triggered',
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_perf_logs_time ON perf_logs(recorded_at);

CREATE TABLE IF NOT EXISTS sys_snapshots (
    snapshot_id INTEGER PRIMARY KEY,
    snapshot_name TEXT NOT NULL,
    snapshot_backend TEXT NOT NULL,
    snapshot_reference TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL DEFAULT 'planned' CHECK (state IN ('planned','created','verified','failed','deleted')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    notes TEXT
);
-- A database row is metadata only: it does not create or restore an actual filesystem snapshot.

CREATE TABLE IF NOT EXISTS dev_envs (
    environment_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    runtime TEXT NOT NULL,
    manifest_path TEXT,
    state TEXT NOT NULL DEFAULT 'not-created' CHECK (state IN ('not-created','ready','stopped','failed')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    last_used_at TEXT
);

CREATE TABLE IF NOT EXISTS privacy_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
INSERT OR IGNORE INTO privacy_settings(setting_key, setting_value) VALUES
    ('remote_telemetry', 'disabled'),
    ('background_metrics', 'disabled'),
    ('user_triggered_local_metrics', 'enabled'),
    ('preload_enabled', 'disabled');

CREATE TABLE IF NOT EXISTS kernel_watermark (
    watermark_key TEXT PRIMARY KEY CHECK (watermark_key = 'developer_name'),
    watermark_value TEXT NOT NULL CHECK (watermark_value = 'عبدالله لازم'),
    module_version TEXT NOT NULL DEFAULT '0.3.1',
    module_sha256 TEXT,
    signing_cert_fingerprint TEXT,
    verification_state TEXT NOT NULL DEFAULT 'unconfigured' CHECK (verification_state IN ('unconfigured','signed','verified','failed')) ,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
INSERT OR IGNORE INTO kernel_watermark(watermark_key, watermark_value)
VALUES ('developer_name', 'عبدالله لازم');

-- Defense in depth for normal application-level SQL access. Root can alter the DB/schema;
-- this is not a cryptographically immutable kernel watermark.
CREATE TRIGGER IF NOT EXISTS kernel_watermark_no_update
BEFORE UPDATE OF watermark_key, watermark_value ON kernel_watermark BEGIN
    SELECT RAISE(ABORT, 'ISO-X developer attribution is read-only');
END;
CREATE TRIGGER IF NOT EXISTS kernel_watermark_no_delete
BEFORE DELETE ON kernel_watermark BEGIN
    SELECT RAISE(ABORT, 'ISO-X developer watermark is read-only');
END;

CREATE TABLE IF NOT EXISTS local_app_usage (
    usage_id INTEGER PRIMARY KEY,
    app_id TEXT NOT NULL,
    hour_of_day INTEGER NOT NULL CHECK (hour_of_day BETWEEN 0 AND 23),
    used_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_local_app_usage_recent ON local_app_usage(used_at);

INSERT OR IGNORE INTO schema_migrations(version) VALUES ('0.1.0');
INSERT OR IGNORE INTO schema_migrations(version) VALUES ('0.2.0');
INSERT OR IGNORE INTO schema_migrations(version) VALUES ('0.3.1');
INSERT OR IGNORE INTO schema_migrations(version) VALUES ('0.4.0');
