# Local Signer Time, Audit, and Runtime Hardening Architecture v0.1

**Foundation:** 123

**Workstream:** 4 of 4 — F122-G05, F122-G06, F122-G07, and F122-G08

**Status:** ARCHITECTURE DEFINED; DOCUMENTATION ONLY; NON-ACTIVATING

**Document version:** `local-signer-time-audit-runtime-hardening-architecture/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Required parent:** `a66f02f224577dca090ac99f4182dade2a2160f1`

**Runtime, service, or deployment implemented:** none

**Runtime authorization:** none

---

## 1. Purpose and scope

This document addresses Foundation122 findings F122-G05 through F122-G08 at
the architecture level. It defines future requirements for trusted production
time, monotonicity/skew/rollback/outage handling, durable tamper-evident audit
evidence, retention/recovery/access control, bounded parsing, resource and rate
limits, process/key isolation, denial-of-service controls, secure errors,
monitoring, deployment boundaries, runbooks, adversarial/fault/concurrency/
crash-recovery testing, and independent review.

It does not implement or start a clock service, audit store, parser, API,
monitor, signer, wallet, key, signature, RPC/network connection, submission,
broadcast, settlement service, deployment, testnet, or infrastructure.

This architecture is subordinate to [L28 Protocol v1.0.0](../PROTOCOL.md),
Foundation117, Foundation122, and the other three Foundation123 architecture
documents. On conflict, Protocol v1.0.0 prevails.

## 2. Fixed authority model

1. L28 remains the sole issuance, supply, canonical-height, validation,
   consensus, historical-ledger, and native-settlement authority.
2. `coin.tx_validation.validate_transaction` remains the canonical mandatory
   validation path. Time, audit, monitoring, adapters, or infrastructure cannot
   replace or override it.
3. Authorization is not Protocol validation.
4. Signer eligibility is not signer invocation.
5. Time evidence determines local evidence freshness only. It cannot determine
   L28 canonical height or settlement finality.
6. Audit evidence records a local decision projection only. It cannot create a
   signature, transaction, ledger record, Protocol history, or settlement.
7. Operational availability or monitoring health cannot convert missing
   security evidence into authorization.

Missing, malformed, stale, unauthenticated, unavailable, rollback-affected,
contradictory, or unrecoverable required time/audit/runtime evidence fails
closed.

## 3. Trusted production-time architecture

### 3.1 Time-authority boundary

A future production profile must name an approved time authority or authority
set, authentication method, monotonic reference, source-health criteria,
maximum accepted uncertainty/skew, rollback policy, and outage behavior. This
document selects none of those values or providers.

The time boundary must emit an authenticated, versioned time-evidence result
binding:

- source/profile identifier;
- evaluation time and monotonic observation reference;
- source uncertainty/health state;
- last accepted time and rollback status;
- policy version;
- request/evaluation identifier;
- evidence freshness and expiry; and
- public audit reference.

Caller-supplied time, process wall-clock time, file timestamps, network receipt
time, Bitcoin height/time, or adapter timestamps cannot independently become
trusted production time.

### 3.2 Monotonicity and rollback

For one administrative domain, accepted evaluation time must not move backward
relative to durable accepted state. A backward jump, monotonic-source reset,
restored stale snapshot, source disagreement outside approved policy, or
missing last-time state blocks time-dependent eligibility until recovery proves
a safe monotonic state.

Rollback recovery must preserve the original observation and create a new
audited recovery decision; it cannot rewrite prior audit records, extend
expired evidence, revive revoked authority, or reduce replay/spending state.

### 3.3 Skew and uncertainty

The future profile must define exact skew and uncertainty rules for evidence
issuance, not-before, expiry, policy windows, approvals, operator evidence, and
revocation freshness. Limits must be versioned, authenticated configuration,
not caller input or hidden defaults.

Unavailable or excessive uncertainty fails closed. This document defines no
numeric skew allowance, grace period, lifetime, poll interval, or fallback.

### 3.4 Outage and disagreement

If required time sources are unavailable, unauthenticated, stale, unhealthy, or
in unresolved disagreement, new eligibility decisions requiring current time
must block. Cached evidence may be used only under a separately approved future
profile with authenticated freshness and rollback guarantees.

Outage mode cannot assume current time, stop expiry, extend validity, default
to the last value indefinitely, or invoke a signer as recovery.

## 4. Durable audit architecture

### 4.1 Audit scope

The future audit boundary records security decisions and control transitions,
including:

- request and canonical digest references;
- authenticated evidence verification results and issuer/policy versions;
- replay, spending, approval, and operator state versions;
- trusted-time evidence and uncertainty status;
- canonical Protocol validation binding and preserved rejection reason;
- custody lifecycle public identifier/state if applicable;
- eligibility result and stable code;
- non-execution assertions;
- administrative lifecycle, configuration, recovery, and incident actions; and
- publication/recovery status.

Audit records must minimize sensitive data and contain public references or
protected internal references as required. Private keys, seeds, mnemonics,
xprv, credentials, wallet material, recovery secrets, and raw sensitive proof
material are forbidden.

### 4.2 Durability and tamper evidence

Future audit storage must provide append-only or monotonic semantics,
authenticated record identity, canonical serialization, integrity chaining or
equivalent tamper evidence, durable ordering, duplicate detection, state-commit
binding, corruption detection, and independently verifiable checkpoints under
an approved future security profile.

No integrity algorithm, checkpoint signer, external anchor, product, or storage
topology is selected here. An audit-integrity mechanism cannot use the
transaction signer as an implicit authority unless a later security decision
explicitly separates and approves that use.

An eligibility decision requiring durable audit evidence must not be reported
as committed until the atomic-state boundary has durably recorded the audit
publication intent or equivalent recovery marker. Publication failure cannot
roll back or duplicate economic-control state; it enters fail-closed recovery.

### 4.3 Public audit projection

Public output is limited to the F117 audit/eligibility projection and additional
public references defined by a later compatible profile. It must state that it
is public evidence only and that signature and settlement evidence were not
created/supplied.

Public audit evidence is not a signed transaction receipt, signature,
submission record, broadcast proof, L28 ledger entry, Protocol history,
settlement proof, or Bitcoin proof.

## 5. Audit retention, access control, and recovery

### 5.1 Retention

A future retention profile must bind legal/security/privacy obligations,
replay and state retention, incident requirements, archive integrity,
verification, deletion authorization, and recovery guarantees. It must prevent
deletion or compaction from making consumed evidence fresh or erasing required
decision lineage.

This document selects no retention duration, archive medium, deletion schedule,
or privacy jurisdiction.

### 5.2 Access control

Audit write, read, export, verification, administration, retention, and
recovery privileges must be distinct, authenticated, least privilege, and
audited. Custody operators, policy operators, service operators, and auditors
must not acquire one another's authority merely through audit access.

Public queries must expose only approved public projections. Error, debug,
monitoring, and support paths must not bypass redaction or access control.

### 5.3 Recovery

Recovery must verify store identity, profile version, complete ordering,
integrity chain/checkpoints, atomic-state linkage, last durable state, backup
provenance, and absence of rollback. Gaps, forks, missing checkpoints,
corruption, stale restores, or uncertain commit linkage block affected runtime
eligibility.

Recovery cannot fabricate missing records, discard adverse decisions, rewrite
history, or infer settlement. A restored audit store remains inactive until
verification and independent operational review complete.

## 6. Bounded parsing and canonical input controls

A future runtime parser must enforce the exact F117/F119 schemas and canonical
rules before semantic evaluation. A versioned security profile must define
bounded values for:

- total request bytes;
- JSON nesting depth;
- object property and array element counts;
- string and UTF-8 byte lengths;
- numeric ranges;
- evidence/provenance chain length;
- approval count;
- batch/concurrency limits; and
- parsing/evaluation work budgets.

Limits must be authenticated configuration, never caller-selected. Unknown,
missing, duplicate, reordered, out-of-range, over-limit, trailing, malformed,
or unsupported input fails closed without repair, coercion, partial evaluation,
or unsafe error echo.

This architecture selects no numeric size, depth, rate, concurrency, timeout,
or resource limit.

## 7. Rate, resource, and denial-of-service controls

The future service boundary must provide independently enforced limits by
authenticated caller/operator/policy scope and by global resource health.
Controls must cover request admission, expensive evidence verification,
revocation/time lookups, state conflicts/retries, audit publication, queues,
memory, CPU, storage, file descriptors, and worker/process capacity.

Requirements:

1. reject before expensive work when an earlier deterministic gate fails;
2. bound retries, queues, concurrency, and per-request work;
3. isolate one tenant/identity/policy failure from other domains;
4. reserve capacity for fail-closed recovery and audit integrity;
5. avoid caller-visible timing/detail that exposes secret or infrastructure
   state beyond an approved threat model;
6. treat resource exhaustion, dependency timeout, circuit-open state, and
   overload as non-authorizing failures; and
7. never bypass authentication, validation, state, time, or audit controls to
   restore availability.

Exact rate policies, priorities, timeouts, and capacity values remain future
security configuration.

## 8. Process and key isolation

A future deployment must separate at least:

- public transport/parser;
- authenticated evidence verification;
- policy/eligibility evaluation;
- atomic replay/economic-control state;
- trusted-time verification;
- audit write and public audit query;
- custody lifecycle administration;
- isolated signer invocation edge; and
- monitoring/operations.

Each boundary must use authenticated, least-privilege, purpose-bound messages
with exact request/profile/digest bindings. The transport and evaluator must
never receive private key material. The isolated signer edge must not receive
arbitrary commands, policy documents, network destinations, wallet paths, or
unvalidated transaction variants.

No component may combine policy authorization, Protocol validation, custody,
signer invocation, broadcast, ledger mutation, and settlement authority.
Network segmentation or process separation alone does not satisfy authenticated
authorization or authority separation.

This document selects no deployment platform, host, container, enclave,
hardware module, operating system, cloud, or network topology.

## 9. Secure errors and information handling

External errors must use the stable F117 taxonomy and safe public fields. They
must not expose:

- private or recovery material;
- credentials, tokens, proof internals, or raw authenticated artifacts;
- host paths, process details, stack traces, memory contents, environment
  values, configuration, network topology, or infrastructure identity;
- policy internals beyond approved public references;
- custody state beyond approved public status; or
- timing/audit details that enable bypass or enumeration.

Internal diagnostics must be access-controlled, minimized, redacted, integrity
protected, and bound to the public error/audit identifier. Unknown internal
failure is safe, deterministic, and fail closed; it never triggers fallback
signing or alternate validation.

## 10. Monitoring and alerting

Future monitoring must cover:

- authentication, revocation, and issuer failures;
- replay/conflict and spending/approval denials;
- time-source health, skew, rollback, and disagreement;
- state/audit integrity, recovery, and replication health;
- custody lifecycle and isolation-policy violations;
- validation binding rejection/unavailability/override attempts;
- parser limits, rate/resource exhaustion, and denial-of-service indicators;
- signer invocation attempts when unauthorized;
- network, RPC, submission, broadcast, settlement, and consensus mutation
  attempts; and
- configuration/profile changes and administrative actions.

Monitoring is advisory operational evidence. It cannot authorize, validate,
sign, broadcast, settle, or suppress a fail-closed decision. Alert delivery
failure cannot silently convert an ineligible request to eligible.

## 11. Deployment boundary

Any future deployment requires a separately authorized milestone after all
applicable architecture, implementation, conformance, and independent-review
gates pass. The deployment design must define trust zones, authenticated
component identities, ingress/egress policy, secret-free public interfaces,
state and audit durability, custody isolation, update/rollback controls,
configuration provenance, health semantics, disaster recovery, and operator
separation.

Development, test, staging, testnet, and production identities/state must be
separate. Passing offline fixtures cannot authorize deployment. Foundation123
creates no DigitalOcean or other infrastructure and selects no provider.

## 12. Operational runbooks

Before any future activation, independently reviewed runbooks must exist for:

1. startup and authoritative-state verification;
2. normal shutdown without uncertain commits;
3. time-source outage, skew, rollback, and disagreement;
4. revocation/issuer outage and evidence compromise;
5. replay/state conflict, corruption, partial commit, and crash recovery;
6. cumulative-spend and approval reconciliation;
7. audit publication failure, corruption, recovery, and access incident;
8. custody compromise, quarantine, rotation, revocation, recovery, and
   destruction;
9. overload, denial of service, dependency failure, and safe degradation;
10. configuration/profile update and failed rollback;
11. validation binding rejection/unavailability and override attempts;
12. incident evidence preservation and independent escalation; and
13. separately authorized activation and emergency deactivation.

Runbooks cannot authorize operations prohibited by Protocol or use emergency
procedures to bypass validation, state, custody, audit, or operator gates.

## 13. Required security testing and review

A later implementation cannot claim readiness without deterministic and
adversarial evidence covering:

- exact schemas, serialization, digests, stable errors, and precedence;
- malformed, oversized, deeply nested, duplicate, reordered, ambiguous, and
  computationally expensive inputs;
- issuer/provenance/revocation forgery, staleness, rollback, and compromise;
- time skew, rollback, source disagreement, outage, and stale recovery;
- replay/idempotency races, duplicate approvals, concurrent spending, version
  conflicts, partial commits, process crashes, stale replicas, and restore;
- audit loss, corruption, fork, truncation, delayed publication, access abuse,
  and recovery;
- custody lifecycle misuse, role-collusion assumptions, isolation failure,
  rotation/revocation races, and compromise response;
- resource exhaustion, queue saturation, rate-limit evasion, dependency
  timeout, and denial of service;
- proof that `coin.tx_validation.validate_transaction` is the exact mandatory
  live path and is never replaced or bypassed;
- proof that eligibility never invokes signing and that signer failure cannot
  alter validation or authorization;
- proof that no component can mint, alter economics/height/history/consensus,
  submit, broadcast, or declare settlement; and
- fault, concurrency, crash-recovery, end-to-end, operational, and independent
  penetration/security review.

Test fixtures must remain disposable and offline unless a later milestone
explicitly authorizes a bounded environment. Passing tests never activates a
runtime.

## 14. Dependencies and remaining gates

This architecture leaves unresolved:

1. trusted time source/profile and all numeric skew/outage parameters;
2. audit integrity/authenticity mechanism, storage, retention, privacy, access,
   and recovery implementation;
3. parser/rate/resource/concurrency limits and production capacity policy;
4. process/key isolation technology and deployment topology;
5. authenticated evidence and custody implementations;
6. atomic state implementation and recovery mechanism;
7. runtime/service implementation, conformance suites, operations, deployment,
   and independent security review;
8. separate operator authorization for implementation, deployment, and
   activation; and
9. evidence that all Foundation122 gates are satisfied together.

Production proof architecture, Bitcoin confirmation/reorg policy and count,
and observer quorum/independence remain
`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`. No Bitcoin observation, time,
height, proof, or monitor may become L28 authority.

## 15. Protected Protocol and economic facts

| Invariant | Exact value |
|---|---:|
| Hard cap | `28000000` L28 |
| Emission ceiling | `11130000` L28 |
| Historically mined | `2824584` L28 |
| Treasury locked | `500000` L28 |
| Circulating snapshot | `2324584` L28 |
| Halving interval | `210000` |
| Reward schedule | `[28,14,7,3,1,0]` |
| Historical mined-through entry | `100877` |
| Next canonical height | `100878` |
| Issuance | coinbase only |
| Canonical height | consensus derived |
| Historical evidence | immutable |

Time, audit, runtime, monitoring, deployment, and Bitcoin evidence have zero
authority to change these facts.

## 16. Non-activation conclusion

Foundation123 defines architecture only. This document creates or starts no
time service, audit store, parser, API, monitor, signer, wallet, key, signature,
RPC/network connection, submission, broadcast, miner, ledger mutation,
settlement, deployment, testnet, DigitalOcean resource, or production service.

Signer implementation, runtime integration, deployment, and activation remain
blocked until every applicable Foundation122 gate is satisfied by later
authorized work, verified, independently reviewed, and separately
operator-authorized.
