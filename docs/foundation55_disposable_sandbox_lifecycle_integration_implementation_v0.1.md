# Foundation 55 Disposable Sandbox Lifecycle Integration Implementation v0.1

**Status:** Implementation of Foundation 54; non-activation beyond governed lifecycle composition

**Locked specification:** `docs/foundation54_disposable_sandbox_lifecycle_integration_spec_v0.1.md`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Base commit:** `0a6045c96653b059c3492a11b184c10501d8295e`

**Branch:** `foundation55-disposable-sandbox-lifecycle-integration`

## Scope and lineage

Foundation 55 implements the Foundation 54 lifecycle-integration contract:
materialize → identity verify → cleanup for exactly one disposable sandbox
directory under a caller-supplied absolute trusted root.

This is a **partial M2 / F37-13 specification-implementation slice**. It does
**not** complete F37-06 process isolation, full F37-13 observability/shutdown,
F38 post-wipe genesis revalidation, or Foundation 37 M2.

## Created files

1. `coin/disposable_sandbox_lifecycle_integration.py`
2. `tests/test_disposable_sandbox_lifecycle_integration.py`
3. `docs/foundation55_disposable_sandbox_lifecycle_integration_implementation_v0.1.md`

No existing files were modified. `coin/__init__.py` was not changed.
`coin/l28_coin.py` was not used or modified.

## Ownership boundaries

| Concern | Owner |
|---|---|
| Materialization | Foundations 50 / 51 (subordinate API) |
| Cleanup | Foundations 52 / 53 (subordinate API) |
| Lifecycle composition contract | Foundation 54 |
| Lifecycle integrator | Foundation 55 (this implementation) |
| F38 post-wipe genesis revalidation | Deferred; not executed here |

## Public API and schemas

1. `run_disposable_sandbox_lifecycle_json(payload: str | bytes) -> SandboxLifecycleResult`

`SandboxLifecycleResult` is a frozen dataclass with the exact Foundation 54
field order. Every path sets `execution_authorized=False`,
`process_launch_authorized=False`, and empty `detail`.

Profile: `l28-disposable-sandbox-lifecycle-integration/v0.1`
`MAX_REQUEST_BYTES = 16384`

Success `report_id` is the lowercase hex SHA-256 digest of the canonical JSON
serialization of the accepted lifecycle request object.

## Locked implementation decisions

1. **Subordinate APIs:** calls
   `materialize_disposable_sandbox_directory_json` and
   `cleanup_disposable_sandbox_directory_json` only; does not reimplement create
   or constrained delete.
2. **Root snapshot:** `os.lstat(trusted_root)` before materialize for identity
   verify and post-lifecycle checks.
3. **Process-stop:** `never_started` only; `stopped` → `stopped_mode_forbidden`.
4. **Cross-stage binds:** all inequalities → `stage_binding_invalid`.
5. **`lifecycle_authority_mismatch`:** authority-intrinsic wrong `data_dir_tag`
   string only.
6. **`lifecycle_partial_failed`:** only after successful identity verify when
   F53 returns non-`cleanup_ok`.
7. **`cleanup_stage_failed`:** only pre-invocation cleanup-request construction
   failures.
8. **F38:** post-wipe genesis revalidation is not executed.

## Stable codes

Distinct result codes: **31**
Success code: `lifecycle_ok`

## Tests

Focused suite: `tests/test_disposable_sandbox_lifecycle_integration.py`

Harness trusted roots use `tempfile.TemporaryDirectory` only inside tests.

## Imports and static hygiene

Production imports: stdlib plus Foundation 39 constants, Foundation 51
materializer API, and Foundation 53 cleanup API.

No Leap28/Nova. No `subprocess`, `socket`, `shutil.rmtree`, `os.environ`, or
`pathlib`.

## Explicit exclusions

No CLI, package export, process spawn, authentic `stopped` producers, genesis
revalidation automation, wallet/mining/ledger mutation, or M3 transport/sync.

## Non-authorization statement

Successful lifecycle integration is disposable sandbox directory **lifecycle
evidence** only. It is not permission to spend L28, admit peers, spawn a
process, wipe unrelated paths, or start a node, network, miner, wallet, or
testnet.
