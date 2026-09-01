# Operator Decision Record — LSOD-CUS-012

## Decision identity

- **Decision ID:** `LSOD-CUS-012`
- **Decision status:** `REQUIRES_SECURITY_EXPERT_REVIEW`
- **Effective version:** `v1.0`
- **Effect:** This version records an unresolved, fail-closed custody implementation gate and grants no implementation or activation authority.

## Original source references

- `docs/local_signer_implementation_gate_matrix_v0.1.md`: `F122-G02`, `F122-G07`, `F122-G08`, and `F122-B04`; custody implementation gate.
- `docs/local_signer_operator_decision_register_v0.1.md`: decision `LSOD-CUS-012`.
- `docs/local_signer_operator_resolution_packet_v0.1.md`: `LSOD-CUS-012`, classified `OPERATOR_CAN_DECIDE_NEXT` without an approved scope.

## Accountable authority

`UNASSIGNED`. Resolution requires a named L28 security approver and an independent custody reviewer.

## Selected policy or value

None. No non-key/non-signing implementation scope, staged gate, reviewer, evidence package, deployment boundary, or activation authority was explicitly provided.

## Rationale

Foundation126 allows a later bounded proposal; it does not authorize custody implementation. Approval without resolving the custody prerequisites and naming reviewers would permit architecture drift and premature activation. The gate remains fail closed.

## Threat model

- Unsafe custody runtime or architecture drift.
- Exposure or misuse of key material.
- Inadequate lifecycle, recovery, or compromise controls.
- Self-review, premature deployment, or signer activation.

## Dependencies

- `LSOD-CUS-001` through `LSOD-CUS-011` remain prerequisites and are not resolved by this record.
- `LSOD-OPS-009` remains unresolved.
- `LSOD-GAT-004` signer activation remains blocked.

## Required evidence

- Separately authorized, traceable custody implementation scope and trust boundary.
- Complete custody-control evidence for generation/import, isolation, access, lifecycle, backup/recovery, destruction, compromise response, and custody verification.
- Explicit prohibited-capability and non-activation evidence.
- Named approval and independent-review records.

## Required tests

- Full custody conformance plan plus implementation-specific adversarial, isolation, lifecycle, recovery, compromise, and fault tests.
- Tests proving no real key operation, wallet access, signing, submission, broadcast, or settlement.
- Regression and remediation evidence for all findings.

## Independent review requirement

An independent end-to-end custody security review is mandatory. The reviewer must be independent of the implementation author and must approve neither deployment nor activation by implication.

## Change control

Any resolution must be a superseding version with explicit scope, authority, prerequisites, evidence, tests, and review. Implementation, deployment, and activation remain separate authorization events.

## Rollback rules

No implementation is approved. A later authorization must define revocation and safe-disable procedures before becoming effective. Withdrawal requires auditable supersession, preservation of evidence, and return to fail-closed non-execution.

## Authority and non-activation invariants

- L28 Protocol v1.0.0 remains authoritative; `coin.tx_validation.validate_transaction` remains the canonical validator.
- Authorization is not validation. Eligibility is not signer invocation.
- No signer or custody component may override issuance, supply, canonical height, validation, consensus, history, or settlement.
- Protected facts remain: `28000000`, `11130000`, `2824584`, `500000`, `2324584`, `210000`, `[28,14,7,3,1,0]`, `100877`, `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.
- Bitcoin remains external evidence only; `LSOD-GAT-001` through `LSOD-GAT-004` remain blocked.
- This record authorizes no signer, wallet, key, signature, RPC, network, broadcast, settlement, database, deployment, or testnet behavior.
