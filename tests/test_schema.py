#!/usr/bin/env python3
"""SQLite schema and attribution-table tests; standard library only."""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "db" / "schema.sql"
MIGRATION = ROOT / "db" / "migrations" / "002_isox_020.sql"

def should_fail_integrity(call, message):
    try:
        call()
    except sqlite3.IntegrityError:
        return
    raise AssertionError(message)

def test_current_schema():
    con = sqlite3.connect(":memory:")
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    expected = {"users", "app_registry", "installed_app_permissions", "fs_index", "perf_logs",
                "sys_snapshots", "dev_envs", "privacy_settings", "kernel_watermark",
                "local_app_usage", "schema_migrations"}
    actual = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert expected <= actual, f"Missing tables: {expected - actual}"
    row = con.execute("SELECT watermark_value,module_version,verification_state FROM kernel_watermark WHERE watermark_key='developer_name'").fetchone()
    assert row[0] == "عبدالله لازم", row
    assert row[1] == "0.3.1", row
    assert row[2] in ("unconfigured", "signed"), row
    versions = {r[0] for r in con.execute("SELECT version FROM schema_migrations")}
    assert "0.4.0" in versions, versions
    settings = dict(con.execute("SELECT setting_key,setting_value FROM privacy_settings"))
    assert settings["remote_telemetry"] == "disabled"
    assert settings["background_metrics"] == "disabled"
    assert settings["preload_enabled"] == "disabled"
    should_fail_integrity(lambda: con.execute("UPDATE kernel_watermark SET watermark_value='changed' WHERE watermark_key='developer_name'"), "Attribution update should be blocked")
    should_fail_integrity(lambda: con.execute("UPDATE kernel_watermark SET watermark_key='other' WHERE watermark_key='developer_name'"), "Attribution key update should be blocked")
    should_fail_integrity(lambda: con.execute("DELETE FROM kernel_watermark WHERE watermark_key='developer_name'"), "Watermark delete should be blocked")
    con.execute("UPDATE kernel_watermark SET module_sha256='test-hash' WHERE watermark_key='developer_name'")
    assert con.execute("SELECT module_sha256 FROM kernel_watermark WHERE watermark_key='developer_name'").fetchone()[0] == 'test-hash'
    con.execute("INSERT INTO app_registry(app_id, display_name) VALUES('test', 'Test App')")
    con.execute("INSERT INTO local_app_usage(app_id,hour_of_day) VALUES('browser',12)")
    assert con.execute("SELECT COUNT(*) FROM local_app_usage").fetchone()[0] == 1
    con.close()

def test_upgrade_migration():
    con = sqlite3.connect(":memory:")
    con.executescript("""
      CREATE TABLE kernel_watermark (watermark_key TEXT PRIMARY KEY, watermark_value TEXT NOT NULL);
      INSERT INTO kernel_watermark VALUES('developer_name','عبدالله لازم');
      CREATE TABLE privacy_settings(setting_key TEXT PRIMARY KEY, setting_value TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE schema_migrations(version TEXT PRIMARY KEY);
      CREATE TRIGGER kernel_watermark_no_update BEFORE UPDATE ON kernel_watermark BEGIN SELECT RAISE(ABORT, 'old read only'); END;
      CREATE TRIGGER kernel_watermark_no_delete BEFORE DELETE ON kernel_watermark BEGIN SELECT RAISE(ABORT, 'old read only'); END;
    """)
    con.executescript(MIGRATION.read_text(encoding="utf-8"))
    columns = {r[1] for r in con.execute("PRAGMA table_info(kernel_watermark)")}
    assert {"module_version", "module_sha256", "signing_cert_fingerprint", "verification_state"} <= columns
    assert con.execute("SELECT setting_value FROM privacy_settings WHERE setting_key='preload_enabled'").fetchone()[0] == "disabled"
    con.execute("UPDATE kernel_watermark SET module_sha256='migration-test' WHERE watermark_key='developer_name'")
    should_fail_integrity(lambda: con.execute("UPDATE kernel_watermark SET watermark_value='edited' WHERE watermark_key='developer_name'"), "Migrated attribution update should be blocked")
    con.close()

if __name__ == "__main__":
    test_current_schema(); test_upgrade_migration()
    print("PASS: SQLite v0.4.0 schema, local privacy defaults, watermark triggers, local usage, and 0.1.0 migration")
