# Operator Decision Record — LSOD-STA-012

## Decision identity

- **Decision ID:** `LSOD-STA-012`
- **Decision status:** `REQUIRES_SECURITY_EXPERT_REVIEW`
- **Effective version:** `v1.0`
- **Effect:** This version records an unresolved, fail-closed atomic-state implementation gate and authorizes no stateful runtime.

## Original source references

- `docs/local_signer_implementation_gate_matrix_v0.1.md`: `F122-G03`, `F122-G04`, `F122-G08`, and `F122-B04`; atomic-state implementation gate.
- `docs/local_signer_operator_decision_register_v0.1.md`: decision `LSOD-STA-012`.
- `docs/local_signer_operator_resolution_packet_v0.1.md`: `LSOD-STA-012`, classified `OPERATOR_CAN_DECIDE_NEXT` without an approved scope.

## Accountable authority

`UNASSIGNED`. Resolution requires a named L28 security approver and an independent state/concurrency reviewer.

## Selected policy or value

None. No abstract or non-production implementation scope, storage boundary, reviewer, acceptance evidence, deployment boundary, or activation authority was explicitly supplied.

## Rationale

Decision readiness does not authorize a database or runtime. Approving an unspecified state boundary before the semantic prerequisites are resolved would risk replay, double-spend-control consumption, and unsafe recovery. The gate remains closed.

## Threat model

- Replay or idempotency bypass.
- Lost updates and double consumption during concurrency.
- Partial commit, rollback, crash, or recovery inconsistency.
- Corrupt, stale, unavailable, or wrongly versioned state.
- Premature deployment or signer activation.

## Dependencies

- `LSOD-STA-001` through `LSOD-STA-011` remain prerequisites and are not resolved here.
- `LSOD-OPS-009` remains unresolved.
- `LSOD-GAT-004` signer activation remains blocked.

## Required evidence

- Separately authorized state-boundary proposal traceable to the atomic-state storage contract and conformance plan.
- Atomic check-and-record, spend/approval consumption, ordering, persistence, integrity, recovery, and unavailable-state evidence.
- Explicit non-production and prohibited-capability boundaries.
- Named approval and independent-review records.

## Required tests

- Deterministic replay, exact-duplicate/conflict, cumulative-spend, approval-consumption, concurrency-race, partial-commit, crash/recovery, corruption, unavailability, retention, and version-integrity tests.
- Adversarial/fault testing demonstrating fail-closed outcomes and no state rollback.
- Regression and remediation evidence for the separately authorized scope.

## Independent review requirement

Independent distributed-state/concurrency security review is mandatory. It must assess linearization, durability, recovery, integrity, and boundary isolation without implying deployment or activation approval.

## Change control

Resolution requires a superseding record defining scope, authority, prerequisites, evidence, tests, and review. Implementation, database selection, migration, deployment, and activation are distinct later authorizations.

## Rollback rules

No state implementation is approved. A future design must prohibit rollback of replay, spend, and approval-consumption state and use auditable compensating/versioned recovery. Withdrawal requires supersession and fail-closed disablement.

## Authority and non-activation invariants

- L28 Protocol v1.0.0 remains authoritative; `coin.tx_validation.validate_transaction` remains the canonical validator.
- Authorization is not validation. Eligibility is not signer invocation.
- State controls cannot override issuance, supply, canonical height, validation, consensus, history, or settlement.
- Protected facts remain: `28000000`, `11130000`, `2824584`, `500000`, `2324584`, `210000`, `[28,14,7,3,1,0]`, `100877`, `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.
- Bitcoin remains external evidence only; `LSOD-GAT-001` through `LSOD-GAT-004` remain blocked.
- This record authorizes no signer, wallet, key, signature, RPC, network, broadcast, settlement, database, deployment, or testnet behavior.
