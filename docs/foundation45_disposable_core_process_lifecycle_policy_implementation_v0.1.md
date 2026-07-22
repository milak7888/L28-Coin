# Foundation 45 Disposable Core Process Lifecycle Policy Implementation v0.1

**Status:** Offline implementation of Foundation 44; non-activation

**Locked specification:** `docs/foundation44_disposable_core_process_lifecycle_spec_v0.1.md`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

## Scope and lineage

Foundation 45 implements the Foundation 44 offline disposable Core lifecycle
policy evaluator. It decides whether an inert Foundation 21
`CoreNodeRoleModel` transition is permitted under a caller-supplied frozen
Foundation 39 identity-binding projection.

This is a **partial M2 Core slice**. It does **not** complete F37 M2 (wallets,
tip authority, issuance acknowledgement, reset/cleanup, or a runnable process).

## Created files

1. `coin/disposable_core_process_lifecycle_policy.py`
2. `tests/test_disposable_core_process_lifecycle_policy.py`
3. `docs/foundation45_disposable_core_process_lifecycle_policy_implementation_v0.1.md`

No existing files were modified. `coin/__init__.py` was not changed.
`coin/l28_coin.py` was not used or modified.

## Ownership boundaries

| Concern | Owner |
|---|---|
| Core states, transitions, transition codes | Foundation 21 (`CoreNodeRoleModel`) |
| Identity/genesis verification | Foundations 38/39 |
| Handshake / admission envelopes | Foundations 40–43 (not imported) |
| Offline Core lifecycle policy contract | Foundation 44 |
| Offline policy evaluator | Foundation 45 (this implementation) |

## Public APIs and schemas

1. `evaluate_core_lifecycle_policy_json(payload, *, model=None) -> CoreLifecyclePolicyResult`
2. `evaluate_core_lifecycle_policy(*, identity_evidence, current_state, requested_state, model=None) -> CoreLifecyclePolicyResult`

`CoreLifecyclePolicyResult` is a frozen dataclass. Every path sets
`execution_authorized=False` and empty `detail`. There is no
`admission_authorized` field.

Frozen F39 projection fields (exact order): `ok`, `code`, `network_id`,
`chain_id`, `genesis_digest`, `protocol_version`, `execution_authorized`,
`report_id`. Structural/equality checks only; no Foundation 39 re-verification.

## Validation precedence

Implements Foundation 44 §6 steps 1–13: size/UTF-8/JSON/schema → policy version →
forbidden environment → disposable environment → request authority flag →
identity evidence → Foundation 21 transition via
`CoreNodeRoleModel._from_valid_state` + `.transition` (or an injected model with
matching `state`).

## Stable codes

Reused F21: `transitioned`, `state_invalid`, `reserved_state_unreachable`,
`transition_not_allowed`.

F44/F45: `input_type_invalid`, `input_too_large`, `encoding_invalid`,
`json_invalid`, `duplicate_key`, `invalid_top_level`, `schema_invalid`,
`policy_version_unsupported`, `environment_invalid`,
`historical_import_forbidden`, `identity_evidence_invalid`,
`execution_authorized_invalid`, `internal_error`.

Total: 17.

## Reserved-state proof

- Reserved current state rejected by `_from_valid_state` → `state_invalid`.
- Reserved requested state rejected by Foundation 21 → `reserved_state_unreachable`.
- Successful `resulting_state` can only be an allowed non-reserved destination.
- Injected models are not mutated; mismatch with `current_state` fails closed.

## Tests and results

Focused suite: `tests/test_disposable_core_process_lifecycle_policy.py`

Also run: Foundation 21 `tests/test_node_role_model.py` and Foundation 39
`tests/test_disposable_network_identity_genesis_binding.py`.

## Economics and coupling

Protected Protocol v1.0.0 constants remain unchanged. No Leap28/Nova, socket,
subprocess, thread, async, wallet, mining, ledger, or F40–F43 imports.

## Explicit exclusions and deferred work

No runtime activation, process spawn, persistence, CLI, package export,
issuance/tip/wallets/reset/cleanup, or M3 transport/sync. No claim of full
F37 M2 completion.

## Non-authorization statement

Successful evaluation is offline Core lifecycle **policy evidence** only. It is
not permission to spend L28, admit peers, spawn a process, or start a node,
network, miner, wallet, or testnet. `execution_authorized` remains false.
