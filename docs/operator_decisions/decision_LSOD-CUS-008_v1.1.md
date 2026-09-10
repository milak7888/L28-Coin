# Operator Decision Record — LSOD-CUS-008

## Decision identity

- **Decision ID:** `LSOD-CUS-008`
- **Decision status:** `OPERATOR_DECISION_RECORDED`
- **Effective version:** `v1.1`
- **Supersedes:** `docs/operator_decisions/decision_LSOD-CUS-008_v1.0.md`
- **Effect:** This version records the operator-selected fail-closed backup policy `backup prohibited`. It authorizes no backup, recovery, or key-material path and does not resolve custody readiness.

## Original source references

- `docs/local_signer_implementation_gate_matrix_v0.1.md`: `F122-G02`; custody backup/recovery control.
- `docs/local_signer_operator_decision_register_v0.1.md`: decision `LSOD-CUS-008`.
- `docs/local_signer_operator_resolution_packet_v0.1.md`: `LSOD-CUS-008`, classified `OPERATOR_CAN_DECIDE_NEXT`.
- `docs/operator_decisions/decision_LSOD-CUS-008_v1.0.md`: predecessor record; preserved unchanged.
- `docs/operator_decisions/decision_LSOD-CUS-002_v1.1.md`: `LSOD-CUS-002=none`.
- `docs/operator_decisions/decision_LSOD-OPS-009_v1.1.md`: `ASSURANCE_MODEL=OPEN_SOURCE_PUBLIC_REVIEW`.

## Accountable authority

Operator-recorded backup-scope decision. No independent reviewer identity or qualification is assigned or invented.

- `INDEPENDENT_REVIEW_STATUS=NOT_PERFORMED`
- `NOT_INDEPENDENTLY_AUDITED=true`

## Selected policy or value

`backup prohibited`

Canonical meaning:

- `BACKUP_PERMITTED=false`
- `RECOVERY_FROM_BACKUP_PERMITTED=false`
- `BACKUP_MECHANISM_SELECTED=false`
- `RECOVERY_QUORUM_SELECTED=false`
- `RETENTION_POLICY_SELECTED=false`
- `RESTORE_AUTHORITY_SELECTED=false`

No private-key backup, export-for-backup, restoration, or recovery mechanism is authorized.

## Rationale

The operator explicitly selects the most restrictive fail-closed backup posture. The v1.0 record left the option unselected while treating backup as prohibited by default. This version records the explicit selection `backup prohibited`.

This selection does not resolve remaining custody architecture. It does not claim custody readiness, signer readiness, production readiness, completed independent review, or implementation authorization.

## Threat model

- Irrecoverable material loss.
- Unauthorized export or recovery.
- Stale, revoked, corrupt, or substituted backup restoration.
- Insufficient recovery quorum and bypass of separation of duties.

Selecting `backup prohibited` keeps every backup and recovery path unauthorized while those threats remain under later technical review.

## Dependencies

- `LSOD-CUS-003` remains unresolved.
- `LSOD-CUS-004` remains unresolved.
- `LSOD-CUS-006` remains unresolved.
- `LSOD-CUS-007` remains unresolved.
- `LSOD-OPS-002` remains unresolved.
- `LSOD-CUS-002=none`; `KEY_GENERATION_PERMITTED=false`; `KEY_IMPORT_PERMITTED=false`.
- `LSOD-GAT-004` remains blocked.

`CUSTODY_READINESS` remains `UNRESOLVED`. `F171_SIGNER_ELIGIBILITY_RESULT` remains `BLOCKED`.

This policy does not convert those technical dependencies into `PASS`.

## Required evidence

- This versioned record of selected policy `backup prohibited` and all backup/recovery flags false.
- Any later change that permits backup still requires a versioned protected-backup policy, mechanism design, quorum, retention, restore authority, and the unresolved CUS-003/004/006/007 and OPS-002 reviews.
- No backup or recovery implementation evidence is created or authorized by this record.

## Required tests

- Structural verification that this record selects `backup prohibited` and sets `BACKUP_PERMITTED=false`.
- No backup, export-for-backup, restoration, or recovery operation is authorized or attempted by this record.
- Later enabled backup work, if ever authorized, still requires adversarial and fault evidence with no real key material.

## Independent review requirement

`ASSURANCE_MODEL=OPEN_SOURCE_PUBLIC_REVIEW`. External signoff is not a release gate. This `backup prohibited` selection is not an independent audit and must not be described as one. A later enabled backup mechanism would still require its substantive technical evidence.

## Change control

The v1.0 record remains immutable historical evidence. Permitting backup, selecting a mechanism, changing recovery authority, or changing retention/protection requires a new decision version. No implicit defaults are permitted.

## Rollback rules

No enabled backup path exists. A future withdrawal or broadening must publish a superseding decision, preserve audit provenance, and must not silently restore an older policy or enable a recovery mechanism.

## Authority and non-activation invariants

This decision grants no key generation, key import, key backup, key recovery, key access, secret access, wallet access, HSM/KMS access, signing, signer invocation, RPC, networking, broadcast, settlement, deployment, runtime activation, or mining.

- L28 Protocol v1.0.0 remains frozen and authoritative; `coin.tx_validation.validate_transaction` remains the canonical validator.
- Authorization is not validation. Eligibility is not signer invocation.
- No signer or custody component may override issuance, supply, canonical height, validation, consensus, history, or settlement.
- Protected facts remain: `28000000`, `11130000`, `2824584`, `500000`, `2324584`, `210000`, `[28,14,7,3,1,0]`, `100877`, `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.
- Bitcoin remains external evidence only; `LSOD-GAT-001` through `LSOD-GAT-004` remain blocked.
- This record authorizes no signer, wallet, key, signature, RPC, network, broadcast, settlement, database, deployment, or testnet behavior.
