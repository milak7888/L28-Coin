# L28 Creator-Wallet Control-Proof Evidence v0.1

**Status:** Offline public verification evidence; non-activation

## Purpose

Foundation 30 binds one caller-supplied Foundation 29 creator-wallet control proof to its expected challenge and deterministic Foundation 29 report.

Success means the public proof and report were recomputed and matched. It does not prove a live wallet balance, make historical allocation spendable, or authorize a transfer.

## Identifiers

- Evidence: `l28-creator-wallet-control-proof-evidence/v0.1`
- Verifier: `l28-creator-wallet-control-proof-evidence-verifier/v0.1`
- Bound Foundation 29 report: `l28-creator-wallet-control-proof-report/v0.1`
- CLI report: `l28-creator-wallet-control-proof-evidence-report/v0.1`
- Maximum evidence size: 8192 bytes

## Security boundary

The core accepts JSON text or bytes only. It performs no filesystem access, wallet lookup, private-key access, seed access, credential access, or signature creation.

It does not load a wallet, sign a transaction, transfer L28, mutate a ledger, connect to a peer, start a listener, mine, select a checkpoint, deploy software, or construct a runtime node.

The real creator private key must never be included in evidence, tests, documentation, commands, logs, or repository files.

## Evidence schema

The JSON object contains exactly these fields in this order:

```json
{
  "evidence_version": "l28-creator-wallet-control-proof-evidence/v0.1",
  "expected_challenge_id": "64-lowercase-hex-characters",
  "proof": {},
  "report": {}
}
```

- `evidence_version` must match exactly.
- `expected_challenge_id` is caller-selected and must match the proof.
- `proof` must satisfy `docs/creator_wallet_control_proof_v0.1.md`.
- `report` must match the recomputed Foundation 29 deterministic report.

Automatic challenge generation and automatic file discovery are not supported.

## Verification

The verifier fails closed unless it can:

1. Reject unsupported types and payloads larger than 8192 bytes before parsing.
2. Parse strict UTF-8 JSON without duplicate keys or non-finite numbers.
3. Enforce the exact schema, field order, version, and challenge shape.
4. Require `proof` and `report` to be objects.
5. Reverify the Foundation 29 public signature proof.
6. Recompute its proof commitment, checks, report body, and report identifier.
7. Require all runtime and mutation safety claims to remain false.
8. Compute the deterministic Foundation 30 evidence commitment.

Unexpected exceptions are sanitized as `internal_error`.

## Determinism

Commitments use UTF-8 JSON with `ensure_ascii=false`, `allow_nan=false`, sorted keys where canonical commitment is required, and compact separators.

The nested Foundation 29 proof retains its protocol-defined field order during revalidation. Equivalent accepted formatting produces the same commitment; semantic mutation changes the commitment or invalidates the report.

## CLI

```text
python -m coin.creator_wallet_control_proof_evidence_cli EVIDENCE_FILE
python -m coin.creator_wallet_control_proof_evidence_cli EVIDENCE_FILE --pretty
```

The CLI accepts one explicit regular-file path. Missing paths, directories, symbolic links, unreadable files, and oversized files fail closed. Compact and pretty reports are logically equivalent, and the report identifier is body-bound.

## Interpretation limits

Success proves only offline public challenge, signature-proof, report, and commitment consistency.

It does not prove current wallet possession, current spendable balance, canonical ledger ownership, transfer readiness, transfer authorization, or runtime availability.

Any future wallet use or transfer protocol requires a separate milestone, explicit authorization, canonical-ledger rules, and independent security review.
