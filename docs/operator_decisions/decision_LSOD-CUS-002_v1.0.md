# Operator Decision Record — LSOD-CUS-002

## Decision identity

- **Decision ID:** `LSOD-CUS-002`
- **Decision status:** `REQUIRES_SECURITY_EXPERT_REVIEW`
- **Effective version:** `v1.0`
- **Effect:** This version records an unresolved, fail-closed decision and enables no key-material path.

## Original source references

- `docs/local_signer_implementation_gate_matrix_v0.1.md`: `F122-G02`; custody generation/import control.
- `docs/local_signer_operator_decision_register_v0.1.md`: decision `LSOD-CUS-002`.
- `docs/local_signer_operator_resolution_packet_v0.1.md`: `LSOD-CUS-002`, classified `OPERATOR_CAN_DECIDE_NEXT` without a selected option.

## Accountable authority

`UNASSIGNED`. A named custody-policy approver and independent custody-ceremony reviewer must be recorded before resolution.

## Selected policy or value

None. The operator has not explicitly selected `generation`, `import`, `both`, or `neither`, nor supplied an approved origin allowlist. Consequently every generation/import path remains prohibited.

## Rationale

Foundation126 establishes that the operator may decide the boundary next; it does not choose one. Defaulting to an enabled path would invent a production custody policy. Missing approval therefore fails closed.

## Threat model

- Untrusted entropy or material origin.
- Unauthorized or duplicate generation/import.
- Transient key-material leakage.
- Unverifiable provenance or bypass of custody separation.

## Dependencies

- `LSOD-CUS-001`, `LSOD-CUS-003`, and `LSOD-CUS-005` remain unresolved prerequisites.
- Any enabled path also depends on the remaining custody lifecycle, evidence, and runtime security decisions.
- `LSOD-GAT-004` signer activation remains blocked.

## Required evidence

- A versioned boundary specifying the selected allowed path and an explicit origin allowlist.
- Ceremony and provenance records for each permitted origin.
- Evidence of isolation, separation of duties, duplicate detection, and zero unauthorized material exposure.
- Named accountable approval and independent review.

## Required tests

- Deterministic rejection of unauthorized paths, unverifiable origins, duplicate material, malformed evidence, and incomplete ceremony records.
- Boundary tests proving no generation/import operation is attempted while the decision is unresolved.
- Custody conformance and adversarial review for any later selected path.

## Independent review requirement

An independent custody-ceremony and security review is mandatory before a path may be approved. No real key, seed, mnemonic, xprv, wallet, HSM, or KMS operation is authorized for this review record.

## Change control

Resolution requires a superseding version naming the selected option, allowed origins, authority, evidence, tests, and review. Adding or broadening a path requires a new decision version and ceremony; no implicit defaults are permitted.

## Rollback rules

No enabled path exists. A future withdrawal must quarantine the affected path and material, preserve audit provenance, revoke its authority, and publish a superseding decision. It must not silently restore an older policy.

## Authority and non-activation invariants

- L28 Protocol v1.0.0 remains authoritative; `coin.tx_validation.validate_transaction` remains the canonical validator.
- Authorization is not validation. Eligibility is not signer invocation.
- No signer or custody component may override issuance, supply, canonical height, validation, consensus, history, or settlement.
- Protected facts remain: `28000000`, `11130000`, `2824584`, `500000`, `2324584`, `210000`, `[28,14,7,3,1,0]`, `100877`, `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.
- Bitcoin remains external evidence only; `LSOD-GAT-001` through `LSOD-GAT-004` remain blocked.
- This record authorizes no signer, wallet, key, signature, RPC, network, broadcast, settlement, database, deployment, or testnet behavior.
