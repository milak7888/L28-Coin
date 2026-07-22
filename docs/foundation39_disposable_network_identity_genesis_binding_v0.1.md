# Foundation 39 Disposable Network Identity and Genesis Binding v0.1

**Status:** Offline implementation of Foundation 38 M1; non-activation

**Locked specification:** `docs/disposable_network_identity_genesis_binding_v0.1.md`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

## Purpose

Foundation 39 implements the Foundation 38 disposable network identity and
genesis-binding verifier for isolated offline tests. It provides deterministic
`network_id`, `chain_id`, genesis document verification, binding-config
verification, and identity-tuple validation surfaces for future handshake and
ledger/replay wiring.

It does not start a node, open sockets, mine, load wallets, mutate ledgers,
import historical state, or authorize a testnet.

## Module

- `coin/disposable_network_identity_genesis_binding.py`

## Public APIs

1. `verify_disposable_network_genesis_json`
2. `verify_disposable_network_binding_config_json`
3. `compute_disposable_chain_id`
4. `compute_disposable_genesis_digest`

Additional M1 helpers (still offline / non-activating):

- `build_disposable_genesis_document`
- `build_disposable_binding_config`
- `validate_disposable_handshake_identity_binding`
- `validate_disposable_ledger_replay_identity_binding`
- `genesis_json_bytes`

## Bound identity

| Field | Value |
|---|---|
| Profile | `l28-disposable-network-identity-genesis-binding/v0.1` |
| Network ID | `l28-disposable-test/v0.1` |
| Protocol version | `l28-protocol/1.0.0` |
| Environment | `DISPOSABLE_TEST` |
| Data-dir tag | `l28-disposable-test` |
| `execution_authorized` | always `false` |

Economics fields are imported from `coin/tx_validation.py` so Protocol v1.0.0
constants remain the single source of truth.

## Tests

- `tests/test_disposable_network_identity_genesis_binding.py`

Coverage groups: determinism, schema acceptance, economics immutability,
historical/canonical separation, mismatch matrix, malformed/size limits,
non-activation, temporary-directory cleanup, and static hygiene.

## Explicit non-scope

Foundation 39 does **not** implement M2–M5:

- no Core process / node lifecycle
- no peer transport, discovery, or synchronization
- no transaction propagation or confirmation
- no fork/reorg policy

Leap28 and Nova identity, authority, state, and code are not reused.

## Non-authorization statement

Successful verification is offline disposable-identity evidence only. It is not
permission to spend L28, not main-network genesis, and not authorization to
start a node, network, miner, wallet, or testnet.
