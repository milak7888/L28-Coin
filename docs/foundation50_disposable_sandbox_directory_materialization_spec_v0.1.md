# L28 Disposable Sandbox Directory Materialization Specification v0.1

**Foundation:** 50

**Status:** Offline specification only; non-activation

**Milestone label:** F37-06 exclusive disposable sandbox directory materialization
contract (partial slice; specification only)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN) — immutable

**Profile:** `l28-disposable-sandbox-directory-materialization/v0.1`

## 1. Purpose, status, terminology, and non-goals

Foundation 50 defines the locked specification for **governed materialization** of
exactly one disposable sandbox data directory from caller-supplied frozen
Foundation 49 creation-plan success evidence, an explicit Foundation 50
materialization-authority binding, and a caller-supplied absolute trusted root.

This foundation is a **partial M2 / F37-06 specification slice**. It does
**not** implement or invoke filesystem mutation in this milestone; it locks the
contract that a later Foundation 51-class materializer MUST obey. It does
**not** complete F37-06, F37-13, or Foundation 37 M2.

### Terminology

| Term | Meaning in this specification |
|---|---|
| Materialization (F50) | Exclusive create-new of one disposable directory under a trusted root |
| Frozen F49 plan evidence | Exact Foundation 49 success result projection (`code=creation_plan_ok`, …) |
| Materialization authority | Caller-supplied F50 authority object binding root, instance, tag, plan report, and attempt; outside the F49 result |
| Trusted root | Caller-supplied absolute, pre-existing, non-symlink directory that is the only allowed parent |
| Child name | Deterministic directory name derived from frozen plan fields |
| Materialization path | Absolute path `trusted_root / child_name` after platform join rules in §11 |
| Path lexeme | Opaque F49 correlation string; **not** filesystem create authority |
| Future materializer | Foundation 51-class implementation of this contract |

### Non-goals

Foundation 50 MUST NOT and does not:

- implement `coin/disposable_sandbox_directory_materialization.py` or any tests;
- create, inspect, delete, wipe, or clean directories in this docs-only milestone;
- spawn processes, threads, async workers, subprocesses, daemons, services, or
  containers;
- open sockets or perform transport, discovery, synchronization, or propagation;
- authorize spend, admission, mining, consensus, tip authority, issuance,
  deployment, or SovereignBrain control;
- rerun Foundation 39, 45, 47, or 49 evaluation;
- call Foundation 21 `transition` or define another lifecycle state machine;
- depend on Foundations 40–43;
- modify or revive `coin/l28_coin.py`;
- claim F37-06, F37-13, or M2 completion;
- introduce Leap28 or Nova coupling.

### Non-authority statement

A conforming Foundation 50 evaluation, and any later successful materialization
under this profile:

- MUST set `execution_authorized` to the JSON/boolean `false` on every path;
- MUST set `process_launch_authorized` to the JSON/boolean `false` on every
  path;
- MUST NOT define, require, or grant `admission_authorized`;
- MUST NOT define, require, or grant `filesystem_create_authorized` (F48/F49
  forbidden field remains forbidden wherever nested);
- MUST NOT grant wipe, process, node, miner, wallet, network, transaction,
  ledger, consensus, deployment, or SovereignBrain authority;
- MUST NOT mean that a Core process is runnable, launched, or admitted;
- is disposable sandbox directory **materialization evidence** only when
  `code=materialization_ok`.

## 2. Frozen dependency chain

| Layer | Role |
|---|---|
| F38 / F39 | Identity constants; `data_dir_tag=l28-disposable-test`; wipe-tag rules |
| F44 / F45 | Offline lifecycle policy (frozen inside upstream F47 evidence) |
| F46 / F47 | Entrypoint preflight; frozen success consumed by F49 |
| F48 / F49 | Creation-plan contract/evaluator; frozen `creation_plan_ok` evidence |
| F48 §10 | Normative deferred filesystem obligations implemented by this profile |
| **F50 (this document)** | Materialization schemas, authority, algorithms, codes, precedence |
| Future F51 | Pure materializer module + focused tests + implementation record |
| Later F37-13 | Successful-directory wipe/reset tooling (not F50) |

### Prerequisites consumed (frozen evidence only)

| Prerequisite | How Foundation 50 consumes it |
|---|---|
| Foundation 49 success | Frozen `SandboxCreationPlanResult` projection; structural equality only |
| Foundation 48 §10 | Normative create/containment/permission/collision/tag obligations |
| Foundation 38 wipe tags | Cleanup ownership handoff rules for successful directories |
| Foundation 39 constants | Compared by value via frozen F49 projection and authority bindings |

Foundation 50 MUST NOT call
`evaluate_sandbox_directory_creation_plan_json`,
`evaluate_core_entrypoint_preflight_json`, Foundation 45 policy APIs, or
Foundation 21 `transition`.

## 3. Trust and threat model

### Trust assumptions

1. The caller supplies an already-approved absolute trusted root directory.
2. The caller supplies a distinct Foundation 50 materialization-authority object
   that is not embedded inside the F49 result.
3. Frozen F49 evidence is treated as untrusted bytes until structural validation
   succeeds.
4. The operating system provides race-resistant exclusive-create primitives
   (`O_CREAT\|O_EXCL` directory create or equivalent).

### Threats in scope

- Path traversal and containment escape
- Symlink and mount-substitution attacks on root, parents, or target
- TOCTOU races between existence check and create
- Reuse or overwrite of pre-existing targets
- Authority forgery via mismatched report_id / instance_id / tag / root
- Accidental recursive parent creation
- Wipe-as-create or recursive delete of unverified paths
- Authority field smuggling (`admission_authorized`,
  `filesystem_create_authorized`, wipe/process/network flags)

### Threats explicitly out of scope

- Multi-tenant OS isolation beyond restrictive directory mode `0700`
- Remote attestation of the host
- Encrypted filesystem guarantees
- Process sandboxing after directory creation

## 4. Future public API

A later Foundation 51-class implementation MUST expose exactly:

```text
materialize_disposable_sandbox_directory_json(
    payload: str | bytes,
) -> SandboxMaterializationResult
```

Module path (locked for later implementation):

`coin/disposable_sandbox_directory_materialization.py`

`SandboxMaterializationResult` MUST be an immutable frozen dataclass.

Foundation 50 itself creates **no** module and **no** tests.

## 5. Normative constants

| Constant | Exact value |
|---|---|
| Profile / `materialization_profile` | `l28-disposable-sandbox-directory-materialization/v0.1` |
| Upstream plan profile | `l28-disposable-sandbox-directory-creation/v0.1` |
| Environment | `DISPOSABLE_TEST` |
| Network id | `l28-disposable-test/v0.1` |
| Protocol version | `l28-protocol/1.0.0` |
| Data-dir tag | `l28-disposable-test` |
| Accepted F49 result code | `creation_plan_ok` |
| Maximum encoded request size | `8192` bytes |
| Directory mode | `0700` (owner rwx only) |
| Zero instance sentinel | `0000000000000000000000000000000000000000000000000000000000000000` |
| Forbidden environments | `MAIN`, `CANONICAL`, `HISTORICAL`, `PRODUCTION` |

No environment-variable, `HOME`, tilde, shell, or variable expansion is
permitted anywhere in this profile.

## 6. Frozen Foundation 49 plan-evidence projection

### 6.1 Exact field order

`plan_evidence` MUST be a JSON object with **exactly** these fields in this
order:

1. `ok` — boolean `true`
2. `code` — exact `"creation_plan_ok"`
3. `creation_profile` — exact `"l28-disposable-sandbox-directory-creation/v0.1"`
4. `environment` — exact `"DISPOSABLE_TEST"`
5. `network_id` — exact `"l28-disposable-test/v0.1"`
6. `chain_id` — 64 lowercase hexadecimal characters
7. `genesis_digest` — 64 lowercase hexadecimal characters
8. `protocol_version` — exact `"l28-protocol/1.0.0"`
9. `preflight_report_id` — 64 lowercase hexadecimal characters
10. `sandbox_instance_id` — 64 lowercase hexadecimal characters; MUST NOT equal
    the zero instance sentinel
11. `path_lexeme` — non-empty string (`strip() != ""`); opaque correlation only
12. `creation_plan_ok` — boolean `true`
13. `process_launch_authorized` — boolean `false`
14. `execution_authorized` — boolean `false`
15. `report_id` — 64 lowercase hexadecimal characters
16. `detail` — exact empty string `""`

### 6.2 Structural-only consumption

Foundation 50:

- MUST treat this object as caller-supplied frozen evidence;
- MUST NOT call Foundation 49 evaluation APIs;
- MUST NOT re-validate Foundation 47/45/39 projections inside the plan;
- MUST reject any deviation from §6.1 with `plan_evidence_invalid`.

## 7. Request and authority schemas

### 7.1 `SandboxMaterializationRequest`

Exact top-level fields in this order:

1. `materialization_profile` — string; MUST equal this profile (§5)
2. `environment` — string; MUST equal `DISPOSABLE_TEST` after forbidden-label
   rejection (§9)
3. `plan_evidence` — frozen Foundation 49 success projection (§6.1)
4. `materialization_authority` — `MaterializationAuthority` (§7.2)
5. `trusted_root` — string; absolute trusted-root path (§11)
6. `execution_authorized` — boolean; MUST be `false`
7. `process_launch_authorized` — boolean; MUST be `false`

Maximum encoded size: `8192` bytes.

### 7.2 `MaterializationAuthority`

Exact fields in this order:

1. `materialization_authorized` — boolean; MUST be `true` for materialization to
   proceed (defaults to absent → fail closed as invalid)
2. `trusted_root` — string; MUST equal top-level `trusted_root` exactly after
   the top-level value has passed §11.1 canonical lexical validation
3. `sandbox_instance_id` — 64 lowercase hex; MUST equal
   `plan_evidence.sandbox_instance_id` (equality checked only at §9 step 16)
4. `data_dir_tag` — exact `"l28-disposable-test"` (equality checked only at §9
   step 16)
5. `plan_report_id` — 64 lowercase hex; MUST equal `plan_evidence.report_id`
   (equality checked only at §9 step 16)
6. `attempt_id` — 64 lowercase hex; required format and single-attempt identity
   only. It has **no** external cross-field binding target. Invalid format or
   wrong type → `materialization_authority_invalid` (never
   `materialization_authority_mismatch`)
7. `not_after_unix` — JSON integer `>= 0`; exclusive upper bound in Unix seconds
   for authority freshness

`materialization_authorized=false`, missing/unknown/reordered/wrong-type
authority fields, non-hex `attempt_id` / pre-plan hex fields, or wrong-type
`trusted_root` / `not_after_unix` fail with
`materialization_authority_invalid`.

`materialization_authority_mismatch` is used only when authority field formats
are already valid and a cross-field equality fails:

- authority `trusted_root` ≠ request `trusted_root` (after §11.1 lexical
  validation of the request value); or
- after plan acceptance: authority `sandbox_instance_id`, `data_dir_tag`, or
  `plan_report_id` disagrees with accepted plan evidence.

**Accepted product decision (wall-clock freshness):** If the implementer’s OS
clock reports a current Unix time `>= not_after_unix`, fail with
`materialization_authority_expired`. The same accepted request may therefore
succeed or expire depending on wall-clock time. Success `report_id` remains
deterministic for an identical accepted request object.

### 7.3 Forbidden authority-bearing fields

Reject with `schema_invalid` if any of the following names appear at any nesting
depth in the request:

- `admission_authorized`
- `filesystem_create_authorized`
- `wipe_authorized`
- `cleanup_authorized`
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

Presence of `execution_authorized=true` or `process_launch_authorized=true` at
the top level uses the dedicated invalid codes in §9 (not `schema_invalid`).

### 7.4 `SandboxMaterializationResult`

`SandboxMaterializationResult` MUST be a frozen dataclass with **exactly** these
fields in this order:

1. `ok` — boolean; `true` only on materialization success
2. `code` — string; stable code from §8
3. `materialization_profile` — string; see recovery rules below
4. `environment` — string; `DISPOSABLE_TEST` on success; else recovered or empty
5. `network_id` — string; from accepted plan evidence on success; else empty
6. `chain_id` — string; from accepted plan evidence on success; else empty
7. `genesis_digest` — string; from accepted plan evidence on success; else empty
8. `protocol_version` — string; from accepted plan evidence on success; else
   empty
9. `plan_report_id` — string; from accepted plan evidence `report_id` on
   success; else empty
10. `sandbox_instance_id` — string; from accepted plan evidence on success; else
    empty
11. `data_dir_tag` — string; `l28-disposable-test` on success; else empty
12. `path_lexeme` — string; from accepted plan evidence on success; else empty
    (correlation-only; never a create path)
13. `child_name` — string; derived child name on success; else empty
14. `materialization_path` — string; absolute created path on success; else empty
15. `materialization_ok` — boolean; `true` only on success; else `false`
16. `process_launch_authorized` — boolean; MUST be `false` on every path
17. `execution_authorized` — boolean; MUST be `false` on every path
18. `report_id` — string; 64 lowercase hex content-derived id on success; empty
    on every failure
19. `detail` — string; MUST be empty string on every success and every failure
    in v0.1 (no paths, errno text, or secrets)

`materialization_profile` recovery:

1. On success: exact profile string.
2. On `materialization_profile_unsupported`: echo recovered string when typed.
3. On any later failure after a conforming profile string was accepted: exact
   profile string.
4. On failures before a typed profile is available: empty string.

No `admission_authorized` or `filesystem_create_authorized` field exists.

### 7.5 Content-derived `report_id` (success only)

On success only, `report_id` MUST be the lowercase hex SHA-256 digest of the
canonical JSON serialization of the accepted request object with:

- exact field order from §7.1 / §7.2 / §6.1;
- compact separators (`,` and `:`);
- no insignificant whitespace;
- `sort_keys=false`;
- `ensure_ascii=false`;
- `allow_nan=false`;
- UTF-8 encoding;
- SHA-256 over those UTF-8 bytes.

Failures MUST use empty `report_id` and empty `detail`.

### 7.6 Parse, encoding, size, duplicate-key, and type rules

1. Payload type MUST be JSON text (`str`) or UTF-8 `bytes` only.
2. Encoded size MUST be `≤ 8192` bytes.
3. Byte payloads MUST be valid UTF-8.
4. JSON MUST be well-formed; non-finite numbers rejected.
5. Duplicate object keys at any depth rejected (`duplicate_key`).
6. Top-level JSON value MUST be an object.
7. Unknown, missing, or reordered fields rejected under §9 codes.
8. Canonical constants MUST match exactly (case-sensitive).
9. Hex digests MUST be exactly 64 characters from `[0-9a-f]`.
10. No environment, `HOME`, tilde, shell, or variable expansion.

## 8. Stable codes

| Code | Meaning |
|---|---|
| `materialization_ok` | Exclusive disposable directory created and post-verified |
| `input_type_invalid` | Payload type is not JSON text/bytes |
| `input_too_large` | Encoded size exceeds `8192` bytes |
| `encoding_invalid` | Invalid UTF-8 |
| `json_invalid` | Malformed JSON / non-finite number |
| `duplicate_key` | Duplicate JSON object key |
| `invalid_top_level` | Top-level value is not an object |
| `schema_invalid` | Missing/unknown/reordered/wrong-type fields or forbidden authority field present |
| `materialization_profile_unsupported` | `materialization_profile` is not this profile |
| `environment_invalid` | Environment is not `DISPOSABLE_TEST` (generic) |
| `historical_import_forbidden` | Environment is MAIN/CANONICAL/HISTORICAL/PRODUCTION |
| `execution_authorized_invalid` | Top-level `execution_authorized` is not boolean `false` |
| `process_launch_authorized_invalid` | Top-level `process_launch_authorized` is not boolean `false` |
| `materialization_authority_invalid` | Authority object missing/false/malformed, or `attempt_id` format invalid |
| `materialization_authority_mismatch` | Authority `trusted_root` or plan-bound fields disagree (never `attempt_id`) |
| `materialization_authority_expired` | `not_after_unix` wall-clock freshness check failed |
| `plan_evidence_invalid` | Frozen F49 projection is not exact success evidence |
| `trusted_root_invalid` | Trusted-root lexical, normalization, existence, type, or symlink defect (§11.1) |
| `plan_binding_invalid` | Accepted plan fields cannot form a governed child name |
| `traversal_rejected` | Traversal/NUL/alternate-separator defect on derived child/materialization path |
| `containment_failure` | Derived target would not remain a direct governed descendant of the trusted root |
| `symlink_rejected` | Symlink detected on derived child/materialization path or post-create target |
| `substitution_ambiguous` | Mount/substitution/alias ambiguity on derived child/materialization path |
| `target_collision` | Target already exists |
| `exclusive_create_failed` | Exclusive create-new failed for a non-collision reason |
| `permission_verification_failed` | Mode/ownership/type failed after create; created dir rolled back |
| `post_create_verification_failed` | Identity/containment failed after create; created dir rolled back |
| `rollback_failed` | Post-create defect found and the created directory could not be rolled back |
| `internal_error` | Sanitized unexpected failure |

**Inventory:** **29** distinct result `code` values (including success).

## 9. Deterministic first-failure validation precedence

A conforming future materializer MUST stop at the first failure:

1. Reject unsupported payload type (`input_type_invalid`).
2. Reject encoded size `>` `8192` bytes (`input_too_large`).
3. Reject invalid UTF-8 (`encoding_invalid`).
4. Reject malformed JSON / non-finite numbers (`json_invalid`); duplicate keys
   (`duplicate_key`); non-object top-level (`invalid_top_level`).
5. Reject missing/unknown/reordered/wrong-type **top-level fields** not assigned
   below (`schema_invalid`). Nested objects present as objects but failing
   dedicated steps use later codes once outer shape is accepted.
6. Reject unsupported `materialization_profile`
   (`materialization_profile_unsupported`).
7. If `environment` ∈ `{MAIN, CANONICAL, HISTORICAL, PRODUCTION}`, fail with
   `historical_import_forbidden`.
8. Else if `environment` ≠ `DISPOSABLE_TEST`, fail with `environment_invalid`.
9. If request `execution_authorized` is not boolean `false`, fail with
   `execution_authorized_invalid`.
10. If request `process_launch_authorized` is not boolean `false`, fail with
    `process_launch_authorized_invalid`.
11. If any forbidden authority-bearing field from §7.3 is present anywhere, fail
    with `schema_invalid`.
12. Validate `materialization_authority` object/schema and field formats only:
    exact field order and types; `materialization_authorized` is exactly
    boolean `true`; `attempt_id` is 64 lowercase hex (single-attempt identity;
    no external bind); other authority strings/integers have valid types and,
    where applicable, hex-64 format. Failures →
    `materialization_authority_invalid`. Do **not** inspect plan evidence here.
13. Pre-plan trusted-root bind (exact; no plan evidence):
    (a) validate the request `trusted_root` against §11.1 canonical **lexical**
    rules (absolute form; no NUL; no `.`/`..` segments; no trailing separators
    except filesystem root `/`; no redundant separators / non-canonical lexical
    forms; no HOME/tilde/env/shell/cwd/variable expansion). Any defect →
    `trusted_root_invalid`.
    (b) require authority `trusted_root` exactly equals that validated request
    string. Inequality → `materialization_authority_mismatch`.
14. Enforce `not_after_unix` wall-clock freshness
    (`materialization_authority_expired`) — accepted product decision per §7.2.
15. Validate frozen Foundation 49 plan evidence per §6.1
    (`plan_evidence_invalid`).
16. Plan-bound authority equality only: authority `sandbox_instance_id`,
    `data_dir_tag`, and `plan_report_id` MUST equal accepted plan evidence
    (`sandbox_instance_id`, implied/`l28-disposable-test` tag, and `report_id`).
    Any inequality → `materialization_authority_mismatch`. `attempt_id` is
    never compared here.
17. Validate remaining §11.1 **filesystem** trusted-root preconditions
    (exists; is a directory; is not a symlink; no symlink components in its
    ancestry for this attempt). Any defect → `trusted_root_invalid`.
18. Derive child name / materialization path per §11.2–§11.3; on local
    derivation impossibility → `plan_binding_invalid`.
19. Reject traversal / NUL / alternate-separator defects on the **derived**
    `child_name` / `materialization_path` only (`traversal_rejected`). Trusted-
    root lexical defects remain step 13 / `trusted_root_invalid`.
20. Prove pre-create containment of the derived target as a direct governed
    descendant of the trusted root (`containment_failure`).
21. Reject symlink components on the **derived** child/materialization path
    (pre-create) (`symlink_rejected`). Trusted-root symlink defects remain
    step 17 / `trusted_root_invalid`.
22. Reject mount/substitution/alias ambiguity on the **derived**
    child/materialization path (`substitution_ambiguous`).
23. Reject pre-existing target (`target_collision`).
24. Perform exclusive create-new (`exclusive_create_failed` on non-collision
    create failure).
25. Verify permissions/ownership/type of the created child. On failure: roll
    back only this attempt’s created directory; if rollback succeeds →
    `permission_verification_failed`; if rollback fails → `rollback_failed`.
26. Continue post-create checks on the created child. On each defect: roll back
    only this attempt’s created directory; if rollback fails →
    `rollback_failed`; if rollback succeeds, return the first defect code:
    (a) symlink on the created child → `symlink_rejected`;
    (b) mount/substitution/alias ambiguity on the created child →
    `substitution_ambiguous`;
    (c) identity or containment failure → `post_create_verification_failed`.
27. Unexpected implementer exception → `internal_error` with empty `detail`.
28. Otherwise success: `ok=true`, `code=materialization_ok`,
    `materialization_ok=true`, both authority flags false, content-derived
    `report_id`, empty `detail`.

Steps 25–26 apply only after a directory was created by step 24. Rollback MUST
never delete a pre-existing path and MUST never recurse into unverified trees.
If rollback fails after any step-25/26 defect, the returned code is
`rollback_failed` rather than the underlying verification code.

Every failure path MUST return empty `report_id` and empty `detail`. Success
MUST keep `execution_authorized=false` and `process_launch_authorized=false`.

## 10. Exact meaning of success

When `code=materialization_ok` and `materialization_ok=true`:

1. Frozen F49 `creation_plan_ok` evidence was accepted structurally.
2. Explicit F50 materialization authority was present, fresh, and correctly bound.
3. Exactly one new directory exists at `materialization_path`.
4. The directory is a direct governed descendant of the trusted root.
5. Mode is `0700` and type is directory; post-create checks passed.
6. `execution_authorized` and `process_launch_authorized` remain false.
7. No process was started; no wipe tooling was invoked; no network/wallet/ledger
   authority was granted.
8. Successful-directory cleanup ownership transfers to the separately governed
   F37-13-compatible wipe lifecycle (not executed here).

## 11. Trusted-root and child-path derivation

### 11.1 Trusted root requirements

Every trusted-root defect in this subsection maps **exclusively** to
`trusted_root_invalid`. Codes `traversal_rejected`, `symlink_rejected`,
`containment_failure`, and `substitution_ambiguous` MUST NOT be used for
trusted-root defects; those codes apply only to the derived
child/materialization path (and post-create child checks) per §9 steps 19–22
and §12.

#### Canonical lexical policy (before authority equality)

The request `trusted_root` MUST already be in canonical lexical form. The
materializer MUST **reject** (not rewrite) non-canonical forms:

1. Be a non-empty string.
2. Be an absolute path on the host platform (POSIX: starts with `/`; Windows:
   drive/UNC absolute form). Relative paths → `trusted_root_invalid`.
3. Contain no NUL bytes (`\0`).
4. Contain no `.` or `..` path segments after platform segment split.
5. Reject trailing separators except filesystem root itself (POSIX `/` may end
   with a single `/` only because it **is** the root; any other path MUST NOT
   end with `/` or `\`).
6. Reject redundant separators and other non-canonical lexical forms (for
   example `//var`, `/var//sandbox`, or mixed alternate separators where the
   platform path grammar does not treat them as the canonical absolute form).
7. Perform **no** `HOME`, tilde, environment, shell, cwd, or variable
   expansion, and no configuration discovery or user-controlled fallback.

After the request `trusted_root` passes this lexical policy, authority
`trusted_root` MUST equal that exact validated string (§9 step 13). Root `/`
remains syntactically eligible when otherwise permitted by this contract.

#### Filesystem preconditions (after plan acceptance)

8. Name an existing directory before create.
9. Not be a symbolic link (`lstat`/`O_NOFOLLOW` or equivalent).
10. Have no symlink components in its ancestry for the materialization attempt.

Lexical prefix comparison alone is **never** sufficient for containment.

### 11.2 Child-name derivation

Let:

- `tag = plan_evidence` implied tag / authority `data_dir_tag` =
  `l28-disposable-test`
- `instance = plan_evidence.sandbox_instance_id`

Child name MUST be exactly:

```text
{tag}-{instance}
```

Example:

```text
l28-disposable-test-a1b2...ff
```

The child name MUST match `^[0-9a-z-]+$` after construction and MUST NOT contain
`/`, `\`, `.`, `..`, or NUL. On impossibility → `plan_binding_invalid`.

### 11.3 Materialization path and path_lexeme role

1. `materialization_path` MUST be the platform join of the validated
   `trusted_root` and `child_name` as a **direct child** (one segment).
2. `plan_evidence.path_lexeme` MUST be accepted as a non-empty opaque
   **correlation-only** string and echoed on success.
3. `path_lexeme` MUST NOT be used as the filesystem create target, MUST NOT
   override `trusted_root`, and MUST NOT authorize arbitrary paths.
4. If `path_lexeme` is empty/whitespace-only in frozen evidence, fail at
   `plan_evidence_invalid` (§6.1).
5. Traversal, NUL, alternate-separator, symlink, and substitution checks on the
   derived child/materialization path use §9 steps 19–22 codes only — never
   `trusted_root_invalid`.

## 12. Race-resistant materialization algorithm

A conforming Foundation 51 materializer MUST implement the following sequence
after §9 steps 1–23 succeed:

1. **Pre-check (no-follow):** Using descriptor-relative or `lstat`-equivalent
   no-follow inspection, verify trusted root is a non-symlink directory and that
   `child_name` does not already exist under that root. Existing target →
   `target_collision`.
2. **Exclusive create-new:** Create exactly one new directory as a direct child
   using exclusive create semantics (`mkdir` with exist-fail, or
   `open(... O_CREAT|O_EXCL|O_DIRECTORY)`-equivalent). Do **not** create parents.
   Do **not** use recursive `makedirs`. Do **not** follow symlinks.
3. **Post-check (no-follow):** Re-open/re-`fstat` the created directory without
   following symlinks. Verify:
   - object is a directory;
   - mode is exactly `0700` (after umask-safe create + `fchmod`/`chmod` as needed
     on the created inode only);
   - identity matches expected child name;
   - containment as direct child of the same trusted-root directory inode used
     in pre-check;
   - no symlink substitution occurred.
4. **Failure rollback:** If post-check fails, remove **only** the directory
   inode created in step 2, and only if it is still the empty directory created
   by this attempt. Never recursively delete. Never delete a pre-existing path.
5. **Success:** Return `materialization_ok` with absolute `materialization_path`.

Collision observed at create time maps to `target_collision` when the failure
mode indicates existence; other exclusive-create failures map to
`exclusive_create_failed`.

## 13. Permissions, ownership, and post-create verification

1. Created directory mode MUST be `0700`.
2. **Accepted product decision (ownership SHOULD):** Implementers SHOULD verify
   owner uid/gid equals the materializer process credentials when the host
   model provides them; mismatch → `permission_verification_failed`. Hosts
   without a uid/gid model MAY omit this check without treating omission as
   success of a failed mode/type check.
3. Result MUST be a directory, not a file, symlink, or special node.
4. Post-create containment MUST confirm the directory’s parent directory inode
   equals the trusted-root directory inode observed at pre-check.
5. `data_dir_tag` binding remains logical metadata via child-name prefix and
   frozen evidence; wipe tooling (later) MUST still honor F38 tag rules.

## 14. Rollback and cleanup ownership

| Situation | Owner | Obligation |
|---|---|---|
| Create succeeded; post-check failed; rollback removed created dir | F50/F51 materializer | Return `post_create_verification_failed` |
| Create succeeded; post-check failed; rollback could not remove created dir | F50/F51 materializer | Return `rollback_failed`; MUST NOT claim success |
| Materialization succeeded | Later F37-13-compatible wipe lifecycle | Owns cleanup/wipe of the successful tagged disposable directory |
| Path existed before attempt | Nobody via F50 create | Fail `target_collision`; never wipe-as-create |

F50 does **not** implement cleanup tooling. Cleanup failure reporting MUST remain
deterministic and MUST NOT grant broader deletion authority.

## 15. Security invariants

1. Exactly zero or one new directory is created per successful attempt (success ⇒
   exactly one).
2. No parent creation; no recursive mkdir; no symlink following.
3. No arbitrary path materialization via `path_lexeme`.
4. No environment/`HOME`/tilde/shell expansion.
5. Both `execution_authorized` and `process_launch_authorized` are always false.
6. Forbidden authority fields never succeed.
7. Lexical prefix checks never suffice for containment.
8. Rollback never recursively deletes unverified or pre-existing paths.
9. Success never implies process launch, admission, spend, mining, networking,
   ledger mutation, deployment, or SovereignBrain authority.
10. Protected Protocol v1.0.0 economic facts remain unchanged.

## 16. Test obligations for future Foundation 51

A Foundation 51 implementation MUST provide focused tests proving at least:

1. Success path returns `materialization_ok` with both authority flags false.
2. Every non-success code in §8 is reachable by a concrete first-failure case.
3. Exact public inventory equals the 29 codes.
4. Parse/schema/duplicate-key/non-finite/size/encoding cases.
5. Forbidden authority fields rejected at every nesting level.
6. Missing/false/mismatched/expired materialization authority cases.
7. Invalid F49 projection cases (including zero instance id and wrong code).
8. Relative/env/tilde trusted roots rejected.
9. Traversal, symlink, substitution, collision, and exclusive-create failures.
10. Permission/post-create verification and rollback distinctions.
11. `path_lexeme` never used as create target.
12. Deterministic success `report_id`; empty failure `report_id`/`detail`.
13. Result immutability.
14. Static hygiene: no Leap28/Nova; no F47/F49 evaluator re-entry for production
    authority; no network/wallet/mining/ledger mutation APIs.

Temporary directories used by tests MUST be created only inside test harness
control and MUST NOT weaken production fail-closed rules.

## 17. Explicit deferred work

Foundation 50 does not specify or implement:

- Foundation 51 materializer module/tests/record;
- F37-13 wipe/reset CLI or recursive cleanup tooling;
- process launch / Core runtime activation;
- tip authority, wallets, issuance wiring;
- transport/sync (M3+);
- multi-sandbox registries;
- package exports via `coin/__init__.py`.

## 18. Protected-file and protocol non-effects

Foundation 50 MUST NOT modify or authorize modification of:

- `PROTOCOL.md` and Protocol v1.0.0 economic constants;
- `coin/tx_validation.py` protected facts;
- historical continuity manifests/archives;
- `coin/l28_coin.py` or `coin/__init__.py`;
- Foundations 38–49 locked modules/documents (consume frozen evidence only).

Protected economic facts (unchanged):

| Fact | Value |
|---|---:|
| Hard cap | `28_000_000` L28 |
| Emission ceiling | `11_130_000` L28 |
| Halving interval | `210_000` |
| Reward sequence | `28 → 14 → 7 → 3 → 1 → 0` |

## 19. Recommended future implementation scope (Foundation 51-class)

If Foundation 50 is locked, a later implementation foundation MAY implement
**only**:

1. `coin/disposable_sandbox_directory_materialization.py`;
2. `tests/test_disposable_sandbox_directory_materialization.py`;
3. one narrow implementation record document.

That implementation MUST keep `execution_authorized=false` and
`process_launch_authorized=false` on every path, MUST reject all §7.3 forbidden
fields, MUST NOT call Foundation 49 evaluation APIs from production authority
paths, MUST NOT implement F37-13 wipe tooling, MUST NOT modify
`coin/l28_coin.py` or `coin/__init__.py`, and MUST NOT introduce Leap28/Nova
coupling.

## Security boundary and non-authorization statement

A completed Foundation 50 specification, and any later successful materialization
under this profile, is disposable sandbox directory **materialization evidence**
only. It is not permission to spend L28, not peer admission, not process
creation, not wipe authority over unrelated paths, and not authorization to
start a node, network, miner, wallet, or testnet.

`execution_authorized` MUST remain the JSON boolean `false` on every conforming
request and every success or failure result path.

`process_launch_authorized` MUST remain the JSON boolean `false` on every
conforming request and every success or failure result path.

`admission_authorized` MUST NOT exist.

`filesystem_create_authorized` MUST NOT exist.
