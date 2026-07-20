# L28 Creator-Wallet Transfer-Intent Authorization v0.1

**Status:** Offline public signature verification only; non-activation

## Purpose

Foundation 33 defines a bounded authorization object proving that the fixed
public L28 creator key signed an exact, independently verified Foundation 32
unsigned transfer intent.

A valid authorization is not a transaction, balance proof, transfer execution,
ledger instruction, network message, or runtime authorization.

## Public identifiers

- Authorization and domain: `l28-creator-wallet-transfer-intent-authorization/v0.1`
- Verifier: `l28-creator-wallet-transfer-intent-authorization-verifier/v0.1`
- CLI report: `l28-creator-wallet-transfer-intent-authorization-report/v0.1`
- Embedded intent: `l28-creator-wallet-transfer-intent/v0.1`
- Maximum encoded authorization size: `8192` bytes

## Exact schema

Fields appear exactly in this order:

1. `authorization_version`
2. `domain`
3. `intent`
4. `intent_sha256`
5. `intent_id`
6. `creator_address`
7. `creator_public_key`
8. `signature`
9. `authorization_id`

Unknown, missing, reordered, duplicated, or incorrectly typed fields fail
closed. Duplicate keys are rejected at every JSON depth.

## Foundation 32 binding

The embedded intent is reverified through the Foundation 32 core using explicit
caller-supplied expected control-bundle SHA-256 and aggregate commitment.
`intent_sha256` and `intent_id` must equal the recomputed results. Core code
performs no file, bundle, wallet, ledger, clock, replay-state, or network lookup.

## Signature payload

The Ed25519 signature covers an object with exactly these fields:

1. `authorization_version`
2. `domain`
3. `intent_sha256`
4. `intent_id`
5. `creator_address`
6. `creator_public_key`

Canonical JSON is UTF-8 with `sort_keys=True`, `ensure_ascii=False`, separators
`(",", ":")`, no non-finite numbers, and no trailing newline. The domain is a
signed field. The signature is exactly 64 bytes encoded as 128 lowercase
hexadecimal characters and is verified only with the fixed public creator key.

## Authorization identifier

`authorization_id` is SHA-256 over the UTF-8 authorization-version domain, one
zero byte, and canonical JSON of every authorization field except
`authorization_id`, including the embedded intent and signature.

## Expiry and replay

The embedded expiry and nonce remain committed. This offline verifier uses no
clock or replay state and makes no current-validity or replay-prevention claim.

## Stable result codes

Stable codes include `ok`, `input_type_invalid`, `input_too_large`,
`encoding_invalid`, `json_invalid`, `duplicate_key`, `schema_invalid`,
`version_invalid`, `domain_invalid`, `intent_invalid`,
`intent_binding_invalid`, `identity_invalid`, `signature_invalid`,
`authorization_id_invalid`, and `internal_error`. Unexpected exceptions are
sanitized.

## Security boundary

Production core imports no Ed25519 private-key primitive; loads no wallet, seed,
credential, or private key; creates no signature or transaction; executes no
transfer; reads or mutates no ledger; reads no clock or replay registry; opens
no file; performs no automatic discovery; and starts no network or runtime.

The CLI accepts only one explicit caller-supplied regular-file path and rejects
symbolic links, directories, missing paths, and oversized files.

Tests use only ephemeral non-production Ed25519 keys and may patch the fixed
public identity in memory. The real creator private key must never appear in
source, tests, documentation, commands, logs, fixtures, or repository history.

## Success claim

Success proves only that the fixed creator public key authorized the exact
verified Foundation 32 unsigned intent. It does not prove balance,
current-time validity, replay safety, execution, ledger acceptance, settlement,
or finality.
