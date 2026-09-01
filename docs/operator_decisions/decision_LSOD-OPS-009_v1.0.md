# Operator Decision Record — LSOD-OPS-009

## Decision identity

- **Decision ID:** `LSOD-OPS-009`
- **Decision status:** `REQUIRES_SECURITY_EXPERT_REVIEW`
- **Effective version:** `v1.0`
- **Effect:** This version records an unresolved, fail-closed implementation-assurance gate and grants no runtime or acceptance authorization.

## Original source references

- `docs/local_signer_implementation_gate_matrix_v0.1.md`: `F122-G08` and `F122-B04`; implementation assurance and activation gate.
- `docs/local_signer_operator_decision_register_v0.1.md`: decision `LSOD-OPS-009`.
- `docs/local_signer_operator_resolution_packet_v0.1.md`: `LSOD-OPS-009`, classified `OPERATOR_CAN_DECIDE_NEXT` without an approved assurance plan.

## Accountable authority

`UNASSIGNED`. Resolution requires a named assurance approver and an organizationally independent security reviewer.

## Selected policy or value

None. No test environments, pass criteria, remediation criteria, reviewer assignments, or assurance acceptance policy was explicitly supplied.

## Rationale

Foundation126 allows the assurance structure to be proposed next but does not approve acceptance criteria. Treating planned or offline tests as implementation acceptance would enable self-certification and overclaim conformance evidence. This gate remains unresolved.

## Threat model

- Untested adversarial, fault, concurrency, crash, recovery, or denial-of-service modes.
- Fixture/test evidence being misrepresented as production assurance.
- Self-certification, waived failures, or incomplete remediation.
- Premature runtime, deployment, or signer activation.

## Dependencies

- All prerequisite `LSOD-EVD-*`, `LSOD-CUS-*`, `LSOD-STA-*`, and `LSOD-OPS-001` through `LSOD-OPS-008` decisions remain unresolved where not separately approved.
- `LSOD-GAT-001` through `LSOD-GAT-004` remain blocked; especially signer activation under `LSOD-GAT-004`.

## Required evidence

- Versioned traceability and assurance plan naming mandatory test families, controlled environments, pass/fail criteria, remediation requirements, provenance, and reviewer independence.
- Reproducible implementation evidence tied to each resolved control and decision version.
- Explicit proof that offline evidence does not activate runtime capabilities.
- Named approval and independent-review records.

## Required tests

- All authenticated-evidence, custody, atomic-state, and time/audit/resource conformance families from Foundation125.
- Implementation-specific adversarial, fault, concurrency, crash/recovery, denial-of-service, isolation, secure-error, and regression tests.
- Deterministic evidence that failures are not waived and remediation is independently reverified.

## Independent review requirement

Independent end-to-end security review is mandatory. The reviewer must be independent of implementation and test authors and must assess evidence provenance, coverage, residual risks, and non-activation boundaries.

## Change control

Resolution requires a superseding version specifying the assurance structure, authority, evidence, acceptance criteria, and review. Any criteria, environment, test-family, or independence change requires versioned reapproval. Runtime/deployment/activation remains separately gated.

## Rollback rules

No assurance policy is approved. A later acceptance may be withdrawn only through an auditable superseding decision that invalidates affected evidence, records remediation requirements, and returns the system to fail-closed non-activation. Test failures cannot be silently waived.

## Authority and non-activation invariants

- L28 Protocol v1.0.0 remains authoritative; `coin.tx_validation.validate_transaction` remains the canonical validator.
- Authorization is not validation. Eligibility is not signer invocation.
- Assurance evidence cannot override issuance, supply, canonical height, validation, consensus, history, or settlement.
- Protected facts remain: `28000000`, `11130000`, `2824584`, `500000`, `2324584`, `210000`, `[28,14,7,3,1,0]`, `100877`, `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.
- Bitcoin remains external evidence only; production proof architecture, confirmation/reorg policy/count, observer quorum/independence, and signer activation remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.
- This record authorizes no signer, wallet, key, signature, RPC, network, broadcast, settlement, database, deployment, or testnet behavior.
