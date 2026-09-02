# L28 Security Review Remediation Workflow v0.1

Status: `FRAMEWORK_ONLY_NO_REMEDIATION`

Decision effect: none. This workflow governs future finding remediation records. It creates no finding, accepts no remediation, approves no LSOD decision, and authorizes no implementation or runtime action.

## 1. Purpose and governing principles

The workflow ensures that a future independent security finding is created, evidenced, remediated, re-reviewed, regressed, closed, changed, or reopened through one auditable fail-closed process.

Principles:

- finding creation, remediation ownership, independent review, operator decision, deployment approval, and activation approval are separate authorities;
- the independent reviewer validates evidence and closure but does not approve an LSOD decision;
- the accountable operator cannot self-certify independent review;
- no finding may be closed by waiver, schedule pressure, undocumented risk acceptance, severity downgrade, or absence of evidence;
- every transition is version-bound, append-only, signed by its authorized actor, and reproducible from public-safe evidence; and
- missing, stale, superseded, contradictory, corrupt, unauthenticated, or unavailable evidence fails closed.

## 2. Roles and separation of duties

| Role | Permitted responsibility | Prohibited authority |
|---|---|---|
| Review coordinator | Allocate review series, verify record completeness, maintain append-only history, route evidence | Cannot assign severity, validate remediation, approve decisions, or authorize runtime |
| Independent reviewer | Create findings, classify severity, validate evidence, accept/reject remediation for re-review, verify remediation, sign closure or reopening | Cannot implement its own remediation and independently approve it; cannot approve LSOD decisions or runtime |
| Remediation owner | Propose and, only under a separately authorized scope, produce remediation evidence | Cannot alter finding history, assign final severity, self-verify, close findings, approve decisions, or activate runtime |
| Evidence custodian | Preserve canonical evidence bundles, provenance, access records, and immutable versions | Cannot change evidence after signoff or infer security disposition |
| Accountable operator | Later consider complete review evidence in a separate LSOD decision process | Cannot bypass independent review, silently waive findings, or treat closure as implementation/deployment/activation authority |

One individual or organization may not occupy conflicting roles for the same finding without a documented independence review; unresolved conflict blocks closure.

## 3. Controlled states and transitions

The canonical remediation states are those in `security_review_finding_registry_v0.1.md`:

`NOT_APPLICABLE`, `OPEN`, `EVIDENCE_SUBMITTED`, `REMEDIATION_PROPOSED`, `UNDER_REVIEW`, `REJECTED`, `VERIFIED`, `CLOSED`, and `REOPENED`.

Allowed transitions are:

| From | To | Required authorization and evidence |
|---|---|---|
| finding creation | `NOT_APPLICABLE` | Independent reviewer assigns supported `PASS`; no remediation is required; closure review still pending |
| finding creation | `OPEN` | Independent reviewer assigns `GAP`, `REQUIRED_CHANGE`, or `BLOCKED` with exact reason and required next evidence |
| `OPEN` | `EVIDENCE_SUBMITTED` | Remediation owner/custodian submits a canonical evidence bundle addressing the finding |
| `OPEN` | `REMEDIATION_PROPOSED` | Remediation owner submits a bounded proposal mapped to threat, requirement, tests, dependencies, and non-activation constraints |
| `REJECTED` | `REMEDIATION_PROPOSED` | Revised proposal addresses every rejection reason with a new version |
| `REMEDIATION_PROPOSED` | `EVIDENCE_SUBMITTED` | Separately authorized remediation work, if any, produces the promised evidence; proposal approval alone is insufficient |
| `EVIDENCE_SUBMITTED` | `UNDER_REVIEW` | Independent reviewer validates bundle identity, provenance, completeness, applicability, and reviewability |
| `EVIDENCE_SUBMITTED` | `REJECTED` | Reviewer records exact evidence-validation failure and required correction |
| `REMEDIATION_PROPOSED` | `REJECTED` | Reviewer records why the proposal cannot satisfy the finding or violates scope/authority |
| `UNDER_REVIEW` | `VERIFIED` | Independent re-review reproduces required evidence and tests, finds remediation effective, and records regression results/residual risk |
| `UNDER_REVIEW` | `REJECTED` | Independent re-review finds incomplete, ineffective, unsafe, non-reproducible, contradictory, or out-of-scope remediation |
| `NOT_APPLICABLE` | `CLOSED` | Independent reviewer verifies all `PASS` closure criteria and signs the exact record version |
| `VERIFIED` | `CLOSED` | Independent reviewer verifies closure criteria, dependencies, regressions, residual risks, and signoff completeness |
| `CLOSED` | `REOPENED` | New vulnerability, evidence expiry, regression, scope/version change, compromise, contradiction, failed dependency, or invalidated independence is recorded |
| `REOPENED` | `OPEN` | Reviewer defines current severity, impact, and required evidence under a new record version |

All unlisted transitions are prohibited. State cannot move backward by editing history; correction uses a new record version and an allowed transition. `VERIFIED` and `CLOSED` do not approve an LSOD decision.

## 4. Stage 1 — Finding creation

An independent reviewer creates a finding only after reviewing identified evidence against an exact requirement and LSOD scope.

Creation requires:

1. an allocated finding ID and record version;
2. one primary and all related LSOD IDs;
3. exact source requirements and reviewed artifact versions;
4. a reproducible description and threat model;
5. severity rationale using `PASS`, `GAP`, `REQUIRED_CHANGE`, or `BLOCKED`;
6. evidence/test manifest and limitations;
7. required remediation or missing prerequisite;
8. maturity-gate effect; and
9. independent reviewer identity, qualifications, conflicts, and initial signoff.

The framework document contains no created findings. Future finding creation requires a separately authorized independent-review engagement.

## 5. Stage 2 — Evidence submission

Evidence submission must provide a canonical ordered manifest containing artifact identity, version/digest, provenance, collection method, custodian, freshness, scope, confidentiality classification, and predecessor. Evidence may be documentation, decisions, implementation artifacts, test results, operational evidence, or prior review evidence, but its type and limitations must be explicit.

Submission rules:

- never include private keys, seeds, mnemonics, xprv, wallet/RPC credentials, tokens, or production secrets;
- do not mix evidence from incompatible versions or environments;
- do not overwrite an earlier bundle;
- identify unavailable, failed, contradictory, or superseded evidence;
- demonstrate exact mapping to each finding requirement; and
- state that submission supplies evidence only and does not authorize remediation execution, deployment, or activation.

## 6. Stage 3 — Reviewer validation

Before substantive re-review, the independent reviewer validates:

- identity, provenance, integrity, version, freshness, and scope of every artifact;
- reviewer access sufficient to reproduce material evidence without accessing prohibited secrets;
- completeness against the finding and unresolved dependencies;
- test determinism, independence, environment, expected outcome, actual outcome, and failure handling;
- absence of self-certification or reviewer conflict; and
- preservation of Protocol, authority, economics, Bitcoin isolation, and non-activation constraints.

Validation failure moves the record to `REJECTED`. It cannot be repaired by reviewer assumption or silent normalization.

## 7. Stage 4 — Remediation proposal

A remediation proposal must state:

- exact finding and record version addressed;
- root cause and security invariant restored;
- bounded proposed change and explicitly excluded capabilities;
- affected LSOD decisions, maturity gates, artifacts, interfaces, dependencies, and evidence;
- threat analysis, new attack surface, migration/change-control implications, and rollback prohibition;
- required positive, negative, boundary, fail-closed, adversarial, fault, concurrency, recovery, abuse, and regression tests as applicable;
- independent re-review plan and acceptance criteria; and
- proof that proposal approval cannot authorize implementation, deployment, or activation.

If remediation would require code, infrastructure, custody, state, network, deployment, or runtime work, that work requires a separate explicit authorization. This workflow does not grant it.

## 8. Stage 5 — Independent re-review

The independent reviewer must:

1. inspect the exact remediation and evidence versions;
2. reproduce material tests and verification steps;
3. test original exploit/failure conditions and credible variants;
4. confirm root cause—not only the observed symptom—is addressed;
5. assess new attack surfaces, regressions, authority changes, privacy effects, and residual risks;
6. verify all dependencies and maturity-gate effects;
7. record findings, limitations, and disposition; and
8. sign the result with current independence/conflict disclosure.

The remediation owner cannot serve as the sole independent reviewer. A favorable re-review produces `VERIFIED`, not automatic closure or decision approval.

## 9. Stage 6 — Rejected remediation

Rejection is mandatory when a proposal or evidence bundle is incomplete, non-reproducible, stale, contradictory, mis-scoped, dependent on an unresolved decision, unsafe, fail-open, authority-expanding, privacy-breaking, or unsupported by independent evidence.

The rejection record must include:

- exact rejected version and evidence bundle;
- each rejection reason mapped to a requirement/threat;
- severity and maturity-gate effect;
- whether prior evidence remains valid;
- required changes or prerequisites for resubmission; and
- reviewer signoff.

Rejection never deletes the submission. Resubmission creates a new version. Repeated rejection cannot be waived into `VERIFIED` or `CLOSED`.

## 10. Stage 7 — Regression review

Before `VERIFIED` or `CLOSED`, regression review must cover:

- the original requirement and threat;
- every directly and transitively affected LSOD/control;
- canonical Protocol and economic invariants;
- authority separation and prohibited override paths;
- `coin.tx_validation.validate_transaction` exact-transaction binding;
- authorization/validation and eligibility/invocation separation;
- deterministic conformance and applicable adversarial/fault/concurrency/recovery/abuse tests;
- security/privacy properties not intended to change; and
- prior closed findings whose evidence shares the changed component, dependency, policy, or assumption.

Any regression failure prevents closure and may reopen linked findings or maturity gates.

## 11. Stage 8 — Closure

Closure requires the separate `security_review_closure_criteria_v0.1.md` to be satisfied, current independent signoff, and a final immutable evidence manifest. Closure records the resulting severity, residual risk, dependencies, regression outcome, and maturity-gate effect.

Closure does not:

- approve or update an LSOD decision automatically;
- authorize a signer, signing, custody, submission, broadcast, settlement, deployment, testnet, or activation; or
- resolve any Bitcoin or activation gate.

## 12. Change-control history and reopening

Every record version and transition must append:

- prior and new version/state/severity;
- actor identity and authority;
- timestamp evidence source and limitations;
- reason and affected requirements/LSOD IDs;
- exact added, removed, superseded, or invalidated evidence;
- reviewer disposition/signoff; and
- maturity-gate and decision-record impact.

History is immutable. Material changes, new vulnerabilities, expired evidence, implementation/configuration changes, changed dependencies, reviewer-independence failures, regressions, incidents, or contradicted assumptions require re-review and may require `REOPENED`. Closed evidence is never silently carried forward.

## 13. Protocol, economics, and non-activation

L28 Protocol v1.0.0 remains authoritative. `coin.tx_validation.validate_transaction` remains the canonical mandatory validator and must bind to the exact transaction. Authorization is not validation. Eligibility is not signer invocation.

Bitcoin remains external evidence only and has zero authority over L28 issuance, supply, canonical height, validation, consensus, history, or settlement. The following remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`: production Bitcoin proof architecture; Bitcoin confirmation/reorganization policy and count; observer quorum/independence; and signer implementation/runtime/deployment/activation.

Protected facts remain exactly: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.

This workflow authorizes no finding disposition, decision approval, protocol or code change, signer, wallet, key, signature, HSM/KMS access, RPC, network, submission, broadcast, mining, bridge, ledger/state mutation, settlement, database, migration, server, deployment, testnet, production process, or activation.
