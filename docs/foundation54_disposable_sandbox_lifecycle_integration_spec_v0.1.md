# L28 Disposable Sandbox Lifecycle Integration Specification v0.1

**Foundation:** 54

**Status:** Offline specification only; non-activation

**Milestone label:** F37-13 create → verify → cleanup lifecycle composition
contract (partial slice; specification only)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN) — immutable

**Profile:** `l28-disposable-sandbox-lifecycle-integration/v0.1`

## 1. Purpose, status, terminology, and non-goals

Foundation 54 defines the locked specification for **governed composition** of
exactly one disposable sandbox directory lifecycle under a caller-supplied
absolute trusted root:

1. **materialize** — Foundation 51 exclusive create of one tagged child;
2. **identity verify** — distinct post-materialization identity re-check;
3. **cleanup** — Foundation 53 constrained deletion of that same child.

This foundation is a **partial M2 / F37-13 specification slice**. It does
**not** implement an orchestrator, invoke Foundation 51/53 APIs, create or
delete directories, or activate a testnet in this milestone. It locks the
contract that a later Foundation 55-class integrator MUST obey. It does **not**
complete F37-06 process isolation, full F37-13 observability/shutdown, or
Foundation 37 M2.

### Terminology

| Term | Meaning in this specification |
|---|---|
| Lifecycle integration (F54) | Fail-closed composition of materialize → identity verify → cleanup |
| Materialize stage | Exact Foundation 51 evaluation of a nested materialization request |
| Identity verify stage | Distinct lifecycle stage that re-checks path/tag/root identity after `materialization_ok` and before any cleanup |
| Cleanup stage | Exact Foundation 53 evaluation of a constructed cleanup request |
| Cleanup handoff | Caller-supplied cleanup authority seed plus process-stop proof; `materialization_report_id` is bound from the F51 success `report_id` only after materialize |
| Authority transfer (forbidden) | Treating `materialization_authorized` as wipe permission, or `cleanup_authorized` as create permission |
| Partial lifecycle failure | Identity verify succeeded and the cleanup stage did not return `cleanup_ok` (`code=lifecycle_partial_failed`) |
| Future integrator | Foundation 55-class implementation of this contract |

### Non-goals

Foundation 54 MUST NOT and does not:

- implement `coin/disposable_sandbox_lifecycle_integration.py` or any tests;
- create, inspect, delete, wipe, or clean directories in this docs-only milestone;
- call Foundation 51 or Foundation 53 production APIs in this milestone;
- spawn processes, threads, async workers, subprocesses, daemons, services, or
  containers;
- open sockets or perform transport, discovery, synchronization, or propagation;
- authorize spend, admission, mining, consensus, tip authority, issuance,
  deployment, or SovereignBrain control;
- implement F37-06 process launch/stop tooling or authentic `stopped` producers;
- implement F38 post-wipe genesis revalidation (deferred obligation; §15);
- redefine Foundation 50–53 algorithms, code inventories, or schemas;
- call Foundation 21 `transition` or define another Core lifecycle state machine;
- depend on Foundations 40–43;
- modify or revive `coin/l28_coin.py`;
- claim F37-06, F37-13, or M2 completion;
- introduce Leap28 or Nova coupling.

### Non-authority statement

A conforming Foundation 54 evaluation, and any later successful lifecycle under
this profile:

- MUST set `execution_authorized` to the JSON/boolean `false` on every path;
- MUST set `process_launch_authorized` to the JSON/boolean `false` on every
  path;
- MUST NOT define, require, or grant `admission_authorized`;
- MUST NOT transfer authority between stages: `materialization_authorized`
  never implies cleanup/wipe permission; `cleanup_authorized` never implies
  create/materialization permission; `lifecycle_authorized` never implies
  either subordinate authority by itself;
- MUST NOT grant process, node, miner, wallet, network, transaction, ledger,
  consensus, deployment, or SovereignBrain authority;
- MUST NOT mean that a Core process may be started, or that genesis reuse is
  validated after wipe;
- is disposable sandbox directory **lifecycle evidence** only when
  `code=lifecycle_ok`.

## 2. Frozen dependency chain

| Layer | Role |
|---|---|
| F38 / F39 | `data_dir_tag=l28-disposable-test`; wipe-tag and post-reset genesis rules |
| F48 / F49 | Creation-plan evidence consumed inside nested F51 request |
| F50 / F51 | Materialization contract and implementation (materialize stage) |
| F52 / F53 | Cleanup contract and implementation (cleanup stage) |
| **F54 (this document)** | Lifecycle composition schemas, stage order, handoff, codes |
| Future F55 | Integrator module + focused tests + implementation record |
| Later F37-06 / F37-13 / F38 | Authentic `stopped` proof; broader stop/health/CLI; genesis revalidation |

### Prerequisites consumed

| Prerequisite | How Foundation 54 / future F55 consume it |
|---|---|
| Foundation 51 | Nested request evaluated by F51; success projection becomes cleanup evidence |
| Foundation 53 | Constructed cleanup request evaluated by F53 after identity verify |
| Foundation 52 §6–§13 | Cleanup authority, process-stop, constrained delete, partial/post codes |
| Foundation 50 §11–§14 | Trusted-root rules; rollback vs wipe ownership; never wipe-as-create |
| Foundation 38 wipe tags | Tagged disposable only; post-wipe genesis duty deferred (§15) |

Foundation 54 itself MUST NOT call production APIs. A later Foundation 55-class
integrator MUST invoke Foundation 51 and Foundation 53 only as subordinate
stage evaluators and MUST NOT reimplement materialization or constrained
deletion algorithms.

## 3. Trust and threat model

### Trust assumptions

1. The caller supplies an already-approved absolute trusted root.
2. Nested materialization authority and cleanup handoff are distinct objects.
3. Frozen F49 plan evidence inside the nested materialization request remains
   untrusted until Foundation 51 accepts it.
4. Process-stop proof for this profile version is structural `never_started`
   only (§6.3).

### Threats in scope

- Authority transfer / wipe-as-create via lifecycle composition
- Cleanup of a path that is not the just-materialized identity
- Forged or stale cross-stage binds (root / instance / tag / attempt / freshness)
- Skipping identity verify before cleanup
- Claiming lifecycle success after materialize-only or partial cleanup
- Accepting `stopped` process-stop proof without F37-06 authenticity
- Expanding wipe set beyond the single verified child

### Threats out of scope

- Multi-tenant OS isolation beyond fail-closed path checks
- Encrypted filesystem guarantees
- Remote attestation
- Full networked process supervisor (F37-06 / broader F37-13)

## 4. Future public API

A later Foundation 55-class implementation MUST expose exactly:

```text
run_disposable_sandbox_lifecycle_json(
    payload: str | bytes,
) -> SandboxLifecycleResult
```

Module path (locked for later implementation):

`coin/disposable_sandbox_lifecycle_integration.py`

`SandboxLifecycleResult` MUST be an immutable frozen dataclass.

Foundation 54 itself creates **no** module and **no** tests.

## 5. Normative constants

| Constant | Exact value |
|---|---|
| Profile / `lifecycle_profile` | `l28-disposable-sandbox-lifecycle-integration/v0.1` |
| Nested materialization profile | `l28-disposable-sandbox-directory-materialization/v0.1` |
| Nested cleanup profile | `l28-disposable-sandbox-directory-cleanup/v0.1` |
| Environment | `DISPOSABLE_TEST` |
| Network id | `l28-disposable-test/v0.1` |
| Protocol version | `l28-protocol/1.0.0` |
| Data-dir tag | `l28-disposable-test` |
| Accepted F51 stage code | `materialization_ok` |
| Accepted F53 stage code | `cleanup_ok` |
| Maximum encoded request size | `16384` bytes |
| Zero instance sentinel | `0000000000000000000000000000000000000000000000000000000000000000` |
| Forbidden environments | `MAIN`, `CANONICAL`, `HISTORICAL`, `PRODUCTION` |
| Allowed process-stop mode (v0.1) | `never_started` only |

No environment-variable, `HOME`, tilde, shell, or variable expansion is
permitted anywhere in this profile.

## 6. Locked product decisions

These decisions close the Foundation 54 baseline open items and are normative.

### 6.1 Stage order (exact)

A conforming integrator MUST execute stages in this order and MUST NOT reorder,
skip, or parallelize them:

1. **materialize** — evaluate the nested Foundation 51 request; require
   `code=materialization_ok` before continuing;
2. **identity verify** — perform §12 identity re-checks against the F51 success
   projection and filesystem; require all checks to pass before cleanup;
3. **cleanup** — construct and evaluate the Foundation 53 cleanup request per
   §8.4; require `code=cleanup_ok` before lifecycle success.

Wipe-as-create is forbidden: cleanup MUST NOT run unless materialize returned
`materialization_ok` for this attempt’s nested request.

### 6.2 No authority transfer between stages

1. Nested `materialization_authority.materialization_authorized=true` authorizes
   only the materialize stage.
2. Cleanup handoff `cleanup_authorized=true` authorizes only the cleanup stage
   after identity verify.
3. `lifecycle_authorized=true` authorizes only orchestration under this profile;
   it MUST NOT substitute for either subordinate authority flag.
4. `materialization_authorized` MUST NOT appear in cleanup handoff or in any
   constructed cleanup request’s forbidden-field set as a grant.
5. `cleanup_authorized` / `wipe_authorized` MUST NOT appear in the nested
   materialization request.

### 6.3 Process-stop evidence: `never_started` only

Until a later foundation supplies authentic Foundation 37-06 `stopped`
evidence producers, this profile MUST accept only:

| `mode` | Required fields |
|---|---|
| `never_started` | `mode`, `sandbox_instance_id` (64 hex; MUST equal lifecycle instance) |

If `mode` equals `stopped`, or if a `stopped`-shaped object is supplied, the
integrator MUST fail with `stopped_mode_forbidden` (not
`process_stop_evidence_invalid`). Any other mode/shape →
`process_stop_evidence_invalid`.

Foundation 54/55 MUST NOT spawn, signal, or inspect live processes to invent
stop proof.

### 6.4 Cross-stage bind (trusted_root / instance / tag / attempt / freshness)

The following values MUST be identical across:

- top-level / lifecycle authority;
- nested materialization request `trusted_root` and
  `materialization_authority` fields named below;
- cleanup handoff fields named below;
- nested plan evidence `sandbox_instance_id` (instance only).

Bound fields:

1. `trusted_root` (exact string after lifecycle lexical acceptance of the
   lifecycle authority / nested request root — see §11);
2. `sandbox_instance_id` (64 lowercase hex; not the zero sentinel);
3. `data_dir_tag` (exact `l28-disposable-test`);
4. `attempt_id` (64 lowercase hex; single lifecycle attempt identity);
5. `not_after_unix` (JSON integer `>= 0`; same exclusive freshness bound).

Every inequality among these bound fields across lifecycle authority, nested
materialization request/authority/plan instance, cleanup handoff, and
process-stop instance — **including** lifecycle authority `trusted_root` ≠
nested `materialization_request.trusted_root` — MUST use
`stage_binding_invalid` only. Cross-stage binding failures MUST NEVER use
`lifecycle_authority_mismatch`.

`report_id` handoff: after materialize success, the constructed cleanup
authority’s `materialization_report_id` MUST equal the F51 success
`report_id`. Callers MUST NOT pre-supply a cleanup `materialization_report_id`
in the lifecycle request (§8.3).

### 6.5 Partial-failure semantics

**Materialization succeeded** means the materialize stage returned
`code=materialization_ok` and a frozen F51 success projection was obtained.

| Outcome | Lifecycle `code` | Directory state | Operator duty |
|---|---|---|---|
| Materialize did not succeed | `materialization_stage_failed` (or earlier parse/authority code) | Per F51 (including rollback cases) | Do not claim lifecycle success; inspect `stage_code` |
| Materialize succeeded; identity verify failed | Exact `identity_verify_*` code | Materialized child may remain | Fail closed; cleanup MUST NOT run; new attempt needs fresh authority/`attempt_id` |
| Materialize + verify succeeded; cleanup did not return `cleanup_ok` | `lifecycle_partial_failed` | Per F53 failure (`stage_code`) | Fail closed; do not claim lifecycle success; do not widen wipe |
| All stages succeeded; post-lifecycle invariant failed | `post_lifecycle_verification_failed` | Target should be absent; parent identity suspect | Fail closed |
| All stages succeeded; post-checks pass | `lifecycle_ok` | Child gone | F38 post-wipe genesis duty applies before reuse (§15) |

`identity_verify_*` codes are not `lifecycle_partial_failed`. Only cleanup-stage
non-`cleanup_ok` after successful identity verify uses
`lifecycle_partial_failed`. Verify-stage failures and
`lifecycle_partial_failed` both imply materialization succeeded and
`lifecycle_ok=false`, but they remain mutually exclusive by stage.

### 6.6 F38 post-wipe responsibility (not executed by F54/F55)

Foundation 54/55 success means **only** that materialize → verify → cleanup
completed under this contract.

**Deferred (not implemented by F54/F55):**

- Revalidation of disposable genesis / identity after wipe (F38 “Reset /
  cleanup requirements”);
- Re-materialization, re-plan, or process restart.

After `lifecycle_ok`, any reuse of the same logical sandbox identity MUST obey
Foundation 38 post-reset genesis revalidation before the directory is treated
as a valid disposable data dir again. That duty is **outside** this profile’s
executable scope.

## 7. Nested Foundation 51 materialization request

### 7.1 Exact nested object

`materialization_request` MUST be a JSON object with **exactly** the Foundation
50/51 request fields in this order:

1. `materialization_profile` — exact
   `"l28-disposable-sandbox-directory-materialization/v0.1"`
2. `environment` — exact `"DISPOSABLE_TEST"` after forbidden-label rejection at
   the lifecycle layer (§10)
3. `plan_evidence` — frozen Foundation 49 success projection (Foundation 50 §6.1)
4. `materialization_authority` — Foundation 50 §7.2 object
5. `trusted_root` — absolute trusted-root path
6. `execution_authorized` — boolean `false`
7. `process_launch_authorized` — boolean `false`

Nested request maximum size is governed by the lifecycle envelope (§5:
`16384` bytes total). Foundation 51’s own `8192` limit still applies when the
nested object is serialized for the materialize-stage call.

### 7.2 Structural gate before stage invoke

Before invoking Foundation 51, the integrator MUST reject nested shape/type
defects with `materialization_request_invalid` when they are not already
classified as top-level `schema_invalid` or `stage_binding_invalid`.
Foundation 51 remains the authority for materialization-stage evaluation codes
once invoked; those codes are echoed in `stage_code` when the lifecycle code is
`materialization_stage_failed`.

## 8. Request, lifecycle authority, and cleanup handoff

### 8.1 `SandboxLifecycleRequest`

Exact top-level fields in this order:

1. `lifecycle_profile` — string; MUST equal this profile (§5)
2. `environment` — string; MUST equal `DISPOSABLE_TEST` after forbidden-label
   rejection (§10)
3. `lifecycle_authority` — `LifecycleAuthority` (§8.2)
4. `materialization_request` — nested Foundation 51 request (§7.1)
5. `cleanup_handoff` — `CleanupHandoff` (§8.3)
6. `process_stop_evidence` — `never_started` object (§6.3 / §8.3)
7. `execution_authorized` — boolean; MUST be `false`
8. `process_launch_authorized` — boolean; MUST be `false`

Maximum encoded size: `16384` bytes.

### 8.2 `LifecycleAuthority`

Exact fields in this order:

1. `lifecycle_authorized` — boolean; MUST be `true`
2. `trusted_root` — string; MUST satisfy §11 lexical rules on this authority
   object alone (cross-stage equality is §6.4 only)
3. `sandbox_instance_id` — 64 lowercase hex
4. `data_dir_tag` — exact `"l28-disposable-test"`
5. `attempt_id` — 64 lowercase hex; lifecycle attempt identity
6. `not_after_unix` — JSON integer `>= 0`; wall-clock freshness

**Accepted product decision (exclusive authority vs bind codes):**

1. Missing/unknown/reordered/wrong-type lifecycle authority fields,
   `lifecycle_authorized is not true`, non-hex `sandbox_instance_id` /
   `attempt_id`, wrong-type/`< 0` `not_after_unix`, or §11 lexical failure of
   lifecycle authority `trusted_root` → `lifecycle_authority_invalid`.
2. Lifecycle authority field types/presence already accepted, but an
   authority-intrinsic exact-value constraint fails (normative v0.1 case:
   `data_dir_tag` is a string and is not exact `"l28-disposable-test"`) →
   `lifecycle_authority_mismatch`. This code MUST NOT be used for any
   comparison against nested materialization, cleanup handoff, or
   process-stop objects.
3. Every cross-stage inequality among the five §6.4 bound fields — including
   lifecycle authority `trusted_root` ≠ nested `materialization_request.trusted_root`
   — → `stage_binding_invalid` only.

`attempt_id` format defects never use bind codes; they use
`lifecycle_authority_invalid` or `cleanup_handoff_invalid` at the object that
carries the bad value.

### 8.3 `CleanupHandoff`

Exact fields in this order (no `materialization_report_id`):

1. `cleanup_authorized` — boolean; MUST be `true`
2. `trusted_root` — string; MUST equal the bound trusted root (§6.4)
3. `sandbox_instance_id` — 64 lowercase hex; MUST equal bound instance
4. `data_dir_tag` — exact `"l28-disposable-test"`
5. `attempt_id` — 64 lowercase hex; MUST equal bound attempt
6. `not_after_unix` — JSON integer `>= 0`; MUST equal bound freshness

Malformed/false handoff → `cleanup_handoff_invalid`. §6.4 mismatches →
`stage_binding_invalid`.

### 8.4 Constructed Foundation 53 cleanup request (after verify)

After identity verify succeeds, the integrator MUST construct a Foundation 53
request with exact F52/F53 field order:

1. `cleanup_profile` —
   `"l28-disposable-sandbox-directory-cleanup/v0.1"`
2. `environment` — `"DISPOSABLE_TEST"`
3. `materialization_evidence` — exact Foundation 51 success projection field
   order (Foundation 52 §7.1 / F53 `MATERIALIZATION_EVIDENCE_FIELDS`)
4. `cleanup_authority` — exact Foundation 52 §8.2 fields in order, where
   `materialization_report_id` MUST equal F51 success `report_id`, and the
   remaining authority fields MUST equal the cleanup handoff / bound values
5. `process_stop_evidence` — the accepted `never_started` object from the
   lifecycle request
6. `trusted_root` — bound trusted root
7. `execution_authorized` — `false`
8. `process_launch_authorized` — `false`

### 8.5 Exact Foundation 51 success projection (cleanup evidence)

`materialization_evidence` MUST use **exactly** these fields in this order
(Foundation 52 §7.1):

1. `ok` — boolean `true`
2. `code` — exact `"materialization_ok"`
3. `materialization_profile` — exact
   `"l28-disposable-sandbox-directory-materialization/v0.1"`
4. `environment` — exact `"DISPOSABLE_TEST"`
5. `network_id` — exact `"l28-disposable-test/v0.1"`
6. `chain_id` — 64 lowercase hexadecimal characters
7. `genesis_digest` — 64 lowercase hexadecimal characters
8. `protocol_version` — exact `"l28-protocol/1.0.0"`
9. `plan_report_id` — 64 lowercase hexadecimal characters
10. `sandbox_instance_id` — 64 lowercase hexadecimal characters; MUST NOT equal
    the zero instance sentinel
11. `data_dir_tag` — exact `"l28-disposable-test"`
12. `path_lexeme` — non-empty string (`strip() != ""`); correlation only
13. `child_name` — exact `l28-disposable-test-{sandbox_instance_id}`
14. `materialization_path` — non-empty absolute path string
15. `materialization_ok` — boolean `true`
16. `process_launch_authorized` — boolean `false`
17. `execution_authorized` — boolean `false`
18. `report_id` — 64 lowercase hexadecimal characters
19. `detail` — exact empty string `""`

The integrator MUST copy these fields from the Foundation 51 success result
object/projection without reordering, renaming, or substituting `path_lexeme`
as a filesystem target.

### 8.6 Forbidden authority-bearing fields

Reject with `schema_invalid` if any of the following names appear at any nesting
depth in the lifecycle request:

- `admission_authorized`
- `filesystem_create_authorized`
- `wipe_authorized`
- `process_authorized`
- `node_authorized`
- `miner_authorized`
- `wallet_authorized`
- `network_authorized`
- `transaction_authorized`
- `ledger_authorized`
- `consensus_authorized`
- `deployment_authorized`
- `sovereign_brain_authorized`
- `SovereignBrain`

Notes:

- `materialization_authorized` is allowed only inside
  `materialization_request.materialization_authority`.
- `cleanup_authorized` is allowed only inside `cleanup_handoff` (and inside the
  constructed F53 authority object at cleanup stage, which is not caller JSON).
- Top-level `execution_authorized=true` /
  `process_launch_authorized=true` use dedicated invalid codes (§10).

### 8.7 `SandboxLifecycleResult`

`SandboxLifecycleResult` MUST be a frozen dataclass with **exactly** these
fields in this order:

1. `ok` — boolean; `true` only on full lifecycle success
2. `code` — string; stable code from §9
3. `lifecycle_profile` — string; see recovery rules below
4. `environment` — string; `DISPOSABLE_TEST` on success; else recovered or empty
5. `network_id` — string; from F51 success on/after materialize success paths
   that populate identity fields; else empty
6. `chain_id` — string; same rule as `network_id`
7. `genesis_digest` — string; same rule as `network_id`
8. `protocol_version` — string; same rule as `network_id`
9. `sandbox_instance_id` — string; bound instance on/after materialize success
   identity population; else empty
10. `data_dir_tag` — string; `l28-disposable-test` when identity fields are
    populated; else empty
11. `child_name` — string; from F51 success when populated; else empty
12. `materialization_path` — string; from F51 success when populated; else empty
13. `materialization_report_id` — string; F51 success `report_id` when
    materialize succeeded; else empty
14. `cleanup_report_id` — string; F53 success `report_id` on full lifecycle
    success; else empty
15. `failed_stage` — string; exact `""`, `"materialize"`, `"identity_verify"`,
    or `"cleanup"`
16. `stage_code` — string; echoed subordinate F51/F53 code when applicable;
    otherwise `""`
17. `lifecycle_ok` — boolean; `true` only on full success; else `false`
18. `process_launch_authorized` — boolean; MUST be `false` on every path
19. `execution_authorized` — boolean; MUST be `false` on every path
20. `report_id` — string; content-derived SHA-256 hex on success; empty on every
    failure
21. `detail` — string; MUST be empty on every success and every failure in v0.1

`lifecycle_profile` recovery:

1. On success: exact profile string.
2. On `lifecycle_profile_unsupported`: echo recovered string when typed.
3. On any later failure after a conforming profile string was accepted: exact
   profile string.
4. On failures before a typed profile is available: empty string.

Population rule for identity fields after materialize success: even when a
later stage fails, a conforming integrator MUST populate
`materialization_report_id`, `sandbox_instance_id`, `data_dir_tag`,
`child_name`, `materialization_path`, and the network identity fields from the
F51 success projection so operators can locate residue without reading
`detail`.

### 8.8 Content-derived `report_id` (success only)

On success only, `report_id` MUST be the lowercase hex SHA-256 digest of the
canonical JSON serialization of the accepted lifecycle request object with
exact field order from §8.1–§8.3 / §7.1; compact separators; `sort_keys=false`;
`ensure_ascii=false`; `allow_nan=false`; UTF-8 bytes.

Failures MUST use empty `report_id` and empty `detail`.

### 8.9 Parse rules

Same family as Foundation 50/52: `str`/`bytes` only; `≤ 16384` UTF-8 bytes;
strict JSON object; duplicate-key rejection; unknown/reordered fields rejected;
hex64 `[0-9a-f]{64}`; no env/`HOME`/tilde/shell expansion.

## 9. Stable codes

| Code | Meaning |
|---|---|
| `lifecycle_ok` | Materialize, identity verify, and cleanup all succeeded |
| `input_type_invalid` | Payload type is not JSON text/bytes |
| `input_too_large` | Encoded size exceeds `16384` bytes |
| `encoding_invalid` | Invalid UTF-8 |
| `json_invalid` | Malformed JSON / non-finite number |
| `duplicate_key` | Duplicate JSON object key |
| `invalid_top_level` | Top-level value is not an object |
| `schema_invalid` | Missing/unknown/reordered/wrong-type fields or forbidden authority field |
| `lifecycle_profile_unsupported` | `lifecycle_profile` is not this profile |
| `environment_invalid` | Environment is not `DISPOSABLE_TEST` (generic) |
| `historical_import_forbidden` | Environment is MAIN/CANONICAL/HISTORICAL/PRODUCTION |
| `execution_authorized_invalid` | Top-level `execution_authorized` is not boolean `false` |
| `process_launch_authorized_invalid` | Top-level `process_launch_authorized` is not boolean `false` |
| `lifecycle_authority_invalid` | Lifecycle authority missing/false/malformed or authority-root lexical failure |
| `lifecycle_authority_mismatch` | Lifecycle authority intrinsic exact-value failure (not cross-stage; see §8.2) |
| `lifecycle_authority_expired` | `not_after_unix` wall-clock freshness check failed |
| `stage_binding_invalid` | Any cross-stage root/instance/tag/attempt/freshness inequality (including lifecycle↔nested `trusted_root`) |
| `materialization_request_invalid` | Nested materialization request shape/type invalid before F51 invoke |
| `cleanup_handoff_invalid` | Cleanup handoff missing/false/malformed |
| `process_stop_evidence_invalid` | Process-stop proof missing/malformed/mismatched for `never_started` |
| `stopped_mode_forbidden` | `stopped` mode supplied; forbidden in this profile version |
| `materialization_stage_failed` | Foundation 51 returned a non-`materialization_ok` code |
| `identity_verify_target_absent` | Verify stage: materialized path missing |
| `identity_verify_symlink_rejected` | Verify stage: symlink or special node at target |
| `identity_verify_mismatch` | Verify stage: path/name/tag/instance identity mismatch |
| `identity_verify_containment_failure` | Verify stage: not a direct child of trusted root inode |
| `identity_verify_substitution_ambiguous` | Verify stage: device/inode substitution ambiguity |
| `cleanup_stage_failed` | Cleanup request could not be constructed/invoked (pre-F53) |
| `lifecycle_partial_failed` | Materialize+verify succeeded; Foundation 53 did not return `cleanup_ok` |
| `post_lifecycle_verification_failed` | Cleanup reported success but lifecycle post-check failed |
| `internal_error` | Sanitized unexpected failure |

**Inventory:** **31** distinct result `code` values (including success).

## 10. Deterministic first-failure validation precedence

A conforming future integrator MUST stop at the first failure:

1. Unsupported payload type (`input_type_invalid`).
2. Encoded size `>` `16384` (`input_too_large`).
3. Invalid UTF-8 (`encoding_invalid`).
4. Malformed JSON / non-finite (`json_invalid`); duplicate keys
   (`duplicate_key`); non-object top-level (`invalid_top_level`).
5. Missing/unknown/reordered/wrong-type **top-level fields** not assigned below
   (`schema_invalid`). Nested values that are **missing or not JSON objects**
   for `lifecycle_authority`, `materialization_request`, `cleanup_handoff`, or
   `process_stop_evidence` fail here as `schema_invalid`.
6. Unsupported `lifecycle_profile` (`lifecycle_profile_unsupported`).
7. Forbidden environment labels (`historical_import_forbidden`).
8. Other non-`DISPOSABLE_TEST` environment (`environment_invalid`).
9. Request `execution_authorized` not boolean `false`
   (`execution_authorized_invalid`).
10. Request `process_launch_authorized` not boolean `false`
    (`process_launch_authorized_invalid`).
11. Forbidden authority-bearing fields anywhere per §8.6 (`schema_invalid`).
12. `lifecycle_authority` object/schema/formats; `lifecycle_authorized is true`;
    §11 lexical validation of lifecycle authority `trusted_root`;
    authority-intrinsic exact `data_dir_tag` (`lifecycle_authority_invalid` /
    `lifecycle_authority_mismatch` per §8.2). This step MUST NOT compare
    lifecycle authority fields to nested materialization, cleanup handoff, or
    process-stop objects.
13. `not_after_unix` freshness on the lifecycle authority value
    (`lifecycle_authority_expired`).
14. Nested `materialization_request` required object shape for §7.1 field order
    and boolean/string types (`materialization_request_invalid`).
15. §11 lexical validation of nested `materialization_request.trusted_root`
    (`materialization_request_invalid` on lexical failure). This step MUST
    complete before any lifecycle↔nested `trusted_root` equality compare.
16. `cleanup_handoff` object/schema/formats; `cleanup_authorized is true`
    (`cleanup_handoff_invalid`).
17. `process_stop_evidence`: if `mode=="stopped"` → `stopped_mode_forbidden`;
    else validate `never_started` shape (`process_stop_evidence_invalid`).
18. §6.4 cross-stage binds among lifecycle authority, nested materialization
    authority/root/plan instance, cleanup handoff, and process-stop instance —
    including lifecycle authority `trusted_root` ≠ nested
    `materialization_request.trusted_root` — (`stage_binding_invalid` only;
    never `lifecycle_authority_mismatch`).
19. Invoke Foundation 51 on the nested request. If result `code !=
    materialization_ok`: `materialization_stage_failed` with
    `failed_stage="materialize"` and `stage_code` equal to the F51 code.
20. Identity verify stage (§12), first defect wins among
    `identity_verify_*` codes; `failed_stage="identity_verify"`;
    `stage_code=""`. Populate materialization identity fields (§8.7).
21. Construct Foundation 53 request (§8.4). Construction failure →
    `cleanup_stage_failed` with `failed_stage="cleanup"`.
22. Invoke Foundation 53. If result `code != cleanup_ok`:
    `lifecycle_partial_failed` with `failed_stage="cleanup"` and
    `stage_code` equal to the F53 code.
23. Post-lifecycle verification (§13): target absent; trusted-root inode/device
    unchanged from pre-materialize root snapshot captured before step 19.
    Failure → `post_lifecycle_verification_failed`.
24. Unexpected exception → `internal_error` with empty `detail`.
25. Otherwise success: `ok=true`, `code=lifecycle_ok`, `lifecycle_ok=true`,
    both authority flags false, content-derived `report_id`, empty `detail`,
    `failed_stage=""`, `stage_code=""`, `cleanup_report_id` set from F53.

Every failure path MUST return empty lifecycle `report_id` and empty `detail`.
Success MUST keep `execution_authorized=false` and
`process_launch_authorized=false`. MUST NOT wipe-as-create. MUST NOT run cleanup
before identity verify success.

## 11. Trusted-root lexical policy (lifecycle bind)

POSIX is the normative platform for v0.1. Lifecycle binding uses the same
canonical lexical rules as Foundation 50/52 for absolute trusted roots:

1. Non-empty string; absolute POSIX path (starts with `/`).
2. No NUL; no `.` / `..` segments; no trailing separators except filesystem root
   `/`; no redundant separators; no `\` alternate separators.
3. No `HOME`, tilde, environment, shell, cwd, or variable expansion.

Nested Foundation 51 remains responsible for filesystem trusted-root
preconditions during the materialize stage (`trusted_root_invalid` echoed via
`materialization_stage_failed` / `stage_code`).

## 12. Identity verify stage (distinct)

After `materialization_ok` and before constructing/invoking cleanup, the
integrator MUST re-check, using no-follow primitives:

1. `materialization_path` equals `trusted_root / child_name` exactly.
2. `child_name` equals `l28-disposable-test-{sandbox_instance_id}`.
3. `lstat(materialization_path)` succeeds; else
   `identity_verify_target_absent`.
4. Target is not a symlink and not a special non-file/non-directory node; else
   `identity_verify_symlink_rejected`.
5. Target is a directory; basename equals `child_name`; else
   `identity_verify_mismatch`.
6. Parent directory path equals `trusted_root` and parent directory inode/device
   equal the trusted-root snapshot captured before materialize; else
   `identity_verify_containment_failure`.
7. Target `st_dev` equals trusted-root `st_dev` from that snapshot; else
   `identity_verify_substitution_ambiguous`.

`path_lexeme` MUST NOT select or alter the verified path.

On any verify failure, cleanup MUST NOT run.

## 13. Post-lifecycle verification

After Foundation 53 returns `cleanup_ok`:

1. `lstat` of `materialization_path` MUST indicate absence.
2. Trusted root MUST still exist as the same directory inode/device captured
   before materialize.

Failure → `post_lifecycle_verification_failed` with `failed_stage="cleanup"`
and `stage_code=""`. A successful cleanup projection MUST always use
`stage_code=""` on this lifecycle code (never echo `cleanup_ok` in
`stage_code`).

## 14. Security invariants

1. At most one materialize and one cleanup of one child per successful lifecycle
   attempt.
2. No cleanup without prior `materialization_ok` and identity verify success.
3. No authority transfer between stages (§6.2).
4. No wipe-as-create.
5. Both `execution_authorized` and `process_launch_authorized` always false.
6. Forbidden authority fields never succeed.
7. `stopped` process-stop mode never succeeds in v0.1.
8. Partial lifecycle never reports `lifecycle_ok`.
9. Success never implies process launch, admission, spend, mining, networking,
   ledger mutation, deployment, SovereignBrain authority, or genesis
   revalidation completion.
10. Protected Protocol v1.0.0 economic facts remain unchanged.

## 15. F38 post-wipe and deferred work

### 15.1 F38 post-wipe (deferred executable duty)

Per `docs/disposable_network_identity_genesis_binding_v0.1.md` — Reset /
cleanup requirements:

1. Wipe only directories tagged `data_dir_tag=l28-disposable-test`.
2. Never touch historical archives, continuity manifests, or untagged paths.
3. **After wipe, genesis/identity revalidation before reuse** is REQUIRED by
   F38 and is **not** performed by Foundation 54/55.

### 15.2 Explicit deferred work

- Foundation 55 integrator module/tests/record;
- F37-06 process launch and authentic `stopped` evidence producers;
- Broader F37-13 health endpoints / networked graceful shutdown CLI;
- Genesis revalidation automation after wipe;
- Package exports via `coin/__init__.py`.

## 16. Test obligations for future Foundation 55

A Foundation 55 implementation MUST provide focused tests proving at least:

1. Success path returns `lifecycle_ok` with both authority flags false and
   empty `detail`.
2. Every non-success code in §9 is reachable by a concrete first-failure case.
3. Exact public inventory equals the 31 codes.
4. Parse/schema/duplicate-key/size/encoding cases (`16384` limit).
5. Forbidden authority fields rejected; no authority transfer across stages.
6. Missing/false/mismatched/expired lifecycle authority; bad `attempt_id`.
7. §6.4 bind failures across root/instance/tag/attempt/freshness.
8. `stopped_mode_forbidden` for `stopped` process-stop objects;
   `never_started` success path.
9. Materialize-stage failure echoes F51 `stage_code` under
   `materialization_stage_failed`.
10. Each `identity_verify_*` code with cleanup not invoked; materialized child
    may remain.
11. Cleanup non-success after verify → `lifecycle_partial_failed` with F53
    `stage_code`.
12. `path_lexeme` never selects materialize or cleanup targets.
13. Deterministic success `report_id`; empty failure `report_id`/`detail`.
14. Result immutability; F55 may call F51/F53 as subordinates only; no
    Leap28/Nova; no network/wallet/mining/ledger mutation APIs; no reimplementation
    of constrained delete or exclusive create algorithms.

Harnesses MAY use temporary trusted roots only inside tests. Production
integrator MUST NOT invent trusted roots from environment, `HOME`, or cwd.

## 17. Protected-file and protocol non-effects

Foundation 54 MUST NOT modify or authorize modification of:

- `PROTOCOL.md` and Protocol v1.0.0 economic constants;
- `coin/tx_validation.py` protected facts;
- historical continuity manifests/archives;
- `coin/l28_coin.py` or `coin/__init__.py`;
- Foundations 38–53 locked modules/documents (compose only; do not revise).

Protected economic facts (unchanged):

| Fact | Value |
|---|---:|
| Hard cap | `28_000_000` L28 |
| Emission ceiling | `11_130_000` L28 |
| Halving interval | `210_000` |
| Reward sequence | `28 → 14 → 7 → 3 → 1 → 0` |

## 18. Recommended future implementation scope (Foundation 55-class)

If Foundation 54 is locked, a later implementation foundation MAY implement
**only**:

1. `coin/disposable_sandbox_lifecycle_integration.py`;
2. `tests/test_disposable_sandbox_lifecycle_integration.py`;
3. one narrow implementation record document.

That implementation MUST keep both authority flags false on every path, MUST
reject all §8.6 forbidden fields, MUST invoke Foundation 51 and Foundation 53
only as subordinate stage evaluators, MUST NOT accept `stopped` mode until a
later profile revision, MUST NOT implement genesis revalidation, MUST NOT
modify `coin/l28_coin.py` or `coin/__init__.py`, and MUST NOT introduce
Leap28/Nova coupling.

## Security boundary and non-authorization statement

A completed Foundation 54 specification, and any later successful lifecycle
under this profile, is disposable sandbox directory **lifecycle evidence**
only. It is not permission to spend L28, not peer admission, not process
creation, not authority to wipe unrelated paths, and not authorization to
start a node, network, miner, wallet, or testnet. It does not complete F38
genesis revalidation after wipe.

`execution_authorized` MUST remain the JSON boolean `false` on every conforming
request and every success or failure result path.

`process_launch_authorized` MUST remain the JSON boolean `false` on every
conforming request and every success or failure result path.

`admission_authorized` MUST NOT exist.

`filesystem_create_authorized` MUST NOT exist as a lifecycle grant.
