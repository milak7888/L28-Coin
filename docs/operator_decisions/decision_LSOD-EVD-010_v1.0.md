# Operator Decision Record — LSOD-EVD-010

## Decision identity

- **Decision ID:** `LSOD-EVD-010`
- **Decision status:** `REQUIRES_SECURITY_EXPERT_REVIEW`
- **Effective version:** `v1.0`
- **Effect:** This version records an unresolved, fail-closed decision. It approves no implementation, deployment, activation, or production policy.

## Original source references

- `docs/local_signer_implementation_gate_matrix_v0.1.md`: `F122-G01`, `F122-G08`, and `F122-B04`; authenticated-evidence implementation gate.
- `docs/local_signer_operator_decision_register_v0.1.md`: decision `LSOD-EVD-010`.
- `docs/local_signer_operator_resolution_packet_v0.1.md`: `LSOD-EVD-010`, classified `OPERATOR_CAN_DECIDE_NEXT` but not selected or approved.

## Accountable authority

`UNASSIGNED`. Resolution requires a named L28 security approver and an independent reviewer with authority recorded in the superseding decision evidence. Decision readiness is not approval authority.

## Selected policy or value

None. No bounded implementation scope, trust-zone allocation, reviewer assignment, evidence package, prohibited-capability set, or approval was explicitly provided.

## Rationale

Foundation126 permits this item to be presented for a later operator decision; it does not select a candidate or prove approval. Approving without a named authority and explicit scope would silently authorize architecture and could be mistaken for runtime permission. The decision therefore remains unresolved and fails closed.

## Threat model

- Architecture drift from the authenticated-evidence contract.
- Self-certification or non-independent review.
- Unauthenticated evidence crossing the signer boundary.
- Unauthorized implementation, deployment, signer invocation, or activation.
- Treating signer eligibility as signer invocation or authorization as Protocol validation.

## Dependencies

- `LSOD-EVD-001` through `LSOD-EVD-009` remain unresolved prerequisites.
- `LSOD-OPS-009` remains unresolved.
- `LSOD-GAT-004` signer activation remains `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

## Required evidence

- A separately authorized, bounded implementation proposal naming components, trust zones, prohibited capabilities, reviewers, and deployment boundary.
- Traceability from the authenticated-evidence profile and conformance plan to implementation/configuration evidence.
- Explicit evidence that the milestone is non-activating and cannot sign, submit, broadcast, settle, or mutate ledger state.
- Named accountable approver and independent-review records.

## Required tests

- Authenticated-evidence conformance, malformed-evidence, revocation, freshness, replay-binding, and fail-closed tests.
- Adversarial, fault, regression, and remediation verification appropriate to the separately authorized scope.
- Tests proving mandatory binding to `coin.tx_validation.validate_transaction` without transferring validation authority.

## Independent review requirement

Independent end-to-end security review is mandatory before any later approval. The reviewer must be organizationally independent of the implementation author and must assess trust boundaries, evidence verification, non-execution controls, and deployment separation.

## Change control

Any resolution must supersede this record with a new version that identifies the selected scope, accountable authority, rationale, evidence, tests, and review outcome. Implementation, deployment, and activation require separate authorization; they cannot be implied by changing this record.

## Rollback rules

There is no approved policy to roll back. If a later version approves a scope and must be withdrawn, publish an auditable superseding decision, revoke its authority, preserve historical evidence, and return the boundary to fail-closed non-execution. Silent reversion is prohibited.

## Authority and non-activation invariants

- L28 Protocol v1.0.0 remains authoritative; `coin.tx_validation.validate_transaction` remains the canonical validator.
- Authorization is not validation. Eligibility is not signer invocation.
- No signer may override issuance, supply, canonical height, validation, consensus, history, or settlement.
- Protected facts remain: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; rewards `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.
- Bitcoin remains external evidence only. `LSOD-GAT-001` through `LSOD-GAT-004` remain blocked.
- This record authorizes no signer, wallet, key, signature, RPC, network, broadcast, settlement, database, deployment, or testnet behavior.
