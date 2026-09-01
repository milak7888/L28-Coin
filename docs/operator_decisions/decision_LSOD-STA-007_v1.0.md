# Operator Decision Record — LSOD-STA-007

## Decision identity

- **Decision ID:** `LSOD-STA-007`
- **Decision status:** `REQUIRES_SECURITY_EXPERT_REVIEW`
- **Effective version:** `v1.0`
- **Effect:** This version records an unresolved, fail-closed economic-control policy; no spending is authorized.

## Original source references

- `docs/local_signer_implementation_gate_matrix_v0.1.md`: `F122-G04`; spending-limit state control.
- `docs/local_signer_operator_decision_register_v0.1.md`: decision `LSOD-STA-007`.
- `docs/local_signer_operator_resolution_packet_v0.1.md`: `LSOD-STA-007`, classified `OPERATOR_CAN_DECIDE_NEXT` without selected partitions, windows, treatment, units, or limits.

## Accountable authority

`UNASSIGNED`. Resolution requires a named local economic-control approver and independent economic/concurrency reviewer.

## Selected policy or value

None. No payer/asset/policy partition, integer accounting unit, time window, pending/reservation treatment, per-request limit, or cumulative limit was explicitly supplied. Missing policy or state fails closed.

## Rationale

Foundation126 permits the operator to define objectives and shape next, but it supplies no production values. Guessing any value or partition would silently create economic authority and risk overspend. This record therefore approves none.

## Threat model

- Overspending through wrong partitions or ambiguous windows.
- Double consumption under concurrency or duplicate requests.
- Integer overflow, unit mismatch, or implicit unlimited behavior.
- Exclusion or double-counting of pending/reserved amounts.
- Rollback of cumulative counters.

## Dependencies

- `LSOD-EVD-006`, `LSOD-STA-002`, `LSOD-STA-003`, and `LSOD-OPS-001` remain unresolved.
- Atomic replay/economic-control state gates remain unresolved.
- `LSOD-GAT-004` signer activation remains blocked.

## Required evidence

- Versioned authenticated economic-control policy defining exact partitions, integer unit, windows, pending/reservation rules, and limits.
- Atomic counter/reservation design and implementation evidence with integrity/version binding.
- Named accountable approval and independent review.

## Required tests

- Exact boundary, below/at/above-limit, integer overflow, unit mismatch, window rollover, missing-state, corrupt-state, and fail-closed tests.
- Deterministic concurrency/race tests covering reservations, duplicate requests, and cumulative spend.
- Tests proving authorization cannot replace `coin.tx_validation.validate_transaction`.

## Independent review requirement

Independent economic-control and concurrency review is mandatory before approval. It must assess partition correctness, arithmetic, atomicity, recovery, and fail-closed behavior.

## Change control

Resolution requires a superseding version naming every selected policy value, authority, rationale, evidence, tests, and review. Any limit, unit, partition, window, or pending treatment change requires a new authenticated version and migration/reconciliation plan; this record authorizes no migration.

## Rollback rules

Counters and consumption state may not roll backward. There is no approved policy to restore. A later policy withdrawal requires an auditable superseding version and compensating records, with fail-closed handling of ambiguous state.

## Authority and non-activation invariants

- L28 Protocol v1.0.0 remains authoritative; `coin.tx_validation.validate_transaction` remains the canonical validator.
- Authorization is not validation. Eligibility is not signer invocation.
- Economic controls cannot override issuance, supply, canonical height, validation, consensus, history, or settlement.
- Protected facts remain: `28000000`, `11130000`, `2824584`, `500000`, `2324584`, `210000`, `[28,14,7,3,1,0]`, `100877`, `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.
- Bitcoin remains external evidence only; `LSOD-GAT-001` through `LSOD-GAT-004` remain blocked.
- This record authorizes no signer, wallet, key, signature, RPC, network, broadcast, settlement, database, deployment, or testnet behavior.
