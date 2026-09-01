# L28 High-Assurance Security Target v0.1

Status: `TARGET_DEFINED_DESIGN_ONLY`

Authority: subordinate to L28 Protocol v1.0.0

Claim status: L28 is **not** certified by this document as institutional-grade, high-assurance in production, more secure than Bitcoin, or superior to any financial or cryptocurrency system. This document defines evidence that would be required before any such future claim could be evaluated.

## 1. Security objective

### 1.1 Meaning of high assurance

For L28, **high assurance** means that every security-critical protocol, authority, implementation, operational, and recovery property has all of the following:

1. a precise, versioned security objective and threat model;
2. explicit accountable decisions with no undocumented defaults;
3. traceability from the objective to design, implementation, configuration, tests, review findings, remediation, and operational evidence;
4. deterministic fail-closed behavior for missing, malformed, contradictory, stale, revoked, superseded, unavailable, corrupt, or unauthenticated inputs and state;
5. independently reproducible security evidence across normal, adversarial, fault, concurrency, crash, and recovery conditions;
6. named independent reviewers with relevant qualifications and conflict disclosures;
7. no unremediated finding that can violate a protected protocol, authority, economic, custody, state, audit, or settlement invariant; and
8. separate, explicit approvals for design, decisions, implementation, deployment, and activation.

Documentation, fixtures, passing unit tests, a favorable review, deployment readiness, or operator intent alone is insufficient. High assurance is a maintained evidence state, not a one-time label.

### 1.2 Required proof categories

| Proof category | Minimum evidence target | Acceptance condition |
|---|---|---|
| Protocol and specification | Frozen normative requirements, complete invariant inventory, exact validation rules, threat model, version/change governance, and requirement traceability | Every consensus/economic rule has one canonical source and deterministic positive, negative, boundary, and fail-closed evidence |
| Authority | Machine-verifiable authority map, prohibited-path analysis, privilege/capability inventory, and separation-of-duty evidence | No component, operator, adapter, evidence source, signer, or external system can bypass or replace canonical L28 authority |
| Implementation | Reviewed source/configuration/build provenance, reproducible artifacts, dependency inventory, static analysis, and exact design-to-code traceability | Implemented behavior matches approved requirements with no undocumented authority or fail-open path |
| Conformance and adversarial testing | Deterministic conformance, malformed-input, abuse, fault, concurrency, crash/recovery, resource-exhaustion, and regression results | Required test families pass without waived security failures; failures are reproducible and remediated |
| Operational resilience | Deployment-boundary review, least privilege, monitoring, incident, backup/recovery, deactivation, and change-control evidence | Controlled exercises demonstrate safe failure, recovery without rollback, and no authority expansion under stress |
| Independent assurance | Reviewer identity/qualifications/independence, reviewed versions, methods, reproduced evidence, severity findings, remediation, residual risk, and signoff | Independent review is complete, reproducible, scope-explicit, and accepted by the accountable operator through a separate record |

### 1.3 Claim discipline

Any future security claim must:

- name the exact target version, implementation version, deployment boundary, evidence bundle, review date, and residual risks;
- distinguish design evidence, test evidence, deployment evidence, and observed operational evidence;
- state its scope and exclusions, including any unresolved operator or security decisions;
- use measurable comparisons under the framework in Section 7; and
- be withdrawn or requalified when evidence expires, scope changes, a material vulnerability appears, or a required gate reopens.

Marketing language such as “institutional-grade,” “high assurance,” “more secure,” “safer,” or “exceeds standards” is prohibited unless a separately governed claim record demonstrates every applicable gate and comparison requirement. This target itself supplies no such proof.

## 2. Protocol security target

### 2.1 Consensus integrity

**Target:** Canonical height, ledger state, transaction validity, issuance state, and history come only from the L28 consensus/ledger boundary. User input and external systems cannot become canonical state.

**Required evidence:**

- a complete consensus-state and trust-boundary specification;
- deterministic validation evidence for canonical height, transaction ordering, state transitions, reorganization/failure handling where applicable, and unavailable state;
- adversarial evidence against conflicting histories, stale state, malformed blocks/transactions, state substitution, and external override attempts; and
- independent Protocol and distributed-systems review with resolved findings.

**Acceptance condition:** every accepted transition derives from one authenticated canonical state; ambiguity or unavailable required state rejects or blocks processing rather than selecting a fallback.

### 2.2 Issuance integrity

**Target:** Coinbase is the only issuance mechanism. No admin, governance, manual, discretionary, adapter, signer, or external-system mint path exists.

**Required evidence:**

- whole-repository authority and call-path analysis showing all value creation passes strict coinbase validation;
- deterministic tests for strict coinbase identity, consensus-derived height, exact reward, zero-reward rejection, supply lookup, emission ceiling, hard cap, and missing-state failure;
- historical bootstrap/supply evidence proving fresh or empty local state cannot reissue historically mined supply; and
- independent economic and Protocol review.

**Acceptance condition:** no tested or reviewed path can increase `IssuedSupply` except a valid consensus coinbase, and all cap, schedule, height, and bootstrap checks fail closed.

### 2.3 Validation authority

**Target:** `coin.tx_validation.validate_transaction` remains the canonical mandatory transaction validator and binds its result to the exact transaction and required canonical state.

**Required evidence:**

- exact call-path and transaction-binding traceability for every acceptance or eligibility path;
- tests proving validation cannot be skipped, replaced, cached across a mismatched transaction/state, or overridden by authorization, signer, operator, adapter, Harness/Evals, or Bitcoin evidence; and
- independent review of validation equivalence and bypass resistance.

**Acceptance condition:** no transaction can become eligible for later processing unless the canonical validator succeeds for that exact transaction under the required canonical state. A successful authorization result is never accepted as validation.

### 2.4 Immutable economics

The protected facts are:

- hard cap: `28000000` L28;
- emission ceiling: `11130000` L28;
- historically mined: `2824584` L28;
- treasury locked: `500000` L28;
- circulating snapshot: `2324584` L28;
- halving interval: `210000`;
- reward schedule: `[28,14,7,3,1,0]`;
- historical mined-through entry: `100877`;
- next canonical height after bootstrap: `100878`;
- coinbase-only issuance;
- consensus-derived canonical height; and
- immutable historical evidence.

**Target:** no code, configuration, migration, decision, signer, operator, adapter, evidence system, or external observation can rewrite, recalculate, round, substitute, or silently supersede these facts.

**Required evidence:** immutable-source and repository-wide constant/use analysis, historical-evidence verification, deterministic boundary tests for every economic rule, migration/change review, and independent economic-security review.

**Acceptance condition:** all implementations and evidence reproduce the exact facts above, and any mismatch, missing history, or incompatible version fails closed.

### 2.5 Fail-closed behavior

**Target:** missing or untrusted consensus, ledger, supply, height, validation, policy, authority, custody, replay, time, audit, resource, or decision state cannot produce success, eligibility, invocation, issuance, or settlement.

**Required evidence:** an exhaustive failure-state inventory, deterministic error precedence, negative and fault-injection tests for every dependency, and proof that fallback, cache, retry, recovery, or emergency behavior cannot weaken the invariant.

**Acceptance condition:** every enumerated uncertain state has one deterministic non-authorizing outcome and an auditable reason.

## 3. Authority security target

### 3.1 Authority separation

**Target:** consensus, validation, authorization, signer eligibility, future signer invocation, custody, submission, settlement, observation, and review are distinct authority domains.

**Required evidence:** versioned authority and data-flow maps; component identity and capability inventories; separation-of-duty policies; authenticated decision/evidence bindings; negative capability tests; and independent authority-boundary review.

**Acceptance condition:** each action is performed only by its designated domain after its prerequisites, with no authority inferred from data possession, successful evaluation, advisory output, or prior-stage approval.

### 3.2 No override paths

**Target:** every issuance, supply, canonical-height, history, validation, consensus, and settlement override remains false.

**Required evidence:** static/AST analysis, runtime capability tests in a separately authorized non-production environment, privilege and administrative-interface review, dependency/adaptor review, and adversarial attempts to reach prohibited paths.

**Acceptance condition:** no direct, indirect, emergency, recovery, configuration, plugin, or external-evidence path can exercise protected authority.

### 3.3 Authorization is not validation

Authorization may decide whether an authenticated caller/operator/policy permits a proposed action. It cannot establish Protocol validity or replace `coin.tx_validation.validate_transaction`.

**Evidence target:** separately represented and version-bound authorization and validation results; tests for every combination of authorization/validation success and failure; exact transaction binding; and fail-closed mismatch handling.

### 3.4 Eligibility is not invocation

Eligibility may state that all currently reviewed prerequisites are satisfied. It cannot invoke a signer, access custody, create a signature, submit, broadcast, mutate a ledger, or settle.

**Evidence target:** separate interfaces, identities, capabilities, audit events, and operator gates; tests showing an eligible response has zero execution side effects; and independent verification that activation requires its own explicit approval.

## 4. Signer security target

The signer remains a future isolated authority boundary. This section defines evidence required before a future implementation could be evaluated; it authorizes none.

| Control target | Required measurable evidence | Blocking condition |
|---|---|---|
| Authenticated evidence | Approved proof and canonicalization profile; issuer/verifier identity and provenance; delegation/revocation/freshness; exact policy, approval, request, nonce, and replay binding; public-safe audit projection; forgery/mismatch/outage tests | Any unassigned authority, unresolved proof/policy choice, unauthenticated evidence, stale/unknown state, or failed independent cryptographic/identity review |
| Custody controls | Approved material policy; isolation/non-exportability; least privilege and separation of duties; lifecycle ceremonies; rotation/revocation; backup/recovery or explicit prohibition; destruction; compromise response; public-safe custody evidence | Any real custody path without approved controls, unverified provenance/health, secret exposure, rollback/reactivation, or unresolved independent custody review |
| Replay protection | Approved replay domain, nonce provenance, exact request/intent/policy binding, atomic check-and-record, durable retention/tombstones, and duplicate/conflict tests | Missing/corrupt/unavailable replay state, cross-domain reuse, ambiguous duplicate, retention loss, or state rollback |
| Atomic state | One authoritative boundary; approved consistency/order model; all-or-none replay/spend/approval/operator/audit-intent updates; monotonic versions; durability, fencing, integrity, recovery, and race/crash tests | Split authority, lost/ambiguous commit, stale replica, partial consumption, rollback, unsafe restore, or unresolved state/security review |
| Trusted time | Approved authenticated sources and selection policy; monotonic reference; uncertainty/skew/jump/rollback/outage handling; time evidence bound to every decision; boundary and source-failure tests | Missing/forged/conflicting/unavailable time, rollback, expired cache, or any unmeasured/unapproved production bound |
| Audit durability | Authenticated append-only lineage; ordered records; durable acknowledgement; checkpoints; access/redaction; public projection; retention and disaster recovery; mutation/deletion/reorder/truncation tests | Success before durable audit commitment, unverifiable lineage, secret leakage, unauthorized access, destructive rollback, or failed recovery |
| Runtime hardening | Bounded canonical parsing; measured request/rate/concurrency/CPU/memory/storage/time limits; least-privilege process/filesystem/network boundaries; safe errors; monitoring; DoS/fault/penetration evidence; runbooks | Missing limits, unbounded/degraded mode, privilege crossover, unauthorized capability, secret leakage, dependency fail-open behavior, or unresolved deployment review |

Passing offline signer fixtures or conformance tests proves only the tested deterministic contract. It does not prove production custody, durable state, trusted time, audit durability, service hardening, deployment safety, or activation eligibility.

## 5. Interoperability security target

### 5.1 Bitcoin external evidence only

Bitcoin interoperability, if separately authorized in the future, may supply authenticated external evidence only. It has zero authority over L28 issuance, supply, canonical height, validation, consensus, history, or settlement.

Bitcoin remains external evidence only.

Production proof architecture, Bitcoin confirmation/reorganization policy and count, and observer quorum/independence remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`. This target chooses none.

### 5.2 No bridge trust assumptions

No bridge, observer, adapter, proof source, chain state, or external finality assertion may be implicitly trusted or treated as L28 consensus. A future interoperability design would require explicit threat models, authenticated provenance, failure/isolation semantics, adversarial evidence, independent review, and a separately governed decision before implementation consideration.

### 5.3 Observation is not settlement

Observing, verifying, or recording an external event cannot issue L28, validate an L28 transaction, mutate the L28 ledger, or settle an L28 obligation.

**Acceptance condition:** absence, delay, contradiction, reorganization, forgery, or outage of external evidence cannot violate an L28 invariant; affected interoperability paths fail closed while L28 authority remains unchanged.

## 6. Adversarial testing target

All applicable tests must be deterministic where controllable, version-bound, reproducible, mapped to threats and requirements, and executed in separately authorized non-production environments. Test data must be fictional or disposable. No passing test grants runtime authority.

### 6.1 Fault testing

Required categories include malformed/unknown inputs, dependency loss, stale/corrupt state, partial operations, lost acknowledgement, storage/time/audit failure, resource exhaustion, component crash, and simultaneous failures.

**Evidence:** fault matrix, injection method, expected fail-closed result, actual result, artifacts, coverage gaps, and remediation verification.

### 6.2 Concurrency testing

Required categories include duplicate and conflicting requests, replay races, approval reuse, threshold races, cumulative-spend races, rotation/revocation overlap, policy transition, stale snapshots, deadlock, split brain, and recovery concurrency.

**Evidence:** stated invariants, controlled schedules or model-based exploration, unique-outcome proof, race findings, and independently reproduced results.

### 6.3 Recovery testing

Required categories include crash at every security-critical commit point, corrupt/stale/missing backup, incomplete restoration, forked lineage, lost commits, replay/counter reopening, incident quarantine, deactivation, and failed recovery.

**Evidence:** recovery-point inventory, authoritative-version proof, reconciliation, rollback prohibition, preserved audit lineage, operator-role evidence, and repeatable exercises.

### 6.4 Abuse testing

Required categories include forgery, replay, downgrade, reassociation, privilege escalation, identity/scope mismatch, collusion, unauthorized role combinations, parser abuse, denial of service, error/timing leakage, audit tampering, privacy leakage, external-authority injection, and prohibited-capability attempts.

**Evidence:** abuse-case catalog, attack preconditions, execution record, expected/actual outcome, residual exposure, and remediation.

### 6.5 Independent security review

Independent reviewers must disclose identity, qualifications, organizational and financial independence, conflicts, scope, exact artifacts/versions, methods, tests reproduced, findings by severity, remediation verification, limitations, and residual risk.

**Acceptance condition:** all required domains are covered by qualified independent reviewers; no critical authority/protocol/economic/custody/state vulnerability remains open; other accepted residual risks are explicit, bounded, justified, and operator-approved through a separate decision record.

## 7. Comparison framework

Comparison is category-based, evidence-normalized, version-specific, and scope-specific. It must not compare marketing labels, maturity by age alone, isolated feature counts, hypothetical designs against deployed systems, or incomparable threat models.

| Comparison category | Questions applied to Bitcoin | Questions applied to traditional financial systems | Questions applied to other cryptocurrency protocols | Evidence required for any future L28 claim |
|---|---|---|---|---|
| Consensus and canonical state | What exact safety/liveness and reorganization assumptions apply within the named scope/version? | What ledger-finality, reconciliation, operator, and institutional-control assumptions apply? | What consensus, validator, governance, finality, and failure assumptions apply? | Comparable threat model; normative rules; implementation/deployment scope; adversarial/fault evidence; independent review |
| Issuance and economics | How is issuance constrained and independently verified? | How can value/claims be created, adjusted, reversed, or reconciled, and by whom? | What mint, burn, governance, upgrade, cap, and emergency authorities exist? | Exact authority inventory; immutable-rule evidence; historical/supply proof; bypass analysis; boundary tests |
| Validation and authorization | Which rules establish validity, and which actors can change or bypass them? | How are transaction validity, permissions, exceptions, reversals, and operator actions separated? | How are protocol validation, application authorization, governance, and privileged paths separated? | Equivalent-scope authority maps; canonical-validator evidence; negative override tests; change governance |
| Custody and signing | What custody/signing assumptions are within the compared boundary? | What institutional custody, separation-of-duty, recovery, and insider controls apply? | What wallet, validator, bridge, multisignature, contract, or administrative custody assumptions apply? | Same-boundary custody scope; lifecycle/compromise evidence; penetration/adversarial results; independent custody review |
| State, time, audit, and recovery | What persistence, time, audit, and recovery properties are actually provided in scope? | What durable books, audit trails, time sources, disaster recovery, and oversight apply? | What replay, storage, oracle/time, event-log, upgrade, and recovery assumptions apply? | Reproducible fault/concurrency/crash/recovery evidence; audit authenticity/durability; measured operational results |
| Runtime and operational resilience | What deployed implementation, network, resource, and incident evidence exists? | What service hardening, access, monitoring, resilience, incident, and regulatory evidence exists? | What client diversity, deployment, dependency, DoS, monitoring, and incident evidence exists? | Equivalent observation period and scope; provenance; penetration/fault/load results; incidents and remediation; independent assessment |

No row states that L28 is equal or superior. A future comparative claim requires:

1. named comparison system, version, deployment boundary, time period, and security property;
2. a common threat model and equivalent evidence scope;
3. current, primary, independently verifiable evidence for both systems;
4. disclosed limitations, uncertainty, incidents, residual risk, and evidence gaps;
5. independent review of the comparison method and conclusion; and
6. wording limited to the measured property—never generalized to overall security without complete comparable evidence.

If comparable evidence is unavailable, the only permitted conclusion is `INSUFFICIENT_COMPARABLE_EVIDENCE`. Absence of public evidence is not evidence of superiority.

## 8. Security maturity gates

The gates are ordered and non-skippable. A later gate cannot retroactively satisfy an earlier one.

| Gate | Required entry evidence | Completion evidence | What completion does not authorize |
|---|---|---|---|
| `DESIGN_REVIEWED` | Versioned objectives, threat models, architecture, interfaces, authority map, and unresolved-decision inventory | Internal consistency review, Protocol/economic compatibility, traceability, and recorded gaps/blockers | Production choices, implementation, deployment, activation, or a high-assurance claim |
| `DECISIONS_APPROVED` | Complete decision register, named accountable authorities, qualified independent advice, candidate analysis, dependencies, and rollback/change control | Separate versioned approval record for every applicable decision, with no undocumented default and all conflicts resolved | Implementation, signer invocation, deployment, activation, or superiority claims |
| `IMPLEMENTATION_COMPLETE` | Separately authorized bounded implementation scope and approved decisions | Traceable reviewed code/configuration/build provenance, dependency inventory, control evidence, and no unauthorized paths | Security acceptance, deployment, activation, or production fitness |
| `SECURITY_TESTED` | Complete implementation and version-bound test/acceptance plans | Required deterministic, conformance, adversarial, fault, concurrency, recovery, abuse, resource, privacy, and regression evidence passes without waived security failures | Independent acceptance, deployment, activation, or institutional-grade claims |
| `INDEPENDENTLY_REVIEWED` | Complete implementation/test evidence, reviewer independence, exact scope, and remediation process | Qualified independent findings, reproduced evidence, verified remediation, explicit residual risks, and accountable operator acceptance | Deployment or activation; review advice is not operator runtime authorization |
| `DEPLOYMENT_APPROVED` | All prior gates complete; reviewed topology, least privilege, configuration provenance, monitoring, runbooks, recovery/deactivation, and environment-specific risks | Separate operator approval for one exact deployment boundary and version | Signer invocation, transaction submission, broadcast, settlement, or activation |
| `ACTIVATION_APPROVED` | All prior gates complete; operational readiness, current evidence, named operators, stop conditions, residual-risk acceptance, and separate activation proposal | Explicit final operator authorization for exact capabilities, environment, version, effective interval, monitoring, and deactivation rules | Any capability, environment, version, or interval outside the approval |

Gate state must revert to incomplete when its evidence becomes stale, invalid, superseded, compromised, materially changed, or contradicted by a security finding. Re-entry requires versioned change control and re-verification; historical evidence is preserved.

## 9. Current maturity and non-activation conclusion

This document defines a target only. It does not certify completion of `DESIGN_REVIEWED` for the whole L28 system and does not advance any later gate. Existing signer architecture, profiles, fixtures, tests, reviews, Phase 1 decision records, and Phase 2 review-preparation documents remain bounded evidence with their recorded unresolved decisions and limitations.

Production Bitcoin proof architecture, Bitcoin confirmation/reorganization policy and count, observer quorum/independence, and signer implementation/runtime/deployment/activation remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

The blocked items are: production Bitcoin proof architecture; Bitcoin confirmation/reorganization policy and count; observer quorum/independence; and signer implementation/runtime/deployment/activation.

L28 may not be described as institutional-grade, high-assurance in production, more secure than Bitcoin, or superior to traditional financial systems or other cryptocurrency protocols on the authority of this document. Such a claim requires all applicable maturity gates plus the comparison evidence in Section 7 and separately governed claim approval.

This specification authorizes no protocol change, code change, signer, wallet, key, signature, RPC, network, submission, broadcast, mining, bridge, ledger mutation, settlement, database, migration, server, deployment, testnet, production process, publication claim, or activation.
