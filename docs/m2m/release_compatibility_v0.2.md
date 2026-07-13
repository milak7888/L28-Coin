# L28 M2M v0.2.0 Release Compatibility

**Document:** L28 M2M Release Compatibility v0.2
**Status:** Frozen release compatibility policy (Foundation 13)
**Release:** L28 M2M v0.2.0 (`frozen`)
**Release compatibility profile:** `l28-m2m-release-compatibility/v0.2`
**Protocol profile:** `l28-m2m/v0.1`

## 1. Release scope

L28 M2M v0.2.0 is the overall offline M2M tooling release. It freezes the complete public surface after Foundation 12 backup and recovery while preserving the existing v0.1 protocol profile for envelopes, transcripts, interoperability, replay registry, admission, and audit.

## 2. Protocol profile unchanged

The following remain at their existing v0.1 profile versions:

- envelope `protocol_version` `0.1`
- L28-M2M Canonical JSON v0.1
- Ed25519 verify-only envelope rules
- transcript validation and state machine
- replay registry schema version `1`
- conformance, admission, and registry-audit report profiles

No v0.1 envelope, signature, transcript, replay, admission, audit, settlement-citation, or registry-schema contract changed in Foundation 12.

## 3. v0.2 tooling addition

Foundation 12 adds optional offline replay-registry backup and verified recovery:

- `coin/m2m_registry_backup.py`
- `coin/m2m_registry_backup_cli.py`
- profile `l28-m2m-replay-registry-backup/v0.1`
- report `l28-m2m-registry-backup-report/v0.1`

Backup and recovery are tooling additions within the v0.2.0 release. They do not create a new envelope or transcript protocol profile.

## 4. Historical v0.1.0 release

L28 M2M v0.1.0 remains available and immutable at tag `l28-m2m-v0.1.0` (commit `7215d585a38155b5a36e7ebe077dcad43e810388`). Its manifest `docs/m2m/release_manifest_v0.1.json` is included in the v0.2 manifest inventory as `historical_release_manifest` and must remain byte-for-byte unchanged.

## 5. Backup artifact boundary

Backup files are:

- unencrypted
- unauthenticated
- locally correlatable hash-only SQLite artifacts
- not settlement proofs, finality proofs, or service-completion records

SHA-256 detects byte changes but does not establish authorship or trust.

## 6. Quiescence and publication

Backup and restore require quiescent source or backup inputs. Operators must close admission, audit, and registry handles before backup or restore.

Publication uses atomic hard-link creation (`os.link(temp, dest, follow_symlinks=False)`), never `os.rename` or `os.replace`. Restore never activates, overwrites, or replaces an operational registry.

## 7. Compatibility classes

| Change class | v0.2.0 policy |
|---|---|
| Documentation clarifications outside hashed inventory | Allowed only outside the frozen v0.2 inventory |
| Bug fix changing bytes in any inventoried artifact | Requires explicit manifest and release-note update |
| New protocol message types or envelope rules | Requires a new protocol profile |
| Dependency pin change | Requires explicit manifest review |
| Security exception | Must be explicit in release notes and compatibility document |

## 8. Non-claims

Neither the v0.1 nor v0.2 release manifest proves authorship, safety, settlement, finality, service completion, or spending authority. Manifest IDs are integrity identifiers only.

## 9. Related documents

- [release_manifest_v0.2.json](release_manifest_v0.2.json)
- [release_notes_v0.2.md](release_notes_v0.2.md)
- [release_manifest_v0.1.json](release_manifest_v0.1.json)
- [registry_backup_recovery_v0.1.md](registry_backup_recovery_v0.1.md)
- [README.md](README.md)
