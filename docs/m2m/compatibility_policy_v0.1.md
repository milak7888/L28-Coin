# L28 M2M v0.1.0 Compatibility Policy

**Document:** L28 M2M Compatibility Policy v0.1

**Status:** Frozen compatibility policy (Foundation 11)

**Release:** L28 M2M v0.1.0 (`frozen`)

**Manifest version:** `l28-m2m-release-manifest/v0.1`

**Compatibility profile:** `l28-m2m/v0.1`

## 1. Purpose

This policy defines what is frozen by the L28 M2M v0.1.0 release and how independent verifiers MUST validate the published release manifest.

It is subordinate to [L28 Protocol v1.0.0](../../PROTOCOL.md). Where any M2M rule conflicts with L28 Protocol v1.0.0, L28 Protocol v1.0.0 prevails.

## 2. Frozen identity

| Field | Value |
|---|---|
| Release name | `L28 M2M v0.1.0` |
| Release version | `0.1.0` |
| Intended tag | `l28-m2m-v0.1.0` |
| Manifest status | `frozen` |
| Compatibility profile | `l28-m2m/v0.1` |
| Envelope `protocol_version` | `0.1` |

## 3. Manifest integrity

### 3.1 Hash algorithm

Artifact digests and the manifest integrity identifier use **SHA-256** rendered as lowercase hexadecimal (`sha256_hex`).

### 3.2 Manifest integrity identifier algorithm

```
manifest_id = SHA-256(
  L28-M2M-V0.1-RELEASE-MANIFEST\x00
  || L28-M2M Canonical JSON v0.1(manifest object excluding manifest_id)
)
```

The domain separator is the UTF-8 byte sequence ending in `NUL` (`0x00`), matching other M2M v0.1 integrity identifiers.

Canonicalization MUST use the same rules as `coin.m2m_verifier.canonical_bytes`.

### 3.3 Artifact inventory rules

Each manifest `artifacts[]` entry MUST contain:

- `path` — repository-relative POSIX path
- `role` — non-empty value from the approved bounded role set below
- `sha256` — lowercase hex digest of raw file bytes
- `size_bytes` — byte length of the file

Approved `role` values:

- `runtime` — `coin/m2m_*.py`
- `normative_document` — `docs/m2m/*.md` except release-packaging documents
- `test_vector` — `docs/m2m/test_vectors*.json`
- `conformance_test` — `tests/test_m2m_*.py`
- `protocol_dependency` — `PROTOCOL.md`, `coin/tx_validation.py`
- `dependency_lock` — `requirements-m2m.txt`
- `ci` — `.github/workflows/ci.yml`
- `legal` — `LICENSE`, `NOTICE`
- `release_document` — release notes and compatibility policy

Release-packaging markdown (`release_document`):

- `docs/m2m/release_notes_v0.1.md`
- `docs/m2m/compatibility_policy_v0.1.md`

Entries MUST be sorted lexicographically by `path`.

The inventory MUST include every tracked file in these groups:

1. `coin/m2m_*.py`
2. `docs/m2m/*.md`
3. `docs/m2m/test_vectors*.json`
4. `tests/test_m2m_*.py`
5. `.github/workflows/ci.yml`, `requirements-m2m.txt`, `PROTOCOL.md`, `coin/tx_validation.py`, `LICENSE`, `NOTICE`

### 3.4 Excluded paths

Only this path MUST NOT appear in `artifacts[]`:

- `docs/m2m/release_manifest_v0.1.json`

### 3.5 Forbidden manifest content

The manifest MUST NOT contain timestamps, hostnames, usernames, process identifiers, absolute filesystem paths, private material, generated secrets, environment-specific values, or unverifiable claims.

## 4. Frozen protocol contracts

The `contracts` object in [release_manifest_v0.1.json](release_manifest_v0.1.json) is authoritative for:

- L28-M2M Canonical JSON v0.1
- Domain-separated digest prefixes
- Ed25519 (`ed25519`) signature suite
- Stable public result codes for verifier, transcript, replay registry, registry audit, and conformance CLI surfaces
- Report profile/version identifiers for conformance, admission, and registry-audit reports
- CLI version strings and exit-code mappings
- Replay registry schema version `1`
- Settlement citation dependency on `coin.tx_validation.compute_tx_id`

Any change to a frozen contract or to any inventoried artifact byte sequence requires a new compatibility profile and manifest; it MUST NOT be backported silently into v0.1.0.

## 5. Supported runtime boundary

Only the following runtime boundary is established by public CI and tests:

- CPython 3.11
- `cryptography==49.0.0`

Implementations MUST NOT claim broader Python or operating-system support under the `l28-m2m/v0.1` profile without a new tested release line and manifest.

## 6. Compatibility classes

| Change class | v0.1.0 policy |
|---|---|
| Documentation clarifications with no contract or artifact change | Allowed only outside the frozen inventory |
| Bug fix that changes bytes in any inventoried artifact | Requires new release (not a silent patch) |
| New message types, codes, domain separators, or CLI behavior | Requires new compatibility profile |
| Dependency pin change | Requires new manifest and explicit review |
| L28 Protocol v1.0.0 change | M2M remains subordinate; may force new M2M release |

## 7. Related documents

- [release_manifest_v0.1.json](release_manifest_v0.1.json)
- [release_notes_v0.1.md](release_notes_v0.1.md)
- [interoperability_profile_v0.1.md](interoperability_profile_v0.1.md)
- [README.md](README.md)
