# L28 Security Review Closure Criteria v0.1

Status: `FRAMEWORK_ONLY_NO_CLOSURES`

Decision effect: none. This document defines future finding-closure requirements. It closes no finding, approves no LSOD decision, resolves no security item, and authorizes no implementation or runtime behavior.

## 1. Closure principles

Finding closure means only that the exact finding, scoped requirement, artifact versions, and evidence bundle satisfy these criteria at the time of independent signoff.

Closure does not mean:

- the linked LSOD decision is approved;
- all findings for that LSOD decision are closed;
- a security maturity gate is complete;
- an implementation, deployment, or activation is authorized; or
- L28 is certified as high-assurance, institutional-grade, or superior to another system.

Closure is prohibited when evidence, scope, versions, dependencies, remediation, regressions, reviewer independence, or authority boundaries are missing, stale, contradictory, unauthenticated, unavailable, or ambiguous. Uncertainty fails closed.

## 2. Universal closure requirements

A finding may enter `CLOSED` only when all of the following are true:

1. the finding ID, record version, primary/related LSOD mappings, source requirements, and review-series identity are valid and immutable;
2. the current severity is `PASS`;
3. the complete reviewed evidence manifest is canonical, ordered, version-bound, provenance-verified, immutable, and reproducible;
4. the threat model, assumptions, failure modes, privacy effects, attack surface, affected invariants, and residual risks are explicit;
5. every required remediation is independently verified, or `required_remediation: NONE` is justified for an original `PASS`;
6. all applicable positive, negative, boundary, fail-closed, adversarial, fault, concurrency, recovery, abuse, privacy, and regression evidence passes without waived security failure;
7. unresolved dependencies do not undermine the scoped conclusion;
8. no related open finding contradicts closure;
9. Protocol, authority, economic, historical, Bitcoin-isolation, and non-activation invariants are preserved;
10. the independent reviewer has reproduced material evidence, verified remediation, documented limitations/residual risks, and signed the exact record version;
11. reviewer qualifications, organizational/financial independence, and conflicts are documented and acceptable; and
12. the immutable change-control history includes every state, severity, evidence, remediation, rejection, re-review, regression, and signoff event.

Failure of any requirement prevents closure.

## 3. Severity-specific criteria

### 3.1 `PASS`

`PASS` qualifies for closure only when:

- the exact requirement is fully evidenced for the reviewed versions and scope;
- required tests and independent reproduction succeed;
- no material remediation remains;
- all residual risks and limitations are explicit and do not contradict the scoped requirement;
- no prohibited override, fail-open behavior, authority transfer, secret exposure, or unresolved high-impact condition exists; and
- independent signoff recommends the scoped finding as `READY_FOR_OPERATOR_CONSIDERATION`.

A `PASS` finding with incomplete signoff, stale evidence, failed regressions, or unresolved contradictory dependency cannot close. `PASS` is evidence disposition only, not operator approval.

### 3.2 `GAP`

A current `GAP` cannot close. It remains `OPEN`, `EVIDENCE_SUBMITTED`, `REMEDIATION_PROPOSED`, `UNDER_REVIEW`, `REJECTED`, or `REOPENED` until the missing evidence/specification/traceability/test/dependency is supplied and independently reviewed.

To become closure-eligible:

1. the gap must be precisely filled with new versioned evidence;
2. the reviewer must verify completeness, provenance, reproducibility, and applicability;
3. required regression review must pass; and
4. a new finding-record version must reclassify the severity to `PASS` with rationale and signoff.

Schedule pressure, undocumented assumptions, evidence unavailability, risk acceptance, or narrowing scope after discovery cannot close a `GAP`.

### 3.3 `REQUIRED_CHANGE`

A current `REQUIRED_CHANGE` cannot close. It remains unresolved until:

1. a bounded remediation proposal addresses the root cause and all affected invariants;
2. any implementation work was separately authorized outside this framework;
3. complete remediation evidence is submitted with provenance and exact versions;
4. the independent reviewer reproduces the original failure and credible variants, verifies the remediation, and assesses new attack surfaces;
5. all direct/transitive regression and security tests pass;
6. related findings and maturity gates are reconciled; and
7. a new record version reclassifies the finding to `PASS` with independent signoff.

Partial mitigation, compensating control without reviewed equivalence, waived failure, or accepted vulnerability does not satisfy closure.

### 3.4 `BLOCKED`

A current `BLOCKED` finding cannot close or be downgraded by assumption. It remains blocked until every stated prerequisite is present, authoritative, version-bound, and independently reviewable.

After prerequisites become available:

1. create a new finding-record version preserving the blocked history;
2. independently validate the prerequisite evidence and reviewer independence;
3. conduct the previously blocked substantive review;
4. assign the evidence-supported current severity; and
5. apply the applicable closure path.

If the blocker is a future security decision, prohibited capability, invalid authority boundary, or unresolved GAT item, closure must wait for a separately governed authorization or decision. This framework cannot supply it.

## 4. Required independent-review evidence

Closure evidence must include:

- reviewer name/role and relevant domain qualifications;
- organizational, financial, authorship, and implementation independence plus conflict disclosure;
- exact finding, LSOD, requirements, artifacts, configurations, environments, versions, and digests reviewed;
- methods, tools where disclosed safely, test selection, evidence sampled, and evidence independently reproduced;
- threat-model assessment, assumptions, limitations, and excluded scope;
- original finding reproduction for remediated `REQUIRED_CHANGE` items where safely possible;
- remediation-difference analysis and root-cause verification;
- complete required test and regression manifests with expected/actual outcomes;
- findings by severity, residual risks, dependencies, and maturity-gate effects;
- remediation and regression verification results;
- closure recommendation and `READY_FOR_OPERATOR_CONSIDERATION` or `NOT_READY_FOR_OPERATOR_CONSIDERATION` disposition; and
- dated signoff bound to the exact immutable finding-record/evidence versions.

Reviewer recommendation remains advisory. Missing, conflicted, self-authored, unverifiable, or version-ambiguous independent-review evidence blocks closure.

## 5. Remediation closure rules

- `VERIFIED` precedes `CLOSED` for remediated findings; verification cannot be skipped.
- The reviewer must verify the security property, not merely confirm that a change occurred.
- Root cause and credible variants must be addressed; symptom-only fixes are insufficient.
- Every rejected proposal/evidence bundle remains in immutable history and its rejection reasons must be resolved explicitly.
- Regression scope includes directly and transitively affected requirements, decisions, components, dependencies, policies, tests, and previously closed findings.
- No finding may close with a failed required test, waived security failure, suppressed evidence, or unexplained result.
- Residual risk must be explicit, bounded, evidence-supported, and compatible with the scoped `PASS`; it cannot override a protected invariant.
- Closure evidence must state the conditions that require reopening.

## 6. Decision-record update rules

A linked LSOD decision record may be considered for a separately authorized update only when:

1. every finding mapped to the exact decision candidate, scope, and version is `CLOSED` with current severity `PASS`;
2. all cross-linked findings and dependencies that can affect the decision are closed or explicitly prove no blocking effect;
3. required Phase 2 evidence and questionnaire responses are complete;
4. the independent review bundle recommends `READY_FOR_OPERATOR_CONSIDERATION` and contains current signoff;
5. every required operator, implementation-evidence, and security dependency is satisfied at an exact version;
6. no `REQUIRED_CHANGE`, `GAP`, `BLOCKED`, `OPEN`, `REJECTED`, `REOPENED`, stale, or contradicted finding remains applicable;
7. the proposed update contains the accountable approver, selected value/profile, rationale, threat model, dependencies, evidence, tests, independent review, effective scope/interval, change control, rollback/deactivation, and public audit reference required by Foundation125/126; and
8. the update explicitly states that decision approval does not imply implementation, signer invocation, deployment, activation, broadcast, or settlement.

Decision records are never edited silently. A later authorized update must create a superseding version that preserves prior history. Closing a finding does not perform or authorize that update. An independent reviewer recommends; the separately accountable operator decides.

The four GAT decisions cannot be updated by this framework:

- `LSOD-GAT-001` — production Bitcoin proof architecture;
- `LSOD-GAT-002` — Bitcoin confirmation/reorganization policy and count;
- `LSOD-GAT-003` — observer quorum/independence; and
- `LSOD-GAT-004` — signer implementation/runtime/deployment/activation.

They remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

## 7. Maturity-gate effects

Under `l28_high_assurance_security_target_v0.1.md`:

- an applicable open `GAP`, `REQUIRED_CHANGE`, or `BLOCKED` prevents completion of the affected gate;
- a reopened finding reopens every gate that relied on its prior closure;
- closure of one finding cannot complete a gate unless all other gate evidence is independently satisfied;
- `DESIGN_REVIEWED` does not imply `DECISIONS_APPROVED`;
- `DECISIONS_APPROVED` does not imply `IMPLEMENTATION_COMPLETE`;
- `IMPLEMENTATION_COMPLETE` does not imply `SECURITY_TESTED`;
- `SECURITY_TESTED` does not imply `INDEPENDENTLY_REVIEWED`;
- `INDEPENDENTLY_REVIEWED` does not imply `DEPLOYMENT_APPROVED`; and
- `DEPLOYMENT_APPROVED` does not imply `ACTIVATION_APPROVED`.

No gate may be skipped, aggregated by assumption, or satisfied retroactively.

## 8. Reopening and closure invalidation

A closed finding must become `REOPENED` when any of the following may affect its conclusion:

- a material design, decision, implementation, configuration, dependency, environment, deployment, or scope change;
- evidence expiry, revocation, corruption, loss, supersession, provenance failure, or contradiction;
- a new vulnerability, attack technique, incident, privacy impact, failed test, or regression;
- reviewer-independence or signoff invalidation;
- changed threat assumptions, authority mapping, recovery model, or protected invariant; or
- discovery that closure omitted an applicable requirement, LSOD mapping, dependency, or finding.

Reopening is append-only and preserves the prior closure record. A reopened finding blocks affected decision consideration and maturity gates until it completes the workflow again.

## 9. Empty closure state

This framework closes zero findings. No `PASS`, `GAP`, `REQUIRED_CHANGE`, or `BLOCKED` conclusion is created or implied. No LSOD security item is resolved.

## 10. Protocol, economics, and non-activation

L28 Protocol v1.0.0 remains authoritative. `coin.tx_validation.validate_transaction` remains the canonical mandatory validator and must bind to the exact transaction. Authorization is not validation. Eligibility is not signer invocation.

Bitcoin remains external evidence only and has zero authority over L28 issuance, supply, canonical height, validation, consensus, history, or settlement. Production Bitcoin proof architecture, Bitcoin confirmation/reorganization policy and count, observer quorum/independence, and signer implementation/runtime/deployment/activation remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

Protected facts remain exactly: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.

This framework authorizes no finding closure, decision approval, protocol or code change, signer, wallet, key, signature, HSM/KMS access, RPC, network, submission, broadcast, mining, bridge, ledger/state mutation, settlement, database, migration, server, deployment, testnet, production process, or activation.
