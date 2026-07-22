# Foundation 41 Peer-Handshake Identity Binding Validator v0.1

**Status:** Offline implementation of Foundation 40; non-activation

**Locked specification:** `docs/peer_handshake_identity_binding_v0.1.md`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

## Purpose

Foundation 41 implements the Foundation 40 peer-handshake identity-binding
validator for isolated offline tests. It verifies disposable handshake messages
with mandatory binding to Foundation 39 network identity values and fails closed
on mismatch, replay, stale messages, malformed input, and historical/canonical
identity reuse.

It does not open sockets, start nodes, mine, load wallets, mutate ledgers, or
activate a testnet.

## Module

- `coin/peer_handshake_identity_binding.py`

## Public APIs

1. `verify_peer_handshake_message_json`
2. `verify_peer_handshake_hello_json`
3. `verify_peer_handshake_challenge_json`
4. `verify_peer_handshake_response_json`
5. `verify_peer_handshake_accept_json`
6. `compute_peer_handshake_message_id`
7. `compute_peer_handshake_challenge_id`
8. `compute_peer_handshake_response`

Identity preconditions call Foundation 39
`validate_disposable_handshake_identity_binding`.

## Tests

- `tests/test_peer_handshake_identity_binding.py`

## Explicit non-scope

- no M3 transport, listeners, discovery, or synchronization
- no Core process lifecycle
- no M4–M5 propagation/reorg
- no Leap28/Nova reuse

## Non-authorization statement

Successful verification is offline disposable peer-identity-binding evidence
only. It is not permission to spend L28 and not authorization to start a node,
network, miner, wallet, or testnet. `execution_authorized` remains false.
