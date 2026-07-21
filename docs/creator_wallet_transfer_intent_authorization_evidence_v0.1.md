# L28 Creator-Wallet Transfer-Intent Authorization Evidence v0.1

**Status:** Offline public verification only; non-activation

## Purpose

Foundation 34 defines deterministic public evidence that binds a Foundation 33
creator-wallet transfer-intent authorization to its independently recomputed
verification report.

A successful result proves only that the supplied public authorization was
reverified and its deterministic public report was recomputed. It does not
establish a live balance, enforce expiry, prevent replay, execute a transfer,
mutate a ledger, or activate a wallet, network, or runtime.

## Public identifiers

- Evidence: `l28-creator-wallet-transfer-intent-authorization-evidence/v0.1`
- Verifier: `l28-creator-wallet-transfer-intent-authorization-evidence-verifier/v0.1`
- CLI report: `l28-creator-wallet-transfer-intent-authorization-evidence-report/v0.1`
- Bound authorization report:
  `l28-creator-wallet-transfer-intent-authorization-report/v0.1`
- Maximum encoded evidence size: `16384` bytes

## Evidence schema

Evidence is one JSON object with exactly these fields in this order:

    {
      "evidence_version": "l28-creator-wallet-transfer-intent-authorization-evidence/v0.1",
      "expected_control_bundle_sha256": "64 lowercase hexadecimal characters",
      "expected_control_bundle_aggregate_commitment": "64 lowercase hexadecimal characters",
      "authorization": {},
      "report": {}
    }

Unknown, missing, reordered, or duplicate fields are rejected. Duplicate keys
at any nesting depth are rejected.

## Authorization verification

The verifier must independently reverify the embedded Foundation 33
authorization using both expected Foundation 31 bundle commitments declared in
the evidence.

Each expected commitment must be exactly 64 lowercase hexadecimal characters.
The verified authorization and embedded intent must bind to those exact values.

## Authorization report binding

The embedded report must use the exact Foundation 33 report field order and
must equal the deterministic report recomputed from the Foundation 33
verification result.

The report identifier is SHA-256 over:

1. UTF-8 bytes of
   `l28-creator-wallet-transfer-intent-authorization-report/v0.1`;
2. one NUL byte;
3. canonical JSON of the complete report body excluding `report_id`.

Canonical JSON uses sorted keys, UTF-8, `ensure_ascii=false`,
`allow_nan=false`, and separators `(",", ":")`.

## Evidence commitment

`evidence_sha256` is SHA-256 over canonical UTF-8 JSON of the complete validated
evidence object. This value is returned by the verifier and is not an additional
evidence field.

## Expiry and replay boundary

The embedded expiry and nonce remain structurally and cryptographically
committed.

This verifier does not access a clock, determine current-time validity, access
replay state, reserve a nonce, or claim uniqueness.

## Security boundary

Production verification accepts JSON text or bytes only and performs no
filesystem discovery or mutation.

It does not:

- load or unlock a wallet;
- access, import, reconstruct, or store private keys or seeds;
- create a signature;
- create, sign, broadcast, or execute a transfer;
- read or mutate a ledger;
- access a clock or replay database;
- open a network connection;
- activate mining, deployment, checkpoints, or runtime nodes.

The real creator private key must never appear in evidence, tests,
documentation, commands, logs, or repository files.

## Failure policy

Verification fails closed on invalid input type, oversized input, invalid UTF-8,
malformed JSON, non-finite values, duplicate keys, invalid top-level type,
schema mismatch, commitment mismatch, authorization failure, report mismatch,
or unexpected internal error.

## Non-authorization statement

A valid Foundation 34 result is public verification evidence only. It is not
permission to spend L28 and is not an executable transaction or ledger command.
