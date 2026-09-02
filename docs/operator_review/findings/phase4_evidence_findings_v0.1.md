# Phase 4 Round 1 — Authenticated-Evidence Security Findings v0.1

Status: `INDEPENDENT_REPOSITORY_REVIEW_ROUND_1`

Review series: `R0001`

Scope: exactly eight Foundation126 authenticated-evidence decisions classified `SECURITY_EXPERT_DECISION_REQUIRED`.

Reviewer capacity: Codex performed an evidence-bound repository review independently from implementation activity in this phase. This is not qualified human security-expert signoff. No reviewer identity, credential, qualification, or independence claim beyond this repository-review role is inferred.

## Common evidence boundary

Evidence reviewed across all eight findings:

- `PROTOCOL.md`;
- `docs/local_signer_interface_security_review_v0.1.md`;
- `docs/authenticated_signer_evidence_architecture_v0.1.md`;
- `docs/authenticated_signer_evidence_profile_v0.1.md`;
- `docs/local_signer_implementation_gate_matrix_v0.1.md`;
- `docs/local_signer_operator_decision_register_v0.1.md`;
- `docs/authenticated_signer_evidence_conformance_plan_v0.1.md`;
- `docs/authenticated_signer_evidence_decision_proposals_v0.1.md`;
- `docs/local_signer_operator_resolution_packet_v0.1.md`;
- Phase 1 decision records, Phase 2 scope/evidence/questionnaire, Phase 3.1 security target, and Phase 3.2 finding/remediation/closure framework;
- 100 `conformance/local_signer_interface/v0.1/fixtures/*.json` artifacts through the Foundation121 test-local readers and assertions; and
- Foundation121 profile/schema/security tests, observed `45 passed` in Round 1.

The test evidence proves deterministic offline fixture conformance only. It does not authenticate a production caller/operator/issuer/verifier, approve a policy, invoke `coin.tx_validation.validate_transaction`, or prove production security.

## L28-SRF-R0001-0001

- **LSOD decision ID:** `LSOD-EVD-001`
- **Disposition:** `GAP`
- **Threat/risk:** Forged or ambiguously canonicalized evidence, algorithm downgrade, parameter/encoding confusion, weak proof material, or cross-profile verification could create false authorization evidence.
- **Repository evidence actually reviewed:** The F123 evidence architecture defines domain separation and proof verification requirements; the F124 profile leaves proof format/algorithm/parameters unselected; the F125 register and F126 proposal compare candidate proof shapes. `coin/uaii_signed_receipt.py` implements a separate PureEd25519 receipt slice with external callback-based private-key custody, but it is not an approved proof profile for caller/operator/policy/approval evidence. F121 validates fictional proof-state fields without cryptographic verification.
- **Evidence missing:** Approved proof format, algorithm and parameters; canonical proof-input vectors; verification-material lifecycle; independent cryptographic analysis; verifier implementation/build provenance; forgery/downgrade evidence; and qualified human signoff.
- **Required remediation:** Produce a versioned candidate decision package with exact proof domains, encodings, algorithms, parameters, lifecycle/deprecation rules, canonical vectors, threat analysis, and independent cryptographic/protocol review. Any implementation evidence requires separate authorization.
- **Residual risk:** Current design-only proof labels can be mistaken for authenticated evidence if consumed outside the non-executing fixture boundary.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`. Closure criteria are not met; no `PASS` is supportable.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; this Codex repository review is unsigned advisory evidence only.

## L28-SRF-R0001-0002

- **LSOD decision ID:** `LSOD-EVD-002`
- **Disposition:** `GAP`
- **Threat/risk:** Rogue issuers, compromised trust roots, excessive/circular delegation, stale enrollment, or unauthenticated revocation could manufacture authority.
- **Repository evidence actually reviewed:** F123 specifies issuer authority, provenance, delegation, revocation, and fail-closed states; F124 defines a future registry-governance contract; F125/F126 enumerate unselected single-registry, hierarchical, and threshold-governed candidates. F120/F121 use fixed fictional identities and do not implement an issuer registry.
- **Evidence missing:** Selected governance model; named accountable authorities; authenticated root/issuer enrollment and delegation records; monotonic revocation lineage; compromise/recovery procedure evidence; adversarial governance tests; and independent identity/PKI review.
- **Required remediation:** Define and independently review an exact registry/trust-root governance candidate, authority scopes, delegation limits, enrollment/revocation state machine, compromise containment, recovery, and audit evidence before operator consideration.
- **Residual risk:** Without a governed trust root, a syntactically valid evidence envelope has no established production authenticity or authority.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; repository design narrows requirements but does not establish a trusted issuer system.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; no qualified identity/PKI reviewer signoff exists in the repository.

## L28-SRF-R0001-0003

- **LSOD decision ID:** `LSOD-EVD-003`
- **Disposition:** `GAP`
- **Threat/risk:** Verifier impersonation, wrong audience, unauthorized roles, stale or compromised verification material, or custody crossover could yield false verification.
- **Repository evidence actually reviewed:** F123/F124 require audience-bound verifier identity, isolated verification material, lifecycle, revocation, and health evidence. F126 lists isolated-service, workload-identity, and offline-bundle candidates without selection. F121 deliberately imports no production verifier or cryptographic/runtime module.
- **Evidence missing:** Approved verifier topology and identity domain; authentication/authorization mechanism; isolated material lifecycle; health/attestation semantics; revocation/rotation evidence; implementation and penetration evidence; and independent verifier security review.
- **Required remediation:** Submit one exact verifier-boundary candidate with capabilities, audiences, lifecycle, failure behavior, provenance, isolation evidence, adversarial tests, and independent review. Keep verifier material separate from signer custody.
- **Residual risk:** A fixture value of `verified` remains caller-supplied fictional data and cannot establish production verification.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; neither verifier authority nor its enforcement evidence exists.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; no qualified verifier/material-lifecycle reviewer signoff exists.

## L28-SRF-R0001-0004

- **LSOD decision ID:** `LSOD-EVD-005`
- **Disposition:** `GAP`
- **Threat/risk:** Revoked evidence may be accepted when status is forged, stale, conflicting, rolled back, cached beyond validity, or unavailable.
- **Repository evidence actually reviewed:** F123/F124 require authenticated monotonic revocation status and fail-closed outage behavior. F126 compares online lookup, short-lived evidence, and authenticated bounded cache candidates. F121 models deterministic revoked/unavailable outcomes but reads no source, cache, production time, or revocation state.
- **Evidence missing:** Approved revocation source and authority; update/freshness/cache/outage semantics; authenticated monotonic state; conflict recovery; measured propagation evidence under `LSOD-EVD-004`; implementation/fault tests; and independent availability/revocation review.
- **Required remediation:** Define the exact revocation authority and source model, bind it to approved trusted-time semantics, specify monotonic/cache/outage behavior, and provide rollback, conflict, outage, recovery, and compromise-latency evidence for independent review.
- **Residual risk:** Unbounded or unauthenticated revocation staleness could preserve compromised authority.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; fail-closed intent is specified but no production revocation evidence exists.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; independent revocation/availability signoff is absent.

## L28-SRF-R0001-0005

- **LSOD decision ID:** `LSOD-EVD-006`
- **Disposition:** `GAP`
- **Threat/risk:** Policy downgrade, split authority, overlapping activation, stale approvals, caller-selected versions, or rollback could apply the wrong economic/security policy.
- **Repository evidence actually reviewed:** F123/F124 specify exact digest/version binding, one authoritative version, effective intervals, monotonic supersession, and preserved history. F126 compares hard cutover, staged activation, and dual-readable migration without selecting transition semantics. F120/F121 test fictional version/digest mismatches only.
- **Evidence missing:** Approved transition model; authenticated policy registry and authority; production effective-time binding; atomic version observation; in-flight request rules; concurrent transition/rollback evidence; and independent governance/atomicity review.
- **Required remediation:** Select and review one monotonic activation/supersession model with exact digest, predecessor/successor, overlap, in-flight, correction, and audit rules, then provide separately authorized atomic-transition evidence and tests.
- **Residual risk:** Mixed or rolled-back policy state could authorize requests under unintended controls.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; the invariant is clear but its production mechanism and evidence are absent.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; no independent policy-governance/atomicity signoff exists.

## L28-SRF-R0001-0006

- **LSOD decision ID:** `LSOD-EVD-007`
- **Disposition:** `GAP`
- **Threat/risk:** Colluding, duplicate, invalid, revoked, or wrong-scope approvals; threshold bypass; or concurrent reuse could create unauthorized control.
- **Repository evidence actually reviewed:** F123/F124 define authenticated approver identities, uniqueness, scopes, thresholds, and atomic consumption requirements. F126 offers fixed, policy-specific, and risk-tiered candidates but selects no role set or threshold. F120/F121 exercise deterministic fictional approval outcomes without identity authentication or state consumption.
- **Evidence missing:** Approved role/threshold model and rationale; named authorities; independence/collusion analysis; authenticated approver lifecycle; exact scope/reuse rules; atomic consumption; threshold-race evidence; and independent authorization review.
- **Required remediation:** Produce a versioned approval-governance candidate with roles, uniqueness, scopes, thresholds, lifecycle, reuse/consumption, emergency behavior, and adversarial concurrency tests, reviewed independently before operator consideration.
- **Residual risk:** Duplicate or reusable fictional approvals could be misconstrued as sufficient authority outside the test boundary.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; no production approval authority or threshold is established.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; independent authorization/separation-of-duty signoff is absent.

## L28-SRF-R0001-0007

- **LSOD decision ID:** `LSOD-EVD-008`
- **Disposition:** `GAP`
- **Threat/risk:** Nonce collision, evidence replay, cross-domain reuse, request reassociation, or premature retention expiry could duplicate authority.
- **Repository evidence actually reviewed:** F123/F124 require exact administrative-domain, nonce, request, intent, policy, evidence, and consumption binding. F126 compares nonce, idempotency-key, and combined candidates. F120 declares replay evidence read-only and atomic transition unimplemented; F121 confirms no replay-state mutation. `coin/m2m_replay_registry.py` is an older offline M2M transcript registry, not an approved or integrated local-signer evidence-consumption store.
- **Evidence missing:** Approved replay domain and nonce provenance; single-use/reuse policy; collision model; retention horizon; atomic check-and-record bound to the local signer request; duplicate/conflict recovery; crash/concurrency tests; and independent replay/state review.
- **Required remediation:** Select an exact replay profile and demonstrate, under separate authorization, durable atomic consumption and deterministic duplicate/conflict behavior with retention/recovery evidence. Prove no reuse of unrelated M2M registry authority by assumption.
- **Residual risk:** Read-only fixture checks cannot prevent replay or double use in a future concurrent runtime.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; current evidence proves non-execution, not replay enforcement.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; independent replay/atomic-state signoff is absent.

## L28-SRF-R0001-0008

- **LSOD decision ID:** `LSOD-EVD-009`
- **Disposition:** `GAP`
- **Threat/risk:** Public evidence may leak personal/secret data, omit critical bindings, be forged/tampered, or lose durable lineage and recoverability.
- **Repository evidence actually reviewed:** F123/F124 define public-minimum projection, allowlisting, authenticity, durability, access, redaction, retention, and recovery requirements. F126 compares public-only, split public/internal, and digest/reference candidates. F120/F121 prove fictional public/disposable fields and deterministic hashes, not authenticity or durable storage.
- **Evidence missing:** Approved disclosure model and field-necessity analysis; privacy/legal review; authenticity mechanism; internal/public audience controls; durable tamper-evident audit; retention/redaction/recovery evidence; mutation/access tests; and independent privacy/audit signoff.
- **Required remediation:** Define one versioned disclosure and audit-projection candidate, prove minimization and complete binding, specify authenticity/access/retention/recovery, and submit adversarial privacy/tamper evidence for independent review.
- **Residual risk:** Deterministic hashes alone do not authenticate records or prevent over-disclosure, deletion, or rollback.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; current artifacts support format conformance only.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; no independent privacy/audit reviewer signoff exists.

## Domain conclusion

Authenticated-evidence dispositions: `PASS 0`, `GAP 8`, `REQUIRED_CHANGE 0`, `BLOCKED 0`.

No finding is closed. No LSOD decision is approved. `coin.tx_validation.validate_transaction` remains canonical and mandatory. Authorization is not validation. Eligibility is not signer invocation. Bitcoin remains external evidence only.

Protected facts remain exactly: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.

Production Bitcoin proof architecture, Bitcoin confirmation/reorganization policy and count, observer quorum/independence, and signer implementation/runtime/deployment/activation remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`. This artifact authorizes no implementation or runtime behavior.
