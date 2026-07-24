# Foundation 49 Disposable Sandbox Directory Creation Implementation v0.1

**Status:** Offline implementation of Foundation 48; non-activation

**Locked specification:** `docs/foundation48_disposable_sandbox_directory_creation_spec_v0.1.md`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Base commit:** `d702ed235b881c816434eddd7342f6bda563d9b3`

**Branch:** `foundation49-disposable-sandbox-directory-creation`

## Scope and lineage

Foundation 49 implements the Foundation 48 offline exclusive disposable sandbox
data-directory **creation-plan** evaluator. It validates a caller-supplied
immutable request containing a frozen Foundation 47 preflight-success
projection, a sandbox descriptor, and creation-intent constraints.

This is a **partial M2 / F37-06 specification-implementation slice**. It does
**not** create or inspect directories, does **not** complete F37-06 runnable
process isolation, does **not** complete F37-13 cleanup, and does **not**
complete Foundation 37 M2.

## Created files

1. `coin/disposable_sandbox_directory_creation.py`
2. `tests/test_disposable_sandbox_directory_creation.py`
3. `docs/foundation49_disposable_sandbox_directory_creation_implementation_v0.1.md`

No existing files were modified. `coin/__init__.py` was not changed.
`coin/l28_coin.py` was not used or modified.

## Ownership boundaries

| Concern | Owner |
|---|---|
| Core states / reserved states | Foundation 21 (not invoked) |
| Identity/genesis constants | Foundations 38/39 (passive constants only) |
| Offline Core lifecycle policy | Foundations 44/45 (frozen inside F47 evidence; not re-run) |
| Offline entrypoint preflight contract / evaluator | Foundations 46/47 (frozen projection only) |
| Offline creation-plan contract | Foundation 48 |
| Offline creation-plan evaluator | Foundation 49 (this implementation) |
| Handshake / admission envelopes | Foundations 40–43 (not imported) |
| Filesystem create / wipe / process launch | Later F37-06 / F37-13 remediation (not this foundation) |

## Public API and schemas

1. `evaluate_sandbox_directory_creation_plan_json(payload: str | bytes) -> SandboxCreationPlanResult`

`SandboxCreationPlanResult` is a frozen dataclass. Every path sets
`execution_authorized=False`, `process_launch_authorized=False`, and empty
`detail`. There is no `admission_authorized` field and no
`filesystem_create_authorized` field.

Profile: `l28-disposable-sandbox-directory-creation/v0.1`
`MAX_REQUEST_BYTES = 8192`

Frozen Foundation 47 projections are checked structurally only. Foundation 47
evaluation APIs are not imported or called. Foundation 21 `transition` is never
called. Foundation 46 §7.3 lexical path rejection is not reapplied.

Success `report_id` is the lowercase hex SHA-256 digest of the canonical JSON
serialization of the accepted request object (ordered fields, compact
separators, `sort_keys=false`, UTF-8).

## Validation precedence

Implements Foundation 48 §8 steps 1–18, including mutually exclusive sandbox
local plan validation (step 14) versus cross-object evidence binding (step 16).

## Stable codes

Distinct result codes: **18**
Success code: `creation_plan_ok`

## Tests and results

Focused suite: `tests/test_disposable_sandbox_directory_creation.py` — 46 passed
(`pytest -p no:cacheprovider`).

Also run (focused regressions), combined with F49: **160 passed**:

- Foundation 47 `tests/test_disposable_core_process_entrypoint.py`
- Foundation 21 `tests/test_node_role_model.py`
- Foundation 39 `tests/test_disposable_network_identity_genesis_binding.py`
- Foundation 45 `tests/test_disposable_core_process_lifecycle_policy.py`

## Imports and static hygiene

Production imports: stdlib (`hashlib`, `json`, `re`, `dataclasses`, `typing`) and
passive Foundation 39 constants only
(`DATA_DIR_TAG`, `ENVIRONMENT`, `NETWORK_ID`, `PROTOCOL_VERSION`).

No `os` / `pathlib` / `tempfile` / `shutil` / `subprocess` / socket / env / time /
random / UUID / F21 / F45 / F47 evaluator / F40–F43 / Leap28 / Nova imports.

## Authority boundaries

- F21 remains sole lifecycle authority and is unused here.
- F39 / F45 / F47 remain frozen evidence or constant sources.
- F48 remains the normative creation-plan contract.
- F49 only evaluates that contract.
- `execution_authorized` and `process_launch_authorized` remain false.
- `admission_authorized` and `filesystem_create_authorized` remain absent and
  rejected wherever nested.

## Economics and coupling

Protected Protocol v1.0.0 constants remain unchanged. No Leap28/Nova, wallet,
mining, ledger, networking, or deployment work.

## Explicit exclusions and deferred work

No runtime activation, process spawn, CLI, package export, filesystem
create/stat/wipe, symlink resolution, issuance/tip/wallets/reset/cleanup, or M3
transport/sync. No claim of full F37-06, F37-13, or F37 M2 completion.

Remaining activation-gated work includes exclusive filesystem create under
Foundation 48 §10 deferred obligations and later process isolation.

## Non-authorization statement

Successful evaluation is offline disposable sandbox directory **creation-plan
evidence** only. It is not permission to spend L28, admit peers, spawn a
process, mutate a filesystem, prove a directory exists, or start a node,
network, miner, wallet, or testnet. `execution_authorized` and
`process_launch_authorized` remain false.
