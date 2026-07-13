# L28 M2M Replay Registry Backup and Recovery v0.1

**Document:** Offline M2M Replay Registry Backup and Recovery v0.1
**Status:** Offline backup and verified recovery (Foundation 12)
**Normative subordination:** Subordinate to [L28 Protocol v1.0.0](../../PROTOCOL.md), [replay_registry_v0.1.md](replay_registry_v0.1.md), and [registry_audit_v0.1.md](registry_audit_v0.1.md).
**Related:** [test_vectors_registry_backup_v0.1.json](test_vectors_registry_backup_v0.1.json), [security_model.md](security_model.md)

## 1. Purpose

Foundation 12 provides offline replay-registry backup and verified recovery through:

- `coin/m2m_registry_backup.py`
- `coin/m2m_registry_backup_cli.py`

The tool preserves local replay/idempotency memory by copying audited Foundation 8 SQLite registries to new destinations outside the repository. It does not add networking, signing, wallet behavior, autonomous spending, ledger access, automatic activation, migration, or repair.

## 2. Quiescence contract

Backup and restore require a **quiescent** registry or backup file:

- No concurrent writer may modify the source during backup.
- No admission process may modify the backup during restore.
- Operators MUST close admission, audit, and registry handles before backup or restore.
- Backup is not an online snapshot service.
- Restore does not coordinate with an active admission process.
- Pre/post stat and logical checks reduce races but do not guarantee protection against a malicious local administrator.

## 3. Public API

```
create_registry_backup(source_path, destination_path) -> RegistryBackupResult
restore_registry_backup(backup_path, destination_path) -> RegistryBackupResult
```

`RegistryBackupResult` includes bounded fields only: `ok`, `code`, `operation`, `destination_created`, `schema_version`, `exchange_count`, `message_count`, `logical_registry_digest`, `input_audit_report_id`, `output_audit_report_id`, `artifact_sha256`, `artifact_size_bytes`, `report_id`.

Never exposed: paths, raw exchange IDs, message IDs, transcripts, identities, keys, settlement material, SQL, exception text, hostnames, usernames, PIDs, or timestamps.

## 4. Path and publication rules

- All paths must be absolute and outside the L28-Coin repository.
- Destination parent must exist; destination must not exist.
- Symlinks, directories, FIFOs, special files, identical paths, and hardlink aliases are rejected.
- Publication uses atomic hard-link creation: `os.link(temp, dest, follow_symlinks=False)`, parent fsync, unlink of the temporary name, parent fsync again. Never uses `os.rename` or `os.replace`.
- No overwrite flag exists in v0.1.
- Failures remove temporary files and never leave a destination.

## 5. Backup operation

1. Audit healthy source.
2. Copy through SQLite backup API from a read-only source connection (`query_only`, `trusted_schema=OFF`; **not** `immutable=1`).
3. Audit temporary backup; require matching schema, counts, and logical registry digest.
4. Recheck source stat identity and bytes unchanged.
5. Publish atomically; audit final destination.

The source is never modified.

## 6. Restore operation

1. Audit healthy backup input.
2. Copy exact backup bytes into a private temporary file within size bounds.
3. Audit temporary restore; require matching schema, counts, logical digest, and raw SHA-256 equality with backup.
4. Recheck backup stat identity unchanged.
5. Publish atomically; audit final restored registry.

Restore never activates, replaces, renames over, or deletes an existing operational registry. The input backup remains untouched.

## 7. Backup artifact boundary

The backup is a standalone SQLite replay registry with the same hash-only replay state as the source. It may contain correlatable exchange hashes, message IDs, chain relationships, states, and counts. It must not contain raw transcripts, raw exchange IDs, identities, public keys, signatures, or settlement payloads unless the source already violates schema (audit rejects).

The backup is:

- not encrypted
- not authenticated
- not anonymous
- not a settlement proof
- not a finality proof
- not a service-completion record

SHA-256 detects byte changes but does not establish authorship or trust.

Repeated backups with equivalent logical state may share a logical digest but are not required to have identical SQLite bytes or artifact SHA-256 values.

## 8. Report integrity

Domain separator: `L28-M2M-V0.1-REGISTRY-BACKUP-REPORT\x00`

```
report_id = SHA-256(domain || Canon(report body excluding report_id))
```

Report version: `l28-m2m-registry-backup-report/v0.1`
Profile: `l28-m2m-replay-registry-backup/v0.1`

## 9. CLI

```
python -m coin.m2m_registry_backup_cli backup --source ABSOLUTE_PATH --destination ABSOLUTE_PATH [--pretty]
python -m coin.m2m_registry_backup_cli restore --backup ABSOLUTE_PATH --destination ABSOLUTE_PATH [--pretty]
python -m coin.m2m_registry_backup_cli --version
```

Exit codes: `0` success, `2` usage/path conflict, `3` audit/integrity/I/O/internal failure.

## 10. Stable result codes

Success: `backup_created`, `restore_created`

Path/input: `invalid_source_path`, `source_not_found`, `invalid_backup_path`, `backup_not_found`, `invalid_destination_path`, `destination_exists`, `unsafe_path`, `same_file`

Verification: `source_audit_failed`, `backup_audit_failed`, `restore_audit_failed`, `source_changed`, `backup_changed`, `logical_registry_mismatch`, `artifact_hash_mismatch`, `unsupported_registry_schema`, `registry_resource_limit`

Operation: `backup_failed`, `restore_failed`, `publish_failed`, `internal_error`
