# L28 Disposable Core Process Entrypoint Specification v0.1

**Foundation:** 46

**Status:** Offline specification only; non-activation

**Milestone label:** F37-06 disposable Core process entrypoint contract (partial
slice; specification only)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN) — immutable

**Profile:** `l28-disposable-core-process-entrypoint/v0.1`

## 1. Purpose, status, terminology, and non-authority statement

Foundation 46 defines the locked offline specification for a **Disposable Core
Process Entrypoint** preflight contract: a deterministic, fail-closed,
immutable request/result schema that decides whether a proposed disposable Core
configuration is **preflight-valid** under caller-supplied frozen Foundation 39
identity evidence, frozen Foundation 45 lifecycle-policy evidence, and an
immutable sandbox data-directory descriptor.

This foundation is a **partial M2 / F37-06 specification slice**. It does
**not** implement a runnable Core process, does **not** complete F37-06
implementation, and does **not** complete Foundation 37 M2.

### Terminology

| Term | Meaning in this specification |
|---|---|
| Entrypoint (F46) | Offline immutable preflight request/result contract |
| Preflight-valid | Request satisfies this specification’s structural and cross-evidence rules |
| Process launch | Actual OS/process creation (deferred; never authorized here) |
| Sandbox descriptor | Immutable logical ownership claim for a future disposable data directory |
| Path lexeme | Caller-supplied path string validated only by lexical rules in this profile; not a filesystem operation |
| Future evaluator | Later implementation that evaluates this contract in memory without spawning a process |
| Future launcher | Still-later component that may create a process only under a separate authorization foundation |

### Non-authority statement

A conforming Foundation 46 evaluation, and any later successful evaluation under
this profile:

- MUST set `execution_authorized` to the JSON/boolean `false` on every path;
- MUST set `process_launch_authorized` to the JSON/boolean `false` on every
  path;
- MUST NOT define, require, or grant `admission_authorized`;
- MUST NOT mean that a process is runnable, launched, admitted, canonical,
  synchronized, or authorized;
- MUST NOT mutate a Foundation 21 lifecycle model, filesystem, network, wallet,
  ledger, or any external state;
- is offline disposable Core entrypoint **preflight evidence** only.

Success means only: the proposed configuration satisfies this specification
contract.

Foundation 46:

- MUST NOT spawn processes, threads, async workers, subprocesses, daemons,
  services, or containers;
- MUST NOT open sockets or perform transport, discovery, synchronization, or
  propagation;
- MUST NOT create, inspect, mutate, reset, wipe, or delete filesystem state;
- MUST NOT authorize spend, admission, mining, consensus, tip authority,
  issuance, or deployment;
- MUST NOT depend on Foundations 40–43;
- MUST NOT modify or revive `coin/l28_coin.py`.

## 2. F37-06 relationship and dependency boundaries

### Roadmap citations

| Source | Citation |
|---|---|
| F37-06 Node lifecycle and process isolation | `docs/bounded_testnet_readiness_gap_audit_v0.1.md` § F37-06 |
| F37 M2 broader scope | same document — Smallest safe isolated-testnet sequence — M2 row |
| F44 deferred runnable entrypoint | `docs/foundation44_disposable_core_process_lifecycle_spec_v0.1.md` § Ownership table / Explicit deferred work |
| F45 deferred runnable process | `docs/foundation45_disposable_core_process_lifecycle_policy_implementation_v0.1.md` § Explicit exclusions |
| F38 data_dir_tag / later wipe rules | `docs/disposable_network_identity_genesis_binding_v0.1.md` § Binding configuration / Reset, cleanup |

### Explicit F37-06 alignment

F37-06 requires a disposable-test-only Core process entrypoint with sandbox data
dirs, start/stop, and unreachable reserved operational states
(`docs/bounded_testnet_readiness_gap_audit_v0.1.md` § F37-06).

Foundation 46 locks only the **offline preflight contract** for that entrypoint.
Runnable process creation, supervision, start/stop execution, and process
lifecycle tests remain deferred. Foundation 46 MUST NOT claim F37-06
implementation complete or Foundation 37 M2 complete.

### Prerequisites consumed (frozen evidence only)

| Prerequisite | How Foundation 46 consumes it |
|---|---|
| F37-12 / Foundations 38–39 | Frozen Foundation 39 success projection |
| F37-01 genesis binder (identity portion) | Same Foundation 39 projection |
| Offline Core lifecycle policy | Frozen Foundation 45 success projection |

### Explicitly out of Foundation 46

| Later work | Owner / milestone |
|---|---|
| Callable evaluator of this contract | Future Foundation 47-class implementation |
| Actual process launch / supervision | Later F37-06 implementation (not this document) |
| Filesystem create / verify | Future sandbox-directory creator (post-F46) |
| Ephemeral ledger layout / reset semantics | F37-05 (depends on F37-06) |
| Stop / reset / cleanup / wipe | F37-13 (depends on F37-06) |
| Tip authority, wallets, issuance wiring | Later M2 slices |
| Transport / sync | M3+ (F37-07) |
| Peer-admission evidence | Foundations 42–43 — **excluded** |

## 3. Entrypoint specification versus future implementation

| Layer | Role |
|---|---|
| Foundation 46 (this document) | Normative schemas, precedence, codes, exclusions |
| Future evaluator | Pure in-memory evaluation of this contract; MUST NOT spawn |
| Future launcher | May create a process only under a later authorized foundation; never implied by F46 success |
| Foundation 21 | Sole Core lifecycle state/transition authority |
| Foundations 38/39 | Sole disposable identity/genesis verification authority |
| Foundations 44/45 | Sole offline Core lifecycle-policy authority |
| Foundations 40–43 | Not used by this profile |

Foundation 46 MUST NOT duplicate or reinterpret Foundation 39 cryptography,
canonicalization, genesis parsing, freshness, or replay logic.

Foundation 46 MUST NOT duplicate or reinterpret Foundation 45 policy evaluation
or Foundation 21 transition tables. It performs **structural and equality
checks only** on frozen projections.

## 4. Ownership table

| Concern | Owner |
|---|---|
| Constructs and retains evidence projections | Caller |
| Core states, allowed transitions, transition codes | Foundation 21 |
| Disposable identity/genesis verification | Foundations 38/39 |
| Offline Core lifecycle-policy evaluation | Foundations 44/45 |
| Offline entrypoint preflight contract | **Foundation 46 (this document)** |
| Future in-memory evaluator of this contract | Later implementation of Foundation 46 |
| Future process create/supervise/stop execution | Later F37-06 process implementation |
| Future exclusive sandbox directory creation | Future sandbox-directory creator (post-F46; not this document) |
| Ephemeral data-dir layout / replay reset rules | Later F37-05 |
| Tagged disposable directory wipe / cleanup | Later F37-13 |
| Peer handshake / admission envelopes | Foundations 40–43 (excluded here) |
| Economics / supply / rewards | Protocol v1.0.0 / existing validators (unchanged) |

Foundation 46 owns **no** process handle, filesystem directory, socket, wallet,
ledger, miner, or external resource.

## 5. Normative dependencies and accepted lifecycle states

### Foundation 21 — Core role model (normative reuse)

| Artifact | Role |
|---|---|
| `docs/node_role_model_v0.1.md` | Locked inert Core role-model specification |
| `coin/node_role_model.py` | `CORE_STATES`, `CORE_RESERVED_STATES`, `CORE_ALLOWED_TRANSITIONS` |
| Model version | `l28-node-role-model/v0.1` |
| Core role name | `CoreL28Node` |

Foundation 46 MUST NOT define a parallel Core FSM, reverse transition, wildcard
transition, skipped transition, or direct private-state mutation.

### Active Core states (real Foundation 21 states only)

`CREATED`, `EVIDENCE_ONLY`, `DISPOSABLE_TEST_READY`, `PAUSED`, `STOPPED`,
`FAILED`

### Reserved Core states (unreachable)

`CANONICAL_READY_RESERVED`, `RUNNING_RESERVED`

### Entrypoint-accepted lifecycle evidence

For a successful preflight, the frozen Foundation 45 projection MUST pass
§6.2.1 and §6.2.2. In particular, after structural acceptance, lifecycle fields
MUST be exactly:

| Field | Required value |
|---|---|
| `previous_state` | Exact `CREATED` |
| `requested_state` | Exact `DISPOSABLE_TEST_READY` |
| `resulting_state` | Exact `DISPOSABLE_TEST_READY` |

together with the §6.2.1 status/identity structural requirements (`ok=true`,
`code=transitioned`, `role=CoreL28Node`, model/policy versions,
`execution_authorized=false`, digest fields, empty `detail`).

This is the sole Foundation 21 inbound edge to the acknowledged disposable test
state (`CREATED` → `DISPOSABLE_TEST_READY`). Foundation 46 does not perform that
transition; it only accepts retained success evidence of it.

### Reserved-state rejection and reachability proof

1. After Foundation 45 evidence passes structural validation (§6.2.1 / §8
   step 13), if any of `previous_state`, `requested_state`, or
   `resulting_state` equals `CANONICAL_READY_RESERVED` or `RUNNING_RESERVED`,
   fail with the Foundation 21 stable string `reserved_state_unreachable`
   reused by value (§8 step 14; §9.1).
2. Other well-formed but unsupported lifecycle values fail with
   `lifecycle_state_invalid` (§8 step 15), not with
   `lifecycle_policy_evidence_invalid`.
3. Foundation 46 never requests a Foundation 21 transition.
4. Foundation 46 never adds edges into reserved states.
5. Therefore `CANONICAL_READY_RESERVED` and `RUNNING_RESERVED` remain
   unreachable under this profile.
6. `STOPPED` teardown and stop commands are out of scope (later F37-13 /
   process implementation).

If a caller optionally injects a Foundation 21 model into a future evaluator for
hygiene checks, the evaluator MUST NOT mutate it. Foundation 46 success and
failure paths require **no** model mutation. Validation failures MUST leave any
injected model unchanged.

## 6. Frozen evidence projections

### 6.1 Foundation 39 identity success projection

Exact fields in this order (aligned to Foundation 44 §3 /
`DisposableIdentityBindingResult`):

| Field | Type | Success requirement |
|---|---|---|
| `ok` | boolean | Exact `true` |
| `code` | string | Exact `ok` |
| `network_id` | string | Exact `l28-disposable-test/v0.1` |
| `chain_id` | string | Non-empty; 64 lowercase hex |
| `genesis_digest` | string | 64 lowercase hex |
| `protocol_version` | string | Exact `l28-protocol/1.0.0` |
| `execution_authorized` | boolean | Exact `false` |
| `report_id` | string | 64 lowercase hex |

Structural/equality checks only. No Foundation 39 re-verification.

### 6.2 Foundation 45 lifecycle-policy success projection

Exact fields in this order (aligned to `CoreLifecyclePolicyResult`):

`ok`, `code`, `role`, `previous_state`, `requested_state`, `resulting_state`,
`model_version`, `policy_version`, `network_id`, `chain_id`, `genesis_digest`,
`protocol_version`, `identity_report_id`, `execution_authorized`, `detail`.

Foundation 45 validation is split so structural defects cannot shadow lifecycle
classification codes (§8 steps 13–15).

#### 6.2.1 Structural / type / required-field / status-code validation

Failures in this subsection map **only** to
`lifecycle_policy_evidence_invalid`:

| Field | Structural requirement |
|---|---|
| object shape | Exact field set and order above; all values correctly typed |
| `ok` | boolean; exact `true` |
| `code` | string; exact `transitioned` |
| `role` | string; exact `CoreL28Node` |
| `previous_state` | string; non-empty |
| `requested_state` | string; non-empty |
| `resulting_state` | string; non-empty |
| `model_version` | string; exact `l28-node-role-model/v0.1` |
| `policy_version` | string; exact `l28-disposable-core-process-lifecycle-policy/v0.1` |
| `network_id` | string; exact `l28-disposable-test/v0.1` |
| `chain_id` | string; 64 lowercase hex |
| `genesis_digest` | string; 64 lowercase hex |
| `protocol_version` | string; exact `l28-protocol/1.0.0` |
| `identity_report_id` | string; 64 lowercase hex |
| `execution_authorized` | boolean; exact `false` |
| `detail` | string; exact empty string |

No Foundation 45 re-evaluation and no Foundation 21 transition call.

#### 6.2.2 Lifecycle value classification

Applies only after §6.2.1 succeeds. Inspect
`previous_state`, `requested_state`, and `resulting_state`:

1. If any equals `CANONICAL_READY_RESERVED` or `RUNNING_RESERVED`, fail with
   `reserved_state_unreachable` (Foundation 21 string reused by value).
2. Else if they are not exactly
   `previous_state=CREATED`,
   `requested_state=DISPOSABLE_TEST_READY`, and
   `resulting_state=DISPOSABLE_TEST_READY`,
   fail with `lifecycle_state_invalid`.
3. Else lifecycle values are accepted for cross-evidence binding.

Cross-field equality of `chain_id`, `genesis_digest`, and
`identity_report_id` against Foundation 39 is **not** part of §6.2.1 or
§6.2.2; it is evaluated only at §8 step 18 (`evidence_mismatch`).

### 6.3 Foundation 43 exclusion

Foundation 46 MUST NOT require, project, import, or validate Foundation 42/43
peer-admission envelopes. Peer-admission evidence is out of scope for F37-06
entrypoint preflight as locked by this specification.

### 6.4 Cross-evidence validation

After Foundation 39 validation, Foundation 45 §6.2.1–§6.2.2, and sandbox
descriptor structural acceptance (§8 step 16) succeed, the following MUST match
exactly:

| Binding | Rule |
|---|---|
| Environment | Request `environment` and sandbox `environment` are exact `DISPOSABLE_TEST` (projections carry no separate environment field; they are disposable-only by upstream contract) |
| `network_id` | F39 = F45 = sandbox |
| `chain_id` | F39 = F45 = sandbox |
| `genesis_digest` | F39 = F45 = sandbox |
| `protocol_version` | F39 = F45 = `l28-protocol/1.0.0` |
| Report lineage | F45 `identity_report_id` = F39 `report_id` |

Any mismatch fails with `evidence_mismatch`. Lifecycle value acceptance is
already decided by §6.2.2 and MUST NOT be re-coded as `evidence_mismatch`.

Stale, duplicated, malformed, authority-bearing (`execution_authorized=true`),
or contradictory evidence MUST fail closed. A caller-supplied assertion MUST NOT
substitute for missing upstream projection fields.

## 7. Immutable schemas

Only the following schemas are required.

### 7.1 `CoreEntrypointRequest`

Exact top-level fields in this order for any JSON encoding:

1. `entrypoint_version` — exact `l28-disposable-core-process-entrypoint/v0.1`
2. `environment` — exact `DISPOSABLE_TEST`
3. `identity_evidence` — Foundation 39 projection object (§6.1), fields in that
   order
4. `lifecycle_policy_evidence` — Foundation 45 projection object (§6.2), fields
   in that order
5. `sandbox` — `SandboxDataDirectoryDescriptor` (§7.2)
6. `process_intent` — object with exact fields in this order:
   1. `offline` — boolean `true`
   2. `transport_enabled` — boolean `false`
   3. `instance_mode` — exact string `single_core_disposable`
7. `execution_authorized` — JSON boolean `false` only
8. `process_launch_authorized` — JSON boolean `false` only

Unknown, missing, reordered, duplicated, or incorrectly typed fields fail
closed with `schema_invalid` (or earlier parse codes).

Forbidden authority-bearing fields: any `admission_authorized` field; any true
value for `execution_authorized` or `process_launch_authorized`.

Maximum encoded request size: `8192` bytes.

### 7.2 `SandboxDataDirectoryDescriptor`

Exact fields in this order:

1. `data_dir_tag` — exact `l28-disposable-test`
2. `environment` — exact `DISPOSABLE_TEST`
3. `network_id` — exact `l28-disposable-test/v0.1`
4. `chain_id` — 64 lowercase hex; MUST equal F39/F45
5. `genesis_digest` — 64 lowercase hex; MUST equal F39/F45
6. `instance_id` — string; MUST be 64 lowercase hex at schema time
7. `exclusive_ownership` — boolean (required); semantic exclusivity is enforced
   at §8 step 17, not by restricting the boolean domain at schema time
8. `path_lexeme` — non-empty string; lexical path claim for later
   implementation (no filesystem access in Foundation 46)

Wrong types, missing sandbox fields, wrong sandbox field order, non-hex
`instance_id`, and empty `path_lexeme` fail at §8 step 16 with
`sandbox_descriptor_invalid` (not `ownership_collision`). Foundation 46 MUST
NOT create, open, stat, follow, wipe, or delete `path_lexeme`.

### 7.3 Path-safety requirements (lexical; later implementation)

A conforming future evaluator MUST reject `path_lexeme` when any of the
following lexical rules match (fail with `sandbox_descriptor_invalid`):

1. Empty string or whitespace-only.
2. Filesystem root forms: `/`, `\`, or equivalent root-only lexemes.
3. Repository-root relative forms: `.`, `./`, or empty-relative claims.
4. Home-directory forms: `~`, `~/…`, or `%USERPROFILE%` / `$HOME` expansions as
   literal prefixes.
5. Traversal sequences: `..` path segments.
6. Untagged / ambiguous disposable claims: path lexeme does not contain the
   exact path segment `l28-disposable-test` (segment split on `/` and `\`;
   logical tag presence check only).
7. Labels indicating production, historical, canonical, shared, or MAIN
   directories as path segments (case-sensitive segment match against
   `MAIN`, `CANONICAL`, `HISTORICAL`, `PRODUCTION`, `shared`).

Foundation 46 MUST NOT claim that lexical validation can detect filesystem
symlinks. No “symlink-ambiguous” lexical rejection exists in this profile.

**Normative warning:** Lexical validation alone does **not** prove filesystem
safety. Later sandbox-directory creators MUST perform real filesystem checks
before any create/use, including at minimum: existence policy, symlink
resolution, symlink-component detection, containment under an approved parent,
canonical-path verification, and exclusive create. Those checks remain outside
Foundation 46. Foundation 46 MUST NOT claim they are satisfied.

### 7.4 Exclusive ownership and collision rejection

1. At sandbox structural validation, `exclusive_ownership` MUST be a boolean
   and `instance_id` MUST be a 64 lowercase hex string. Wrong type, missing
   field, or malformed hex fails with `sandbox_descriptor_invalid` per §8
   step 16 — never with `ownership_collision`.
2. After the sandbox descriptor is structurally valid, `ownership_collision`
   applies when either:
   - `exclusive_ownership` is boolean `false` (structurally valid non-exclusive
     claim); or
   - `instance_id` equals the all-zero digest
     `0000000000000000000000000000000000000000000000000000000000000000`
     (prohibited null-instance sentinel).
3. Successful preflight requires `exclusive_ownership=true` and a non-zero
   `instance_id`.
4. Within one request, only one `sandbox` object is permitted in v0.1. A future
   multi-sandbox extension MUST reject colliding `instance_id` values with
   `ownership_collision`.
5. `data_dir_tag` MUST equal `l28-disposable-test` and MUST bind with the
   identity tuple in §6.4.

Foundation 46 does not consult an external registry. Collision rules are
request-local and structural.

### 7.5 `CoreEntrypointResult`

Every result MUST include at least these fields:

| Field | Rule |
|---|---|
| `ok` | `true` only when preflight succeeds |
| `code` | Stable code from §9 |
| `entrypoint_version` | See explicit recovery rules immediately below |
| `environment` | `DISPOSABLE_TEST` on success; else recovered or empty |
| `network_id` | From accepted evidence on success; else empty |
| `chain_id` | From accepted evidence on success; else empty |
| `genesis_digest` | From accepted evidence on success; else empty |
| `protocol_version` | From accepted evidence on success; else empty |
| `identity_report_id` | From accepted F39 evidence on success; else empty |
| `lifecycle_policy_version` | From accepted F45 evidence on success; else empty |
| `lifecycle_resulting_state` | `DISPOSABLE_TEST_READY` on success; on `reserved_state_unreachable` or `lifecycle_state_invalid`, the first offending recovered state string; otherwise empty |
| `sandbox_instance_id` | From accepted sandbox on success; else empty |
| `preflight_ok` | boolean `true` only on success; else `false` |
| `process_launch_authorized` | MUST be boolean `false` on every path |
| `execution_authorized` | MUST be boolean `false` on every path |
| `report_id` | 64 lowercase hex content-derived id on success; empty string on failure |
| `detail` | MUST be empty string in v0.1 |

`entrypoint_version` recovery (references §8 validation precedence):

1. On success (§8 step 21): exact
   `l28-disposable-core-process-entrypoint/v0.1`.
2. On `entrypoint_version_unsupported` (§8 step 6): echo the recovered string
   value of request `entrypoint_version` when it was parsed as a string;
   otherwise empty.
3. On any failure at §8 steps 7–20 after a conforming string
   `entrypoint_version` was accepted at step 6: exact profile string
   `l28-disposable-core-process-entrypoint/v0.1`.
4. On failures at §8 steps 1–5 (before a typed `entrypoint_version` is
   available): empty string.

No `admission_authorized` field exists in this profile.

### 7.6 Content-derived `report_id` (success only)

On success only, `report_id` MUST be the lowercase hex SHA-256 digest of the
canonical JSON serialization of the accepted request object with:

- exact field order from §7.1 / §7.2 / nested projection orders;
- no insignificant whitespace;
- UTF-8 encoding.

Identical accepted request bytes MUST yield identical `report_id` values.
Failures MUST NOT invent a content digest (empty `report_id`).

## 8. Deterministic first-failure validation precedence

A conforming future evaluator MUST stop at the first failure:

1. Reject unsupported payload type (`input_type_invalid`).
2. Reject encoded size `>` `8192` bytes (`input_too_large`).
3. Reject invalid UTF-8 (`encoding_invalid`).
4. Reject malformed JSON, non-finite numbers, duplicate keys, or non-object
   top-level (`json_invalid` / `duplicate_key` / `invalid_top_level`).
5. Reject missing/unknown/reordered/wrong-type **top-level or nested request
   fields that are not otherwise assigned below** (`schema_invalid`). Nested
   Foundation 39/45/sandbox objects that are present but fail their dedicated
   steps use those later codes instead of double-counting here once the outer
   request shape is accepted.
6. Reject unsupported `entrypoint_version`
   (`entrypoint_version_unsupported`).
7. If `environment` ∈ `{MAIN, CANONICAL, HISTORICAL, PRODUCTION}`, fail with
   `historical_import_forbidden`.
8. Else if `environment` ≠ `DISPOSABLE_TEST`, fail with `environment_invalid`.
9. If request `execution_authorized` is not boolean `false`, fail with
   `execution_authorized_invalid`.
10. If request `process_launch_authorized` is not boolean `false`, fail with
    `process_launch_authorized_invalid`.
11. If `admission_authorized` is present anywhere in the request, fail with
    `schema_invalid`.
12. Validate Foundation 39 projection (structural and success equality per
    §6.1); on failure `identity_evidence_invalid`.
13. Validate Foundation 45 projection **structure / types / required fields /
    status codes** per §6.2.1 only; on failure
    `lifecycle_policy_evidence_invalid`.
    This step MUST NOT classify lifecycle state values.
14. Classify Foundation 45 lifecycle state fields per §6.2.2: if any of
    `previous_state`, `requested_state`, or `resulting_state` is
    `CANONICAL_READY_RESERVED` or `RUNNING_RESERVED`, fail with
    `reserved_state_unreachable`.
15. Else if those lifecycle fields are not exactly the §6.2.2 success triple
    (`CREATED`, `DISPOSABLE_TEST_READY`, `DISPOSABLE_TEST_READY`), fail with
    `lifecycle_state_invalid`.
16. Sandbox descriptor structural/tag/path-lexeme failures
    (`sandbox_descriptor_invalid`), including wrong types for sandbox fields,
    non-hex `instance_id`, non-boolean `exclusive_ownership`, empty/unsafe
    `path_lexeme` per §7.3, and local tag/environment/network_id constants
    required by §7.2 (exact `data_dir_tag`, `environment`, `network_id`).
17. Ownership collision after structural sandbox acceptance
    (`ownership_collision`): structurally valid `exclusive_ownership=false`,
    or all-zero `instance_id` sentinel (§7.4).
18. Cross-evidence identity/lineage mismatch per §6.4 → `evidence_mismatch`.
19. `process_intent` constraint failure → `process_intent_invalid`.
20. Unexpected evaluator exception → `internal_error` with empty `detail`.
21. Otherwise success: `ok=true`, `code=preflight_ok`, `preflight_ok=true`,
    `process_launch_authorized=false`, `execution_authorized=false`.

Steps 13, 14, and 15 are mutually exclusive by construction: step 13 never
emits lifecycle classification codes; steps 14–15 run only after §6.2.1
success; step 14 precedes step 15 and consumes reserved values first.
Steps 16 and 17 are mutually exclusive for ownership booleans: non-boolean
`exclusive_ownership` fails at step 16; boolean `false` fails at step 17.

## 9. Stable codes

### 9.1 Reused upstream values

These strings keep their upstream meanings. Foundation 46 does **not** create or
own them; it compares or returns them by value only.

| Code / value | Source | Role inside F46 |
|---|---|---|
| `ok` | Foundation 39 | Required F39 projection `code` on success |
| `transitioned` | Foundation 21 / 45 | Required F45 projection `code` on success |
| Foundation 21 state names | Foundation 21 | Compared structurally in §6.2.2 |
| `reserved_state_unreachable` | Foundation 21 | Existing F21 stable string reused by value as the Foundation 46 **result** `code` when §8 step 14 fires |

### 9.2 Foundation 46–defined validation codes

| Code | Meaning |
|---|---|
| `preflight_ok` | Request satisfies this offline preflight contract |
| `input_type_invalid` | Payload type is not JSON text/bytes |
| `input_too_large` | Encoded size exceeds `8192` bytes |
| `encoding_invalid` | Invalid UTF-8 |
| `json_invalid` | Malformed JSON / non-finite number |
| `duplicate_key` | Duplicate JSON object key |
| `invalid_top_level` | Top-level value is not an object |
| `schema_invalid` | Missing/unknown/reordered/wrong-type fields or forbidden field present |
| `entrypoint_version_unsupported` | `entrypoint_version` is not this profile |
| `environment_invalid` | Environment is not `DISPOSABLE_TEST` (generic) |
| `historical_import_forbidden` | Environment is MAIN/CANONICAL/HISTORICAL/PRODUCTION |
| `execution_authorized_invalid` | `execution_authorized` is not boolean `false` |
| `process_launch_authorized_invalid` | `process_launch_authorized` is not boolean `false` |
| `identity_evidence_invalid` | Malformed/missing/failed F39 projection |
| `lifecycle_policy_evidence_invalid` | F45 structural/type/required-field/status-code failure (§6.2.1) |
| `evidence_mismatch` | Cross-evidence identity/lineage mismatch (§6.4) |
| `lifecycle_state_invalid` | Well-formed unsupported non-reserved lifecycle values (§6.2.2) |
| `sandbox_descriptor_invalid` | Sandbox descriptor or path-lexeme lexical failure |
| `ownership_collision` | Structurally valid non-exclusive claim or all-zero `instance_id` |
| `process_intent_invalid` | `process_intent` constraints failed |
| `internal_error` | Sanitized unexpected failure |

**Inventory:**

| Class | Count |
|---|---:|
| Foundation 46–defined result codes (including success) | 21 |
| Foundation 21 string reused by value as a result code | 1 (`reserved_state_unreachable`) |
| **Distinct result `code` values under this profile** | **22** |

### 9.3 Concrete reachability (normative)

Every distinct result `code` MUST be producible by a concrete offline request
(or narrow fault injection for `internal_error`) under §8:

| Result `code` | Concrete first-failure input |
|---|---|
| `input_type_invalid` | Non-`str`/non-`bytes` evaluator argument |
| `input_too_large` | UTF-8 JSON larger than `8192` bytes |
| `encoding_invalid` | Invalid UTF-8 byte sequence |
| `json_invalid` | Truncated JSON object |
| `duplicate_key` | JSON object with duplicated key |
| `invalid_top_level` | JSON array top-level |
| `schema_invalid` | Missing top-level field, or `admission_authorized` present |
| `entrypoint_version_unsupported` | Foreign `entrypoint_version` string |
| `historical_import_forbidden` | `environment=MAIN` (also CANONICAL/HISTORICAL/PRODUCTION) |
| `environment_invalid` | `environment=OTHER` |
| `execution_authorized_invalid` | Request `execution_authorized=true` |
| `process_launch_authorized_invalid` | Request `process_launch_authorized=true` |
| `identity_evidence_invalid` | F39 `ok=false` or wrong field order/types |
| `lifecycle_policy_evidence_invalid` | F45 missing field, wrong type, `ok=false`, or `code≠transitioned` |
| `reserved_state_unreachable` | Structurally valid F45 with `requested_state=RUNNING_RESERVED` (or other reserved state field) |
| `lifecycle_state_invalid` | Structurally valid F45 with `previous_state=PAUSED` (non-reserved, non-success triple) |
| `sandbox_descriptor_invalid` | `path_lexeme="/"` or missing `l28-disposable-test` segment |
| `ownership_collision` | `exclusive_ownership=false` **or** all-zero `instance_id` |
| `evidence_mismatch` | F39/F45/sandbox `chain_id` differ after steps 12–17 success |
| `process_intent_invalid` | `process_intent.transport_enabled=true` |
| `internal_error` | Narrow evaluator fault injection |
| `preflight_ok` | Fully conforming DISPOSABLE_TEST request |

### Authority fields (always false)

| Field | Normative value |
|---|---|
| `execution_authorized` | Always `false` |
| `process_launch_authorized` | Always `false` |
| `admission_authorized` | Must not exist |

Distinguish carefully:

- `preflight_ok` / `code=preflight_ok` = specification contract satisfied;
- process runnable = **not** granted by this profile;
- process launched = **not** performed or authorized;
- execution authorized = **always false**;
- admission authorized = **undefined and forbidden**.

## 10. Determinism, idempotency, limits, and exceptions

1. Identical request bytes MUST produce identical results.
2. Evaluation MUST NOT read wall-clock time, randomness, PID, hostname, port,
   environment variables, or runtime process tables.
3. Evaluation MUST NOT mutate repository state, filesystem state, lifecycle
   model state, or external state.
4. Repeated evaluation of the same request is idempotent and side-effect free.
5. Maximum request size: `8192` bytes.
6. Hex digest fields MUST match `^[0-9a-f]{64}$`.
7. Unexpected exceptions MUST map to `internal_error` with `detail=""`.
8. No timestamps appear in request or result schemas for v0.1.

### Success postconditions

- `ok=true`
- `code=preflight_ok`
- `preflight_ok=true`
- `process_launch_authorized=false`
- `execution_authorized=false`
- `lifecycle_resulting_state=DISPOSABLE_TEST_READY`
- `report_id` is the content-derived digest
- no process created; no directory created; no model mutated

### Failure postconditions

- `ok=false`
- `preflight_ok=false`
- `process_launch_authorized=false`
- `execution_authorized=false`
- `report_id=""`
- `detail=""`
- first-failure stable `code` from §8
- no process created; no directory created; no model mutated

## 11. Environment rules

1. Request `environment` MUST be exact `DISPOSABLE_TEST`.
2. Sandbox `environment` MUST be exact `DISPOSABLE_TEST`.
3. `MAIN`, `CANONICAL`, `HISTORICAL`, and `PRODUCTION` are forbidden
   (`historical_import_forbidden`).
4. Any other non-`DISPOSABLE_TEST` value fails with `environment_invalid`.
5. Foundation 46 MUST NOT authorize MAIN or production operation.

## 12. Future acceptance-test traceability

A conforming future evaluator suite MUST include at least:

1. **Valid DISPOSABLE_TEST request** — returns `preflight_ok` with both
   authority flags false.
2. **MAIN/CANONICAL rejection** — `historical_import_forbidden`.
3. **Malformed F39 evidence** — `identity_evidence_invalid`.
4. **Malformed F45 structure** — missing/reordered/wrong-type F45 field or
   `ok=false` / `code≠transitioned` → `lifecycle_policy_evidence_invalid`
   (must not emit lifecycle classification codes).
5. **Reserved lifecycle state** — structurally valid F45 with a reserved state
   in `previous_state`, `requested_state`, or `resulting_state` →
   `reserved_state_unreachable` (must not emit
   `lifecycle_policy_evidence_invalid` or `lifecycle_state_invalid`).
6. **Unsupported non-reserved lifecycle state** — structurally valid F45 with
   e.g. `previous_state=PAUSED` → `lifecycle_state_invalid` (must not emit
   `lifecycle_policy_evidence_invalid` or `reserved_state_unreachable`).
7. **Identity/genesis/protocol mismatch** — `evidence_mismatch` after
   successful steps 12–17 (F39, F45 lifecycle classification, and sandbox
   structure/ownership).
8. **Environment rejection** — MAIN/CANONICAL/HISTORICAL/PRODUCTION and generic
   non-disposable values as in §8 steps 7–8.
9. **Reserved operational states remain unreachable** — no success path yields
   `CANONICAL_READY_RESERVED` or `RUNNING_RESERVED` as
   `lifecycle_resulting_state` on `preflight_ok`.
10. **`execution_authorized` always false** — asserted on all result codes.
11. **`process_launch_authorized` always false** — asserted on all result codes.
12. **No admission-authority expansion** — `admission_authorized` absent /
    rejected via `schema_invalid`.
13. **Deterministic repeated evaluation** — identical bytes → identical results.
14. **Injected lifecycle model unchanged** — if a future evaluator accepts an
    optional model for hygiene, it is not mutated on success or failure.
15. **Sandbox descriptor and unsafe-path rejection** —
    `sandbox_descriptor_invalid` for empty/root/home/traversal/untagged/
    production-segment path lexemes.
16. **Structurally valid non-exclusive ownership** —
    `exclusive_ownership=false` → `ownership_collision` (must not emit
    `schema_invalid` or `sandbox_descriptor_invalid` for that boolean value).
17. **All-zero instance identifier** — zero `instance_id` sentinel →
    `ownership_collision`.
18. **Deferred filesystem symlink verification** — document/assert that F46
    performs no symlink detection; lexical success is not FS-safety proof;
    symlink resolution remains outside this profile (§7.3).
19. **Oversized input** — `input_too_large`.
20. **Exception containment** — `internal_error` with empty `detail`.
21. **No process/subprocess/thread/async/signal/service creation** — static and
    behavioral hygiene.
22. **No filesystem create/inspect/mutate/reset/wipe/delete** — hygiene.
23. **No socket/transport/sync/discovery/network activity** — hygiene.
24. **No wallet/key/ledger/transaction/consensus/mining/issuance/reward/tip
    authority** — hygiene.
25. **No economic-fact changes** — assert Protocol v1.0.0 constants unchanged.
26. **No `coin/l28_coin.py` dependency** — static hygiene.
27. **No Leap28 or Nova coupling** — static hygiene.
28. **Distinct result-code reachability** — every code in §9.3 is demonstrated
    through the public API (`internal_error` via narrow fault injection), with
    no impossible shadowing between steps 13–15 or 16–17.

## 13. Explicit deferred work

Foundation 46 MUST NOT and does not specify:

- production implementation or package exports;
- callable/CLI entrypoint implementation;
- process creation, supervision, signals, threads, async workers, daemons,
  services, or containers;
- environment-variable or OS-specific launch behavior;
- filesystem creation, realpath verification, symlink resolution, or
  symlink-component detection;
- shutdown, reset, cleanup, or deletion (F37-13 / F37-05);
- wallet availability;
- tip authority and issuance acknowledgement wiring;
- transport and synchronization (M3+);
- MAIN or production operation;
- Foundation 40–43 admission evidence.

## 14. Explicit prohibited capabilities

- No production code or tests in this milestone.
- No executable Core entrypoint or CLI.
- No sockets, ports, networking, discovery, transport, synchronization, or
  propagation.
- No wallet, keys, signing, transactions, ledger mutation, consensus, mining,
  issuance, rewards, supply changes, or tip selection.
- No F21 transition changes or parallel lifecycle state machine.
- No modification of Foundations 21 or 38–45.
- No use or modification of `coin/l28_coin.py`.
- No Leap28 or Nova coupling.
- No historical evidence migration, rewriting, or deletion.
- No installation, deployment, or service activation.

## 15. Protected economic facts and prohibited coupling

Foundation 46 MUST NOT alter, recalculate, reinterpret, migrate, mint, simulate,
or overwrite:

| Fact | Value |
|---|---:|
| Hard cap | `28_000_000` L28 |
| Emission ceiling | `11_130_000` L28 |
| Historically mined | `2_824_584` L28 |
| Treasury locked | `500_000` L28 |
| Circulating snapshot | `2_324_584` L28 |
| Halving interval | `210_000` |
| Reward sequence | `28 → 14 → 7 → 3 → 1 → 0` |
| Historical mined-through entry | `100_877` |
| Next canonical height after bootstrap | `100_878` |

Evidence baselines include `coin/tx_validation.py` Protocol constants,
`docs/m2m/protocol_v0.1.md`, and
`docs/l28_historical_continuity_manifest_v0.1.json`.

Prohibited coupling: Leap28, Nova, MAIN runtime activation, historical import as
live genesis, canonical continuation, and revival or extension of
`coin/l28_coin.py`.

## 16. Smallest authorized future implementation follow-up

If Foundation 46 is locked, a later implementation foundation MAY implement
**only**:

1. An offline pure evaluator module for this profile;
2. Focused acceptance tests covering §12;
3. A narrow implementation record document.

That implementation MUST keep `execution_authorized=false` and
`process_launch_authorized=false` on every path, MUST NOT spawn processes, MUST
NOT create or wipe directories, MUST NOT import Foundations 40–43, and MUST NOT
modify `coin/l28_coin.py`.

Actual runnable process isolation remains a separate later F37-06 remediation
step after the offline evaluator exists.

## Security boundary and non-authorization statement

A completed Foundation 46 specification, and any later successful offline
evaluation under this profile, is disposable Core entrypoint **preflight
evidence** only. It is not permission to spend L28, not an executable
transaction, not ledger mutation, not peer admission, not process creation, not
filesystem mutation, and not authorization to start a node, network, miner,
wallet, or testnet.

`execution_authorized` MUST remain the JSON boolean `false` on every conforming
request and every success or failure result path.

`process_launch_authorized` MUST remain the JSON boolean `false` on every
conforming request and every success or failure result path.
