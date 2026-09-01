# Local Signer Atomic State Conformance Plan v0.1

Status: `DEFINED_PLAN_ONLY`

Foundation: 125, workstream 4

Source contract: `l28-local-signer-atomic-state-storage/v0.1`

Addresses: F122-G03, F122-G04, and decisions `LSOD-STA-001` through `LSOD-STA-012`

## 1. Scope

This document plans deterministic future tests for local replay/idempotency, cumulative spending, approval/operator consumption, concurrency, atomic commit, rollback prohibition, partial failure, crash recovery, corruption, unavailability, retention, versioning, and integrity. It implements no database, migration, transaction engine, store, service, runtime, signer, wallet, key, signature, RPC/network path, broadcast, settlement, or deployment.

The planned state is local authorization-control state only. It is not the L28 ledger, consensus state, issued supply, canonical height, history, or settlement state. `coin.tx_validation.validate_transaction` remains canonical and mandatory and is represented only through exact binding evidence. Authorization is not validation. A committed eligibility result is not signer invocation.

Every production mechanism/value in `LSOD-STA-001` through `012` remains `OPERATOR_DECISION_REQUIRED`. Deterministic plans parameterize isolation, retry, timeout, limits, retention, durability, and recovery rather than selecting them.

## 2. Deterministic model and observables

Future test models use an in-memory test-local abstract state machine only if a later fixture/test milestone separately authorizes it. They must not import or invoke production storage or runtime code. Inputs are fixed public/disposable records, monotonic integer versions, deterministic schedules, explicit fault points, and fixed trusted-time evidence.

Observable output is limited to:

- authoritative snapshot/result classification;
- state version before and after;
- exact records that would be committed or remain unchanged;
- deterministic public decision/audit references;
- applicable existing Foundation117 status/code;
- authority and non-execution assertions.

No planned case writes persistent state, reads a real clock/environment, or performs signing, wallet, network, RPC, submission, broadcast, ledger mutation, or settlement.

Immutable family IDs are:

- `AST-POS-NN`: coherent atomic-state outcome;
- `AST-NEG-NN`: invalid binding, arithmetic, consumption, transition, or recovery claim;
- `AST-BND-NN`: exact version, amount, window, retry, timeout, retention, or crash boundary;
- `AST-FCL-NN`: unavailable, corrupt, ambiguous, partially committed, undecided, or unrecoverable state.

Expected outcomes:

- POS: exact fully committed result or exact idempotent prior result, with all-or-none state effects.
- NEG: deterministic rejection and zero authoritative partial mutation.
- BND: exact parameterized boundary result and invariant-preserving state.
- FCL: no eligibility result unless a unique durable outcome is proven; no fallback or guessed success.

## 3. Planned family inventory

### 3.1 Positive families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `AST-POS-01` | Exact contract/profile/schema/order and coherent decision binding | Conformant snapshot | All identities, policy, transaction, evidence, validation and time bindings exact |
| `AST-POS-02` | Fresh replay/idempotency identity with available authoritative state | Continue evaluation without mutation | Freshness not committed before atomic decision |
| `AST-POS-03` | Exact committed duplicate | Return identical prior public result | No re-consumption, spend, approval/operator update, or invocation |
| `AST-POS-04` | Exact previously rejected duplicate | Return exact prior rejection under approved policy | No new mutation or authority |
| `AST-POS-05` | Proposed spend below cumulative limit | Conditional commit may proceed | Integer arithmetic and exact partition/window binding |
| `AST-POS-06` | Proposed spend exactly equal to approved remaining allowance | Commit per approved inclusive rule | Amount consumed exactly once |
| `AST-POS-07` | Distinct authenticated approvals exactly satisfy threshold | Conditional commit may proceed | Threshold and consumption use same snapshot |
| `AST-POS-08` | Valid operator authorization available and single-use | Conditional commit may proceed | Exact scope and policy binding |
| `AST-POS-09` | Nonconflicting concurrent schedules | Equivalent deterministic final state | Authoritative order is monotonic committed version |
| `AST-POS-10` | Full atomic commit | All records share one committed version | Replay, spend, approvals, operator, decision, audit intent all or none |
| `AST-POS-11` | Crash before commit with proven non-commit | Fresh full reevaluation permitted if evidence remains valid | No state consumed by failed attempt |
| `AST-POS-12` | Crash after durable commit with proven commit | Exact committed result returned | No duplicate commit or signer invocation |
| `AST-POS-13` | Verified backup/recovery to unique latest durable version | Domain may leave recovery after review | No lost committed decision or rollback |
| `AST-POS-14` | Integrity-preserving retention expiry/tombstone | Historical binding remains non-replayable | Expiry never makes consumed identity fresh |

### 3.2 Negative families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `AST-NEG-01` | Unknown contract/version/record/field or wrong property order | Reject before state semantics | No schema inference or ignored field |
| `AST-NEG-02` | Duplicate/reordered approval or evidence arrays, reassociated binding | Reject canonical binding | Arrays remain exact ordered correspondence |
| `AST-NEG-03` | Idempotency key reused with different request/intent/policy/party/amount/digest | Binding-conflict rejection | Identifier cannot transfer authority |
| `AST-NEG-04` | Consumed replay/evidence/approval/operator item reused | Replay/consumption rejection | Prior validation or authorization does not permit reuse |
| `AST-NEG-05` | Missing/negative/floating/overflowed/underflowed spend value | Economic-control rejection | Non-negative exact integers only |
| `AST-NEG-06` | Proposed spend exceeds per-request or cumulative limit | Limit rejection | No spend state consumed on rejection |
| `AST-NEG-07` | Wrong payer/asset/policy/window/operator partition | Binding rejection | Counters cannot cross partitions |
| `AST-NEG-08` | Duplicate approver identity, invalid role, insufficient threshold, wrong scope | Approval rejection | Duplicate identity adds no authority |
| `AST-NEG-09` | Operator authorization wrong scope/version/identity or expired/revoked | Operator-gate rejection | Operator evidence is authorization only |
| `AST-NEG-10` | Stale snapshot/version at conditional commit | Conflict/abort | No partial mutation; full affected re-evaluation required |
| `AST-NEG-11` | Canonical validation binding missing, mismatched, stale, rejected, or pending | Validation rejection | Storage never invokes/substitutes validator; consumes nothing |
| `AST-NEG-12` | Authorization accepted but validation rejected, or inverse | Ineligible | Authorization and validation remain independent |
| `AST-NEG-13` | Commit omits one required record or assigns mixed versions | Reject/uncertain recovery | No partial unit can become authoritative |
| `AST-NEG-14` | Administrative rollback/decrement/delete of replay/spend/consumption | Reject mutation | Corrections require append-only authorized compensation |
| `AST-NEG-15` | Recovery attempts to infer success or replay invocation | Reject recovery | Recovery discovers state; it does not recreate success |
| `AST-NEG-16` | Version downgrade, broken lineage, missing predecessor, digest mismatch | Integrity rejection | Historical binding remains immutable |
| `AST-NEG-17` | Empty/fresh store or zero counter treated as authoritative production state | Reject initialization | Missing bootstrap/state fails closed |
| `AST-NEG-18` | State result claims ledger mutation, settlement, or L28 authority | Reject authority assertion | Local state has no Protocol authority |

### 3.3 Boundary families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `AST-BND-01` | Exact supported contract version versus adjacent version | Exact passes; adjacent rejects | No version negotiation |
| `AST-BND-02` | Committed spend immediately below, exactly at, and one unit above limit | Below/exact follow approved inclusive rule; above rejects | Limit value from `LSOD-STA-007`, not fixture default |
| `AST-BND-03` | Integer arithmetic maximum safe value and one beyond | Maximum follows approved representation; overflow rejects | No wraparound or float conversion |
| `AST-BND-04` | Spending window immediately before/at start and before/at end | Exact approved interval semantics | One authoritative window only |
| `AST-BND-05` | Approval count below/exact/above threshold | Below rejects; exact/above follow approved policy | Distinct identities only |
| `AST-BND-06` | Version conflict on last unchanged versus first changed version | Unchanged may commit; changed aborts | Conditional version check exact |
| `AST-BND-07` | Approved retry maximum and one beyond | Maximum follows approved policy; beyond fails closed | No unbounded retry |
| `AST-BND-08` | Timeout immediately before/at/after approved value | Exact policy classification | Timeout never implies success |
| `AST-BND-09` | Crash at every atomic-commit cut point | Only fully committed or fully absent is authoritative | Partial observation becomes uncertain |
| `AST-BND-10` | Replay/retention at just-before/at/after expiry | Exact approved semantics with non-replay tombstone | Expiry never reopens consumed authority |
| `AST-BND-11` | Last durable version before/after backup checkpoint | Recovery selects unique proven latest state only | No point-in-time rollback of committed records |
| `AST-BND-12` | Policy-version transition concurrent with state commit | Old or new exact version, never mixed | Atomic policy/state binding |

### 3.4 Fail-closed families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `AST-FCL-01` | Storage/trust-boundary decision unresolved | Security-decision-required | No in-memory/default store authority |
| `AST-FCL-02` | Consistency/order policy unresolved | Security-decision-required | No best-effort atomicity |
| `AST-FCL-03` | Authoritative state unavailable/degraded/recovering | Unavailable rejection | Only approved AVAILABLE state can support eligibility |
| `AST-FCL-04` | Split brain, partition, leader uncertainty, or excessive replica lag | Unavailable/uncertain rejection | No quorum or fallback invented |
| `AST-FCL-05` | Commit acknowledgement lost or outcome ambiguous | Uncertain; block domain/request | No guessed commit/non-commit |
| `AST-FCL-06` | Partial write or mixed record versions observed | Corrupt/uncertain; block | No partial state repaired in place |
| `AST-FCL-07` | Integrity/checkpoint/lineage verification fails | Corrupt; block | No state trusted without integrity evidence |
| `AST-FCL-08` | Retention metadata missing or stale restore detected | Unavailable/corrupt; block | No consumed identity becomes fresh |
| `AST-FCL-09` | Trusted time, policy, revocation, custody, or evidence version unavailable at commit | Abort/fail closed | Snapshot success cannot bypass recheck |
| `AST-FCL-10` | Audit publication intent cannot be durably included | No committed eligibility result | Required atomic unit remains complete |
| `AST-FCL-11` | Recovery cannot prove unique durable outcome | Remain blocked for independent reconciliation | No automatic retry/invocation |
| `AST-FCL-12` | Implementation/deployment/activation decision unresolved | Security-decision-required | Passing abstract tests authorizes nothing |

## 4. Deterministic schedules and fault injection

Concurrency cases must enumerate explicit schedules rather than rely on wall-clock/thread nondeterminism. For two or more contenders, cases fix read versions, conflict keys, commit order, fault point, and expected final records. Coherent whole-bundle reorder may be tested separately, but bindings and ordered arrays may never be set-normalized.

Fault cases place one deterministic event before snapshot, after snapshot, before conditional commit, between logical writes, before durability acknowledgement, after durability acknowledgement, during audit-intent publication, at crash, and during recovery. An abstract model must expose partial internal observations only to prove they never become authoritative public results.

## 5. Acceptance and traceability

Future materialization must trace every `LSOD-STA-*` decision to applicable POS/NEG/BND/FCL cases, independently verify exact final state for every schedule, show zero mutation on rejected/aborted cases, prove all-or-none commit and rollback prohibition, and preserve existing Foundation117 status/code precedence.

Passing future tests proves only the approved model/implementation semantics in the bounded environment. It does not create authoritative L28 state, invoke a signer, sign, submit, broadcast, settle, or activate a service.

## 6. Protocol and economic invariants

Preserved exactly: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.

Bitcoin remains external evidence only. Production Bitcoin proof architecture, Bitcoin confirmation/reorg policy and count, observer quorum/independence, and signer implementation/runtime/deployment/activation remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

Foundation125 authorizes no database, runtime, implementation, deployment, or activation.
