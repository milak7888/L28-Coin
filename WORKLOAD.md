# L28 Workload Interface (Draft, Non-Normative)

Status: Draft (documentation only)
Scope: Defines an interface for future AI mining / proof-of-useful-work (PoUW)
Note: This does NOT change v1.0.0 issuance rules.

## Goal

Enable miners to prove they performed verifiable useful work (e.g., model evaluation, dataset transforms,
compute tasks) while remaining:
- deterministic
- verifiable
- machine-consumable
- non-investor-facing

## Where Work Attaches

Work claims MUST be attached to STRICT coinbase as metadata.
Coinbase validity in v1.0.0 remains defined by PROTOCOL.md.

Recommended fields (all strings unless noted):

- metadata.work_type: short identifier (e.g., "eval", "train_step", "retrieval_bench", "transform")
- metadata.work_spec_hash: hash of canonical work spec document (inputs/constraints)
- metadata.work_result_hash: hash of canonical result payload
- metadata.work_proof: compact proof blob (format depends on work_type)
- metadata.work_units: integer-like (declared work units, optional)
- metadata.work_verifier: verifier id/version (e.g., "l28-verifier/v0")

## Verifier Contract (Concept)

A verifier is a deterministic function:

verify(work_type, work_spec, work_result, work_proof) -> (ok: bool, score: int)

Rules:
- MUST be deterministic
- MUST fail-closed
- MUST be implementable by independent nodes
- MUST be pinned by version (no silent upgrades)

## Economics (Not in v1)

v1.0.0 reward is height-based and deterministic.
Future versions MAY incorporate verified work signals, but only as a major version change (v2.0.0+).

