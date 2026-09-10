# Operator Decision Record — LSOD-OPS-009

## Decision identity

- **Decision ID:** `LSOD-OPS-009`
- **Decision status:** `OPERATOR_DECISION_RECORDED`
- **Decision state:** `OPERATOR_DECISION_RECORDED`
- **Effective version:** `v1.1`
- **Supersedes:** `docs/operator_decisions/decision_LSOD-OPS-009_v1.0.md`
- **Effect:** This version records the operator-selected development/release assurance policy. It does not authorize implementation, custody, signing, runtime, deployment, or activation.

## Original source references

- `docs/local_signer_implementation_gate_matrix_v0.1.md`: `F122-G08` and `F122-B04`; implementation assurance and activation gate.
- `docs/local_signer_operator_decision_register_v0.1.md`: decision `LSOD-OPS-009`.
- `docs/local_signer_operator_resolution_packet_v0.1.md`: `LSOD-OPS-009`, classified `OPERATOR_CAN_DECIDE_NEXT`.
- `docs/operator_decisions/decision_LSOD-OPS-009_v1.0.md`: predecessor record; preserved unchanged.

## Accountable authority

Operator-recorded assurance-policy decision. No independent reviewer identity or qualification is assigned or invented.

- `INDEPENDENT_REVIEW_STATUS=NOT_PERFORMED`
- `INDEPENDENT_REVIEW_REQUIRED_FOR_RELEASE=false`

## Selected policy or value

`ASSURANCE_MODEL=OPEN_SOURCE_PUBLIC_REVIEW`

Canonical meaning:

- `PAID_INDEPENDENT_SECURITY_AUDIT_REQUIRED=false`
- `ASSIGNED_INDEPENDENT_REVIEWER_REQUIRED=false`
- `EXTERNAL_SECURITY_SIGNOFF_REQUIRED=false`
- `EXTERNAL_REVIEW_RELEASE_GATE=false`
- `PUBLIC_REVIEW_INVITED=true`
- `REPRODUCIBLE_TEST_EVIDENCE_REQUIRED=true`
- `ADVERSARIAL_FAULT_TESTING_REQUIRED=true`
- `KNOWN_LIMITATIONS_DISCLOSURE_REQUIRED=true`
- `NOT_INDEPENDENTLY_AUDITED_DISCLOSURE_REQUIRED=true`

## Rationale

The operator replaces the v1.0 mandatory independent-review release gate with an open-source/public-review assurance model suitable for a self-hosted public cryptocurrency project.

This changes development/release assurance policy only. It does not modify L28 Protocol v1.0.0 and does not change issuance, supply, consensus, canonical height, transaction validation, history, settlement, or economics.

Where historical F122, F126, or OPS-009 v1.0 records require an independent reviewer as a future assurance prerequisite, v1.1 supersedes that release-assurance requirement for future work. Those historical statements remain accurate for their versions. This policy does not automatically resolve technical decisions that still require architecture selection, implementation evidence, fault evidence, custody controls, or runtime controls.

## Policy

L28 does not require a paid security audit, an assigned independent security reviewer, external security-company certification, external signoff before source release, or external signoff before a bounded development milestone.

L28 does require, before affected functionality is considered ready:

1. deterministic automated tests
2. affected regression tests
3. protocol-invariant tests
4. adversarial/security tests appropriate to the component
5. fault/crash/recovery testing where applicable
6. structural/AST security review where applicable
7. reproducible evidence tied to exact commits
8. unresolved failures disclosed and not silently waived
9. exact authority and activation boundaries documented
10. public source availability for community inspection
11. explicit disclosure when no independent audit/review occurred

## Release disclosure

When no genuine independent review has occurred, records and releases must state:

`NOT_INDEPENDENTLY_AUDITED=true`

Do not claim independently audited, independently certified, externally verified, or formally verified unless that evidence actually exists.

## Public review

Public and community review is invited. Findings may become repository evidence. Public review may be unpaid and may occur after source publication.

Public review is not itself authority over L28. It cannot change Protocol rules, activate signer or runtime behavior, or waive failing tests or known security findings.

## Self-review limit

Implementation-author review and automated evaluation may satisfy this project's internal release-assurance process under this policy. They must never be described as independent review.

## Security fail-closed rule

Known CRITICAL or HIGH security findings affecting secret/key exposure, unauthorized signing, protocol-authority bypass, arbitrary minting, supply/history mutation, validation bypass, or unauthorized settlement must block the affected capability until remediated.

Absence of an external reviewer alone does not block development or open-source publication.

This policy must not convert an unresolved technical or security defect into `PASS`.

## Threat model

- Untested adversarial, fault, concurrency, crash, recovery, or denial-of-service modes.
- Fixture or test evidence being misrepresented as production assurance.
- Self-certification described as independent review.
- Silently waived failures or incomplete remediation.
- Premature runtime, deployment, or signer activation.

## Dependencies

- `LSOD-CUS-002=none`; `KEY_GENERATION_PERMITTED=false`; `KEY_IMPORT_PERMITTED=false`.
- Other applicable `LSOD-EVD-*`, `LSOD-CUS-*`, `LSOD-STA-*`, and `LSOD-OPS-001` through `LSOD-OPS-008` technical decisions remain separately gated where not already recorded.
- `LSOD-GAT-001` through `LSOD-GAT-004` remain blocked.
- `CUSTODY_READINESS` remains `UNRESOLVED`.
- `RUNTIME_HARDENING` remains `UNRESOLVED`.
- `FAULT_RECOVERY` remains `UNRESOLVED`.
- `F171_SIGNER_ELIGIBILITY_RESULT` remains `BLOCKED`.

This assurance policy does not resolve those technical blockers.

## Required evidence

- Deterministic, reproducible test and review evidence tied to exact commits.
- Affected regression and protocol-invariant results.
- Adversarial and, where applicable, fault/crash/recovery and structural/AST security evidence.
- Documented authority and activation boundaries.
- `NOT_INDEPENDENTLY_AUDITED=true` when no genuine independent review occurred.
- Disclosure of unresolved failures; silent waiver is prohibited.

## Required tests

- Deterministic automated tests, affected regressions, and protocol-invariant tests remain mandatory.
- Adversarial/security tests appropriate to the component remain mandatory.
- Fault/crash/recovery testing remains mandatory where applicable.
- Structural/AST security review remains mandatory where applicable.
- Failures are not waived; Critical/High security defects remain capability blockers.

## Independent review requirement

- `INDEPENDENT_REVIEW_STATUS=NOT_PERFORMED`
- `INDEPENDENT_REVIEW_REQUIRED_FOR_RELEASE=false`

No independent reviewer is assigned. No paid audit is required. External signoff is not a release gate. Public/community review remains invited and is not described as independent review unless that evidence exists.

## Change control

The v1.0 record remains immutable historical evidence. Changing the assurance model, test obligations, disclosure rules, or independence claims requires a new decision version. Runtime, deployment, and activation remain separately gated.

## Rollback rules

A later withdrawal or tightening of this policy must publish a superseding decision, preserve audit provenance, and must not silently restore the v1.0 mandatory independent-review release gate or waive failing tests.

## Signer / custody boundary

This decision alone authorizes no key generation or import, private-key access, seed/mnemonic/xprv access, wallet access, signing, signer invocation, RPC, runtime activation, networking, broadcast, transaction submission, settlement, mining, deployment, or public testnet.

Existing custody and runtime decisions remain separately gated.

## Authority and non-activation invariants

- L28 Protocol v1.0.0 remains frozen and authoritative; `coin.tx_validation.validate_transaction` remains the canonical validator.
- Authorization is not validation. Eligibility is not signer invocation.
- Assurance evidence cannot override issuance, supply, canonical height, validation, consensus, history, or settlement.
- Protected facts remain: `28000000`, `11130000`, `2824584`, `500000`, `2324584`, `210000`, `[28,14,7,3,1,0]`, `100877`, `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.
- Bitcoin remains external evidence only; production proof architecture, confirmation/reorg policy/count, observer quorum/independence, and signer activation remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.
- This record authorizes no signer, wallet, key, signature, RPC, network, broadcast, settlement, database, deployment, or testnet behavior.
