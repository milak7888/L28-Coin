# L28 M2M v0.2.0 Release Notes (Release Candidate)

**Release name:** L28 M2M v0.2.0

**Status:** `frozen` (release candidate until merge, CI validation, and tagging)

**Release compatibility profile:** `l28-m2m-release-compatibility/v0.2`

**Protocol profile:** `l28-m2m/v0.1` (unchanged)

**Intended tag after merge:** `l28-m2m-v0.2.0` (not created by this milestone)

**Manifest:** [release_manifest_v0.2.json](release_manifest_v0.2.json)

## Summary

Foundation 13 freezes the L28 M2M v0.2.0 release candidate with a dual-manifest model. The v0.2 manifest inventories the complete current public surface and includes the immutable v0.1.0 manifest as a historical artifact.

## v0.1 capabilities retained

Foundations 5–11 remain unchanged at the protocol profile `l28-m2m/v0.1`:

- Verify-only Ed25519 envelope verification
- Offline transcript validation
- Conformance CLI and deterministic reports
- Local replay/idempotency registry
- Optional replay admission gate
- Read-only registry audit

## v0.2 addition: Foundation 12 backup and recovery

Foundation 12 adds offline replay-registry backup and verified recovery:

- `coin/m2m_registry_backup.py`
- `coin/m2m_registry_backup_cli.py`
- profile `l28-m2m-replay-registry-backup/v0.1`
- report `l28-m2m-registry-backup-report/v0.1`

Publication uses true atomic hard-link no-overwrite creation (`os.link` with `follow_symlinks=False`). Source and backup inputs must be quiescent. There is no overwrite, migration, encryption, automatic activation, or repair.

## Historical v0.1.0 release

Published release `l28-m2m-v0.1.0` remains immutable at commit `7215d585a38155b5a36e7ebe077dcad43e810388`. See [release_manifest_v0.1.json](release_manifest_v0.1.json).

## Limitations

- Backup files are unencrypted and locally correlatable
- Backup is not an online snapshot service
- Restore creates a new destination only; it does not activate or replace operational registries
- Supported runtime: CPython 3.11 with `cryptography==49.0.0` only
- Manifest IDs are integrity identifiers only, not trust anchors

## Verification

Offline tests in `tests/test_m2m_release_v0_2.py` independently verify the v0.2 manifest inventory, contracts, and historical v0.1 anchoring.

**Validated test count:** 376

## Non-goals

This release candidate does not create a Git tag, GitHub Release, package, or signature. It does not change runtime behavior beyond documenting and freezing the Foundation 12 surface.
