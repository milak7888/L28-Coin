# L28 Disposable Sandbox Directory Cleanup Specification v0.1

**Foundation:** 52

**Status:** Offline specification only; non-activation

**Milestone label:** F37-13 tagged disposable sandbox directory cleanup/wipe
contract (partial slice; specification only)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN) — immutable

**Profile:** `l28-disposable-sandbox-directory-cleanup/v0.1`

## 1. Purpose, status, terminology, and non-goals

Foundation 52 defines the locked specification for **governed cleanup** of exactly
one successful Foundation 51-materialized disposable sandbox data directory:
fail-closed authority binding, process-stop proof, race-resistant identity
re-verification, and a constrained no-follow deletion algorithm under a
caller-supplied absolute trusted root.

This foundation is a **partial M2 / F37-13 specification slice**. It does
**not** implement or invoke filesystem deletion in this milestone; it locks the
contract that a later Foundation 53-class cleaner MUST obey. It does **not**
complete F37-06 process isolation, full F37-13 observability/shutdown, or
Foundation 37 M2.

### Terminology

| Term | Meaning in this specification |
|---|---|
| Cleanup / wipe (F52) | Constrained deletion of one verified tagged disposable sandbox directory tree |
| Frozen F51 materialization evidence | Exact Foundation 51 success result projection (`code=materialization_ok`, …) |
| Cleanup authority | Caller-supplied F52 authority object outside the F51 result |
| Process-stop proof | Caller-supplied evidence that no process holds the sandbox, or that none was started |
| Trusted root | Caller-supplied absolute, pre-existing, non-symlink directory that is the only allowed parent |
| Target path | Absolute path equal to frozen F51 `materialization_path` (direct child of trusted root) |
| Constrained deletion | Bottom-up, no-follow unlink confined to the verified target tree only |
| Partial cleanup failure | Deletion began but the target tree was not fully removed |
| Future cleaner | Foundation 53-class implementation of this contract |

### Non-goals

Foundation 52 MUST NOT and does not:

- implement `coin/disposable_sandbox_directory_cleanup.py` or any tests;
- create, inspect, delete, wipe, or clean directories in this docs-only milestone;
- spawn processes, threads, async workers, subprocesses, daemons, services, or
  containers;
- open sockets or perform transport, discovery, synchronization, or propagation;
- authorize spend, admission, mining, consensus, tip authority, issuance,
  deployment, or SovereignBrain control;
- implement F37-06 process launch/stop tooling or networked graceful shutdown;
- implement F38 post-wipe genesis revalidation (deferred obligation; §15);
- rerun Foundation 39, 45, 47, 49, or 51 evaluation;
- call Foundation 21 `transition` or define another lifecycle state machine;
- depend on Foundations 40–43;
- modify or revive `coin/l28_coin.py`;
- claim F37-06, F37-13, or M2 completion;
- introduce Leap28 or Nova coupling.

### Non-authority statement

A conforming Foundation 52 evaluation, and any later successful cleanup under
this profile:

- MUST set `execution_authorized` to the JSON/boolean `false` on every path;
- MUST set `process_launch_authorized` to the JSON/boolean `false` on every
  path;
- MUST NOT define, require, or grant `admission_authorized`;
- MUST NOT define, require, or grant `filesystem_create_authorized` or
  `materialization_authorized` as wipe authority;
- MUST NOT grant process, node, miner, wallet, network, transaction, ledger,
  consensus, deployment, or SovereignBrain authority;
- MUST NOT mean that a Core process may be started, or that genesis reuse is
  validated;
- is disposable sandbox directory **cleanup evidence** only when
  `code=cleanup_ok`.

## 2. Frozen dependency chain

| Layer | Role |
|---|---|
| F38 / F39 | `data_dir_tag=l28-disposable-test`; wipe-tag and post-reset genesis rules |
| F48 / F49 | Creation-plan; `cleanup_ownership=tagged_disposable_only` intent |
| F50 / F51 | Materialization; successful-dir cleanup ownership handoff (F50 §14) |
| **F52 (this document)** | Cleanup schemas, authority, process-stop proof, algorithms, codes |
| Future F53 | Cleaner module + focused tests + implementation record |
| Later F37-13 / F37-06 | Broader stop/health/CLI; process-stop evidence producers |

### Prerequisites consumed (frozen evidence only)

| Prerequisite | How Foundation 52 consumes it |
|---|---|
| Foundation 51 success | Frozen `SandboxMaterializationResult` projection; structural equality only |
| Foundation 50 §11–§14 | Trusted-root lexical/FS rules; child naming; rollback vs wipe ownership |
| Foundation 38 wipe tags | Tagged disposable only; never archives/untagged paths; post-wipe genesis duty |

Foundation 52 MUST NOT call
`materialize_disposable_sandbox_directory_json`,
`evaluate_sandbox_directory_creation_plan_json`,
`evaluate_core_entrypoint_preflight_json`, Foundation 45 policy APIs, or
Foundation 21 `transition`.

## 3. Trust and threat model

### Trust assumptions

1. The caller supplies an already-approved absolute trusted root.
2. The caller supplies distinct F52 cleanup authority and process-stop proof
   objects that are not embedded inside the F51 result.
3. Frozen F51 evidence is untrusted bytes until structural validation succeeds.
4. The operating system provides no-follow `lstat`/`unlink`/`rmdir` primitives.

### Threats in scope

- Path traversal and containment escape during delete
- Symlink / mount-substitution delete-outside-root attacks
- Wipe of pre-existing, untagged, archive, or continuity paths
- Wipe-as-create or wipe without materialization evidence
- Authority forgery via mismatched report_id / instance / tag / root
- Deleting while a process still holds the directory (when stop proof is forged)
- Unbounded recursive delete / TOCTOU races
- Partial wipe falsely reported as success

### Threats out of scope

- Multi-tenant OS isolation beyond fail-closed path checks
- Encrypted filesystem guarantees
- Remote attestation
- Full networked process supervisor (F37-06 / broader F37-13)

## 4. Future public API

A later Foundation 53-class implementation MUST expose exactly:

```text
cleanup_disposable_sandbox_directory_json(
    payload: str | bytes,
) -> SandboxCleanupResult
```

Module path (locked for later implementation):

`coin/disposable_sandbox_directory_cleanup.py`

`SandboxCleanupResult` MUST be an immutable frozen dataclass.

Foundation 52 itself creates **no** module and **no** tests.

## 5. Normative constants

| Constant | Exact value |
|---|---|
| Profile / `cleanup_profile` | `l28-disposable-sandbox-directory-cleanup/v0.1` |
| Upstream materialization profile | `l28-disposable-sandbox-directory-materialization/v0.1` |
| Environment | `DISPOSABLE_TEST` |
| Network id | `l28-disposable-test/v0.1` |
| Protocol version | `l28-protocol/1.0.0` |
| Data-dir tag | `l28-disposable-test` |
| Accepted F51 result code | `materialization_ok` |
| Maximum encoded request size | `8192` bytes |
| Zero instance sentinel | `0000000000000000000000000000000000000000000000000000000000000000` |
| Forbidden environments | `MAIN`, `CANONICAL`, `HISTORICAL`, `PRODUCTION` |
| Max tree entries (files+dirs) | `4096` |
| Max tree depth | `64` |

No environment-variable, `HOME`, tilde, shell, or variable expansion is
permitted anywhere in this profile.

## 6. Locked product decisions

These decisions close the Foundation 52 baseline open items and are normative.

### 6.1 Constrained deletion algorithm (not unconstrained `rmtree`)

Cleanup MUST use **constrained bottom-up no-follow deletion** confined to the
verified target path:

1. After identity prechecks (§12–§13), open/walk the target directory without
   following symlinks.
2. During survey (before any unlink), reject with exactly one first-failure code:
   - symlink → `symlink_rejected`;
   - special object that is neither a regular file nor a directory (FIFO,
     socket, device node, whiteout, or equivalent) → `symlink_rejected`
     (same exclusive code; special objects are not treated as deletable
     content);
   - walk-time `st_dev` mismatch vs trusted-root device from precheck →
     `substitution_ambiguous`;
   - entry count or depth above §5 maxima → `tree_limit_exceeded`.
3. Unlink regular files first; then remove empty subdirectories bottom-up; then
   `rmdir` the target directory itself.
4. MUST NOT call `shutil.rmtree`, MUST NOT follow symlinks, MUST NOT delete
   parents, MUST NOT delete siblings, MUST NOT delete outside the target path.
5. MUST NOT wipe a path that fails identity prechecks. MUST NOT wipe-as-create.
6. `exclusive_cleanup_failed` is reserved for constrained delete **operation**
   failures that occur before any successful unlink of target contents (for
   example first `unlink`/`rmdir` errno). Survey defects NEVER use this code.

### 6.2 Process-stop proof (required before any deletion)

Cleanup MUST NOT begin deletion unless `process_stop_evidence` validates under
exactly one of these modes:

| `mode` | Meaning | Required fields |
|---|---|---|
| `never_started` | No Core/process was started against this sandbox instance | `mode`, `sandbox_instance_id` |
| `stopped` | A process that used the sandbox was stopped and listeners cleared | `mode`, `sandbox_instance_id`, `listeners_cleared=true`, `stop_report_id` (64 hex) |

While Foundation 37-06 process launch remains incomplete, conforming callers
MUST use `never_started` unless a later foundation supplies authentic
`stopped` evidence. Fabricating `stopped` without a real stop producer is out
of profile for production operators; the cleaner validates structure only.

Process-stop proof is **caller-supplied frozen evidence**. Foundation 52/53
MUST NOT spawn, signal, or inspect live processes to invent this proof.

### 6.3 Freshness and attempt binding

- `attempt_id`: 64 lowercase hex; single-attempt identity; **no** external
  cross-field bind; invalid format → `cleanup_authority_invalid`.
- `not_after_unix`: JSON integer `>= 0`; exclusive upper bound in Unix seconds.
  **Accepted product decision (wall-clock freshness):** if OS time
  `>= not_after_unix` → `cleanup_authority_expired`.

### 6.4 Partial-failure and post-cleanup verification semantics

**Deletion began** means at least one successful `unlink` or `rmdir` of an
object that was inside the verified target tree (including the target directory
itself).

| Outcome | Code | Directory state | Operator duty |
|---|---|---|---|
| No deletion started; precheck/survey/op failed | Specific precheck, survey, or `exclusive_cleanup_failed` | Unchanged | Retry only after fixing cause |
| Deletion began; post-cleanup verification still sees the target or any residue under the former target path | `cleanup_partial_failed` | Partially deleted | Fail closed; do **not** claim success; do **not** widen wipe; new attempt needs fresh authority/`attempt_id` and re-verification |
| Deletion completed with **no** detected target/residue, but a remaining post-cleanup invariant fails (trusted-root inode/device identity changed, or absence check is otherwise ambiguous without residue) | `post_cleanup_verification_failed` | Target absent; parent identity suspect | Fail closed; do not claim success; do not widen wipe |
| Target fully removed; post-checks pass | `cleanup_ok` | Gone | F38 post-wipe genesis duty applies before reuse (§15) |

`cleanup_partial_failed` and `post_cleanup_verification_failed` are mutually
exclusive under the delete-started rule above. Partial/post failures MUST leave
empty `report_id` and empty `detail` (no path leakage).

### 6.5 F38 post-wipe responsibility

Foundation 52/53 success means **only** that the verified tagged disposable
directory tree was removed under this contract.

**Deferred (not implemented by F52/F53):**

- Revalidation of disposable genesis / identity after wipe (F38 “Reset /
  cleanup requirements”).
- Re-materialization, re-plan, or process restart.

After `cleanup_ok`, any reuse of the same logical sandbox identity MUST obey
Foundation 38 post-reset genesis revalidation before the directory is treated
as a valid disposable data dir again. That duty is **outside** this profile’s
executable scope.

## 7. Frozen Foundation 51 materialization-evidence projection

### 7.1 Exact field order

`materialization_evidence` MUST be a JSON object with **exactly** these fields
in this order:

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
14. `materialization_path` — non-empty absolute path string; create target
15. `materialization_ok` — boolean `true`
16. `process_launch_authorized` — boolean `false`
17. `execution_authorized` — boolean `false`
18. `report_id` — 64 lowercase hexadecimal characters
19. `detail` — exact empty string `""`

### 7.2 Structural-only consumption

Foundation 52 MUST treat this object as caller-supplied frozen evidence; MUST
NOT call Foundation 51 APIs; MUST reject any deviation with
`materialization_evidence_invalid`.

## 8. Request, authority, and process-stop schemas

### 8.1 `SandboxCleanupRequest`

Exact top-level fields in this order:

1. `cleanup_profile` — string; MUST equal this profile (§5)
2. `environment` — string; MUST equal `DISPOSABLE_TEST` after forbidden-label
   rejection (§10)
3. `materialization_evidence` — frozen Foundation 51 success projection (§7.1)
4. `cleanup_authority` — `CleanupAuthority` (§8.2)
5. `process_stop_evidence` — `ProcessStopEvidence` (§8.3)
6. `trusted_root` — string; absolute trusted-root path (§12)
7. `execution_authorized` — boolean; MUST be `false`
8. `process_launch_authorized` — boolean; MUST be `false`

Maximum encoded size: `8192` bytes.

### 8.2 `CleanupAuthority`

Exact fields in this order:

1. `cleanup_authorized` — boolean; MUST be `true` (absent/false → fail closed)
2. `trusted_root` — string; MUST equal top-level `trusted_root` after §12
   canonical lexical validation of the request value
3. `sandbox_instance_id` — 64 lowercase hex; MUST equal evidence
   `sandbox_instance_id` (equality at §10 step 17 only)
4. `data_dir_tag` — exact `"l28-disposable-test"` (equality at step 17)
5. `materialization_report_id` — 64 lowercase hex; MUST equal evidence
   `report_id` (equality at step 17)
6. `attempt_id` — 64 lowercase hex; format/single-attempt only; no external bind
7. `not_after_unix` — JSON integer `>= 0`; wall-clock freshness (§6.3)

`cleanup_authority_mismatch` is used only for cross-field equality failures
after formats are valid (trusted_root string equality; plan-bound fields at
step 17). Invalid `attempt_id` → `cleanup_authority_invalid` never mismatch.

### 8.3 `ProcessStopEvidence`

Exact fields depend on `mode`:

**Mode `never_started` — exact field order:**

1. `mode` — exact `"never_started"`
2. `sandbox_instance_id` — 64 lowercase hex; MUST equal evidence instance id

**Mode `stopped` — exact field order:**

1. `mode` — exact `"stopped"`
2. `sandbox_instance_id` — 64 lowercase hex; MUST equal evidence instance id
3. `listeners_cleared` — boolean; MUST be `true`
4. `stop_report_id` — 64 lowercase hex

Any other mode, field order, or value → `process_stop_evidence_invalid`.

### 8.4 Forbidden authority-bearing fields

Reject with `schema_invalid` if any of the following names appear at any nesting
depth:

- `admission_authorized`
- `filesystem_create_authorized`
- `materialization_authorized`
- `wipe_authorized` (use `cleanup_authorized` in §8.2 only)
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

Top-level `execution_authorized=true` /
`process_launch_authorized=true` use dedicated invalid codes (§10).

### 8.5 `SandboxCleanupResult`

`SandboxCleanupResult` MUST be a frozen dataclass with **exactly** these fields
in this order:

1. `ok` — boolean; `true` only on cleanup success
2. `code` — string; stable code from §9
3. `cleanup_profile` — string; see recovery rules below
4. `environment` — string; `DISPOSABLE_TEST` on success; else recovered or empty
5. `network_id` — string; from evidence on success; else empty
6. `chain_id` — string; from evidence on success; else empty
7. `genesis_digest` — string; from evidence on success; else empty
8. `protocol_version` — string; from evidence on success; else empty
9. `materialization_report_id` — string; evidence `report_id` on success; else
   empty
10. `sandbox_instance_id` — string; on success; else empty
11. `data_dir_tag` — string; `l28-disposable-test` on success; else empty
12. `child_name` — string; on success; else empty
13. `cleanup_path` — string; absolute removed path on success; else empty
14. `cleanup_ok` — boolean; `true` only on success; else `false`
15. `process_launch_authorized` — boolean; MUST be `false` on every path
16. `execution_authorized` — boolean; MUST be `false` on every path
17. `report_id` — string; content-derived SHA-256 hex on success; empty on every
    failure
18. `detail` — string; MUST be empty on every success and every failure in v0.1

`cleanup_profile` recovery:

1. On success: exact profile string.
2. On `cleanup_profile_unsupported`: echo recovered string when typed.
3. On any later failure after a conforming profile string was accepted: exact
   profile string.
4. On failures before a typed profile is available: empty string.

### 8.6 Content-derived `report_id` (success only)

On success only, `report_id` MUST be the lowercase hex SHA-256 digest of the
canonical JSON serialization of the accepted request object with exact field
order from §8.1–§8.3 / §7.1; compact separators; `sort_keys=false`;
`ensure_ascii=false`; `allow_nan=false`; UTF-8 bytes.

Failures MUST use empty `report_id` and empty `detail`.

### 8.7 Parse rules

Same family as Foundation 50: `str`/`bytes` only; `≤ 8192` UTF-8 bytes; strict
JSON object; duplicate-key rejection; unknown/reordered fields rejected; hex64
`[0-9a-f]{64}`; no env/`HOME`/tilde/shell expansion.

## 9. Stable codes

| Code | Meaning |
|---|---|
| `cleanup_ok` | Verified tagged disposable directory fully removed |
| `input_type_invalid` | Payload type is not JSON text/bytes |
| `input_too_large` | Encoded size exceeds `8192` bytes |
| `encoding_invalid` | Invalid UTF-8 |
| `json_invalid` | Malformed JSON / non-finite number |
| `duplicate_key` | Duplicate JSON object key |
| `invalid_top_level` | Top-level value is not an object |
| `schema_invalid` | Missing/unknown/reordered/wrong-type fields or forbidden authority field |
| `cleanup_profile_unsupported` | `cleanup_profile` is not this profile |
| `environment_invalid` | Environment is not `DISPOSABLE_TEST` (generic) |
| `historical_import_forbidden` | Environment is MAIN/CANONICAL/HISTORICAL/PRODUCTION |
| `execution_authorized_invalid` | Top-level `execution_authorized` is not boolean `false` |
| `process_launch_authorized_invalid` | Top-level `process_launch_authorized` is not boolean `false` |
| `cleanup_authority_invalid` | Authority object missing/false/malformed, or `attempt_id` format invalid |
| `cleanup_authority_mismatch` | Authority `trusted_root` or evidence-bound fields disagree (never `attempt_id`) |
| `cleanup_authority_expired` | `not_after_unix` wall-clock freshness check failed |
| `process_stop_evidence_invalid` | Process-stop proof missing/malformed/mismatched |
| `materialization_evidence_invalid` | Frozen F51 projection is not exact success evidence |
| `trusted_root_invalid` | Trusted-root lexical, normalization, existence, type, or symlink defect |
| `target_identity_invalid` | Target path/name/tag/identity does not match frozen F51 evidence |
| `traversal_rejected` | Traversal/NUL/alternate-separator defect on derived target path |
| `containment_failure` | Target is not a direct governed descendant of the trusted root |
| `symlink_rejected` | Symlink or special non-file/non-directory object on target or in survey |
| `substitution_ambiguous` | Mount/device/inode substitution ambiguity (including walk-time `st_dev` mismatch) |
| `untagged_or_protected_path` | Path fails tagged-disposable-only / protected-path rules |
| `target_absent` | Target does not exist (not success; fail closed) |
| `tree_limit_exceeded` | Entry count or depth exceeds §5 maxima |
| `exclusive_cleanup_failed` | First constrained delete operation failed before any successful unlink |
| `cleanup_partial_failed` | Deletion began; target or residue still present at post-check |
| `post_cleanup_verification_failed` | No residue detected after completed delete, but a post-cleanup invariant failed |
| `internal_error` | Sanitized unexpected failure |

**Inventory:** **31** distinct result `code` values (including success).

## 10. Deterministic first-failure validation precedence

A conforming future cleaner MUST stop at the first failure:

1. Unsupported payload type (`input_type_invalid`).
2. Encoded size `>` `8192` (`input_too_large`).
3. Invalid UTF-8 (`encoding_invalid`).
4. Malformed JSON / non-finite (`json_invalid`); duplicate keys
   (`duplicate_key`); non-object top-level (`invalid_top_level`).
5. Missing/unknown/reordered/wrong-type **top-level fields** not assigned below
   (`schema_invalid`). Nested values that are **missing or not JSON objects**
   for `cleanup_authority`, `process_stop_evidence`, or
   `materialization_evidence` fail here as `schema_invalid`. Nested objects
   present as objects but failing dedicated field validation use later codes
   once outer shape is accepted (Foundation 50 typing pattern).
6. Unsupported `cleanup_profile` (`cleanup_profile_unsupported`).
7. Forbidden environment labels (`historical_import_forbidden`).
8. Other non-`DISPOSABLE_TEST` environment (`environment_invalid`).
9. Request `execution_authorized` not boolean `false`
   (`execution_authorized_invalid`).
10. Request `process_launch_authorized` not boolean `false`
    (`process_launch_authorized_invalid`).
11. Forbidden authority-bearing fields anywhere (`schema_invalid`).
12. `cleanup_authority` object/schema/formats; `cleanup_authorized is true`;
    `attempt_id` hex64 (`cleanup_authority_invalid`). No evidence inspect.
13. Pre-evidence trusted-root bind:
    (a) request `trusted_root` §12 canonical lexical rules →
    `trusted_root_invalid`;
    (b) authority `trusted_root` exact equality →
    `cleanup_authority_mismatch`.
14. `not_after_unix` freshness (`cleanup_authority_expired`).
15. `process_stop_evidence` per §8.3 (`process_stop_evidence_invalid`).
16. Frozen Foundation 51 materialization evidence per §7.1
    (`materialization_evidence_invalid`).
17. Evidence-bound authority equality: `sandbox_instance_id`, `data_dir_tag`,
    `materialization_report_id` (`cleanup_authority_mismatch`). `attempt_id`
    never compared. Also require process-stop `sandbox_instance_id` equals
    evidence instance (if not already enforced in step 15 structural checks,
    enforce here as `process_stop_evidence_invalid`).
18. Remaining §12 **filesystem** trusted-root preconditions
    (`trusted_root_invalid`).
19. Bind target = evidence `materialization_path`; require
    `child_name` / path / tag consistency (`target_identity_invalid`).
20. Derived-path traversal/NUL/alternate-separator (`traversal_rejected`).
21. Direct-child containment vs trusted root (`containment_failure`).
22. Symlink on target (pre-delete) (`symlink_rejected`).
23. Mount/device/inode substitution on target/parent vs trusted root
    (`substitution_ambiguous`).
24. Tagged-disposable-only / protected-path rules
    (`untagged_or_protected_path`).
25. Target must exist as a directory (`target_absent` if missing).
26. Pre-walk survey without deletion, first defect wins:
    (a) entry count or depth above maxima → `tree_limit_exceeded`;
    (b) symlink → `symlink_rejected`;
    (c) special non-file/non-directory object → `symlink_rejected`;
    (d) walk-time `st_dev` mismatch → `substitution_ambiguous`.
    Survey NEVER returns `exclusive_cleanup_failed`.
27. Perform constrained deletion (§6.1 / §13). Failure of the first delete
    operation before any successful unlink → `exclusive_cleanup_failed`.
28. Post-cleanup verification (§6.4 / §13):
    (a) If deletion began and the target or any residue remains →
    `cleanup_partial_failed`;
    (b) Else if deletion completed with no detected residue, but trusted-root
    identity/absence invariants fail → `post_cleanup_verification_failed`.
29. Unexpected exception → `internal_error` with empty `detail`.
30. Otherwise success: `ok=true`, `code=cleanup_ok`, `cleanup_ok=true`, both
    authority flags false, content-derived `report_id`, empty `detail`.

Every failure path MUST return empty `report_id` and empty `detail`. Success
MUST keep `execution_authorized=false` and `process_launch_authorized=false`.
MUST NOT wipe-as-create.

## 11. Exact meaning of success

When `code=cleanup_ok` and `cleanup_ok=true`:

1. Frozen F51 `materialization_ok` evidence was accepted structurally.
2. Explicit F52 cleanup authority was present, fresh, and correctly bound.
3. Process-stop proof was accepted (`never_started` or `stopped`).
4. The target path was a verified direct tagged disposable child of the trusted
   root and has been fully removed.
5. No process launch/admission/spend/network/ledger authority was granted.
6. F38 post-wipe genesis revalidation remains a deferred duty before reuse
   (§6.5 / §15).

## 12. Trusted-root and target binding

### 12.1 Trusted root (exclusive code: `trusted_root_invalid`)

Every trusted-root defect maps **exclusively** to `trusted_root_invalid`.
Derived-path codes MUST NOT be used for trusted-root defects.

#### Canonical lexical policy (before authority equality)

**POSIX is the normative cleanup platform for v0.1.** Conforming implementations
MUST provide the full §10–§13 guarantees on POSIX. Windows absolute forms
(drive/UNC) are **out of normative scope** for this profile version; a cleaner
MAY reject non-POSIX absolute roots as `trusted_root_invalid` rather than
emulating Windows path grammar.

Reject (do not rewrite) non-canonical forms:

1. Non-empty string; absolute POSIX path (starts with `/`).
2. No NUL; no `.` / `..` segments; no trailing separators except filesystem root
   `/`; no redundant separators; no `\` alternate separators.
3. No `HOME`, tilde, environment, shell, cwd, or variable expansion.

Authority `trusted_root` MUST equal that exact validated string.

#### Filesystem preconditions

4. Exists; is a directory; is not a symlink; no symlink in ancestry.

Lexical prefix comparison alone is never sufficient for containment.

### 12.2 Target identity

1. `cleanup_path` / delete target MUST equal evidence `materialization_path`
   exactly (after the same lexical absolute-path discipline as F50 for the
   evidence path string; relative evidence paths are
   `materialization_evidence_invalid`).
2. `child_name` MUST equal `l28-disposable-test-{sandbox_instance_id}`.
3. Target MUST be the direct child `trusted_root / child_name`.
4. `path_lexeme` remains correlation-only and MUST NOT select the delete path.
5. Protected paths (historical archives, continuity manifests, repository roots
   not equal to the verified target, untagged names) →
   `untagged_or_protected_path`.

## 13. Race-resistant constrained cleanup algorithm

After §10 steps 1–26 succeed:

1. **Re-check (no-follow):** `lstat` target; require directory, not symlink;
   parent directory inode equals trusted-root inode from step 18; `st_dev`
   matches; basename equals `child_name`.
2. **Survey (no deletion):** no-follow walk with exclusive codes from §10
   step 26 / §6.1 item 2. Do not unlink during survey.
3. **Delete:** bottom-up unlink/rmdir per §6.1 only inside the target. First
   operation failure before any successful unlink →
   `exclusive_cleanup_failed`. Mid-delete abort after any successful unlink
   with residue remaining → `cleanup_partial_failed` (do not wait for a later
   post-check to reclassify).
4. **Post-check after a completed delete attempt that reports no residue:**
   `lstat` target must indicate absence; trusted root still exists as the same
   directory inode/device from step 18. If residue/target is still present →
   `cleanup_partial_failed` (deletion began path). If no residue is detected
   but trusted-root identity/absence invariants fail →
   `post_cleanup_verification_failed`.
5. MUST NOT expand the wipe set. MUST NOT delete the trusted root. MUST NOT
   wipe-as-create.

## 14. Security invariants

1. At most one target tree is deleted per successful attempt.
2. No parent deletion; no symlink following; no env/`HOME`/tilde expansion.
3. No wipe without frozen F51 success evidence and F52 cleanup authority.
4. No wipe without process-stop proof.
5. Both `execution_authorized` and `process_launch_authorized` always false.
6. Forbidden authority fields never succeed.
7. Lexical prefix checks never suffice for containment.
8. Partial cleanup never reports `cleanup_ok`.
9. Success never implies process launch, admission, spend, mining, networking,
   ledger mutation, deployment, SovereignBrain authority, or genesis
   revalidation completion.
10. Protected Protocol v1.0.0 economic facts remain unchanged.

## 15. F38 post-wipe and deferred work

### 15.1 F38 post-wipe (deferred executable duty)

Per `docs/disposable_network_identity_genesis_binding_v0.1.md` — Reset /
cleanup requirements:

1. Wipe only directories tagged `data_dir_tag=l28-disposable-test` (enforced
   here via child-name/tag binding).
2. Never touch historical archives, continuity manifests, or untagged paths
   (enforced via `untagged_or_protected_path` and containment).
3. **After wipe, genesis/identity revalidation before reuse** is REQUIRED by
   F38 and is **not** performed by Foundation 52/53. A later foundation or
   operator runbook owns that step.

### 15.2 Explicit deferred work

- Foundation 53 cleaner module/tests/record;
- F37-06 process launch and authentic `stopped` evidence producers;
- Broader F37-13 health endpoints / networked graceful shutdown CLI;
- Genesis revalidation automation after wipe;
- Package exports via `coin/__init__.py`.

## 16. Test obligations for future Foundation 53

A Foundation 53 implementation MUST provide focused tests proving at least:

1. Success path returns `cleanup_ok` with both authority flags false.
2. Every non-success code in §9 is reachable by a concrete first-failure case.
3. Exact public inventory equals the 31 codes.
4. Parse/schema/duplicate-key/size/encoding cases.
5. Forbidden authority fields rejected at every nesting level.
6. Missing/false/mismatched/expired cleanup authority; bad `attempt_id`.
7. Both process-stop modes; invalid stop evidence.
8. Invalid F51 projection (including zero instance id and wrong code).
9. Relative/env/tilde trusted roots rejected; symlink ancestry rejected.
10. Target mismatch, traversal, containment, symlink, substitution, absent,
    tree-limit, exclusive-fail, partial-fail, post-check fail.
11. `path_lexeme` never selects the delete path.
12. Constrained delete never follows symlinks and never deletes trusted root.
13. Deterministic success `report_id`; empty failure `report_id`/`detail`.
14. Result immutability; no F51 materializer re-entry; no Leap28/Nova;
    no network/wallet/mining/ledger mutation APIs.

Harnesses MAY materialize a disposable child under a temporary trusted root
using Foundation 51 **only inside tests**, then invoke cleanup. Production
cleaner MUST NOT invent trusted roots.

## 17. Protected-file and protocol non-effects

Foundation 52 MUST NOT modify or authorize modification of:

- `PROTOCOL.md` and Protocol v1.0.0 economic constants;
- `coin/tx_validation.py` protected facts;
- historical continuity manifests/archives;
- `coin/l28_coin.py` or `coin/__init__.py`;
- Foundations 38–51 locked modules/documents (consume frozen evidence only).

Protected economic facts (unchanged):

| Fact | Value |
|---|---:|
| Hard cap | `28_000_000` L28 |
| Emission ceiling | `11_130_000` L28 |
| Halving interval | `210_000` |
| Reward sequence | `28 → 14 → 7 → 3 → 1 → 0` |

## 18. Recommended future implementation scope (Foundation 53-class)

If Foundation 52 is locked, a later implementation foundation MAY implement
**only**:

1. `coin/disposable_sandbox_directory_cleanup.py`;
2. `tests/test_disposable_sandbox_directory_cleanup.py`;
3. one narrow implementation record document.

That implementation MUST keep both authority flags false on every path, MUST
reject all §8.4 forbidden fields, MUST NOT call Foundation 51 materialization
APIs from production authority paths, MUST NOT implement genesis revalidation,
MUST NOT modify `coin/l28_coin.py` or `coin/__init__.py`, and MUST NOT
introduce Leap28/Nova coupling.

## Security boundary and non-authorization statement

A completed Foundation 52 specification, and any later successful cleanup under
this profile, is disposable sandbox directory **cleanup evidence** only. It is
not permission to spend L28, not peer admission, not process creation, not
authority to wipe unrelated paths, and not authorization to start a node,
network, miner, wallet, or testnet. It does not complete F38 genesis
revalidation after wipe.

`execution_authorized` MUST remain the JSON boolean `false` on every conforming
request and every success or failure result path.

`process_launch_authorized` MUST remain the JSON boolean `false` on every
conforming request and every success or failure result path.

`admission_authorized` MUST NOT exist.

`filesystem_create_authorized` MUST NOT exist.
