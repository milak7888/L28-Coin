# Local Signer Atomic State Semantics v0.1

**Foundation:** 123

**Workstream:** 3 of 4 — F122-G03 and F122-G04

**Status:** ARCHITECTURE DEFINED; DOCUMENTATION ONLY; NON-ACTIVATING

**Document version:** `local-signer-atomic-state-semantics/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Required parent:** `a66f02f224577dca090ac99f4182dade2a2160f1`

**Database, store, or runtime implementation:** none

**Runtime authorization:** none

---

## 1. Purpose and scope

This document addresses Foundation122 findings F122-G03 and F122-G04 at the
architecture level. It defines future atomic semantics for replay/idempotency,
cumulative spending, approval consumption, concurrency ordering, persistence,
retention, rollback, crash recovery, duplicates, and partial failure.

It does not select or implement a database, log, transaction engine, lock,
consensus mechanism, runtime service, signer, wallet, key, signature, RPC or
network path, submission, broadcast, settlement, deployment, or testnet.

This architecture is subordinate to [L28 Protocol v1.0.0](../PROTOCOL.md),
Foundation117, Foundation122,
`authenticated_signer_evidence_architecture_v0.1.md`, and
`local_signer_key_custody_lifecycle_architecture_v0.1.md`. On conflict,
Protocol v1.0.0 prevails.

## 2. Authority and safety invariants

1. The state described here is local authorization-control state only. It is
   not the L28 ledger, consensus state, issued-supply state, canonical height,
   Protocol history, or settlement state.
2. `coin.tx_validation.validate_transaction` remains the canonical mandatory
   validation path. Local atomic state cannot make an invalid transaction valid
   or substitute for unavailable Protocol state.
3. Authorization is not Protocol validation.
4. Signer eligibility is not signer invocation.
5. A committed local eligibility decision is not a signature, submission,
   broadcast, ledger mutation, or settlement.
6. The state boundary cannot mint, modify supply, alter height/history, or
   confer consensus or settlement authority.
7. Missing, unavailable, stale, inconsistent, partially recovered, or
   unverifiable required state fails closed.

## 3. Logical state boundary

A future implementation requires one authoritative local security-state
boundary for each configured administrative domain. The storage technology is
not selected here. The boundary must atomically coordinate:

- replay identities and retention state;
- idempotency bindings and prior public results;
- exact policy identifier, version, and digest;
- per-policy cumulative authorized spending windows;
- approval identities and consumption state;
- operator-authorization consumption where policy requires single use;
- lifecycle and revocation version observations needed by the decision;
- deterministic decision/audit lineage; and
- a durable public-audit publication intent or equivalent recovery marker.

No second store, cache, adapter, or caller-provided state may independently
authorize the same decision. Replicas and caches may serve only under an
approved consistency profile and cannot convert unavailable authoritative
state into fresh state.

## 4. Canonical identities and bindings

Every atomic decision must bind exact canonical values for:

1. interface profile and version;
2. request ID and request digest;
3. intent ID;
4. idempotency key;
5. payer and payee identities;
6. asset and exact integer amount;
7. policy ID, policy version, and policy digest;
8. approval IDs and ordered approver identities;
9. operator evidence ID where required;
10. transaction input digest;
11. validation binding digest and validation report ID;
12. trusted evaluation-time evidence reference;
13. custody/lifecycle public key identifier and state version if a future
    signer edge is ever separately authorized; and
14. final public eligibility decision and report/audit identifiers.

Bindings are exact. No case folding, aliasing, truncation, default value,
cross-policy reuse, or caller-controlled normalization is permitted.

## 5. Replay and idempotency semantics

### 5.1 Replay identity

Replay identity is the tuple of administrative domain, interface profile,
payer, request ID, intent ID, and idempotency key, bound to the request digest
and policy version. A future profile may add stricter bindings but cannot remove
these.

### 5.2 Required outcomes

| Observed state | Required semantic outcome |
|---|---|
| No retained identity and authoritative state available | Continue evaluation; no freshness claim is committed yet |
| Exact identity and request digest already committed | Return the previously committed public result only; do not consume state or invoke a signer again |
| Identifier retained with a different digest, intent, policy, party, asset, or amount | Fail closed as a conflicting binding |
| Single-use request, intent, approval, or operator evidence already consumed | Fail closed as replay/duplicate use |
| State unavailable, stale, contradictory, partially recovered, or outside verified retention | Fail closed; never assume fresh |

The existing F117 stable taxonomy remains authoritative. This architecture does
not invent replacement runtime codes.

### 5.3 Check-and-record rule

Freshness and consumption must be decided by one atomic conditional commit, not
by a check followed by an independent write. A read-only preflight may reject a
known replay early, but a successful decision must recheck all replay and
economic preconditions at commit time.

## 6. Cumulative spending semantics

For each exact payer, asset, policy ID/version, and policy window, the state
boundary must maintain the committed authorized total using exact integer
arithmetic.

The conditional commit must prove:

1. the policy and window are current and exactly bound;
2. the transaction amount does not exceed the per-transaction limit;
3. committed prior authorized total plus the amount does not exceed the
   cumulative limit;
4. the prior-total version read by evaluation still matches at commit;
5. no concurrent commit has consumed the remaining allowance; and
6. the amount is added exactly once only if every required gate succeeds.

Equality with an approved limit may pass as specified by F117/F118. Missing,
inactive, unauthenticated, overflowed, wrong-version, contradictory, or
unavailable policy/spending state fails closed and never means unlimited spend.

The cumulative total is local authorization state. It does not represent an
L28 balance, issued supply, ledger debit, transaction settlement, or historical
coin movement.

## 7. Approval consumption semantics

Each approval is bound to an exact authenticated approver identity, request,
intent, policy version, amount, decision, and validity interval.

Atomic commit must:

- reject duplicate approver identities before counting;
- count only distinct, authenticated, authorized, current approvals;
- enforce the exact threshold without inventing missing approvals;
- verify approvals remain unconsumed and unrevoked at commit;
- consume single-use approvals in the same commit as replay and cumulative
  spending state;
- prevent one approval from authorizing multiple conflicting requests; and
- preserve ordered approval lineage in the public audit record.

A commit that cannot atomically update every required approval fails without
consuming any approval or spending allowance.

## 8. Evaluation and commit sequence

A future runtime must preserve F117 first-failure precedence while preventing
time-of-check/time-of-use races. The logical sequence is:

1. parse and validate the exact request/profile/schema/digests without state
   mutation;
2. reject forbidden secret, authority, invocation, or unresolved-gate claims;
3. obtain authenticated evidence, trusted-time evidence, and a versioned
   read-only snapshot of replay/economic-control state;
4. evaluate identity, replay, time, policy, limits, approvals, operator, and
   local authorization against that snapshot;
5. require exact accepted binding evidence from the canonical
   `coin.tx_validation.validate_transaction` path; unavailable/rejected/pending
   validation blocks and consumes nothing;
6. begin one conditional atomic commit and re-read/recheck replay,
   idempotency, policy version/window, cumulative total, approvals, operator
   evidence, revocation/lifecycle versions, and trusted-time validity;
7. if any version or predicate changed, abort without partial consumption and
   reevaluate from fresh authoritative evidence or fail closed under a bounded
   future retry policy;
8. atomically write replay/idempotency state, cumulative amount, approval and
   operator consumption, decision lineage, and durable audit-publication intent;
   and
9. return only the committed public eligibility result.

Commit success does not authorize or invoke signing. A later signer invocation
would require a separate, explicitly authorized boundary and an exact binding
to the still-current committed result.

## 9. Concurrency ordering

Concurrent requests that touch any shared replay identity, payer/policy/window
allowance, approval, operator evidence, or custody lifecycle state must be
serialized by deterministic conflict semantics or equivalent conditional
versioning.

Requirements:

- at most one conflicting request may commit;
- ordering must not be caller-selected or silently nondeterministic;
- losing/conflicting requests must re-evaluate from authoritative state or fail
  closed;
- retries must be bounded by a future approved policy;
- retry cannot change request identity, digest, amount, policy, or evidence;
- deadlock, timeout, leader loss, partition, stale replica, or version conflict
  cannot default to success; and
- no concurrency mechanism may become L28 consensus or settlement authority.

This document selects no lock, isolation level, consensus algorithm, retry
count, timeout, or storage product.

## 10. Atomic commit and partial failure

The following changes form one all-or-nothing local decision unit:

1. replay/idempotency record;
2. cumulative authorized-spend increment;
3. approval/operator consumption records;
4. decision and state-version lineage; and
5. durable audit publication intent or equivalent recovery record.

If any member cannot commit, none may become authoritative. A partial write,
uncertain acknowledgement, checksum mismatch, storage error, process crash, or
replication ambiguity produces an `UNKNOWN` recovery condition that fails
closed until authoritative recovery proves either fully committed or not
committed.

No component may guess the outcome, rerun signing, decrement counters, delete a
replay record, or return success while commit status is uncertain.

## 11. Persistence and durability expectations

Future storage must provide:

- atomic conditional updates across the entire local decision unit;
- durable monotonic state versions;
- integrity verification and corruption detection;
- authenticated administrative access and least privilege;
- encrypted/confidential storage where evidence sensitivity requires it;
- tamper-evident audit linkage;
- recoverable, verified backups if an approved future profile permits them;
- deterministic startup/recovery checks; and
- explicit fail-closed behavior for unavailable, stale, or degraded state.

An in-memory default, empty store, zero counter, missing directory, or fresh
clone cannot be treated as authoritative production state.

## 12. Retention

Retention must be versioned policy, bound to evidence lifetimes, replay risk,
audit obligations, privacy requirements, and recovery guarantees. The policy
must define when identifiers, approvals, authorization totals, and audit
lineage remain authoritative and how expiration is proven.

Deletion or compaction must not make a previously used identifier appear fresh,
erase required audit lineage, roll back cumulative state, or permit reuse of a
single-use approval. Unavailable retention metadata fails closed. This document
selects no duration, grace period, archive tier, or deletion schedule.

## 13. Rollback and correction

Committed state is append-only or monotonically versioned from the decision
perspective. Administrative rollback of replay, consumption, or cumulative
spend is forbidden.

Corrections require an authenticated, separately authorized compensating
record that preserves the original decision and audit lineage. A compensation
does not rewrite L28 ledger history, reverse settlement, restore a consumed
approval automatically, or authorize another transaction.

Restoring a backup must prove that no committed decisions are lost. If that
cannot be proven, the recovered domain remains fail-closed and ineligible for
signer use.

## 14. Crash recovery

Startup and crash recovery must:

1. verify store identity, security profile, integrity, monotonic version, and
   recovery lineage;
2. resolve every in-progress or uncertain decision from durable evidence;
3. distinguish fully committed, fully aborted, and unknown outcomes;
4. never replay a signer invocation or reconstruct success from partial state;
5. reconcile audit publication intent without duplicating economic or approval
   consumption;
6. block the affected administrative domain while any required state is
   uncertain; and
7. require independent operational review after corruption, rollback, or
   unreconciled loss.

Recovery procedures, tooling, storage format, and service implementation remain
future work.

## 15. Dependencies and remaining gates

This architecture does not resolve:

1. storage technology, transaction/isolation mechanism, replication, or
   deployment topology;
2. exact administrative-domain partitioning and migration;
3. authenticated evidence, revocation, and policy governance;
4. custody lifecycle state implementation;
5. trusted time and retention durations;
6. audit durability, privacy, and recovery implementation;
7. bounded retry, timeout, and operational-degradation policy;
8. runtime implementation, fixtures/tests, fault/concurrency/crash testing,
   operations, and independent security review; or
9. separate operator authorization for any later state/runtime milestone.

Production proof architecture, Bitcoin confirmation/reorg policy and count,
and observer quorum/independence remain
`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`. Bitcoin has no authority over this
local state or L28 consensus.

## 16. Protected Protocol and economic facts

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

Local spending counters must never be interpreted as or substituted for any
protected economic fact.

## 17. Non-activation conclusion

Foundation123 defines atomic state semantics only. This document creates no
database, store, transaction, runtime, signer, wallet, key, signature,
RPC/network connection, submission, broadcast, ledger mutation, settlement,
deployment, testnet, or production service.

Signer implementation and runtime remain blocked until every applicable
Foundation122 gate is satisfied by later authorized work, verified,
independently reviewed, and separately operator-authorized.
