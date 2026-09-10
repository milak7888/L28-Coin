# Operator Decision Record — LSOD-CUS-002

## Decision identity

- **Decision ID:** `LSOD-CUS-002`
- **Decision status:** `REQUIRES_SECURITY_EXPERT_REVIEW`
- **Effective version:** `v1.1`
- **Supersedes:** `docs/operator_decisions/decision_LSOD-CUS-002_v1.0.md`
- **Effect:** This version records the operator-selected fail-closed generation/import policy `none`. It enables no key-material path and does not resolve custody readiness.

## Original source references

- `docs/local_signer_implementation_gate_matrix_v0.1.md`: `F122-G02`; custody generation/import control.
- `docs/local_signer_operator_decision_register_v0.1.md`: decision `LSOD-CUS-002`.
- `docs/local_signer_operator_resolution_packet_v0.1.md`: `LSOD-CUS-002`, classified `OPERATOR_CAN_DECIDE_NEXT`.
- `docs/operator_decisions/decision_LSOD-CUS-002_v1.0.md`: predecessor record; preserved unchanged.

## Accountable authority

`UNASSIGNED`. A named custody-policy approver and independent custody-ceremony reviewer remain required before any later enabled path may be approved. This record does not assign those roles.

## Selected policy or value

`none`

Canonical meaning:

- `generation_permitted=false`
- `import_permitted=false`
- `origin_allowlist=[]`
- `key_material_path_enabled=false`

Explicitly rejected enabled choices:

- `generation`
- `import`
- `both`

No generation ceremony is authorized. No import ceremony is authorized. No origin class is approved.

## Rationale

The operator intentionally selects the most restrictive fail-closed policy: no key generation and no key import. The v1.0 record left the option unselected; this version records the explicit selection `none`.

This selection does not resolve remaining custody architecture or security-review requirements. It does not claim custody readiness, signer readiness, production readiness, completed security-expert review, or implementation authorization.

## Threat model

- Untrusted entropy or material origin.
- Unauthorized or duplicate generation/import.
- Transient key-material leakage.
- Unverifiable provenance or bypass of custody separation.

Selecting `none` keeps every generation/import path prohibited while those threats remain under later security review.

## Dependencies

- `LSOD-CUS-001=UNRESOLVED`
- `LSOD-CUS-003=UNRESOLVED`
- `LSOD-CUS-005=UNRESOLVED`
- Other applicable custody and security decisions remain unchanged.
- `LSOD-GAT-004` remains `BLOCKED`.

`CUSTODY_READINESS` remains `UNRESOLVED`. `F171_SIGNER_ELIGIBILITY_RESULT` remains `BLOCKED`.

## Required evidence

- This versioned record of selected policy `none`, empty origin allowlist, and disabled generation/import.
- Any later change that enables `generation`, `import`, or `both` still requires a versioned boundary, explicit origin allowlist, ceremony and provenance records, isolation evidence, and named independent review.
- No implementation evidence is created or authorized by this record.

## Required tests

- Structural verification that this record selects `none` and sets generation/import false.
- No generation/import operation is authorized or attempted by this record.
- Custody conformance and adversarial review remain required before any later enabled path.

## Independent review requirement

Decision status remains `REQUIRES_SECURITY_EXPERT_REVIEW`. An independent custody-ceremony and security review is mandatory before a generation or import path may be approved. This `none` selection does not complete that review. No real key, seed, mnemonic, xprv, wallet, HSM, or KMS operation is authorized.

## Change control

The v1.0 record remains immutable historical evidence. Adding or broadening a path to `generation`, `import`, or `both` requires a new decision version, ceremony, origin allowlist, and independent review. No implicit defaults are permitted.

## Rollback rules

No enabled path exists. A future withdrawal or broadening must publish a superseding decision, preserve audit provenance, and must not silently restore an older policy or enable a key-material path.

## Authority and non-activation invariants

This decision grants no key generation, key import, key access, secret access, wallet access, HSM/KMS access, signing, signer invocation, RPC, networking, broadcast, settlement, deployment, runtime activation, or mining.

- L28 Protocol v1.0.0 remains authoritative; `coin.tx_validation.validate_transaction` remains the canonical validator.
- Authorization is not validation. Eligibility is not signer invocation.
- No signer or custody component may override issuance, supply, canonical height, validation, consensus, history, or settlement.
- Protected facts remain: `28000000`, `11130000`, `2824584`, `500000`, `2324584`, `210000`, `[28,14,7,3,1,0]`, `100877`, `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.
- Bitcoin remains external evidence only; `LSOD-GAT-001` through `LSOD-GAT-004` remain blocked.
- This record authorizes no signer, wallet, key, signature, RPC, network, broadcast, settlement, database, deployment, or testnet behavior.
