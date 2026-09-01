# Local Signer Time, Audit, and Resource Conformance Plan v0.1

Status: `DEFINED_PLAN_ONLY`

Foundation: 125, workstream 5

Source policy: `l28-local-signer-time-audit-resource/v0.1`

Addresses: F122-G05 through F122-G08 and decisions `LSOD-OPS-001` through `LSOD-OPS-009`

## 1. Scope

This document plans deterministic future conformance for trusted time, audit durability/tamper evidence, bounded parsing, rate/resource controls, secure errors, dependency failure, process isolation, monitoring, runbooks, faults, and recovery. It implements or starts no clock, audit store, parser service, rate limiter, monitor, server, signer, wallet, key, HSM/KMS, network, RPC, broadcast, database, settlement, deployment, or testnet.

The plan is subordinate to L28 Protocol v1.0.0. `coin.tx_validation.validate_transaction` remains canonical and mandatory. Authorization is not validation. Eligibility is not signer invocation. Time, audit, monitoring, and infrastructure evidence cannot alter issuance, supply, height, history, validation, consensus, or settlement.

All mechanisms, sources, providers, topologies, and numeric values in `LSOD-OPS-001` through `009` remain `OPERATOR_DECISION_REQUIRED`. Test symbols such as `MAX_REQUEST_BYTES`, `MAX_SKEW`, `RATE_LIMIT`, or `TIMEOUT` are parameters resolved only by later approved decision profiles. This plan selects no number, count, duration, quorum, provider, or platform.

## 2. Deterministic test model

Future cases use fixed public/disposable inputs, integer synthetic time observations, explicit audit record sequences, exact parser payloads, abstract resource counters, deterministic dependency states, and declared isolation capabilities. They do not read a system/network clock, environment, secret, filesystem configuration, live process state, network, RPC, or service.

Immutable family IDs are:

- `TAR-POS-NN`: coherent approved time/audit/resource-policy result;
- `TAR-NEG-NN`: one invalid, excessive, tampered, leaking, or unauthorized condition;
- `TAR-BND-NN`: immediately below, exactly at, and immediately above an approved parameter;
- `TAR-FCL-NN`: unavailable, contradictory, corrupt, undecided, or unrecoverable dependency/control.

Expected outcomes:

- POS: policy-conformant control evidence only; no invocation or activation.
- NEG: deterministic rejection at the earliest applicable Foundation117/policy gate.
- BND: exact approved parameter semantics; over-limit always rejects.
- FCL: unavailable/security-decision-required/internal-failure outcome with no bypass or degraded authorization.

These categories are test-plan labels, not replacement public status codes.

## 3. Planned family inventory

### 3.1 Positive families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `TAR-POS-01` | Exact policy profile/version/schema/order | Policy-conformant | No unknown/default/caller-selected policy value |
| `TAR-POS-02` | Authenticated approved time sources agree within parameterized bounds | Time evidence conformant | Source/profile/measurement/uncertainty/request binding exact |
| `TAR-POS-03` | Monotonic time advances with current durable prior state | Time evidence conformant | Accepted time never moves backward |
| `TAR-POS-04` | Approved bounded outage/cache case | Time evidence follows approved policy | Cache is authenticated, fresh, and never indefinite |
| `TAR-POS-05` | Canonical authenticated audit event appended to exact prior lineage | Audit evidence conformant | Origin, payload, prior record, time, decision/state bindings exact |
| `TAR-POS-06` | Durable checkpoint and verified recovery | Audit evidence conformant | Complete order and pre-failure lineage preserved |
| `TAR-POS-07` | Request immediately below every approved parser bound | Parsing conformant | Canonical input preserved without normalization |
| `TAR-POS-08` | Request below approved rate/resource limits | Admission conformant | Authenticated identity dimensions and resource state exact |
| `TAR-POS-09` | Secure error mapped to existing Foundation117 status/code | Error conformant | Minimal deterministic public detail and bound correlation ID |
| `TAR-POS-10` | Allowlisted public-safe metrics/logs and authenticated health evidence | Monitoring conformant | Monitoring remains advisory and secret-free |
| `TAR-POS-11` | Declared least-privilege process capability set | Isolation conformant | Public/evidence/state/audit/custody boundaries remain distinct |
| `TAR-POS-12` | Deterministic runbook exercise for safe startup/shutdown/recovery | Exercise conformant | Authoritative state verified and no activation implied |

### 3.2 Negative families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `TAR-NEG-01` | Unknown/malformed policy/version/property/order/value | Reject policy/schema | No implicit default or ignored field |
| `TAR-NEG-02` | Caller/system/file/Bitcoin/adapter time used as sole authority | Reject time evidence | Unapproved time cannot become trusted time |
| `TAR-NEG-03` | Forged source identity/proof, excessive uncertainty/skew, or policy mismatch | Reject time evidence | No fallback source |
| `TAR-NEG-04` | Time rollback, monotonic reset, stale snapshot, or unapproved forward jump | Reject and enter recovery | Prior accepted state cannot be rewritten |
| `TAR-NEG-05` | Audit record mutation, insertion, deletion, duplication, reorder, truncation, or rollback | Reject audit integrity | Lineage/checkpoint failure is detectable |
| `TAR-NEG-06` | Audit event lacks required state/validator/time binding or durability acknowledgement | Reject/withhold eligibility | Audit intent/evidence cannot be partial |
| `TAR-NEG-07` | Audit projection/log exposes secret, credential, private evidence, topology, or unnecessary personal data | Reject disclosure | Public output remains allowlisted/minimal |
| `TAR-NEG-08` | Duplicate/unknown JSON property, invalid UTF-8, float/noncanonical integer, trailing data | Reject parser gate | No coercion, repair, or partial evaluation |
| `TAR-NEG-09` | Any request/response/depth/property/array/string/integer/evidence/provenance/approval/work bound exceeded | Reject over-limit input | Rejection precedes expensive semantic work where safe |
| `TAR-NEG-10` | Rate identity derived solely from caller-controlled network metadata | Reject rate identity | Authenticated dimensions required |
| `TAR-NEG-11` | Sustained/burst/concurrency/queue/CPU/memory/storage/descriptor/timeout limit exceeded | Reject/overload fail closed | No control bypass to restore availability |
| `TAR-NEG-12` | Error exposes stack trace, host/configuration, proof internals, timing oracle, or retry bypass | Reject error projection | Internal detail stays protected |
| `TAR-NEG-13` | Required monitoring metric/log missing or non-allowlisted secret telemetry | Reject health evidence | Monitoring outage cannot authorize |
| `TAR-NEG-14` | Public process gains custody/state/admin/network/filesystem/secret capability outside profile | Reject isolation | Unexpected privilege fails closed |
| `TAR-NEG-15` | Dependency timeout/circuit-open/audit backpressure causes authentication/validation/state/time/audit bypass | Reject request | Degraded mode never weakens gates |
| `TAR-NEG-16` | Runbook attempts rollback, emergency signing, alternate validation, or unaudited recovery | Reject procedure | Emergency operation remains subordinate to Protocol/security gates |
| `TAR-NEG-17` | Harness/Evals, adapter, monitor, or Bitcoin evidence claims authorization/validation/settlement authority | Reject authority assertion | External/advisory systems have zero L28 authority |
| `TAR-NEG-18` | Control evidence claims signer invocation/runtime activation | Reject non-execution assertion | Passing control checks activates nothing |

### 3.3 Boundary families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `TAR-BND-01` | Each time-source skew bound: below/exact/above | Approved exact semantics; above rejects | `MAX_SKEW` remains operator parameter |
| `TAR-BND-02` | Each uncertainty bound: below/exact/above | Approved exact semantics; above rejects | No hidden tolerance |
| `TAR-BND-03` | Not-before and expiry integer instants | `now == not_before` passes; `now == expires_at` rejects | Exact F124 time rules |
| `TAR-BND-04` | Forward-jump/rollback/outage/cache duration bounds | Exact approved semantics; unsafe side rejects | No implicit grace or indefinite cache |
| `TAR-BND-05` | Audit checkpoint/retention/recovery objectives at boundary | Exact approved semantics | No duration selected by test |
| `TAR-BND-06` | Request and response byte limits: below/exact/above | At/below may pass; above rejects | Exact byte counting/canonical encoding |
| `TAR-BND-07` | JSON depth/property/array/string/integer limits | At/below may pass; above rejects | Every dimension independently enforced |
| `TAR-BND-08` | Evidence/provenance/approval/work-budget limits | At/below may pass; above rejects | No set normalization or partial evaluation |
| `TAR-BND-09` | Rate window and sustained/burst limit | Exact approved semantics; above rejects | Authenticated identity and window exact |
| `TAR-BND-10` | Concurrency/queue limit | At limit follows policy; one beyond rejects | No race-created extra admission |
| `TAR-BND-11` | Timeout and dependency circuit threshold | Exact approved classification | Timeout/circuit activation never implies success |
| `TAR-BND-12` | CPU/memory/storage/descriptor budget | At limit follows policy; over rejects | No negative/wraparound/unbounded budget |
| `TAR-BND-13` | Monitoring lag/health-evidence freshness boundary | Exact approved semantics | Stale required health blocks |
| `TAR-BND-14` | Capability allowlist last permitted versus first forbidden capability | Allowed set only; forbidden rejects | Least privilege exact |

### 3.4 Fail-closed families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `TAR-FCL-01` | Trusted-time decision/source/profile unavailable or unresolved | Security-decision-required/unavailable | No system/caller/Bitcoin time fallback |
| `TAR-FCL-02` | Required sources disagree without approved resolution | Unavailable rejection | No source chosen ad hoc |
| `TAR-FCL-03` | Durable monotonic prior-time state unavailable/corrupt | Recovery-required rejection | No rollback assumption |
| `TAR-FCL-04` | Audit authenticity/integrity/checkpoint/durability decision unresolved | Security-decision-required | No unsigned/best-effort audit accepted |
| `TAR-FCL-05` | Audit store/checkpoint/recovery state unavailable, corrupt, forked, or stale | Unavailable/corrupt rejection | No eligibility before unique lineage proven |
| `TAR-FCL-06` | Any parser numeric bound unresolved/missing | Security-decision-required | No unlimited parser default |
| `TAR-FCL-07` | Rate/resource state or required dependency unavailable | Unavailable/overload rejection | No fail-open admission |
| `TAR-FCL-08` | Secure-error mapping encounters unknown internal failure | Existing internal-failure response | No detail leak or alternate action |
| `TAR-FCL-09` | Monitoring/health evidence required by policy unavailable | Ineligible/unavailable | Monitoring cannot be assumed healthy |
| `TAR-FCL-10` | Isolation/attestation/capability state unavailable or contradictory | Ineligible/unavailable | No co-located/unrestricted fallback |
| `TAR-FCL-11` | Runbook/recovery authorization/independent review missing | Recovery remains blocked | Operations cannot self-authorize |
| `TAR-FCL-12` | Implementation assurance/activation decision unresolved | Security-decision-required | Offline conformance authorizes nothing |

## 4. Parameterized numeric test rules

Every numeric dimension is represented symbolically until its decision record is approved. A future materialization must bind the decision ID and decision-record version to the test vector and generate at least `value - 1`, `value`, and `value + 1` cases where the domain permits. It must additionally test zero, negative, non-integer, overflow, missing, duplicate, and caller-supplied forms where structurally relevant.

No symbolic value may be replaced by an undocumented fixture constant. A test runner must fail closed or skip materialization as blocked if the approved decision record is absent; it must never infer a production value.

## 5. Fault, isolation, monitoring, and runbook review

Fault schedules must explicitly enumerate dependency failure before evaluation, during evidence verification, before/after state commit, during audit publication, during monitoring loss, at process crash, and during recovery. Isolation probes must be capability/AST-aware and use test-local declarations—not real filesystem, secret, process, service, or network access.

Runbook cases review declarative steps and expected evidence only. They do not execute commands, start/restart services, deploy infrastructure, access secrets, restore databases, rotate keys, or activate a signer.

## 6. Acceptance and traceability

Future materialization must trace every `LSOD-OPS-*` decision to applicable POS/NEG/BND/FCL families, test every approved numeric value at boundaries, prove audit mutation classes are detected, prove no secure-error leakage, prove resource/dependency failures never bypass security gates, and preserve exact non-execution and authority assertions.

Passing future tests cannot establish production readiness without production-representative evidence and independent review. It does not activate a time source, audit service, runtime, signer, deployment, or settlement path.

## 7. Protocol and economic invariants

Preserved exactly: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.

Bitcoin remains external evidence only. Production Bitcoin proof architecture, Bitcoin confirmation/reorg policy and count, observer quorum/independence, and signer implementation/runtime/deployment/activation remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

Foundation125 authorizes no implementation, service, deployment, or activation.
