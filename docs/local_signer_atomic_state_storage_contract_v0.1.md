# Local Signer Atomic State Storage Contract v0.1

Status: `DEFINED_DESIGN_ONLY`

Foundation: 124, workstream 3

Addresses: Foundation122 `F122-G03` and `F122-G04`

Subordinate authority: L28 Protocol v1.0.0

## 1. Scope and authority

This contract defines future logical storage semantics for replay/idempotency, cumulative spending limits, approval consumption, operator-authorization consumption, and eligibility-decision evidence. It defines no database, schema migration, driver, storage service, transaction coordinator, runtime, or executable API.

The state described here is local security-control state only. It is not the L28 ledger, canonical height, consensus state, historical evidence, or settlement state. It cannot validate or mutate an L28 transaction. `coin.tx_validation.validate_transaction` remains the canonical and mandatory validator.

Immutable separations are:

- authorization is not Protocol validation;
- signer eligibility is not signer invocation;
- a committed eligibility result is not a signature, broadcast, submission, or settlement;
- storage success conveys no authority over issuance, supply, height, history, validation, consensus, or settlement;
- unavailable, corrupt, inconsistent, stale, ambiguous, unversioned, or partially committed required state fails closed.

The public contract identifier is `l28-local-signer-atomic-state-storage/v0.1`. Compatibility requires exact contract and major-version equality.

## 2. Logical state boundary

One future atomic security-state boundary must own the mutually dependent records for a request decision. Its logical record types are:

1. `idempotency_record`
2. `replay_record`
3. `spend_counter_record`
4. `approval_consumption_record`
5. `operator_authorization_consumption_record`
6. `decision_record`
7. `audit_publication_intent`
8. `recovery_record`

No record may be caller authoritative. Every record is keyed and partitioned by an operator-approved security domain, policy version, and canonical identity bindings. Records use monotonic versions and integrity evidence. Unknown record types, fields, versions, or integrity states fail closed.

## 3. Canonical decision binding

The exact property order for the immutable decision binding is:

1. `contract_profile`
2. `contract_version`
3. `security_domain_id`
4. `request_id`
5. `intent_id`
6. `idempotency_key`
7. `replay_nonce`
8. `caller_id`
9. `operator_id`
10. `payer_id`
11. `payee_id`
12. `asset`
13. `amount`
14. `policy_id`
15. `policy_version`
16. `policy_digest`
17. `spending_scope_id`
18. `approval_threshold_set_id`
19. `approval_ids`
20. `operator_authorization_id`
21. `transaction_digest`
22. `validation_binding_id`
23. `validation_result_digest`
24. `trusted_time_evidence_id`
25. `custody_evidence_id`
26. `authenticated_evidence_ids`
27. `decision_input_digest`

Arrays preserve exact order. Duplicate identities are invalid. A whole binding must match an existing idempotency record exactly; partial equality, reordered arrays, set normalization, repaired values, or caller-requested reassociation is forbidden.

The validation binding must identify a result from `coin.tx_validation.validate_transaction`, the exact transaction digest, validator identity/version, validation result, and result digest. A missing, failed, mismatched, stale, or unverifiable validation binding blocks the conditional commit. The storage layer never invokes or substitutes for the validator.

## 4. Logical interface contracts

These interfaces are semantic design boundaries, not callable code.

### 4.1 `read_security_snapshot`

Input property order:

1. `decision_binding`
2. `read_consistency_profile`
3. `minimum_state_version`

Output property order:

1. `storage_state`
2. `snapshot_id`
3. `snapshot_version`
4. `idempotency_outcome`
5. `replay_outcome`
6. `spend_snapshot`
7. `approval_snapshot`
8. `operator_authorization_snapshot`
9. `prior_decision_ref`
10. `integrity_state`
11. `read_at`

The snapshot must be coherent at one atomic read boundary. Combining records from different snapshots, versions, partitions, or policy epochs is forbidden.

### 4.2 `commit_eligibility_decision`

Input property order:

1. `decision_binding`
2. `snapshot_id`
3. `expected_snapshot_version`
4. `authorization_result`
5. `validation_result`
6. `eligibility_result`
7. `spend_delta`
8. `approval_consumptions`
9. `operator_authorization_consumption`
10. `audit_publication_intent`
11. `commit_id`

Output property order:

1. `commit_state`
2. `commit_id`
3. `committed_state_version`
4. `decision_record_id`
5. `spend_record_id`
6. `approval_consumption_record_ids`
7. `operator_consumption_record_id`
8. `audit_publication_intent_id`
9. `prior_result_ref`
10. `integrity_evidence_ref`

The commit is conditional on exact snapshot version and full re-evaluation of all inputs affected by concurrency. It must atomically record the idempotency binding, replay consumption, spend delta, approval consumption, operator-authorization consumption, decision result, and audit-publication intent. Either all become durable at one committed version or none do.

### 4.3 `read_committed_result`

Input property order:

1. `security_domain_id`
2. `idempotency_key`
3. `decision_input_digest`

Output property order:

1. `result_state`
2. `decision_record_id`
3. `public_response_ref`
4. `committed_state_version`
5. `integrity_evidence_ref`

This read may return only a fully committed, integrity-verified public result for the exact decision binding. It never resumes or invokes signing.

### 4.4 `recover_uncertain_decision`

Input property order:

1. `security_domain_id`
2. `commit_id`
3. `decision_input_digest`
4. `recovery_authorization_evidence_id`

Output property order:

1. `recovery_state`
2. `authoritative_commit_state`
3. `decision_record_id`
4. `recovery_record_id`
5. `integrity_evidence_ref`

Recovery determines existing authoritative state; it does not replay a commit by assumption. If a unique durable outcome cannot be proven, the decision remains blocked for independent reconciliation.

## 5. Replay and idempotency semantics

The allowed idempotency outcomes are:

- `fresh`: no binding exists and eligibility evaluation may continue;
- `exact_committed_duplicate`: the full binding matches a committed record; return the same public result without re-consuming state or invoking a signer;
- `exact_rejected_duplicate`: return the same committed rejection without re-evaluation unless an operator-approved retention/re-evaluation policy explicitly requires a new request identity;
- `binding_conflict`: the key exists with any different bound value; fail closed;
- `already_consumed`: replay or single-use evidence was consumed by another binding; fail closed;
- `uncertain`: state may be partially observed or recovery is incomplete; fail closed;
- `unavailable`: required state cannot be read; fail closed.

The idempotency key, replay nonce, evidence identifiers, request and intent, transaction digest, policy version, parties, amount, and security domain are inseparable. A duplicate cannot change response content, state consumption, or authority scope.

Replay check-and-record is atomic with every economic-control update. A read-then-write gap is nonconforming. Replay state cannot be bypassed because a request was previously validated, authorized, rejected, timed out, or retried.

## 6. Cumulative spending semantics

`spend_snapshot` property order is:

1. `spending_scope_id`
2. `counter_partition_id`
3. `policy_version`
4. `window_id`
5. `window_start`
6. `window_end`
7. `limit_amount`
8. `committed_amount`
9. `pending_amount`
10. `proposed_amount`
11. `post_commit_amount`
12. `counter_version`

Amounts are non-negative integers in the canonical L28 unit defined by the active policy. No floating-point arithmetic is permitted. The invariant is:

`committed_amount + pending_amount + proposed_amount = post_commit_amount`

The conditional commit is eligible only when the complete active policy permits `post_commit_amount`. Limits bind payer, asset, policy version, time window, operator scope, and any other active partition dimension. Missing counters, overflow, underflow, negative values, window ambiguity, policy mismatch, stale versions, or unknown pending reservations fail closed.

Rejected decisions consume no spend. Committed eligible decisions consume exactly once. Rollback cannot decrement committed spend; correction requires a separately authorized compensating security-state event that preserves history and never mutates the L28 ledger.

## 7. Approval and operator-authorization consumption

`approval_snapshot` entries have exact property order:

1. `approval_id`
2. `approver_id`
3. `approver_role`
4. `threshold_set_id`
5. `scope_digest`
6. `consumption_state`
7. `consumption_version`

Approval identities and approver identities must be unique where required by the active threshold policy. Duplicate, invalid, expired, revoked, out-of-scope, mismatched, already-consumed, or unavailable approvals fail closed. Approval threshold satisfaction and consumption are evaluated against the same atomic snapshot and committed together.

`operator_authorization_snapshot` property order is:

1. `operator_authorization_id`
2. `operator_id`
3. `scope_digest`
4. `policy_version`
5. `expiration`
6. `consumption_state`
7. `consumption_version`

Operator authorization cannot be consumed twice or transferred to another request, intent, transaction, policy, party, amount, or operator. It is authorization evidence only; it cannot replace Protocol validation or cause invocation.

## 8. Concurrency and ordering

All contenders for the same replay, idempotency, spending, approval, operator, or policy partition are serialized by one future operator-approved concurrency model. The authoritative order is the monotonic committed state version, not arrival time, caller time, thread scheduling, or network order.

On optimistic conflict, a future implementation must discard the stale eligibility computation, read one new coherent snapshot, and re-run every affected check. It may not reuse stale authorization, validation, time, custody, limit, approval, or evidence results beyond their explicitly verified validity. Retry limits and conflict handling are operator decisions; exhaustion fails closed.

Deadlock, timeout, leader uncertainty, split-brain indication, replication lag beyond policy, concurrent policy change, or unknown commit outcome produces no eligibility response until a unique authoritative state is recovered.

## 9. Commit, partial failure, and crash recovery

Allowed `commit_state` values are `committed`, `not_committed`, `conflict`, `uncertain`, `corrupt`, and `unavailable`. Only `committed` with independently verifiable integrity evidence permits a public eligibility result.

The system must preserve these invariants:

- no replay/approval/operator item is consumed without its corresponding decision record;
- no spend is charged without the same decision record;
- no eligible decision exists without every required consumption and audit-publication intent;
- no failed or rejected decision creates an eligible result;
- no crash converts `uncertain` into `committed` by assumption;
- no recovery rewrites or erases prior committed history.

After a crash, recovery must establish a unique last durable version, verify integrity and policy lineage, reconcile commit identifiers, and classify each in-flight decision. A proven committed result is returned idempotently. A proven non-commit may be retried only as a fresh atomic evaluation under still-valid evidence. An ambiguous or corrupt result remains blocked and is escalated through a separately authorized recovery procedure.

## 10. Persistence, retention, integrity, and versioning

Storage health states are `AVAILABLE`, `DEGRADED`, `RECOVERING`, `CORRUPT`, and `UNAVAILABLE`. Only `AVAILABLE`, with current integrity evidence and an approved consistency profile, can support eligibility evaluation.

Records must be durable for at least the longest applicable replay, policy, audit, incident, and dispute horizon. Retention cannot delete a record while any binding, receipt, audit projection, approval, authorization, or recovery obligation depends on it. Expiry is monotonic and produces a tombstone or equivalent integrity-preserving public lineage; it cannot permit replay.

Every mutation must bind contract version, record version, prior version, policy version, commit identifier, canonical payload digest, trusted-time evidence, and integrity evidence. Unknown versions, downgrade attempts, broken lineage, duplicate versions, missing predecessors, or digest mismatches fail closed.

## 11. Status and error behavior

This contract uses the Foundation117 stable response taxonomy and precedence. It invents no replacement public status or error code. Storage-specific internal detail must map to the least revealing applicable fail-closed code. Secure errors expose no topology, credentials, record contents, secret material, timing oracle, or recovery controls.

An earlier schema, evidence, revocation, time, binding, authorization, validation, replay, economic, approval, operator, custody, or state failure is never hidden by a later one. No error path attempts signing, accesses a wallet/key, submits, broadcasts, connects RPC/network, mutates the L28 ledger, or settles.

## 12. Operator decisions and remaining gates

Each item below is `OPERATOR_DECISION_REQUIRED` before implementation evidence can satisfy `F122-G03` or `F122-G04`:

- storage technology, trust boundary, administrative domain, and failure model;
- consistency, isolation, concurrency, partitioning, and authoritative ordering model;
- durability, replication, quorum, split-brain prevention, and availability policy;
- record/version/commit identifier formats and integrity mechanism;
- conflict retry, timeout, deadlock, uncertain-commit, and recovery policies;
- replay, idempotency, evidence-consumption, audit, and dispute retention horizons;
- spending partitions, windows, pending-reservation treatment, limits, and arithmetic unit;
- approval and operator-authorization single-use/reuse policy and threshold consumption;
- backup, restore, point-in-time recovery, rollback prohibition, and recovery ceremonies;
- storage encryption, access control, monitoring, audit, and non-signer key management;
- schema evolution and migration security review without weakening historical bindings;
- implementation boundary, adversarial/concurrency/crash tests, independent review, deployment, and activation authorization.

No database, migration, runtime, or storage system is selected or authorized. Until every applicable choice and evidence exists, atomic replay and economic controls remain `GAP_REQUIRES_FUTURE_WORK`.

## 13. Protocol and economic invariants

This contract preserves: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; and immutable historical evidence.

Bitcoin remains external evidence only. Production Bitcoin proof architecture, Bitcoin confirmation/reorg policy and count, and observer quorum/independence remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

Foundation124 grants no signer, storage runtime, database, migration, wallet, key, signature, RPC, network, broadcast, settlement, deployment, or activation authorization.
