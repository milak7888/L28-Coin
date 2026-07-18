# L28 Creator-Wallet Control Evidence Bundle v0.1

**Status:** Offline public verification only; non-activation

## Purpose

Foundation 31 defines a bounded deterministic bundle of independently verified Foundation 30 creator-wallet control-proof evidence objects. Success means every member passed Foundation 30 verification and the bundle satisfied canonical ordering, uniqueness, and aggregate-commitment rules. It does not prove a live balance, authorize a transfer, or activate runtime state.

## Public identifiers

- Bundle: `l28-creator-wallet-control-evidence-bundle/v0.1`
- Verifier: `l28-creator-wallet-control-evidence-bundle-verifier/v0.1`
- CLI report: `l28-creator-wallet-control-evidence-bundle-report/v0.1`
- Member evidence: `l28-creator-wallet-control-proof-evidence/v0.1`
- Member count: 1 through 32
- Maximum encoded bundle size: 270336 bytes

## Schema

The bundle is one JSON object with exactly `bundle_version` followed by `members`. Members contains 1 through 32 Foundation 30 evidence objects. Unknown, missing, duplicate, reordered, or incorrectly typed fields fail closed, as do duplicate JSON keys, invalid UTF-8, non-finite numbers, unsupported inputs, and oversized input.

## Member verification

Every member must independently pass `verify_creator_wallet_control_proof_evidence_json`. Foundation 31 recomputes each `evidence_sha256`; caller-supplied digest claims are not trusted. Any failed member fails the entire bundle.

## Canonical ordering and duplicates

Members must be supplied in strictly ascending lexical order by recomputed lowercase `evidence_sha256`. The verifier must not silently reorder members. It rejects duplicate recomputed evidence hashes and duplicate `expected_challenge_id` values.

## Aggregate commitment

The commitment body contains exactly the bundle version and the strictly ordered array `member_evidence_sha256`. Canonical JSON uses UTF-8, `ensure_ascii=False`, `allow_nan=False`, `sort_keys=True`, and `separators=(",", ":")`.

The aggregate commitment is lowercase hexadecimal:

`sha256(UTF8("l28-creator-wallet-control-evidence-bundle/v0.1") || 0x00 || canonical_json_bytes(commitment_body))`

## Failure behavior

The verifier fails closed on malformed, empty, oversized, over-capacity, duplicate, noncanonical, or unverifiable bundles. Public results contain sanitized stable codes and no raw exception, path, credential, or secret.

## Security boundary

The production core accepts JSON text or bytes only and performs no filesystem discovery, filesystem access, or mutation. The optional CLI reads one explicit regular-file path and rejects directories and symbolic links.

Foundation 31 does not load or modify wallets; access seeds, credentials, or private keys; create signatures or transactions; transfer L28; read or mutate ledgers; connect to peers; start listeners; or activate mining, checkpoints, deployments, or runtime nodes. Real creator secret material must never appear in source, tests, documentation, evidence, commands, or logs.

## Non-claims

A successful bundle is offline public verification evidence only. It does not establish current spendability, a live wallet balance, transfer authorization, historical allocation settlement, or runtime state.
