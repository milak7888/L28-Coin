# L28 Disposable Sandbox Directory Creation Plan Specification v0.1

**Foundation:** 48

**Status:** Offline specification only; non-activation

**Milestone label:** F37-06 exclusive disposable sandbox directory creation-plan
contract (partial slice; specification only)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN) — immutable

**Profile:** `l28-disposable-sandbox-directory-creation/v0.1`

## 1. Purpose, status, terminology, and non-goals

Foundation 48 defines the locked offline specification for an **exclusive
disposable sandbox data-directory creation plan**: a deterministic, fail-closed,
immutable request/result schema that decides whether a proposed creation plan is
**structurally plan-valid** when bound to caller-supplied frozen Foundation 47
preflight-success evidence, an accepted sandbox descriptor, and creation-intent
constraints.

This foundation is a **partial M2 / F37-06 specification slice**. It does
**not** create, inspect, mutate, wipe, or delete directories; does **not**
authorize filesystem mutation or process launch; does **not** complete F37-06,
F37-13, or Foundation 37 M2.

### Terminology

| Term | Meaning in this specification |
|---|---|
| Creation plan (F48) | Offline immutable request/result contract for exclusive sandbox directory creation intent |
| Plan-valid / `creation_plan_ok` | Request satisfies this specification’s structural and binding rules only |
| Frozen F47 preflight-success evidence | Exact Foundation 47 success result projection (`ok=true`, `code=preflight_ok`, …) supplied by the caller |
| Sandbox descriptor | Immutable logical ownership claim fields from Foundation 46 §7.2, carried forward for plan binding |
| Path lexeme | Opaque caller-supplied path string carried in the sandbox descriptor; not validated by reapplying Foundation 46 §7.3 lexical rules in this profile |
| Deferred filesystem obligation | Mandatory future check/create rule that a later authorized creator MUST perform; never claimed as executed by F48 |
| Future evaluator | Later Foundation 49-class pure in-memory evaluator of this contract |
| Future filesystem creator | Still-later component that MAY perform exclusive create only under a separate authorization foundation |

### Non-goals

Foundation 48 MUST NOT and does not:

- implement a callable evaluator, CLI, or package export;
- perform filesystem access, `stat`, `realpath`, symlink resolution, `mkdir`,
  wipe, cleanup, or any mutation;
- spawn processes, threads, async workers, subprocesses, daemons, services, or
  containers;
- open sockets or perform transport, discovery, synchronization, or propagation;
- authorize spend, admission, mining, consensus, tip authority, issuance, or
  deployment;
- duplicate or reinterpret Foundation 46 §7.3 lexical path validation;
- rerun Foundation 39, 45, or 47 evaluation;
- call Foundation 21 `transition` or define another lifecycle state machine;
- depend on Foundations 40–43;
- modify or revive `coin/l28_coin.py`;
- claim F37-06, F37-13, or M2 completion.

### Non-authority statement

A conforming Foundation 48 evaluation, and any later successful evaluation under
this profile:

- MUST set `execution_authorized` to the JSON/boolean `false` on every path;
- MUST set `process_launch_authorized` to the JSON/boolean `false` on every
  path;
- MUST NOT define, require, or grant `admission_authorized`;
- MUST NOT define, require, or grant `filesystem_create_authorized` or any other
  true-able authority field;
- MUST NOT mean that a directory exists, was created, may be created now, or is
  filesystem-safe;
- MUST NOT mean that a process is runnable, launched, admitted, canonical,
  synchronized, or authorized;
- MUST NOT mutate a Foundation 21 lifecycle model, filesystem, network, wallet,
  ledger, or any external state;
- is offline disposable sandbox directory **creation-plan evidence** only.

Success means only: the proposed creation plan satisfies this specification
contract structurally.

## 2. Roadmap relationship and dependency boundaries

### Roadmap citations

| Source | Citation |
|---|---|
| F37-06 Node lifecycle and process isolation | `docs/bounded_testnet_readiness_gap_audit_v0.1.md` § F37-06 |
| F37-05 Deterministic ledger replay / data-dir lifecycle | same document — § F37-05 |
| F37-13 Observability, shutdown, reset, and cleanup | same document — § F37-13 |
| F37 M2 broader scope | same document — Smallest safe isolated-testnet sequence — M2 row |
| F46 deferred exclusive sandbox creation | `docs/foundation46_disposable_core_process_entrypoint_spec_v0.1.md` §2, §4, §7.2–§7.4, §13, §16 |
| F47 preflight evaluator boundary | `docs/foundation47_disposable_core_process_entrypoint_implementation_v0.1.md` |
| F38 `data_dir_tag` / later wipe rules | `docs/disposable_network_identity_genesis_binding_v0.1.md` — Binding configuration / Reset, cleanup |

### Explicit F37-06 alignment

F37-06 requires a disposable-test-only Core process entrypoint with sandbox data
dirs (`docs/bounded_testnet_readiness_gap_audit_v0.1.md` § F37-06). Foundation
46 locked the offline preflight contract; Foundation 47 implemented that
evaluator. Foundation 48 locks only the **offline creation-plan contract** that
binds frozen Foundation 47 success evidence to exclusive sandbox creation intent
and deferred filesystem-safety obligations.

Actual directory creation, realpath/symlink enforcement, process launch, and
reset/wipe tooling remain deferred. Foundation 48 MUST NOT claim F37-06, F37-13,
or Foundation 37 M2 complete. This non-completion claim is normative.

### Prerequisites consumed (frozen evidence only)

| Prerequisite | How Foundation 48 consumes it |
|---|---|
| Foundation 47 preflight success | Frozen success result projection; structural equality only |
| Foundation 46 sandbox descriptor shape | Field order and constant bindings; **no** reapplication of §7.3 lexical reject matrix |
| Foundations 38/39 identity constants | Compared by value via the frozen F47 projection and sandbox constants |
| Foundations 44/45 lifecycle evidence | Already accepted inside frozen F47 success; not re-evaluated |
| Foundation 21 lifecycle authority | Not invoked; F48 never calls `transition` |

### Explicitly out of Foundation 48

| Later work | Owner / milestone |
|---|---|
| Callable evaluator of this contract | Future Foundation 49-class implementation |
| Actual exclusive directory create / verify | Later filesystem-creator foundation (post-F48) |
| Process launch / supervision | Later F37-06 process implementation |
| Ephemeral ledger layout / reset semantics | F37-05 (depends on F37-06) |
| Stop / reset / cleanup / wipe tooling | F37-13 (depends on F37-06 + owned disposable dirs) |
| Tip authority, wallets, issuance wiring | Later M2 slices |
| Transport / sync | M3+ (F37-07) |
| Peer-admission evidence | Foundations 40–43 — **excluded** |

## 3. Specification versus future implementation

| Layer | Role |
|---|---|
| Foundation 48 (this document) | Normative schemas, precedence, codes, deferred obligations, exclusions |
| Future evaluator (Foundation 49-class) | Pure in-memory evaluation of this contract; MUST NOT spawn or touch the filesystem |
| Future filesystem creator | May create a directory only under a later authorized foundation; never implied by F48 success |
| Foundation 21 | Sole Core lifecycle state/transition authority |
| Foundations 38/39 | Sole disposable identity/genesis verification authority |
| Foundations 44/45 | Sole offline Core lifecycle-policy authority |
| Foundations 46/47 | Sole offline entrypoint preflight contract / evaluator |
| Foundations 40–43 | Not used by this profile |

Foundation 48 MUST NOT duplicate or reinterpret Foundation 39 cryptography,
Foundation 45 policy evaluation, Foundation 47 preflight evaluation, or
Foundation 46 §7.3 lexical path validation. It performs **structural and
equality checks only** on frozen projections and plan fields.

## 4. Authority and ownership matrix

| Concern | Owner |
|---|---|
| Constructs and retains evidence projections | Caller |
| Core states, allowed transitions, transition codes | Foundation 21 |
| Disposable identity/genesis verification | Foundations 38/39 |
| Offline Core lifecycle-policy evaluation | Foundations 44/45 |
| Offline entrypoint preflight contract / evaluator | Foundations 46/47 |
| Offline exclusive sandbox **creation-plan** contract | **Foundation 48 (this document)** |
| Future in-memory evaluator of this contract | Later Foundation 49-class implementation |
| Future exclusive sandbox directory create/verify | Later filesystem-creator foundation (not this document) |
| Future process create/supervise/stop execution | Later F37-06 process implementation |
| Tagged disposable directory wipe / cleanup | Later F37-13 |
| Ephemeral data-dir layout / replay reset rules | Later F37-05 |
| Peer handshake / admission envelopes | Foundations 40–43 (excluded here) |
| Economics / supply / rewards | Protocol v1.0.0 / existing validators (unchanged) |

### Forbidden authority

Foundation 48 grants **no**:

- admission authority (`admission_authorized` absent and forbidden);
- filesystem-create authority (`filesystem_create_authorized` absent; no substitute true-able create flag);
- execution authority (`execution_authorized` always false);
- process-launch authority (`process_launch_authorized` always false);
- ledger, wallet, mining, network, deployment, or MAIN/production authority.

Foundation 48 owns **no** process handle, filesystem directory, socket, wallet,
ledger, miner, or external resource.

## 5. Normative constants

| Constant | Exact value |
|---|---|
| Profile / `creation_profile` | `l28-disposable-sandbox-directory-creation/v0.1` |
| Upstream entrypoint profile | `l28-disposable-core-process-entrypoint/v0.1` |
| Environment | `DISPOSABLE_TEST` |
| Network id | `l28-disposable-test/v0.1` |
| Protocol version | `l28-protocol/1.0.0` |
| Data-dir tag | `l28-disposable-test` |
| Lifecycle policy version (inside frozen F47 evidence) | `l28-disposable-core-process-lifecycle-policy/v0.1` |
| Accepted F47 result code | `preflight_ok` |
| Accepted lifecycle resulting state | `DISPOSABLE_TEST_READY` |
| Maximum encoded request size | `8192` bytes |
| Zero instance sentinel | `0000000000000000000000000000000000000000000000000000000000000000` |
| Forbidden environments | `MAIN`, `CANONICAL`, `HISTORICAL`, `PRODUCTION` |

## 6. Frozen Foundation 47 success projection

### 6.1 Exact field order

`preflight_evidence` MUST be a JSON object with **exactly** these fields in this
order (no extras, no omissions, no reordering):

1. `ok` — boolean `true`
2. `code` — exact `"preflight_ok"`
3. `entrypoint_version` — exact `"l28-disposable-core-process-entrypoint/v0.1"`
4. `environment` — exact `"DISPOSABLE_TEST"`
5. `network_id` — exact `"l28-disposable-test/v0.1"`
6. `chain_id` — 64 lowercase hexadecimal characters
7. `genesis_digest` — 64 lowercase hexadecimal characters
8. `protocol_version` — exact `"l28-protocol/1.0.0"`
9. `identity_report_id` — 64 lowercase hexadecimal characters
10. `lifecycle_policy_version` — exact `"l28-disposable-core-process-lifecycle-policy/v0.1"`
11. `lifecycle_resulting_state` — exact `"DISPOSABLE_TEST_READY"`
12. `sandbox_instance_id` — 64 lowercase hexadecimal characters and MUST NOT equal
    the zero instance sentinel
13. `preflight_ok` — boolean `true`
14. `process_launch_authorized` — boolean `false`
15. `execution_authorized` — boolean `false`
16. `report_id` — 64 lowercase hexadecimal characters
17. `detail` — exact empty string `""`

### 6.2 Structural-only consumption

Foundation 48:

- MUST treat this object as caller-supplied frozen evidence;
- MUST NOT call Foundation 47 `evaluate_core_entrypoint_preflight_json`;
- MUST NOT re-validate Foundation 39 or Foundation 45 projections;
- MUST NOT call Foundation 21 `transition`;
- MUST reject any deviation from §6.1 with `preflight_evidence_invalid`.

## 7. Request and result schemas

### 7.1 `SandboxCreationPlanRequest`

Exact top-level fields in this order:

1. `creation_profile` — string; MUST equal this profile (§5)
2. `environment` — string; MUST equal `DISPOSABLE_TEST` after forbidden-label
   rejection (§8)
3. `preflight_evidence` — frozen Foundation 47 success projection (§6.1)
4. `sandbox` — `SandboxDataDirectoryDescriptor` (§7.2)
5. `creation_intent` — `CreationIntent` (§7.3)
6. `execution_authorized` — boolean; MUST be `false`
7. `process_launch_authorized` — boolean; MUST be `false`

Forbidden authority-bearing fields: any `admission_authorized` field at any
nesting depth; any `filesystem_create_authorized` field at any nesting depth;
any true value for `execution_authorized` or `process_launch_authorized`.

Maximum encoded size: `8192` bytes.

### 7.2 `SandboxDataDirectoryDescriptor`

Exact fields in this order (shape aligned with Foundation 46 §7.2; **not** a
re-lock of Foundation 46 §7.3 lexical reject rules):

1. `data_dir_tag` — exact `l28-disposable-test`
2. `environment` — exact `DISPOSABLE_TEST`
3. `network_id` — exact `l28-disposable-test/v0.1`
4. `chain_id` — 64 lowercase hex; MUST equal `preflight_evidence.chain_id`
5. `genesis_digest` — 64 lowercase hex; MUST equal `preflight_evidence.genesis_digest`
6. `instance_id` — 64 lowercase hex; MUST equal
   `preflight_evidence.sandbox_instance_id` and MUST NOT be the zero sentinel
7. `exclusive_ownership` — boolean `true`
8. `path_lexeme` — non-empty string (after stripping is **not** required; empty
   or whitespace-only string fails plan validation)

Foundation 48 MUST NOT:

- reapply Foundation 46 §7.3 lexical rejection cases (root, home, traversal,
  forbidden segments, tag-segment presence matrix, etc.);
- claim that accepting `path_lexeme` proves filesystem safety;
- create, open, `stat`, follow, wipe, or delete `path_lexeme`.

`path_lexeme` is carried forward as an opaque plan field for a later filesystem
creator that MUST apply §10 deferred obligations.

### 7.3 `CreationIntent`

Exact fields in this order:

1. `create_mode` — exact `"exclusive_create_new"`
2. `existing_path_policy` — exact `"reject"`
3. `symlink_policy` — exact `"reject"`
4. `cleanup_ownership` — exact `"tagged_disposable_only"`
5. `deferred_filesystem_obligations` — boolean `true`

These values encode **plan constraints and deferred-obligation acknowledgement**
only. They do **not** authorize filesystem mutation. In particular,
`deferred_filesystem_obligations=true` means “later creator MUST honor §10”; it
MUST NOT be interpreted as “filesystem checks were performed” or “create is
authorized now”.

### 7.4 `SandboxCreationPlanResult`

Every result MUST include at least these fields:

| Field | Rule |
|---|---|
| `ok` | `true` only when the creation plan succeeds |
| `code` | Stable code from §9 |
| `creation_profile` | See recovery rules below |
| `environment` | `DISPOSABLE_TEST` on success; else recovered or empty |
| `network_id` | From accepted evidence on success; else empty |
| `chain_id` | From accepted evidence on success; else empty |
| `genesis_digest` | From accepted evidence on success; else empty |
| `protocol_version` | From accepted evidence on success; else empty |
| `preflight_report_id` | From accepted F47 evidence `report_id` on success; else empty |
| `sandbox_instance_id` | From accepted sandbox on success; else empty |
| `path_lexeme` | From accepted sandbox on success; else empty |
| `creation_plan_ok` | boolean `true` only on success; else `false` |
| `process_launch_authorized` | MUST be boolean `false` on every path |
| `execution_authorized` | MUST be boolean `false` on every path |
| `report_id` | 64 lowercase hex content-derived id on success; empty string on failure |
| `detail` | MUST be empty string in v0.1 |

`creation_profile` recovery (references §8 validation precedence):

1. On success (§8 final step): exact
   `l28-disposable-sandbox-directory-creation/v0.1`.
2. On `creation_profile_unsupported`: echo the recovered string value of request
   `creation_profile` when it was parsed as a string; otherwise empty.
3. On any failure after a conforming string `creation_profile` was accepted:
   exact profile string `l28-disposable-sandbox-directory-creation/v0.1`.
4. On failures before a typed `creation_profile` is available: empty string.

No `admission_authorized` field exists in this profile.
No `filesystem_create_authorized` field exists in this profile.

### 7.5 Content-derived `report_id` (success only)

On success only, `report_id` MUST be the lowercase hex SHA-256 digest of the
canonical JSON serialization of the accepted request object with:

- exact field order from §7.1 / §7.2 / §7.3 / §6.1;
- compact separators (`,` and `:`);
- no insignificant whitespace;
- `sort_keys=false` (order is schema order, not lexicographic sort);
- `ensure_ascii=false`;
- `allow_nan=false`;
- UTF-8 encoding of that JSON text;
- SHA-256 over those UTF-8 bytes;
- lowercase hexadecimal digest encoding.

Identical accepted request objects MUST yield identical `report_id` values.
Failures MUST NOT invent a content digest (empty `report_id`).

### 7.6 Parse, encoding, size, duplicate-key, and type rules

A conforming future evaluator MUST enforce:

1. Payload type MUST be JSON text (`str`) or UTF-8 `bytes` only.
2. Encoded size MUST be `≤ 8192` bytes (byte length before/at decode boundary
   consistent with Foundations 46/47 practice).
3. Byte payloads MUST be valid UTF-8.
4. JSON MUST be well-formed; non-finite numbers are rejected.
5. Duplicate object keys at any depth are rejected (`duplicate_key`).
6. Top-level JSON value MUST be an object (`invalid_top_level` otherwise).
7. Unknown, missing, or reordered fields at any schema-controlled object are
   rejected (`schema_invalid` unless a later dedicated code applies).
8. Wrong JSON types for required fields are rejected under the dedicated code for
   that object, or `schema_invalid` for top-level typed fields before nested
   dedicated steps.
9. Canonical constant strings MUST match exactly (case-sensitive).
10. Hex digests MUST be exactly 64 characters from `[0-9a-f]`.

## 8. Deterministic first-failure validation precedence

A conforming future evaluator MUST stop at the first failure:

1. Reject unsupported payload type (`input_type_invalid`).
2. Reject encoded size `>` `8192` bytes (`input_too_large`).
3. Reject invalid UTF-8 (`encoding_invalid`).
4. Reject malformed JSON or non-finite numbers (`json_invalid`); duplicate keys
   (`duplicate_key`); non-object top-level (`invalid_top_level`).
5. Reject missing/unknown/reordered/wrong-type **top-level fields that are not
   otherwise assigned below** (`schema_invalid`). Nested objects that are present
   as objects but fail dedicated steps use those later codes once the outer
   request shape is accepted.
6. Reject unsupported `creation_profile`
   (`creation_profile_unsupported`).
7. If `environment` ∈ `{MAIN, CANONICAL, HISTORICAL, PRODUCTION}`, fail with
   `historical_import_forbidden`.
8. Else if `environment` ≠ `DISPOSABLE_TEST`, fail with `environment_invalid`.
9. If request `execution_authorized` is not boolean `false`, fail with
   `execution_authorized_invalid`.
10. If request `process_launch_authorized` is not boolean `false`, fail with
    `process_launch_authorized_invalid`.
11. If `admission_authorized` is present anywhere in the request, fail with
    `schema_invalid`.
12. If `filesystem_create_authorized` is present anywhere in the request, fail
    with `schema_invalid`.
13. Validate frozen Foundation 47 success projection per §6.1; on failure
    `preflight_evidence_invalid`.
14. Validate sandbox descriptor plan constraints per §7.2 **except** identity
    cross-binding that is reserved for step 16; structural/type/constant/
    exclusivity/non-empty `path_lexeme` failures use `sandbox_plan_invalid`.
    This step MUST NOT reapply Foundation 46 §7.3 lexical rejection rules.
15. Validate `creation_intent` per §7.3; on failure `creation_intent_invalid`.
16. Cross-bind sandbox identity/instance fields to frozen F47 evidence per §7.2
    equality requirements (`chain_id`, `genesis_digest`, `instance_id`, and
    environment/network constants already required). On mismatch
    `evidence_mismatch`.
17. Unexpected evaluator exception → `internal_error` with empty `detail`.
18. Otherwise success: `ok=true`, `code=creation_plan_ok`,
    `creation_plan_ok=true`, `process_launch_authorized=false`,
    `execution_authorized=false`, content-derived `report_id`, empty `detail`.

Steps 14 and 16 are mutually exclusive for binding failures: step 14 covers
local sandbox plan structure; step 16 covers cross-object equality against
accepted frozen F47 evidence after both nested objects are locally acceptable.

## 9. Stable codes

### 9.1 Foundation 48–defined result codes

| Code | Meaning |
|---|---|
| `creation_plan_ok` | Request satisfies this offline creation-plan contract |
| `input_type_invalid` | Payload type is not JSON text/bytes |
| `input_too_large` | Encoded size exceeds `8192` bytes |
| `encoding_invalid` | Invalid UTF-8 |
| `json_invalid` | Malformed JSON / non-finite number |
| `duplicate_key` | Duplicate JSON object key |
| `invalid_top_level` | Top-level value is not an object |
| `schema_invalid` | Missing/unknown/reordered/wrong-type fields, or forbidden authority field present |
| `creation_profile_unsupported` | `creation_profile` is not this profile |
| `environment_invalid` | Environment is not `DISPOSABLE_TEST` (generic) |
| `historical_import_forbidden` | Environment is MAIN/CANONICAL/HISTORICAL/PRODUCTION |
| `execution_authorized_invalid` | `execution_authorized` is not boolean `false` |
| `process_launch_authorized_invalid` | `process_launch_authorized` is not boolean `false` |
| `preflight_evidence_invalid` | Malformed/non-success/failed frozen F47 projection |
| `sandbox_plan_invalid` | Sandbox plan structural/type/constant/exclusivity/`path_lexeme` emptiness failure |
| `creation_intent_invalid` | `creation_intent` constraints failed |
| `evidence_mismatch` | Sandbox ↔ frozen F47 identity/instance binding mismatch |
| `internal_error` | Sanitized unexpected failure |

**Inventory:**

| Class | Count |
|---|---:|
| Foundation 48–defined distinct result `code` values (including success) | **18** |

Foundation 48 does **not** reuse Foundation 21 `reserved_state_unreachable` as a
result code. Lifecycle classification remains outside this profile.

### 9.2 Authority fields (always false / absent)

| Field | Normative value |
|---|---|
| `execution_authorized` | Always `false` |
| `process_launch_authorized` | Always `false` |
| `admission_authorized` | Must not exist |
| `filesystem_create_authorized` | Must not exist |

Distinguish carefully:

- `creation_plan_ok` / `code=creation_plan_ok` = specification contract satisfied;
- directory exists = **not** implied;
- directory create authorized now = **not** granted;
- filesystem checks executed = **not** claimed;
- process runnable / launched = **not** granted or performed;
- execution authorized = **always false**;
- admission authorized = **undefined and forbidden**.

## 10. Mandatory deferred filesystem obligations (future creators only)

The following obligations are **normative for a later authorized filesystem
creator**. Foundation 48 and any conforming Foundation 49-class offline
evaluator MUST NOT claim these checks were performed, MUST NOT execute them, and
MUST NOT treat `creation_plan_ok` as proof they passed.

A later creator MUST, before any create/use of `path_lexeme`:

1. **Exclusive ownership** — require exclusive create semantics for the planned
   `instance_id`; reject shared or non-exclusive claims.
2. **Realpath containment** — resolve the path and prove containment under an
   approved disposable parent; reject escape.
3. **Symlink and traversal rejection** — reject symlink components and `..`
   traversal at the filesystem layer (independent of Foundation 46 lexical
   rules).
4. **Create-new semantics** — create only when absent; honor
   `existing_path_policy=reject` (no overwrite, no adopt-in-place).
5. **Permissions** — apply restrictive directory permissions suitable for
   disposable-test isolation; do not widen to shared world-writable state.
6. **Collision handling** — on existence or ownership collision, fail closed;
   do not wipe as a create side effect.
7. **Cleanup/wipe ownership** — any later wipe/reset MUST obey Foundation 38
   tagged disposable rules: wipe only directories tagged with
   `data_dir_tag=l28-disposable-test`; never touch historical archives,
   continuity manifests, or untagged paths (F37-13 owner).
8. **Disposable `data_dir_tag` binding** — created state MUST remain bound to
   `l28-disposable-test` and the identity tuple carried from frozen F47
   evidence.

These obligations close the Foundation 46 §7.3 normative warning that lexical
validation alone does not prove filesystem safety. They remain outside
Foundations 46, 47, and 48 execution.

## 11. Exact meaning of success

When `code=creation_plan_ok` and `creation_plan_ok=true`:

1. The request is structurally plan-valid under this profile.
2. Frozen Foundation 47 preflight-success evidence was accepted by equality.
3. Sandbox and creation-intent constraints bound correctly.
4. `execution_authorized` and `process_launch_authorized` remain false.
5. No directory is asserted to exist.
6. No filesystem operation is authorized or performed.
7. No process launch is authorized or performed.
8. §10 obligations remain future mandatory work for a later creator.

## 12. Acceptance matrix for a future Foundation 49 evaluator

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
| `schema_invalid` | Missing top-level field; or `admission_authorized` present; or `filesystem_create_authorized` present |
| `creation_profile_unsupported` | Foreign `creation_profile` string |
| `historical_import_forbidden` | `environment=MAIN` (also CANONICAL/HISTORICAL/PRODUCTION) |
| `environment_invalid` | `environment=OTHER` |
| `execution_authorized_invalid` | Request `execution_authorized=true` |
| `process_launch_authorized_invalid` | Request `process_launch_authorized=true` |
| `preflight_evidence_invalid` | F47 projection `ok=false`, `code≠preflight_ok`, wrong field order/types, or zero `sandbox_instance_id` |
| `sandbox_plan_invalid` | `exclusive_ownership=false`; or empty `path_lexeme`; or wrong `data_dir_tag` |
| `creation_intent_invalid` | `create_mode` foreign; or `deferred_filesystem_obligations=false` |
| `evidence_mismatch` | Sandbox `instance_id` ≠ frozen F47 `sandbox_instance_id` after local sandbox/intent acceptance |
| `internal_error` | Narrow evaluator fault injection |
| `creation_plan_ok` | Fully conforming DISPOSABLE_TEST creation-plan request |

### Additional acceptance requirements

1. **Success postconditions** — `ok=true`, `code=creation_plan_ok`,
   `creation_plan_ok=true`, both authority flags false, non-empty
   `report_id`, empty `detail`, no `admission_authorized`, no
   `filesystem_create_authorized`.
2. **Failure postconditions** — `ok=false`, `creation_plan_ok=false`, both
   authority flags false, empty `report_id`, empty `detail`.
3. **No F47 re-entry** — production evaluator MUST NOT import/call Foundation
   47 evaluation APIs; tests MAY construct frozen projections as fixtures.
4. **No F46 lexical re-matrix** — rejecting `path_lexeme="/"` solely by
   reimplemented Foundation 46 §7.3 rules is out of profile; emptiness/type/
   constant/exclusivity failures remain `sandbox_plan_invalid`.
5. **No F21 transition** — static and behavioral hygiene.
6. **No F39/F45 re-evaluation** — structural consumption of frozen F47 evidence
   only.
7. **Determinism** — identical accepted request objects yield identical results
   and `report_id`.
8. **Static hygiene** — no `socket`, `subprocess`, `threading`, `asyncio`,
   `os`/`pathlib` filesystem mutation, environment reads, time/random,
   Leap28/Nova, wallet/mining/ledger, or Foundations 40–43 imports.
9. **Economics unchanged** — assert Protocol v1.0.0 constants remain
   `28_000_000`, `11_130_000`, `(28, 14, 7, 3, 1)`.
10. **All 18 stable codes** asserted through the public API (`internal_error`
    via narrow fault injection).

## 13. Determinism, limits, dependency, and static-hygiene requirements

1. Identical request bytes/objects MUST produce identical results.
2. Evaluation MUST NOT read wall-clock time, randomness, PID, hostname, port,
   environment variables, or runtime process tables.
3. Evaluation MUST NOT touch the filesystem or network.
4. Evaluation MUST NOT create persistent state.
5. Future evaluator MUST introduce **no** new third-party dependencies.
6. Future evaluator MUST NOT modify `coin/__init__.py` or `coin/l28_coin.py`.
7. Future evaluator MUST NOT export new package roots beyond the single new
   module file authorized by §16.
8. Exceptions MUST be sanitized to `internal_error` with empty `detail`.

## 14. Security considerations and protected economic facts

### Security considerations

- Creation-plan success is not filesystem permission and not process-launch
  permission.
- Carrying `path_lexeme` without reapplying Foundation 46 lexical rules does not
  weaken Foundation 47 preflight; it avoids duplicate competing validators.
  Filesystem safety remains entirely on the later creator under §10.
- Forbidden authority fields (`admission_authorized`,
  `filesystem_create_authorized`) MUST fail closed wherever nested.
- Zero `instance_id` and non-exclusive ownership remain rejectable at plan
  layer to preserve exclusive disposable isolation intent.

### Protected economic facts

Foundation 48 MUST NOT alter, recalculate, reinterpret, migrate, mint, simulate,
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

## 15. Explicit completion and non-completion claims

### Completion claims (this foundation)

When this specification document is locked, Foundation 48 completes **only** the
offline exclusive disposable sandbox directory **creation-plan contract**
definition: schemas, precedence, stable codes, deferred-obligation list,
authority boundaries, and future acceptance matrix.

### Non-completion claims

Foundation 48 does **not** complete and MUST NOT be cited as completing:

- Foundation 37 M2;
- F37-06 runnable Core process isolation;
- F37-13 stop/reset/cleanup tooling;
- F37-05 ephemeral ledger/reset layout;
- actual directory creation or wipe;
- process launch or supervision;
- Foundation 49 evaluator implementation;
- tip authority, disposable wallets, or issuance wiring;
- M3+ transport/sync;
- any MAIN/production activation.

## 16. Recommended future implementation scope (Foundation 49-class)

If Foundation 48 is locked, a later implementation foundation MAY implement
**only**:

1. One pure offline evaluator module for this profile;
2. One focused acceptance test file covering §12;
3. One narrow implementation record document.

That implementation MUST keep `execution_authorized=false` and
`process_launch_authorized=false` on every path, MUST NOT define
`admission_authorized` or `filesystem_create_authorized`, MUST NOT spawn
processes, MUST NOT create/stat/wipe directories, MUST NOT import Foundations
40–43, MUST NOT call Foundation 21 `transition`, MUST NOT call Foundation 47
evaluation APIs from production code, MUST NOT reimplement Foundation 46 §7.3
lexical rejection as a second authority, and MUST NOT modify
`coin/l28_coin.py` or `coin/__init__.py`.

Actual exclusive filesystem create remains a separate later remediation after
the offline evaluator exists.

## Security boundary and non-authorization statement

A completed Foundation 48 specification, and any later successful offline
evaluation under this profile, is disposable sandbox directory **creation-plan
evidence** only. It is not permission to spend L28, not an executable
transaction, not ledger mutation, not peer admission, not process creation, not
filesystem mutation, not proof that a directory exists, and not authorization to
start a node, network, miner, wallet, or testnet.

`execution_authorized` MUST remain the JSON boolean `false` on every conforming
request and every success or failure result path.

`process_launch_authorized` MUST remain the JSON boolean `false` on every
conforming request and every success or failure result path.

`admission_authorized` MUST NOT exist.

`filesystem_create_authorized` MUST NOT exist.
