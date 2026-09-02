# Phase 4 Round 1 — Custody Security Findings v0.1

Status: `INDEPENDENT_REPOSITORY_REVIEW_ROUND_1`

Review series: `R0001`

Scope: exactly eight Foundation126 custody decisions classified `SECURITY_EXPERT_DECISION_REQUIRED`.

Reviewer capacity: Codex performed an evidence-bound repository review independently from implementation activity in this phase. This is not qualified human custody/cryptographic signoff, and no reviewer credentials are invented.

## Common evidence boundary

Evidence reviewed across all eight findings:

- `PROTOCOL.md` and `docs/local_signer_interface_security_review_v0.1.md`;
- `docs/local_signer_key_custody_lifecycle_architecture_v0.1.md`;
- `docs/local_signer_custody_control_profile_v0.1.md`;
- `docs/local_signer_implementation_gate_matrix_v0.1.md`;
- the custody rows in `docs/local_signer_operator_decision_register_v0.1.md`;
- `docs/local_signer_custody_conformance_plan_v0.1.md`;
- `docs/local_signer_custody_decision_proposals_v0.1.md` and the Foundation126 resolution packet;
- Phase 1–3.2 operator-review and assurance artifacts;
- F120 local-signer-interface fixtures and Foundation121 tests; and
- the limited separate boundaries in `coin/uaii_signed_receipt.py` and `coin/isolated_agent_purchase_demo.py`.

The receipt module keeps private material behind a callback, while the demo may generate disposable in-memory Ed25519 keys. Neither supplies a production local-signer custody system, approved custody policy, lifecycle evidence, or production signoff.

## L28-SRF-R0001-0009

- **LSOD decision ID:** `LSOD-CUS-001`
- **Disposition:** `GAP`
- **Threat/risk:** Weak, ambiguous, downgraded, cross-purpose, mismatched, or unreviewed signing material/algorithms could invalidate identity and custody guarantees.
- **Repository evidence actually reviewed:** F123/F124 require an explicit versioned allowlist with parameters, material forms, derivations, public identifiers, use scope, and deprecation. F126 compares narrow, multi-profile, and migration candidates without selecting one. `coin/uaii_signed_receipt.py` fixes `ed25519-pure/v0.1` for its separate receipt slice, but no source establishes that choice as the future local-signer custody policy.
- **Evidence missing:** Approved material/algorithm profile; cryptographic threat model; parameter and public-identifier vectors; purpose separation; provenance; lifecycle/deprecation/migration evidence; and independent cryptographic/custody review.
- **Required remediation:** Produce a versioned candidate allowlist and threat analysis with canonical vectors, purpose/origin constraints, downgrade resistance, lifecycle/migration rules, and qualified independent review. Do not infer policy from the receipt demo.
- **Residual risk:** Reusing an isolated demo algorithm as an implicit production custody decision would bypass governance and lifecycle analysis.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; repository evidence defines constraints but selects no custody material policy.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; qualified cryptographic/custody signoff is absent.

## L28-SRF-R0001-0010

- **LSOD decision ID:** `LSOD-CUS-003`
- **Disposition:** `GAP`
- **Threat/risk:** Secret export, privilege crossover, host/service compromise, false/stale attestation, or degraded isolation could expose signer authority.
- **Repository evidence actually reviewed:** F123/F124 define non-exportability, trust-zone, capability, attestation, health, quarantine, and fail-closed requirements. F126 compares software-process, hardware-backed, and offline-ceremony boundaries but chooses no technology. F121 proves its tests import no signer/key/runtime module; it does not test a custody boundary.
- **Evidence missing:** Selected isolation class and trust zones; capability map; process/storage/export controls; attestation and health mechanism; platform/host threat model; penetration/fault evidence; and independent isolation review.
- **Required remediation:** Submit an exact isolation candidate with prohibited capabilities, non-exportability, authenticated attestation/health, degradation/quarantine behavior, fault/recovery tests, and independent penetration assessment.
- **Residual risk:** Without an enforced boundary, compromise could expose signing authority or let custody become a protocol override path.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; logical isolation is specified but no production mechanism or evidence exists.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; platform/isolation reviewer signoff is absent.

## L28-SRF-R0001-0011

- **LSOD decision ID:** `LSOD-CUS-004`
- **Disposition:** `GAP`
- **Threat/risk:** Single-person control, collusion, privilege escalation, duplicate approvals, forbidden role combinations, or emergency bypass could authorize custody operations.
- **Repository evidence actually reviewed:** F123/F124 require least privilege, authenticated roles, explicit scopes, forbidden combinations, thresholds, and separation of duties. F126 presents fixed-role, threshold-sensitive, and risk-tiered candidates without names or thresholds. F120/F121 model fictional operators/approvers only.
- **Evidence missing:** Approved role/threshold matrix; named accountable authority classes; authentication; independence/collusion model; emergency scope; access audit; availability analysis; adversarial role/threshold tests; and organizational review.
- **Required remediation:** Define and independently review exact roles, scopes, forbidden combinations, thresholds, authentication, emergency procedure, revocation, and audit rules with collusion and availability evidence.
- **Residual risk:** Undefined organizational control leaves custody vulnerable to unilateral or collusive misuse.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; no production role or threshold has been approved or evidenced.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; independent access-control/organizational signoff is absent.

## L28-SRF-R0001-0012

- **LSOD decision ID:** `LSOD-CUS-005`
- **Disposition:** `GAP`
- **Threat/risk:** Forged, partial, reordered, duplicated, abandoned, or improperly resumed ceremonies could cause unauthorized lifecycle transitions.
- **Repository evidence actually reviewed:** F123/F124 specify versioned ceremony state machines, ordered roles/approvals, public records, abort/recovery, and review. F126 compares checklist, threshold-workflow, and prepare/approve/execute candidates; none is selected. The custody conformance plan is future planning only.
- **Evidence missing:** Approved ceremony topology and state machine; participant/observer independence; authenticated evidence format; abort/restart rules; durable audit binding; simulated adversarial/fault evidence; and independent ceremony review.
- **Required remediation:** Define each lifecycle ceremony as a deterministic fail-closed state machine, including roles, order, thresholds, evidence, abort, quarantine, fresh restart, and independent observation/review requirements.
- **Residual risk:** Ambiguous ceremony recovery could turn incomplete intent into effective custody authority.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; no ceremony is currently approved, executed, or independently assessed.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; custody-ceremony signoff is absent.

## L28-SRF-R0001-0013

- **LSOD decision ID:** `LSOD-CUS-006`
- **Disposition:** `GAP`
- **Threat/risk:** Stale material use, uncontrolled overlap, concurrent rotation, unsafe in-flight handling, rollback, or reactivation could create dual signing authority.
- **Repository evidence actually reviewed:** F123/F124 require monotonic lifecycle state, exact predecessor/successor binding, controlled overlap, disablement, and non-reactivation. F126 offers hard cutover, bounded overlap, and successor prepublication without choosing durations or mechanism. No production lifecycle store exists for this boundary.
- **Evidence missing:** Approved lifecycle/rotation profile; trusted time; atomic transition mechanism; overlap and in-flight semantics; activation/disable evidence; concurrency/crash/recovery tests; and independent lifecycle review.
- **Required remediation:** Select and review exact monotonic activation, expiry, rotation, overlap, predecessor disablement, in-flight, quarantine, and recovery semantics; provide atomic transition evidence under separate authorization.
- **Residual risk:** Concurrent or rolled-back lifecycle state could allow more than one effective authority or revive revoked material.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; only abstract lifecycle invariants are present.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; independent lifecycle/concurrency signoff is absent.

## L28-SRF-R0001-0014

- **LSOD decision ID:** `LSOD-CUS-007`
- **Disposition:** `GAP`
- **Threat/risk:** Delayed, unauthorized, stale, conflicting, or non-atomic revocation could permit continued use of compromised material.
- **Repository evidence actually reviewed:** F123/F124 require authenticated revocation authority, triggers, monotonic publication, freshness, atomic visibility, incident handling, and irreversible status. F126 compares dedicated, threshold emergency, and automated-quarantine candidates without selecting authority or deadlines.
- **Evidence missing:** Approved revocation authority and triggers; authenticated publication; freshness/deadline values and measurement; atomic visibility; incident/recovery coordination; adversarial outage/concurrency evidence; and independent incident/revocation review.
- **Required remediation:** Define the revocation authority, trigger, publication, freshness, quarantine, successor, and incident model; measure any production deadlines separately; prove irreversibility and fail-closed outage behavior.
- **Residual risk:** A compromised key could remain usable during undefined or inconsistent revocation state.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; revocation intent is clear but no enforceable production policy exists.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; incident/revocation signoff is absent.

## L28-SRF-R0001-0015

- **LSOD decision ID:** `LSOD-CUS-010`
- **Disposition:** `GAP`
- **Threat/risk:** Missed compromise, incomplete containment, lost forensic evidence, privacy violations, unauthorized recovery, or unsafe return could repeat or extend compromise.
- **Repository evidence actually reviewed:** F123/F124 define compromise triggers, immediate block/quarantine, forensics, notifications, successor separation, recovery, return criteria, and post-incident review. F126 compares predeclared, severity-tiered, and default-quarantine incident candidates without selection. No operational detection or exercise evidence exists.
- **Evidence missing:** Approved incident authority and runbook; detection/alert coverage; containment deadlines and measurement; forensics/privacy rules; communications; successor ceremony; recovery/return criteria; exercises; and independent incident review.
- **Required remediation:** Produce a versioned compromise-response candidate with roles, triggers, quarantine/revocation, evidence preservation, privacy-safe forensics, notification, successor, no-automatic-return, exercises, and independent review.
- **Residual risk:** Inadequate containment or return criteria could preserve compromised authority and erase accountability.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; design requirements are not backed by operational evidence.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; independent incident-response signoff is absent.

## L28-SRF-R0001-0016

- **LSOD decision ID:** `LSOD-CUS-011`
- **Disposition:** `GAP`
- **Threat/risk:** Forged, stale, revoked, over-disclosing, or unverifiable custody evidence could support unsupported custody claims or expose sensitive material.
- **Repository evidence actually reviewed:** F123/F124 require authenticated public-safe custody evidence, lifecycle state, freshness/revocation, independent verification, durable lineage, and privacy controls. F126 compares attestation summary, lifecycle digest, and combined models without selecting proof/cadence. F120/F121 exclude secrets but contain no custody evidence implementation.
- **Evidence missing:** Approved public evidence fields/proof and cadence; verifier authority; lifecycle/revocation binding; authenticity and durability mechanism; privacy/field-necessity analysis; outage/recovery tests; and independent custody-evidence review.
- **Required remediation:** Define an exact public-safe custody-evidence profile, proof and verifier model, freshness/revocation/cadence rules, durable history, privacy controls, and adversarial verification/recovery evidence.
- **Residual risk:** A public identifier or deterministic digest can be mistaken for proof of custody controls that were never implemented.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; current evidence proves secret exclusion in fixtures, not custody assurance.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; custody-evidence/privacy/audit signoff is absent.

## Domain conclusion

Custody dispositions: `PASS 0`, `GAP 8`, `REQUIRED_CHANGE 0`, `BLOCKED 0`.

No real key, wallet, HSM/KMS, signature, custody service, or ceremony was accessed or operated. No finding is closed and no custody decision is approved.

L28 Protocol v1.0.0 and canonical `coin.tx_validation.validate_transaction` remain authoritative. Authorization is not validation. Eligibility is not signer invocation. Bitcoin remains external evidence only.

Protected facts remain exactly: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.

Production Bitcoin proof architecture, Bitcoin confirmation/reorganization policy and count, observer quorum/independence, and signer implementation/runtime/deployment/activation remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`. This artifact authorizes no implementation or runtime behavior.
