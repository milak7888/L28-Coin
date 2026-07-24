# Foundation 51 Disposable Sandbox Directory Materialization Implementation v0.1

**Status:** Implementation of Foundation 50; non-activation beyond governed create

**Locked specification:** `docs/foundation50_disposable_sandbox_directory_materialization_spec_v0.1.md`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Base commit:** `fdf2c0ba060752ea2409805a2ccff4ee3d5ab0ee`

**Branch:** `foundation51-disposable-sandbox-directory-materialization`

## Scope and lineage

Foundation 51 implements the Foundation 50 governed materialization contract: exclusive
create-new of exactly one disposable sandbox directory under a caller-supplied
absolute trusted root, bound to frozen Foundation 49 `creation_plan_ok` evidence
and an explicit Foundation 50 materialization-authority object.

This is a **partial M2 / F37-06 specification-implementation slice**. It does
**not** complete F37-06 runnable process isolation, does **not** complete F37-13
cleanup/wipe tooling, and does **not** complete Foundation 37 M2.

## Created files

1. `coin/disposable_sandbox_directory_materialization.py`
2. `tests/test_disposable_sandbox_directory_materialization.py`
3. `docs/foundation51_disposable_sandbox_directory_materialization_implementation_v0.1.md`

No existing files were modified. `coin/__init__.py` was not changed.
`coin/l28_coin.py` was not used or modified.

## Ownership boundaries

| Concern | Owner |
|---|---|
| Offline creation-plan contract / evaluator | Foundations 48 / 49 (frozen evidence only) |
| Materialization contract | Foundation 50 |
| Materializer implementation | Foundation 51 (this implementation) |
| Wipe / reset of successful directories | Later F37-13-compatible lifecycle |
| Process launch / admission | Not granted; both authority flags remain false |

## Public API and schemas

1. `materialize_disposable_sandbox_directory_json(payload: str | bytes) -> SandboxMaterializationResult`

`SandboxMaterializationResult` is a frozen dataclass with the exact Foundation 50
field order. Every path sets `execution_authorized=False`,
`process_launch_authorized=False`, and empty `detail`. There is no
`admission_authorized` field and no `filesystem_create_authorized` field.

Profile: `l28-disposable-sandbox-directory-materialization/v0.1`
`MAX_REQUEST_BYTES = 8192`
Directory mode: `0700`

Frozen Foundation 49 projections are checked structurally only. Foundation 49
evaluation APIs are not imported or called.

Success `report_id` is the lowercase hex SHA-256 digest of the canonical JSON
serialization of the accepted request object (ordered fields, compact
separators, `sort_keys=false`, UTF-8).

## Locked implementation decisions

1. **Exclusive create equivalent:** `os.mkdir` + post-create `chmod` to `0700`
   (Darwin Python lacks `mkdirat` / `openat`).
2. **`substitution_ambiguous`:** trusted-root `st_dev`/`st_ino` change between
   filesystem precheck and pre-create substitution check; also child `st_dev`
   mismatch vs trusted root after create.
3. **Ownership SHOULD:** when `os.geteuid` exists, require `st_uid == geteuid()`.
4. **Wall-clock freshness:** `time.time()` compared to `not_after_unix`.
5. **`path_lexeme`:** echoed correlation only; never used as create target.
6. **Rollback:** `os.rmdir` of only this attempt’s created empty directory.

## Validation precedence

Implements Foundation 50 §9 steps 1–28, including trusted-root-only
`trusted_root_invalid`, derived-path steps 19–22, and post-create rollback
classification.

## Stable codes

Distinct result codes: **29**
Success code: `materialization_ok`

## Tests

Focused suite: `tests/test_disposable_sandbox_directory_materialization.py`

Harness trusted roots use `tempfile.TemporaryDirectory` only inside tests. No
production path invents a trusted root from environment, `HOME`, or cwd.

## Imports and static hygiene

Production imports: stdlib (`errno`, `hashlib`, `json`, `os`, `re`, `stat`,
`time`, `dataclasses`, `typing`) and passive Foundation 39 constants only.

No Foundation 47/49 evaluator imports. No Leap28/Nova. No `subprocess`,
`socket`, `shutil.rmtree`, `os.makedirs`, `os.environ`, or `pathlib`.

## Authority boundaries

- `execution_authorized` and `process_launch_authorized` remain false.
- Forbidden authority-bearing fields fail closed wherever nested.
- Materialization success is not process launch, admission, wipe, spend, mining,
  networking, ledger, consensus, or deployment authority.

## Explicit exclusions

No CLI, package export, F37-13 wipe tooling, process spawn, wallet/mining/ledger
mutation, or M3 transport/sync. No claim of full F37-06 / F37-13 / M2 completion.

## Non-authorization statement

Successful materialization is disposable sandbox directory **materialization
evidence** only. It is not permission to spend L28, admit peers, spawn a
process, wipe unrelated paths, or start a node, network, miner, wallet, or
testnet.
