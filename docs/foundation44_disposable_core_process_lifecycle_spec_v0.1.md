# L28 Disposable Core Process Lifecycle Policy Specification v0.1

**Foundation:** 44

**Status:** Offline specification only; non-activation

**Milestone label:** F37/F38 table **M2 Core** lifecycle policy (partial slice)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN) — immutable

**Profile:** `l28-disposable-core-process-lifecycle-policy/v0.1`

## 1. Purpose, roadmap alignment, and exact scope

Foundation 44 defines the locked offline specification for a **Disposable Core
Process Lifecycle Policy**: a deterministic, fail-closed policy layer that
decides whether an inert Foundation 21 `CoreNodeRoleModel` transition is
permitted when the caller supplies a successful frozen Foundation 39 identity
binding projection.

This foundation is a **partial M2 Core slice**. It does **not** complete F37 M2
(issuance acknowledgement, tip authority, disposable wallets, reset/cleanup, or
a runnable process). It only locks the offline lifecycle-policy contract that a
future Foundation 45 implementation may evaluate in memory.

Foundation 44:

- MUST NOT spawn processes, threads, async workers, or subprocesses;
- MUST NOT open sockets or perform transport, discovery, or synchronization;
- MUST NOT persist filesystem, database, or peer state;
- MUST NOT authorize spend, admission, mining, consensus, or deployment;
- MUST keep `execution_authorized=false` on every conforming path;
- MUST NOT define or grant admission authority;
- MUST NOT depend on Foundations 40–43.

### Roadmap citations

| Source | Citation |
|---|---|
| F37 M2 scope (broader than this slice) | `docs/bounded_testnet_readiness_gap_audit_v0.1.md` § Smallest safe isolated-testnet sequence — M2 row |
| F37-06 Core lifecycle gap | `docs/bounded_testnet_readiness_gap_audit_v0.1.md` § F37-06 Node lifecycle and process isolation — Recommended milestone order M2 |
| F38 M2 dependency on identity | `docs/disposable_network_identity_genesis_binding_v0.1.md` § Milestone dependencies — M2 row: Core MUST load/verify Foundation 38 genesis/binding |
| F38 defers M2–M5 | same section — Foundation 38 implements M1 specification only |
| F40 leaves F38-table M2 Core to a separate foundation | `docs/peer_handshake_identity_binding_v0.1.md` § Later-milestone boundaries |

M3+ transport/sync/propagation/reorg remain deferred
(`docs/bounded_testnet_readiness_gap_audit_v0.1.md` M3–M5 rows;
`docs/disposable_network_identity_genesis_binding_v0.1.md` M3–M5 rows).

## 2. Normative dependencies

### Foundation 21 — Core role model (normative reuse)

| Artifact | Role |
|---|---|
| `docs/node_role_model_v0.1.md` | Locked inert Core/P2P role-model specification |
| `coin/node_role_model.py` | `CoreNodeRoleModel`, `CORE_STATES`, `CORE_RESERVED_STATES`, `CORE_ALLOWED_TRANSITIONS`, `STABLE_CODES`, `NodeRoleTransitionResult` |
| Model version | `l28-node-role-model/v0.1` |
| Core role name | `CoreL28Node` |

Foundation 44 MUST NOT define a parallel Core FSM. States, reserved states,
allowed transitions, and the four Foundation 21 transition codes are
**authoritative** as implemented in `coin/node_role_model.py` and documented in
`docs/node_role_model_v0.1.md` § Core role states / Transition result /
Reserved-state enforcement.

### Foundation 39 — Disposable identity evidence (trust root)

| Artifact | Role |
|---|---|
| `docs/disposable_network_identity_genesis_binding_v0.1.md` | Locked M1 identity/genesis specification |
| `docs/foundation39_disposable_network_identity_genesis_binding_v0.1.md` | Foundation 39 implementation record |
| `coin/disposable_network_identity_genesis_binding.py` | Offline verifier; `DisposableIdentityBindingResult`; `ENVIRONMENT=DISPOSABLE_TEST`; `NETWORK_ID=l28-disposable-test/v0.1`; `PROTOCOL_VERSION=l28-protocol/1.0.0` |

Foundation 44 trusts only a **caller-supplied frozen success projection** of a
Foundation 39 identity-binding result. It MUST NOT re-run Foundation 39
cryptography, canonicalization, genesis parsing, freshness, or replay logic.

## 3. Frozen Foundation 39 success projection

A conforming policy evaluation MUST require an immutable projection object with
exactly these fields (names aligned to
`DisposableIdentityBindingResult` in
`coin/disposable_network_identity_genesis_binding.py`):

| Field | Success requirement |
|---|---|
| `ok` | Exact boolean `true` |
| `code` | Exact string `ok` |
| `network_id` | Exact `l28-disposable-test/v0.1` |
| `chain_id` | Non-empty string; caller asserts it is the Foundation 39 verified disposable chain ID |
| `genesis_digest` | 64 lowercase hex string; caller asserts Foundation 39 verified digest |
| `protocol_version` | Exact `l28-protocol/1.0.0` |
| `execution_authorized` | Exact boolean `false` |
| `report_id` | 64 lowercase hex string from the Foundation 39 success report |

### Trust assumptions

1. The caller obtained the projection from a successful Foundation 39 evaluation
   in the same offline composition.
2. Foundation 44 performs **structural and equality checks only** against the
   projection fields above.
3. Foundation 44 MUST NOT recompute `chain_id`, `genesis_digest`, or `report_id`.
4. A projection with `ok=false`, non-`ok` code, `execution_authorized=true`,
   non-disposable `network_id`/`protocol_version`, or malformed fields fails
   closed before any Core transition is considered.

## 4. Input and output contracts

### Policy input (`CoreLifecyclePolicyRequest`)

Exact fields in this order for any JSON encoding of the request:

1. `policy_version` — exact `l28-disposable-core-process-lifecycle-policy/v0.1`
2. `environment` — exact `DISPOSABLE_TEST`
3. `identity_evidence` — object with the eight projection fields in §3, in that
   field order
4. `current_state` — Foundation 21 Core state string
5. `requested_state` — Foundation 21 Core state string
6. `execution_authorized` — JSON boolean `false` only

Unknown, missing, reordered, duplicated, or incorrectly typed fields fail
closed. Maximum encoded request size: `4096` bytes.

### Policy output (`CoreLifecyclePolicyResult`)

Every result MUST include at least:

| Field | Rule |
|---|---|
| `ok` | `true` only when policy permits the Foundation 21 transition |
| `code` | Stable code from §7 |
| `role` | Exact `CoreL28Node` |
| `previous_state` | Evaluated current state (empty string only on pre-transition parse failures where state is unavailable) |
| `requested_state` | Requested state when recovered; else empty string |
| `resulting_state` | New state on success; otherwise unchanged current state (Foundation 21 semantics) |
| `model_version` | Exact `l28-node-role-model/v0.1` |
| `policy_version` | Exact policy profile |
| `network_id` | From accepted evidence on success; else empty string |
| `chain_id` | From accepted evidence on success; else empty string |
| `genesis_digest` | From accepted evidence on success; else empty string |
| `protocol_version` | From accepted evidence on success; else empty string |
| `identity_report_id` | From accepted evidence on success; else empty string |
| `execution_authorized` | MUST be boolean `false` on every path |
| `detail` | MUST be empty string in v0.1 (no exception/path/secret leakage) |

No `admission_authorized` field exists in this profile. Foundation 44 MUST NOT
introduce admission authority.

## 5. Exact Foundation 21 state and transition reuse

### Active Core states (normative)

`CREATED`, `EVIDENCE_ONLY`, `DISPOSABLE_TEST_READY`, `PAUSED`, `STOPPED`,
`FAILED`

### Reserved Core states (unreachable destinations)

`CANONICAL_READY_RESERVED`, `RUNNING_RESERVED`

### Allowed transitions (normative; identical to Foundation 21)

| From | To |
|---|---|
| `CREATED` | `EVIDENCE_ONLY` |
| `CREATED` | `DISPOSABLE_TEST_READY` |
| `CREATED` | `PAUSED` |
| `EVIDENCE_ONLY` | `PAUSED` |
| `DISPOSABLE_TEST_READY` | `PAUSED` |
| `PAUSED` | `STOPPED` |
| `CREATED` | `FAILED` |
| `EVIDENCE_ONLY` | `FAILED` |
| `DISPOSABLE_TEST_READY` | `FAILED` |
| `PAUSED` | `FAILED` |
| `FAILED` | `STOPPED` |

`STOPPED` is terminal. Self-transitions are not allowed.
`CANONICAL_READY_RESERVED` and `RUNNING_RESERVED` remain unreachable.

Foundation 44 adds **no** ornamental states (no envelope-bound, pid, listen,
sync, wallet, tip, or issuance states).

A future Foundation 45 implementation MUST delegate the transition decision to
`CoreNodeRoleModel.transition` (or an equivalent pure function that applies the
same tables) after policy preconditions pass.

## 6. Deterministic first-failure validation precedence

A conforming Foundation 45 evaluator MUST stop at the first failure:

1. Reject unsupported payload type (`input_type_invalid`).
2. Reject encoded size `>` `4096` bytes (`input_too_large`).
3. Reject invalid UTF-8 (`encoding_invalid`).
4. Reject malformed JSON, non-finite numbers, duplicate keys, or non-object
   top-level (`json_invalid` / `duplicate_key` / `invalid_top_level`).
5. Reject missing/unknown/reordered/wrong-type fields (`schema_invalid`).
6. Reject unsupported `policy_version` (`policy_version_unsupported`).
7. If `environment` ∈ `{MAIN, CANONICAL, HISTORICAL, PRODUCTION}`, fail with
   `historical_import_forbidden`.
8. Else if `environment` ≠ `DISPOSABLE_TEST`, fail with `environment_invalid`.
9. If request `execution_authorized` is not JSON `false`, fail with
   `execution_authorized_invalid`.
10. Validate `identity_evidence` structural rules in §3; on failure emit
    `identity_evidence_invalid` (or `execution_authorized_invalid` when the
    evidence flag is not `false`).
11. Require evidence `ok=true`, `code=ok`, disposable `network_id` and
    `protocol_version`, and `execution_authorized=false`; otherwise
    `identity_evidence_invalid`.
12. Apply Foundation 21 Core transition rules to
    `(current_state, requested_state)` and surface Foundation 21 codes
    unchanged: `state_invalid`, `reserved_state_unreachable`,
    `transition_not_allowed`, or `transitioned`.
13. On success, return `ok=true`, `code=transitioned`,
    `execution_authorized=false`, and evidence identity fields copied from the
    accepted projection.

No permissive repair, coercion, silent field dropping, hidden mutation,
wall-clock use, randomness, or exception text leakage is allowed. Unexpected
internal failures sanitize to `internal_error` with empty `detail`.

## 7. Minimal stable-code registry

| Code | Origin | Meaning |
|---|---|---|
| `transitioned` | F21 | Policy permitted the Core transition |
| `state_invalid` | F21 | Empty, non-string, or unknown Core state |
| `reserved_state_unreachable` | F21 | Reserved Core state requested |
| `transition_not_allowed` | F21 | Known states but transition absent |
| `input_type_invalid` | F44 | Unsupported payload type |
| `input_too_large` | F44 | Encoded size exceeds `4096` bytes |
| `encoding_invalid` | F44 | Invalid UTF-8 |
| `json_invalid` | F44 | Malformed JSON or non-finite number |
| `duplicate_key` | F44 | Duplicate key at any depth |
| `invalid_top_level` | F44 | Top-level value is not an object |
| `schema_invalid` | F44 | Missing/unknown/reordered/wrong-type fields |
| `policy_version_unsupported` | F44 | Unsupported policy version |
| `environment_invalid` | F44 | Environment is not `DISPOSABLE_TEST` |
| `historical_import_forbidden` | F44 | Forbidden environment label |
| `identity_evidence_invalid` | F44 | Missing/unsuccessful/mismatched F39 projection |
| `execution_authorized_invalid` | F44 | `execution_authorized` is not JSON `false` |
| `internal_error` | F44 | Sanitized unexpected failure |

**Stable error-code count:** 17

Foundation 21 codes retain their Foundation 21 meanings and precedence inside
step 12.

## 8. Authority invariants and fail-closed behavior

1. `execution_authorized` MUST be JSON/boolean `false` on every request and
   every result path.
2. Foundation 44 defines **no** admission authority and MUST NOT add
   `admission_authorized`.
3. Success means only: an inert Foundation 21 Core transition is policy-allowed
   under disposable identity evidence.
4. Success is **not** permission to start a node, spawn a process, open a
   socket, mutate a ledger, mine, admit peers, or activate a testnet.
5. `DISPOSABLE_TEST_READY` remains an offline model state only; it is not
   runtime readiness.
6. Reserved states stay unreachable.

## 9. Resource limits and dependency-injection boundaries

| Boundary | Rule |
|---|---|
| Payload | JSON text or bytes only; max `4096` bytes |
| Identity evidence | Caller-supplied frozen projection; no Foundation 39 re-entry required inside the policy function |
| Transition engine | Foundation 21 tables / `CoreNodeRoleModel.transition` |
| Time | No wall clock; no logical freshness window in Foundation 44 |
| Replay | Not owned by Foundation 44 (Foundation 39/21 do not require a Core replay set for this policy) |
| I/O | None in Foundation 44; Foundation 45 MUST NOT add filesystem discovery |

Optional future CLI (Foundation 45 only) MAY read one explicit regular-file path
and MUST reject directories and symbolic links. Foundation 44 ships no CLI.

## 10. Foundation 45 acceptance-test matrix (normative)

A conforming Foundation 45 suite MUST include at least:

1. **Success path** — valid F39 success projection +
   `CREATED` → `DISPOSABLE_TEST_READY` returns `transitioned` with
   `execution_authorized=false`.
2. **Evidence-only path** — `CREATED` → `EVIDENCE_ONLY` succeeds under the same
   evidence rules.
3. **Identity evidence failure** — `ok=false` or wrong `network_id` fails with
   `identity_evidence_invalid` before transition evaluation.
4. **Forbidden environment precedence** — `environment=CANONICAL` (and MAIN /
   HISTORICAL / PRODUCTION) → `historical_import_forbidden`.
5. **Generic invalid environment** — e.g. `OTHER` → `environment_invalid`.
6. **Authority flag** — request or evidence `execution_authorized=true` fails
   with `execution_authorized_invalid`.
7. **Reserved unreachable** — request `RUNNING_RESERVED` or
   `CANONICAL_READY_RESERVED` → `reserved_state_unreachable`.
8. **Illegal transition** — e.g. `STOPPED` → `CREATED` →
   `transition_not_allowed` (or `state_invalid` if current state handling
   requires it under Foundation 21 rules for the chosen fixture).
9. **Terminal STOPPED** — no outgoing transition succeeds.
10. **Malformed matrix** — type/size/UTF-8/JSON/duplicate-key/top-level/schema/
    unknown-field/order.
11. **Unsupported policy version** — foreign `policy_version` fails.
12. **Determinism** — identical request bytes yield identical results.
13. **Static hygiene** — no socket/subprocess/thread/Leap28/Nova/wallet/mining
    imports; empty `detail`; no F40–F43 imports.
14. **Economics unchanged** — assert Protocol v1.0.0 constants remain
    `28_000_000`, `11_130_000`, `(28, 14, 7, 3, 1)`.
15. **All 17 stable codes** asserted through the public API (`internal_error`
    via narrow monkeypatch).

## 11. Ownership table

| Concern | Owner |
|---|---|
| Core/P2P role FSM tables and transition codes | Foundation 21 |
| Disposable identity/genesis verification | Foundations 38/39 |
| Peer-handshake identity binding | Foundations 40/41 |
| Peer admission decision envelope | Foundations 42/43 |
| Offline Core lifecycle **policy** under F39 evidence | **Foundation 44 (this document)** |
| Issuance acknowledgement, tip authority, disposable wallets, reset/cleanup | Later M2 slices (not Foundation 44) |
| Runnable Core process entrypoint / sandbox data dirs | Later M2 remediation of F37-06 (not Foundation 44) |
| P2P transport, discovery, sync | M3+ |
| Propagation / confirmation | M4 |
| Fork / reorg | M5 |

## 12. Protected economic facts and prohibited coupling

| Fact | Value | Evidence |
|---|---:|---|
| Hard cap | `28_000_000` | `coin/tx_validation.py` `L28_MAX_SUPPLY` |
| Emission ceiling | `11_130_000` | `coin/tx_validation.py` `L28_EMISSION_CEILING` |
| Halving interval | `210_000` | `coin/tx_validation.py` `L28_HALVING_INTERVAL` |
| Max coinbase reward | `28` | `coin/tx_validation.py` `L28_MAX_COINBASE_REWARD` |
| Reward schedule | `(28, 14, 7, 3, 1)` | `coin/tx_validation.py` `L28_REWARD_SCHEDULE` |

Foundation 44 MUST NOT alter these facts, carry balances/rewards, or authorize
issuance.

Prohibited coupling: Leap28, Nova, MAIN runtime activation, historical import,
canonical continuation, and revival or extension of `coin/l28_coin.py`.

## 13. Explicit deferred work and exclusions

Foundation 44 MUST NOT and does not specify:

- wallets, tip authority, issuance acknowledgement, reset/cleanup;
- runnable entrypoints, subprocesses, threads, async workers;
- sockets, transport, discovery, synchronization;
- persistence, filesystem state, databases;
- signing, transactions, ledger mutation, consensus, mining, deployment;
- MAIN environment authorization or historical import;
- new third-party dependencies;
- Leap28 or Nova integration;
- Foundation 40–43 imports, fields, or metadata;
- production implementation, tests, or CLI (those are Foundation 45+).

This document does **not** claim F37 M2 completion.

## 14. Smallest authorized Foundation 45 follow-up scope

If Foundation 44 is locked, Foundation 45 MAY implement **only**:

1. `coin/disposable_core_process_lifecycle_policy.py` — offline evaluator of this
   policy that calls Foundation 21 `CoreNodeRoleModel.transition` after §6
   preconditions;
2. `tests/test_disposable_core_process_lifecycle_policy.py` — acceptance matrix
   in §10;
3. `docs/foundation45_disposable_core_process_lifecycle_policy_v0.1.md` — narrow
   implementation record.

Foundation 45 MUST NOT spawn processes, open sockets, persist state, modify
`coin/l28_coin.py`, export through `coin/__init__.py` unless separately
authorized, or set `execution_authorized=true`.

## Required public APIs (Foundation 45 contract)

1. `evaluate_core_lifecycle_policy_json(payload: str | bytes) -> CoreLifecyclePolicyResult`
2. Optional pure helper:
   `evaluate_core_lifecycle_policy(*, identity_evidence: Mapping[str, Any], current_state: str, requested_state: str) -> CoreLifecyclePolicyResult`

These APIs MUST remain offline and non-activating.

## Security boundary and non-authorization statement

A completed Foundation 44 specification, and any later successful Foundation 45
policy evaluation under this profile, is offline disposable Core lifecycle
**policy evidence** only. It is not permission to spend L28, not an executable
transaction, not ledger mutation, not peer admission, not process creation, and
not authorization to start a node, network, miner, wallet, or testnet.

`execution_authorized` MUST remain the JSON boolean `false` on every conforming
request and every success or failure result path.
