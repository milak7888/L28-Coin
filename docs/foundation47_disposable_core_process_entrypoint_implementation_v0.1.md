# Foundation 47 Disposable Core Process Entrypoint Implementation v0.1

**Status:** Offline implementation of Foundation 46; non-activation

**Locked specification:** `docs/foundation46_disposable_core_process_entrypoint_spec_v0.1.md`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

## Scope and lineage

Foundation 47 implements the Foundation 46 offline disposable Core process
entrypoint **preflight** evaluator. It validates a caller-supplied immutable
request containing frozen Foundation 39 identity evidence, frozen Foundation 45
lifecycle-policy evidence, a sandbox data-directory descriptor, and process
intent constraints.

This is a **partial M2 / F37-06 specification-implementation slice**. It does
**not** complete F37-06 runnable process isolation and does **not** complete
Foundation 37 M2.

## Created files

1. `coin/disposable_core_process_entrypoint.py`
2. `tests/test_disposable_core_process_entrypoint.py`
3. `docs/foundation47_disposable_core_process_entrypoint_implementation_v0.1.md`

No existing files were modified. `coin/__init__.py` was not changed.
`coin/l28_coin.py` was not used or modified.

## Ownership boundaries

| Concern | Owner |
|---|---|
| Core states / reserved states | Foundation 21 (`CORE_RESERVED_STATES`) |
| Identity/genesis verification | Foundations 38/39 (frozen projection only) |
| Offline Core lifecycle policy evaluation | Foundations 44/45 (frozen projection only) |
| Offline entrypoint preflight contract | Foundation 46 |
| Offline preflight evaluator | Foundation 47 (this implementation) |
| Handshake / admission envelopes | Foundations 40–43 (not imported) |
| Process launch / filesystem create | Later F37-06 remediation (not this foundation) |

## Public APIs and schemas

1. `evaluate_core_entrypoint_preflight_json(payload: str | bytes) -> CoreEntrypointResult`

`CoreEntrypointResult` is a frozen dataclass. Every path sets
`execution_authorized=False`, `process_launch_authorized=False`, and empty
`detail`. There is no `admission_authorized` field.

Profile: `l28-disposable-core-process-entrypoint/v0.1`  
`MAX_REQUEST_BYTES = 8192`

Frozen projections are checked structurally only. Foundation 45 is not
re-executed. Foundation 21 `transition` is never called.

Success `report_id` is the lowercase hex SHA-256 digest of the canonical JSON
serialization of the accepted request object (ordered fields, compact
separators, UTF-8).

## Validation precedence

Implements Foundation 46 §8 steps 1–21, including mutually exclusive F45
structural vs reserved vs unsupported lifecycle classification (steps 13–15)
and sandbox structure vs ownership collision (steps 16–17).

## Stable codes

Distinct result codes: 22  
Foundation 46–defined: 21  
Foundation 21 string reused by value: `reserved_state_unreachable`

## Reserved-state proof

- Reserved values in F45 state fields → `reserved_state_unreachable`.
- Successful `lifecycle_resulting_state` is only `DISPOSABLE_TEST_READY`.
- No Foundation 21 transition edges are invoked.

## Tests and results

Focused suite: `tests/test_disposable_core_process_entrypoint.py`

Also run: Foundation 21 `tests/test_node_role_model.py`, Foundation 39
`tests/test_disposable_network_identity_genesis_binding.py`, and Foundation 45
`tests/test_disposable_core_process_lifecycle_policy.py`.

## Economics and coupling

Protected Protocol v1.0.0 constants remain unchanged. No Leap28/Nova, socket,
subprocess, thread, async, pathlib/os filesystem, wallet, mining, ledger, or
F40–F43 imports.

## Explicit exclusions and deferred work

No runtime activation, process spawn, CLI, package export, filesystem
create/wipe, symlink resolution, issuance/tip/wallets/reset/cleanup, or M3
transport/sync. No claim of full F37-06 or F37 M2 completion.

## Non-authorization statement

Successful evaluation is offline disposable Core entrypoint **preflight
evidence** only. It is not permission to spend L28, admit peers, spawn a
process, mutate a filesystem, or start a node, network, miner, wallet, or
testnet. `execution_authorized` and `process_launch_authorized` remain false.
