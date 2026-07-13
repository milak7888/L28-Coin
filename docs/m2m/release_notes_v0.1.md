# L28 M2M v0.1.0 Release Notes (Release Candidate Branch)

**Release name:** L28 M2M v0.1.0

**Manifest status:** `frozen`

**Branch role:** release candidate (pre-tag)

**Intended tag after merge:** `l28-m2m-v0.1.0` (not created by this milestone)

**Compatibility profile:** `l28-m2m/v0.1`

**Manifest:** [release_manifest_v0.1.json](release_manifest_v0.1.json)

## Summary

Foundation 11 stabilizes the public L28 M2M coordination layer on a release-candidate branch. The published manifest status is `frozen`. This milestone does not add runtime functionality, change protocol behavior, or alter normative M2M documents other than the documentation index.

The release candidate publishes:

- A deterministic SHA-256 artifact inventory of the frozen public surface
- Frozen compatibility contracts extracted from the existing implementation
- A machine-verifiable manifest integrity identifier over the manifest body

## Frozen public surface

The manifest covers every tracked file in these groups:

- All `coin/m2m_*.py` modules (Foundations 5–10)
- All `docs/m2m/*.md` documents, including this file and [compatibility_policy_v0.1.md](compatibility_policy_v0.1.md)
- All `docs/m2m/test_vectors*.json` fixtures
- All `tests/test_m2m_*.py` offline test modules, including `tests/test_m2m_release_candidate.py`
- Explicit dependencies: `.github/workflows/ci.yml`, `requirements-m2m.txt`, `PROTOCOL.md`, `coin/tx_validation.py`, `LICENSE`, `NOTICE`

The only excluded path is `docs/m2m/release_manifest_v0.1.json` itself.

## Supported runtime

Established by CI and offline tests only:

- **Implementation:** CPython
- **Python release line:** 3.11
- **Cryptographic dependency:** `cryptography==49.0.0` (`requirements-m2m.txt`)

No operating-system support claim is made beyond what CI exercises.

## Components included

| Foundation | Component | Role |
|---|---|---|
| 5 | `coin/m2m_verifier.py` | Verify-only Ed25519 envelope verification |
| 6 | `coin/m2m_transcript_validator.py` | Offline ordered transcript validation |
| 7 | `coin/m2m_conformance_cli.py` | Offline conformance CLI and report |
| 8 | `coin/m2m_replay_registry.py` | Local offline replay/idempotency registry |
| 9 | Conformance CLI replay admission | Optional registry integration and admission report |
| 10 | `coin/m2m_registry_audit.py`, `coin/m2m_registry_audit_cli.py` | Read-only registry audit |

Settlement citation verification remains bound to `coin.tx_validation.compute_tx_id` and L28 Protocol v1.0.0.

## Verification

Recompute artifact SHA-256 hashes and the manifest integrity identifier from [release_manifest_v0.1.json](release_manifest_v0.1.json) using the algorithm in [compatibility_policy_v0.1.md](compatibility_policy_v0.1.md). The repository test `tests/test_m2m_release_candidate.py` performs this check offline.

## Non-goals

This release candidate branch does not:

- Create a Git tag, GitHub release, package, archive, or signature
- Start services, wallets, miners, or networks
- Change L28 Protocol v1.0.0 economics, ledger behavior, or settlement finality rules
- Claim live public-network availability
