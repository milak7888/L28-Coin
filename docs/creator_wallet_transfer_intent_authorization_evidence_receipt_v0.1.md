# L28 Creator-Wallet Transfer-Intent Authorization Evidence Receipt v0.1

**Status:** Offline public verification only; non-activation

## Purpose

Foundation 35 defines a deterministic offline public verification receipt for one
successfully verified Foundation 34 creator-wallet transfer-intent
authorization-evidence object.

A successful receipt proves only that the embedded Foundation 34 evidence was
independently reverified and that the receipt fields are exactly bound to the
Foundation 31 commitments, Foundation 33 authorization report identifier, and
Foundation 34 evidence commitment and verification result. It does not
establish a live balance, enforce expiry, prevent replay, execute a transfer,
mutate a ledger, authorize spending, or activate a wallet, network, or runtime.

This receipt is not an M2M `service_receipt`, settlement citation, transaction,
or ledger command.

## Public identifiers

- Receipt: `l28-creator-wallet-transfer-intent-authorization-evidence-receipt/v0.1`
- Verifier:
  `l28-creator-wallet-transfer-intent-authorization-evidence-receipt-verifier/v0.1`
- CLI report:
  `l28-creator-wallet-transfer-intent-authorization-evidence-receipt-report/v0.1`
- Bound Foundation 34 evidence:
  `l28-creator-wallet-transfer-intent-authorization-evidence/v0.1`
- Bound Foundation 33 authorization report:
  `l28-creator-wallet-transfer-intent-authorization-report/v0.1`
- Maximum encoded receipt size: `24576` bytes

## Exact receipt schema

The receipt is one JSON object with exactly these fields in this order:

```json
{
  "receipt_version": "l28-creator-wallet-transfer-intent-authorization-evidence-receipt/v0.1",
  "expected_control_bundle_sha256": "64 lowercase hexadecimal characters",
  "expected_control_bundle_aggregate_commitment": "64 lowercase hexadecimal characters",
  "evidence": {},
  "evidence_sha256": "64 lowercase hexadecimal characters",
  "authorization_report_id": "64 lowercase hexadecimal characters",
  "authorization_sha256": "64 lowercase hexadecimal characters",
  "authorization_id": "64 lowercase hexadecimal characters",
  "checks": [],
  "execution_authorized": false,
  "receipt_id": "64 lowercase hexadecimal characters"
}
```

Unknown, missing, reordered, duplicated, or incorrectly typed fields are
rejected. Duplicate JSON keys are rejected at every nesting depth. Non-finite
JSON numbers are rejected.

## Field rules

- `receipt_version` must equal the receipt identifier exactly.
- Both Foundation 31 commitment fields must be exactly 64 lowercase hexadecimal
  characters.
- `evidence` must be an object satisfying
  `docs/creator_wallet_transfer_intent_authorization_evidence_v0.1.md`.
- `evidence_sha256`, `authorization_report_id`, `authorization_sha256`, and
  `authorization_id` must each be exactly 64 lowercase hexadecimal characters.
- `checks` must be an array of strings.
- `execution_authorized` must be the JSON boolean `false`. Any other value fails
  closed.
- `receipt_id` must be exactly 64 lowercase hexadecimal characters.

## Foundation 34 verification

The verifier must independently invoke the Foundation 34 public evidence
verifier on the embedded `evidence` object, supplying both expected Foundation
31 commitments declared in the receipt.

Verification fails closed unless Foundation 34 returns success. Caller-supplied
digest claims are not trusted until recomputed from that independent result.

The receipt commitments must equal the commitments declared inside the embedded
Foundation 34 evidence.

## Binding requirements

After successful Foundation 34 verification, the receipt must bind exactly to:

1. both Foundation 31 commitments used for that verification;
2. the Foundation 33 authorization report identifier from the verified embedded
   Foundation 34 evidence report (`report.report_id`);
3. the Foundation 34 recomputed `evidence_sha256`;
4. the Foundation 34 recomputed `authorization_sha256` and `authorization_id`;
5. the Foundation 34 success checks array.

Any mismatch fails closed.

## Receipt identifier

`receipt_id` is lowercase hexadecimal SHA-256 over:

1. UTF-8 bytes of
   `l28-creator-wallet-transfer-intent-authorization-evidence-receipt/v0.1`;
2. one NUL byte;
3. canonical JSON of the complete receipt body excluding `receipt_id`.

Canonical JSON uses sorted keys, UTF-8, `ensure_ascii=false`,
`allow_nan=false`, and separators `(",", ":")`.

The nested Foundation 34 evidence retains its protocol-defined field order
during revalidation. Equivalent accepted formatting of the receipt envelope
produces the same `receipt_id`; semantic mutation changes the identifier or
fails verification.

## Expiry and replay boundary

Embedded expiry and nonce values remain structurally and cryptographically
committed inside the nested authorization path.

This verifier does not access a clock, determine current-time validity, access
replay state, reserve a nonce, claim uniqueness, or assert that an intent is
currently spendable.

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

The optional CLI may read only one explicitly supplied regular-file path and
must reject directories, symbolic links, missing paths, unreadable files, and
oversized files.

The real creator private key must never appear in receipts, tests,
documentation, commands, logs, or repository files.

## Failure policy

Verification fails closed on invalid input type, oversized input, invalid UTF-8,
malformed JSON, non-finite values, duplicate keys, invalid top-level type,
schema mismatch, commitment mismatch, Foundation 34 verification failure,
authorization-report binding mismatch, evidence-commitment mismatch, receipt-id
mismatch, `execution_authorized` not exactly false, or unexpected internal
error.

Public results use stable sanitized codes only and must not expose raw
exception text, paths, credentials, or secrets.

## Non-authorization statement

A valid Foundation 35 receipt is public offline verification evidence only. It
is not permission to spend L28, not an executable transaction, not a ledger
command, not settlement finality, and not runtime activation.
