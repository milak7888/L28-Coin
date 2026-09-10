# Operator Decision Record — LSOD-CUS-012

## Decision identity

- **Decision ID:** `LSOD-CUS-012`
- **Decision status:** `OPERATOR_DECISION_RECORDED`
- **Effective version:** `v1.1`
- **Supersedes:** `docs/operator_decisions/decision_LSOD-CUS-012_v1.0.md`
- **Effect:** This version records the operator-selected bounded non-key custody evidence scope `A`. It authorizes no custody implementation, key operation, signing, or runtime.

## Original source references

- `docs/local_signer_implementation_gate_matrix_v0.1.md`: `F122-G02`, `F122-G07`, `F122-G08`, and `F122-B04`; custody implementation gate.
- `docs/local_signer_operator_decision_register_v0.1.md`: decision `LSOD-CUS-012`.
- `docs/local_signer_operator_resolution_packet_v0.1.md`: `LSOD-CUS-012`, classified `OPERATOR_CAN_DECIDE_NEXT`.
- `docs/local_signer_custody_decision_proposals_v0.1.md`: option `A` — public custody-evidence/test harness only, with no key boundary.
- `docs/operator_decisions/decision_LSOD-CUS-012_v1.0.md`: predecessor record; preserved unchanged.
- `docs/operator_decisions/decision_LSOD-CUS-002_v1.1.md`: `LSOD-CUS-002=none`.
- `docs/operator_decisions/decision_LSOD-CUS-008_v1.1.md`: `LSOD-CUS-008=backup prohibited`.
- `docs/operator_decisions/decision_LSOD-OPS-009_v1.1.md`: `ASSURANCE_MODEL=OPEN_SOURCE_PUBLIC_REVIEW`.

## Accountable authority

Operator-recorded evidence-scope decision. No independent reviewer identity or qualification is assigned or invented.

- `INDEPENDENT_REVIEW_STATUS=NOT_PERFORMED`
- `NOT_INDEPENDENTLY_AUDITED=true`

## Selected policy or value

`A`

Canonical scope:

- `CUSTODY_EVIDENCE_SCOPE=PUBLIC_NON_SECRET_ONLY`
- `REAL_KEY_BOUNDARY=false`
- `SIMULATED_KEY_OPERATION=false`
- `CUSTODY_IMPLEMENTATION_AUTHORIZED=false`
- `SIGNER_IMPLEMENTATION_AUTHORIZED=false`
- `RUNTIME_AUTHORIZED=false`

Permitted future work only:

- public/non-secret custody evidence schemas
- fail-closed evidence validation
- structural/security tests
- dependency resolution evidence
- F172 audit evidence binding
- F173 trusted-time evidence binding
- reproducible adversarial/fault tests that use no key material

## Prohibited

- private keys
- seeds
- mnemonics
- xprv
- key generation
- key import
- key backup
- key recovery
- key destruction operations
- wallet access
- HSM/KMS access
- signing
- signer invocation
- RPC
- networking
- transaction submission
- broadcast
- settlement
- mining
- deployment
- runtime activation

Option `B` (isolated custody-control prototype using disposable simulated material) is not selected. Option `C` (later production custody boundary) remains blocked.

## Rationale

The operator selects Foundation126 option `A`: a public custody-evidence/test harness only, with no key boundary. This is the lowest-risk evidence milestone and cannot prove real custody.

This selection does not authorize custody implementation, signer implementation, or runtime. It does not resolve remaining technical custody gates and does not claim independent review.

## Threat model

- Unsafe custody runtime or architecture drift.
- Exposure or misuse of key material.
- Simulated-key work treated as production custody.
- Self-review described as independent review.
- Premature deployment or signer activation.

Selecting option `A` confines later work to public/non-secret evidence and keeps every key and runtime path unauthorized.

## Dependencies

Recorded operator policies:

- `LSOD-CUS-002=none`; `KEY_GENERATION_PERMITTED=false`; `KEY_IMPORT_PERMITTED=false`.
- `LSOD-CUS-008=backup prohibited`; `BACKUP_PERMITTED=false`.
- `LSOD-OPS-009=v1.1`; `ASSURANCE_MODEL=OPEN_SOURCE_PUBLIC_REVIEW`; `NOT_INDEPENDENTLY_AUDITED=true`.

Remain unresolved and are not converted to `PASS`:

- `LSOD-CUS-001`
- `LSOD-CUS-003`
- `LSOD-CUS-004`
- `LSOD-CUS-005`
- `LSOD-CUS-006`
- `LSOD-CUS-007`
- `LSOD-CUS-009`
- `LSOD-CUS-010`
- `LSOD-CUS-011`

`LSOD-GAT-004` remains blocked.

`F172_PRODUCTION_AUDIT_BACKEND=RESOLVED`. `F173_PRODUCTION_TIME_BACKEND=RESOLVED`.

`CUSTODY_READINESS` remains `UNRESOLVED`. `RUNTIME_HARDENING` remains `UNRESOLVED`. `FAULT_RECOVERY` remains `UNRESOLVED`. `F171_SIGNER_ELIGIBILITY_RESULT` remains `BLOCKED`.

## Required evidence

- This versioned record of option `A` and the public/non-secret-only scope.
- Later option-A work must remain public-only, fail-closed, and free of key material.
- F172 and F173 bindings, if used, remain evidence/hash references only.
- No custody-implementation, signer-implementation, or runtime evidence is authorized.

## Required tests

- Structural verification that this record selects option `A` and sets all key/runtime authorization flags false.
- Any later option-A tests must use no key material and must not sign, broadcast, settle, or activate runtime.
- Adversarial and fault tests remain required where applicable and must stay non-secret.

## Independent review requirement

`ASSURANCE_MODEL=OPEN_SOURCE_PUBLIC_REVIEW`. External signoff is not a release gate. This option-A selection is not an independent audit and must not be described as one. Public review is invited and is not L28 authority.

## Change control

The v1.0 record remains immutable historical evidence. Broadening to option `B`, production option `C`, a real key boundary, simulated key operations, or any prohibited capability requires a new decision version. Implementation, deployment, and activation remain separate authorization events.

## Rollback rules

No implementation is approved. A later withdrawal or broadening must publish a superseding decision, preserve audit provenance, and return the boundary to fail-closed non-execution. Silent restoration of an older policy is prohibited.

## Authority and non-activation invariants

This decision grants no key generation, key import, key backup, key recovery, key destruction, key access, secret access, wallet access, HSM/KMS access, signing, signer invocation, RPC, networking, transaction submission, broadcast, settlement, mining, deployment, or runtime activation.

- L28 Protocol v1.0.0 remains frozen and authoritative; `coin.tx_validation.validate_transaction` remains the canonical validator.
- Authorization is not validation. Eligibility is not signer invocation.
- No signer or custody component may override issuance, supply, canonical height, validation, consensus, history, or settlement.
- Protected facts remain: `28000000`, `11130000`, `2824584`, `500000`, `2324584`, `210000`, `[28,14,7,3,1,0]`, `100877`, `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.
- Bitcoin remains external evidence only; `LSOD-GAT-001` through `LSOD-GAT-004` remain blocked.
- This record authorizes no signer, wallet, key, signature, RPC, network, broadcast, settlement, database, deployment, or testnet behavior.
