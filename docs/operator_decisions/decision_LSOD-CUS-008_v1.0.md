# Operator Decision Record — LSOD-CUS-008

## Decision identity

- **Decision ID:** `LSOD-CUS-008`
- **Decision status:** `REQUIRES_SECURITY_EXPERT_REVIEW`
- **Effective version:** `v1.0`
- **Effect:** This version records an unresolved, fail-closed decision; backup and recovery remain prohibited.

## Original source references

- `docs/local_signer_implementation_gate_matrix_v0.1.md`: `F122-G02`; custody backup/recovery control.
- `docs/local_signer_operator_decision_register_v0.1.md`: decision `LSOD-CUS-008`.
- `docs/local_signer_operator_resolution_packet_v0.1.md`: `LSOD-CUS-008`, classified `OPERATOR_CAN_DECIDE_NEXT` without selecting backup prohibition or permission.

## Accountable authority

`UNASSIGNED`. Resolution requires a named custody-recovery approver and an independent recovery reviewer.

## Selected policy or value

None. The operator has not explicitly selected `backup prohibited` or a versioned protected-backup policy. No recovery quorum, protection control, retention period, or restore authority has been approved. Backup and recovery therefore remain prohibited.

## Rationale

Permitting backup by inference would invent security-sensitive production controls. Readiness to decide is not a decision, and missing custody-recovery evidence must fail closed.

## Threat model

- Irrecoverable material loss.
- Unauthorized export or recovery.
- Stale, revoked, corrupt, or substituted backup restoration.
- Insufficient recovery quorum and bypass of separation of duties.

## Dependencies

- `LSOD-CUS-003`, `LSOD-CUS-004`, `LSOD-CUS-006`, `LSOD-CUS-007`, and `LSOD-OPS-002` remain unresolved.
- `LSOD-GAT-004` signer activation remains blocked.

## Required evidence

- An explicit prohibition decision or a versioned protected-backup policy.
- If later permitted: authenticated inventory, provenance, protection, retention, recovery ceremony, inactive-restore, and revocation evidence.
- Named accountable approval and independent recovery-review evidence.

## Required tests

- Deterministic rejection of unauthorized export/recovery, corrupt or stale backups, revoked material, insufficient quorum, and incomplete evidence.
- Recovery exercises using fictional/disposable evidence only and no real key material.
- Tests proving no backup or recovery action occurs while this decision is unresolved.

## Independent review requirement

Independent custody-recovery review is mandatory before any protected-backup policy can be approved. The review must cover separation of duties, provenance, recovery authorization, revocation, and compromise paths.

## Change control

Any resolution must supersede this record and identify the selected posture and all approved controls. Permitting backup, changing recovery authority, or changing retention/protection requires a new version and independent review.

## Rollback rules

There is no approved backup policy to roll back. Withdrawal of a later policy requires auditable revocation, quarantine of affected artifacts, preservation of historical evidence, and a superseding fail-closed decision. Restoration may never roll policy or custody state backward silently.

## Authority and non-activation invariants

- L28 Protocol v1.0.0 remains authoritative; `coin.tx_validation.validate_transaction` remains the canonical validator.
- Authorization is not validation. Eligibility is not signer invocation.
- No signer or custody component may override issuance, supply, canonical height, validation, consensus, history, or settlement.
- Protected facts remain: `28000000`, `11130000`, `2824584`, `500000`, `2324584`, `210000`, `[28,14,7,3,1,0]`, `100877`, `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.
- Bitcoin remains external evidence only; `LSOD-GAT-001` through `LSOD-GAT-004` remain blocked.
- This record authorizes no signer, wallet, key, signature, RPC, network, broadcast, settlement, database, deployment, or testnet behavior.
