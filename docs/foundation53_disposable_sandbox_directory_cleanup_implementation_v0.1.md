# Foundation 53 Disposable Sandbox Directory Cleanup Implementation v0.1

**Status:** Implementation of Foundation 52; non-activation beyond governed cleanup

**Locked specification:** `docs/foundation52_disposable_sandbox_directory_cleanup_spec_v0.1.md`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Base commit:** `3894b04ccba291e29f052eeefad812321e0b1b97`

**Branch:** `foundation53-disposable-sandbox-directory-cleanup`

## Scope and lineage

Foundation 53 implements the Foundation 52 governed cleanup contract: constrained
bottom-up, no-follow deletion of exactly one successful Foundation 51-materialized
disposable sandbox directory under a caller-supplied absolute trusted root, after
process-stop proof and an explicit Foundation 52 cleanup-authority object.

This is a **partial M2 / F37-13 specification-implementation slice**. It does
**not** complete F37-06 runnable process isolation, does **not** complete full
F37-13 wipe tooling for arbitrary paths, and does **not** complete Foundation 37 M2.

## Created files

1. `coin/disposable_sandbox_directory_cleanup.py`
2. `tests/test_disposable_sandbox_directory_cleanup.py`
3. `docs/foundation53_disposable_sandbox_directory_cleanup_implementation_v0.1.md`

No existing files were modified. `coin/__init__.py` was not changed.
`coin/l28_coin.py` was not used or modified.

## Ownership boundaries

| Concern | Owner |
|---|---|
| Offline creation-plan / materialization contracts | Foundations 48–51 (frozen evidence only) |
| Cleanup contract | Foundation 52 |
| Cleanup implementation | Foundation 53 (this implementation) |
| Process launch / admission | Not granted; both authority flags remain false |

## Public API and schemas

1. `cleanup_disposable_sandbox_directory_json(payload: str | bytes) -> SandboxCleanupResult`

`SandboxCleanupResult` is a frozen dataclass with the exact Foundation 52
field order. Every path sets `execution_authorized=False`,
`process_launch_authorized=False`, and empty `detail`. There is no
`admission_authorized`, `wipe_authorized`, or `materialization_authorized` field.

Profile: `l28-disposable-sandbox-directory-cleanup/v0.1`
`MAX_REQUEST_BYTES = 8192`
Tree limits: `MAX_TREE_ENTRIES = 4096`, `MAX_TREE_DEPTH = 64`

Frozen Foundation 51 success projections are checked structurally only.
Foundation 51 materialization APIs are not imported or called from production.

Success `report_id` is the lowercase hex SHA-256 digest of the canonical JSON
serialization of the accepted request object (ordered fields, compact
separators, `sort_keys=false`, UTF-8).

## Locked implementation decisions

1. **Constrained delete:** survey with `os.lstat` / `os.listdir` (no follow), then
   bottom-up `os.unlink` / `os.rmdir` only. No library recursive tree wipe.
2. **Process-stop proof:** exact `never_started` or `stopped` object shapes;
   instance id must match materialization evidence.
3. **Survey vs delete codes:** survey raises only survey-family codes
   (`symlink_rejected`, `substitution_ambiguous`, `tree_limit_exceeded`);
   pre-delete target `lstat` OSError other than absence maps to
   `substitution_ambiguous`; `exclusive_cleanup_failed` is reserved strictly for
   first `unlink`/`rmdir` failure before any successful deletion; mid-delete
   residue uses `cleanup_partial_failed`; post-check uses
   `post_cleanup_verification_failed` when deletion completed with no residue
   but an invariant fails.
4. **Wall-clock freshness:** `time.time()` compared to authority `not_after_unix`.
5. **Trusted root:** lexical absolute path plus symlink-free ancestry `lstat`
   checks, exclusive `trusted_root_invalid`.

## Validation precedence

Implements Foundation 52 §9 steps through post-cleanup verification, including
authority binding, process-stop proof, trusted-root-only `trusted_root_invalid`,
target identity/containment, survey limits, constrained delete, and partial vs
post-cleanup failure separation.

## Stable codes

Distinct result codes: **31**
Success code: `cleanup_ok`

## Tests

Focused suite: `tests/test_disposable_sandbox_directory_cleanup.py`

Harness trusted roots use `tempfile.TemporaryDirectory` only inside tests. No
production path invents a trusted root from environment, `HOME`, or cwd.
Tests build frozen Foundation 51-shaped evidence fixtures; they do not require
calling the Foundation 51 materializer on the production cleanup path.

Concrete first-failure coverage includes zero instance id, invalid `attempt_id`,
tilde/`$HOME`/env-shaped roots, symlink ancestry, parent-inode containment
failure, derived-path traversal and tagged/protected helpers (without mocking
`_evaluate_parsed`), and `path_lexeme` proving it never selects the delete target.

## Imports and static hygiene

Production imports: stdlib (`hashlib`, `json`, `os`, `re`, `stat`, `time`,
`dataclasses`, `typing`) and passive Foundation 39 constants only.

No Foundation 49/51 evaluator or materializer imports. No Leap28/Nova. No
`subprocess`, `socket`, recursive tree-wipe helpers, `os.environ`, or `pathlib`.

## Authority boundaries

- `execution_authorized` and `process_launch_authorized` remain false.
- Forbidden authority-bearing fields fail closed wherever nested.
- Cleanup success is not process launch, admission, materialization, spend,
  mining, networking, ledger, consensus, or deployment authority.

## Explicit exclusions

No CLI, package export, arbitrary wipe tooling, process spawn, wallet/mining/ledger
mutation, or M3 transport/sync. No claim of full F37-06 / F37-13 / M2 completion.
No production execution of cleanup against live environments in this slice.

## Non-authorization statement

Successful cleanup is disposable sandbox directory **cleanup evidence** only.
It is not permission to spend L28, admit peers, spawn a process, materialize a
new sandbox, wipe unrelated paths, or start a node, network, miner, wallet, or
testnet.
