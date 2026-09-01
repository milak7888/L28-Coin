# Local Signer Implementation Gate Matrix v0.1

Status: `DEFINED_DESIGN_ONLY`

Foundation: 124, workstream 5

Review boundary: Foundations122-124

Subordinate authority: L28 Protocol v1.0.0

## 1. Purpose

This matrix maps every Foundation122 `GAP_REQUIRES_FUTURE_WORK` and `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` finding through its Foundation123 architecture and Foundation124 profile/contract to the evidence needed before any later signer implementation could be considered.

It is a planning and security-gate artifact only. It grants no authority to implement, invoke, deploy, or activate a signer. No row is satisfied by documentation alone. No row transfers authority from L28 Protocol v1.0.0, `coin.tx_validation.validate_transaction`, or the canonical ledger.

Matrix status meanings:

- `PROFILE_DEFINED_DESIGN_ONLY`: Foundation124 defines a future control contract, but no production decision or implementation is approved.
- `BLOCKED_PENDING_OPERATOR_DECISIONS_AND_IMPLEMENTATION_EVIDENCE`: one or more named `OPERATOR_DECISION_REQUIRED` items, implementation artifacts, tests, or independent reviews are absent.
- `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`: the security architecture or production policy itself remains intentionally undecided.
- `INELIGIBLE_FOR_ACTIVATION`: implementation, runtime, deployment, and activation are prohibited at this milestone.

Authorization is not Protocol validation. Signer eligibility is not signer invocation. Passing an implementation gate in the future would not itself authorize signing, broadcast, settlement, deployment, or activation.

## 2. Complete Foundation122 gap/blocked matrix

| F122 finding and class | Foundation123 architecture | Foundation124 profile or contract | Remaining operator decision | Required implementation evidence | Required tests and review | Activation status |
|---|---|---|---|---|---|---|
| `F122-G01` — `GAP_REQUIRES_FUTURE_WORK`: authenticated caller/operator/policy/approval evidence | `authenticated_signer_evidence_architecture_v0.1.md` | `authenticated_signer_evidence_profile_v0.1.md` | Proof format/algorithm; issuer registry and delegation; verifier identity/material; lifetimes; revocation; policy activation; approval governance; replay domain; audit disclosure | Independent issuer registry and verifier; authenticated provenance/revocation/time/policy resolution; exact request and replay binding; public audit projection; secure failure evidence | Deterministic conformance plus forgery, stale/revoked, delegation, mismatch, replay, policy-version, threshold, outage, privacy, and independent security tests/review | `BLOCKED_PENDING_OPERATOR_DECISIONS_AND_IMPLEMENTATION_EVIDENCE`; `INELIGIBLE_FOR_ACTIVATION` |
| `F122-G02` — `GAP_REQUIRES_FUTURE_WORK`: signer key custody and lifecycle | `local_signer_key_custody_lifecycle_architecture_v0.1.md` | `local_signer_custody_control_profile_v0.1.md` | Algorithm/material allowlist; generation/import boundary; isolation; role thresholds; ceremonies; activation/rotation/revocation; backup/recovery; destruction; compromise response; custody evidence | Isolated custody implementation; authenticated ceremonies; non-exportability/access evidence; monotonic lifecycle; revocation/rotation/recovery/destruction evidence; public-safe custody evidence | Provisioning, access, separation-of-duty, lifecycle, compromise, recovery, destruction, leakage, isolation, fault, and independent custody review | `BLOCKED_PENDING_OPERATOR_DECISIONS_AND_IMPLEMENTATION_EVIDENCE`; `INELIGIBLE_FOR_ACTIVATION` |
| `F122-G03` — `GAP_REQUIRES_FUTURE_WORK`: atomic replay/idempotency state | `local_signer_atomic_state_semantics_v0.1.md` | `local_signer_atomic_state_storage_contract_v0.1.md` | Storage/consistency model; partition/order rules; idempotency/replay scope and retention; conflicts/timeouts; durability; recovery; integrity/versioning | Atomic check-and-record; exact duplicate response; conflict rejection; monotonic versions; durable unique outcome; corruption/unavailability fail closed; recovery evidence | Duplicate, conflict, concurrent race, split-brain, timeout, partial commit, crash-point, recovery, retention, integrity, and independent storage review | `BLOCKED_PENDING_OPERATOR_DECISIONS_AND_IMPLEMENTATION_EVIDENCE`; `INELIGIBLE_FOR_ACTIVATION` |
| `F122-G04` — `GAP_REQUIRES_FUTURE_WORK`: atomic economic-control and spending-limit state | `local_signer_atomic_state_semantics_v0.1.md` | `local_signer_atomic_state_storage_contract_v0.1.md` | Spend partitions/windows/pending treatment; arithmetic unit; approval/operator consumption; isolation/order; compensation and retention policy | Atomic replay, spend, approval, operator, decision, and audit-intent commit; integer-safe counters; exact threshold consumption; no rollback; lineage evidence | Boundary/overflow/underflow, concurrent spend, duplicate approval, threshold race, policy transition, rollback, compensation, crash/recovery, and independent review | `BLOCKED_PENDING_OPERATOR_DECISIONS_AND_IMPLEMENTATION_EVIDENCE`; `INELIGIBLE_FOR_ACTIVATION` |
| `F122-G05` — `GAP_REQUIRES_FUTURE_WORK`: trusted production time | `local_signer_time_audit_runtime_hardening_architecture_v0.1.md` | `local_signer_time_audit_resource_policy_v0.1.md` | Authenticated sources; selection/quorum; monotonic reference; skew/uncertainty; rollback/forward-jump; outage/cache values | Authenticated time evidence bound to every decision; monotonic/rollback detection; uncertainty enforcement; outage fail-closed evidence | Boundary, rollback, forward jump, disagreement, skew, uncertainty, source forgery, outage/cache expiry, recovery, and independent time review | `BLOCKED_PENDING_OPERATOR_DECISIONS_AND_IMPLEMENTATION_EVIDENCE`; `INELIGIBLE_FOR_ACTIVATION` |
| `F122-G06` — `GAP_REQUIRES_FUTURE_WORK`: durable tamper-evident audit evidence | `local_signer_time_audit_runtime_hardening_architecture_v0.1.md` | `local_signer_time_audit_resource_policy_v0.1.md` | Authenticity/integrity mechanism; checkpoints; storage/durability; retention/recovery; access/redaction/publication | Authenticated append-only lineage; durable acknowledgement; access evidence; public-safe projection; checkpoint and recovery proof; no secret leakage | Mutation/deletion/insertion/reorder/truncation/rollback, access, redaction, durability loss, checkpoint, disaster recovery, privacy, and independent audit review | `BLOCKED_PENDING_OPERATOR_DECISIONS_AND_IMPLEMENTATION_EVIDENCE`; `INELIGIBLE_FOR_ACTIVATION` |
| `F122-G07` — `GAP_REQUIRES_FUTURE_WORK`: runtime/service hardening | `local_signer_time_audit_runtime_hardening_architecture_v0.1.md` | `local_signer_time_audit_resource_policy_v0.1.md` | Parser limits; rates/resources; secure errors; monitoring; process/network/filesystem/secret isolation; topology/runbooks | Enforced bounded parsing and budgets; authenticated rate state; least-privilege isolation; safe errors; monitoring health; fail-closed dependency behavior | Below/exact/above boundaries, malformed/adversarial/DoS, exhaustion, privilege escape, dependency failure, backpressure, error leakage, runbook, and independent penetration review | `BLOCKED_PENDING_OPERATOR_DECISIONS_AND_IMPLEMENTATION_EVIDENCE`; `INELIGIBLE_FOR_ACTIVATION` |
| `F122-G08` — `GAP_REQUIRES_FUTURE_WORK`: fixture/test evidence limitations | `local_signer_time_audit_runtime_hardening_architecture_v0.1.md` | All four Foundation124 control profiles/contracts, with test policy in `local_signer_time_audit_resource_policy_v0.1.md` | Implementation-specific conformance, fault, adversarial, concurrency, crash, recovery, custody, time, audit, resource, and integration acceptance criteria | Production-representative test harnesses and review evidence without real activation; traceability from every control and operator decision to executable tests | All tests named in `F122-G01`-`F122-G07`, regression preservation, static/AST security review, fault injection, independent assessment, and remediation verification | `BLOCKED_PENDING_OPERATOR_DECISIONS_AND_IMPLEMENTATION_EVIDENCE`; `INELIGIBLE_FOR_ACTIVATION` |
| `F122-B01` — `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`: production Bitcoin proof architecture | Preserved unresolved across all four Foundation123 architecture documents | Explicitly preserved unresolved across all four Foundation124 profiles/contracts | `OPERATOR_DECISION_REQUIRED`: separately authorized production proof architecture; Foundation124 chooses none | Later approved architecture and implementation evidence proving Bitcoin is authenticated external evidence only and cannot affect L28 authority | Adversarial proof, provenance, mismatch, isolation, availability, fail-closed, and independent interoperability security review | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`; `INELIGIBLE_FOR_ACTIVATION` |
| `F122-B02` — `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`: Bitcoin confirmation/reorg policy and count | Preserved unresolved across all four Foundation123 architecture documents | Explicitly preserved unresolved across all four Foundation124 profiles/contracts | `OPERATOR_DECISION_REQUIRED`: separately authorized confirmation/reorg policy and count; no value selected | Later approved policy, authenticated evidence binding, reorg handling, and fail-closed implementation evidence | Boundary/reorg/stale/conflicting proof/outage tests and independent policy/security review | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`; `INELIGIBLE_FOR_ACTIVATION` |
| `F122-B03` — `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`: observer quorum and independence | Preserved unresolved across all four Foundation123 architecture documents | Explicitly preserved unresolved across all four Foundation124 profiles/contracts | `OPERATOR_DECISION_REQUIRED`: separately authorized observer quorum/independence model; no quorum selected | Later approved independence model, authenticated observer identity/provenance, equivocation detection, and outage evidence | Collusion, equivocation, correlated failure, insufficient/unavailable observer, mismatch, and independent security review | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`; `INELIGIBLE_FOR_ACTIVATION` |
| `F122-B04` — `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`: eligibility for future signer implementation/runtime/activation | All four Foundation123 architecture documents are design-only prerequisites | All four Foundation124 profiles/contracts plus this matrix | Every applicable operator decision in this matrix; separate scope, implementation, deployment, and activation authorizations; all earlier gates explicitly satisfied | Reviewed implementation proving authenticated evidence, custody, atomic controls, trusted time, durable audit, hardening, canonical validation binding, authority firewall, and non-execution-to-invocation separation | Complete conformance, regression, adversarial, security, custody, fault, concurrency, crash/recovery, deployment-boundary, independent review, remediation, and operator acceptance evidence | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`; `INELIGIBLE_FOR_ACTIVATION` |

The inventory above is exhaustive for Foundation122 non-PASS findings: eight GAP rows and four BLOCKED rows, with each identifier appearing exactly once.

## 3. Cross-profile operator-decision register

The following production decisions remain `OPERATOR_DECISION_REQUIRED`:

### 3.1 Authenticated evidence

- proof format, algorithm, parameters, canonical proof input, and verification-material lifecycle;
- issuer/trust-root governance, enrollment, delegation, revocation, and verifier authorization;
- evidence freshness/lifetimes, revocation freshness/outage, and policy version transitions;
- approval roles, threshold governance, replay domain, audit disclosure, and privacy.

### 3.2 Custody

- algorithm/material allowlist, origin, generation/import permissions, and derivation policy;
- custody technology and isolation, roles, thresholds, ceremonies, and attestation;
- activation, expiry, rotation, revocation, backup/recovery, destruction, and compromise handling;
- custody evidence, verification cadence, audit, implementation, and independent review.

### 3.3 Atomic security state

- storage technology/boundary, consistency/isolation/order, partitioning, and failure model;
- durability/replication, identifiers/versioning/integrity, conflicts/timeouts, and recovery;
- replay/idempotency/retention, spend partitions/windows/pending treatment, approval/operator consumption;
- backup/restore, encryption/access, migration security, monitoring, and implementation review.

### 3.4 Time, audit, and hardening

- trusted-time sources/authentication/selection, monotonic reference, numeric bounds, outage/cache;
- audit authenticity/integrity/checkpoints/storage/retention/recovery/access/redaction/publication;
- all parser, rate, concurrency, queue, timeout, CPU, memory, storage, and descriptor limits;
- errors, monitoring, process/filesystem/network/secret isolation, topology, runbooks, and test criteria.

### 3.5 Bitcoin and activation

- production Bitcoin proof architecture;
- Bitcoin confirmation/reorg policy and count;
- observer quorum and independence;
- separate implementation scope, deployment authorization, operator acceptance, and activation decision.

An operator decision must identify accountable authority, exact policy/version, rationale, threat model, rollback prohibition, evidence requirements, test acceptance criteria, independent review, and approval record. An undocumented default, implementation convenience, caller choice, adapter output, Harness/Evals recommendation, Bitcoin observation, or prior offline fixture cannot satisfy a decision.

## 4. Required evidence progression

No future work may skip a stage:

1. `DESIGN_REVIEWED`: architecture and public contract are internally consistent and subordinate to Protocol v1.0.0.
2. `OPERATOR_DECISIONS_APPROVED`: every applicable production choice is explicit, versioned, threat-modeled, and independently reviewed.
3. `IMPLEMENTATION_SEPARATELY_AUTHORIZED`: a later bounded milestone authorizes only named implementation artifacts and no activation.
4. `IMPLEMENTATION_EVIDENCE_COMPLETE`: code, configuration, static analysis, provenance, build evidence, and control evidence satisfy the approved profile.
5. `TEST_AND_SECURITY_REVIEW_COMPLETE`: deterministic, adversarial, fault, concurrency, crash/recovery, custody, service, and independent reviews pass without waived security failures.
6. `DEPLOYMENT_SEPARATELY_AUTHORIZED`: a later operator decision approves a named deployment boundary after prior gates pass.
7. `ACTIVATION_SEPARATELY_AUTHORIZED`: a final explicit operator authorization is required; deployment or eligibility never implies activation.

Foundation124 reaches only `DESIGN_REVIEWED` for the five new documents. It does not certify that Foundation122 gaps or blocked decisions are resolved.

## 5. Mandatory implementation invariants

Any later implementation evidence must prove all of the following without transferring authority:

- L28 Protocol v1.0.0 remains authoritative;
- `coin.tx_validation.validate_transaction` is invoked exactly as the canonical mandatory validation boundary and its result is bound to the exact transaction;
- authorization is evaluated separately from validation;
- eligibility is evaluated separately from signer invocation;
- missing required evidence, state, policy, time, audit, custody, resources, or security decisions fails closed;
- Harness/Evals and adapters remain advisory only;
- Bitcoin remains external evidence only;
- every issuance, supply, height, history, validation, consensus, and settlement override remains false;
- no interface response itself signs, creates a signature, accesses a wallet/key, submits, broadcasts, connects RPC/network, mutates a ledger, or settles;
- public evidence contains no private key, seed, mnemonic, xprv, wallet material, credential, or secret.

## 6. Protected protocol and economics

The matrix preserves exactly:

- hard cap: `28000000`;
- emission ceiling: `11130000`;
- historically mined: `2824584`;
- treasury locked: `500000`;
- circulating snapshot: `2324584`;
- halving interval: `210000`;
- reward schedule: `[28,14,7,3,1,0]`;
- historical mined-through entry: `100877`;
- next canonical height: `100878`;
- coinbase-only issuance;
- consensus-derived canonical height;
- immutable historical evidence.

No evidence, custody, state, clock, audit, resource policy, adapter, Harness/Evals output, Bitcoin observation, operator decision, or future signer can alter these facts.

## 7. Final gate conclusion

Foundation124 defines future public control profiles and an implementation gate matrix only. `F122-G01` through `F122-G08` remain `GAP_REQUIRES_FUTURE_WORK` pending operator decisions, implementation evidence, tests, and review. `F122-B01` through `F122-B04` remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

Production Bitcoin proof architecture, Bitcoin confirmation/reorg policy and count, and observer quorum/independence are not selected or implied. Signer implementation, runtime, deployment, and activation remain blocked. Foundation124 grants zero signer, wallet, key, signature, RPC, network, broadcast, mining, settlement, database, server, deployment, testnet, or activation authorization.
