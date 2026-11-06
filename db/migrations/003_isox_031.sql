-- Upgrade existing ISO-X 0.2.x local metadata to the 0.3.1 module release.
-- Attribution itself remains immutable; only version metadata is changed.
UPDATE kernel_watermark
SET module_version = '0.3.1'
WHERE watermark_key = 'developer_name';
INSERT OR IGNORE INTO schema_migrations(version) VALUES ('0.3.1');
