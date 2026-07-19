# L28 Creator-Wallet Transfer Intent v0.1

**Status:** Offline unsigned intent verification only; non-activation

## Purpose

Foundation 32 defines a deterministic unsigned transfer-intent object for the
fixed public L28 creator identity.

A valid intent expresses public data that could be reviewed by a future,
separately authorized signing and execution system. It is not a transaction,
signature, balance proof, spending authorization, ledger instruction, or
network message.

## Public identifiers

- Intent: `l28-creator-wallet-transfer-intent/v0.1`
- Domain: `l28-creator-wallet-transfer-intent/v0.1`
- Verifier: `l28-creator-wallet-transfer-intent-verifier/v0.1`
- CLI report: `l28-creator-wallet-transfer-intent-report/v0.1`
- Maximum encoded intent size: `4096` bytes

## Intent schema

The intent is one JSON object with exactly these fields in this order:

```json
{
  "intent_version": "l28-creator-wallet-transfer-intent/v0.1",
  "domain": "l28-creator-wallet-transfer-intent/v0.1",
  "creator_address": "L28d7d0903ab9e10e706c418c31fac95109577cdea6",
  "recipient_address": "L28 plus 40 lowercase hexadecimal characters",
  "amount": 1,
  "nonce": "64 lowercase hexadecimal characters",
  "expires_at_unix": 1,
  "control_bundle_sha256": "64 lowercase hexadecimal characters",
  "control_bundle_aggregate_commitment": "64 lowercase hexadecimal characters",
  "intent_id": "64 lowercase hexadecimal characters"
}
```

Unknown, missing, reordered, or duplicate fields are rejected.

## Field rules

- `intent_version` and `domain` must exactly match the public identifiers.
- `creator_address` must equal the fixed public creator address.
- `recipient_address` must match `L28[0-9a-f]{40}` and must differ from the
  creator address.
- `amount` must be a strict positive JSON integer. Boolean, floating-point,
  string, zero, negative, missing, and null values are rejected.
- `nonce` is caller-supplied and must be exactly 64 lowercase hexadecimal
  characters.
- `expires_at_unix` must be a strict positive JSON integer.
- Both Foundation 31 commitment fields must be lowercase SHA-256 values.
- No signature, private key, seed, credential, or wallet path is permitted.

## Intent identity

`intent_id` is lowercase SHA-256 over:

1. the UTF-8 domain bytes
   `l28-creator-wallet-transfer-intent/v0.1\x00`;
2. followed by canonical JSON bytes for every intent field except `intent_id`.

Canonical JSON uses `ensure_ascii=false`, `allow_nan=false`, sorted keys,
separators `,` and `:`, and UTF-8 encoding.

Formatting differences do not alter `intent_id`. Any semantic mutation does.

## Foundation 31 binding

The intent commits to both the recomputed Foundation 31 `bundle_sha256` and
`aggregate_commitment`. The verifier does not discover or read a bundle file.

A commitment records logical linkage only. It does not convert historical
control evidence into transaction authorization.

## Expiry and replay boundary

The offline verifier confirms only the structure and commitment of
`expires_at_unix` and `nonce`.

It does not read a clock, ledger, replay registry, wallet, or network.
Therefore it does not claim that an intent is currently unexpired or unused.
Those checks require a future explicitly authorized stateful layer.

## Security boundary

Foundation 32 performs no wallet loading, private-key access, signature
creation, transaction construction, transfer execution, balance lookup,
ledger access or mutation, network access, mining, checkpoint, deployment, or
runtime activation.

The real creator private key must never be placed in an intent, repository
file, test, command, log, or report.
