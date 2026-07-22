# Foundation 43 Disposable Peer Admission Decision Envelope Validator v0.1

**Status:** Offline implementation of Foundation 42; non-activation

**Locked specification:** `docs/foundation42_peer_admission_decision_envelope_spec_v0.1.md`
**Locked SHA-256:** `359f2e9ed39f3580c057a785624262adfc70c378e6723a2502c71d53bf900975`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

## Purpose

Foundation 43 implements the Foundation 42 disposable peer admission decision
envelope validator for isolated offline tests. It binds successful Foundation 39
identity values to Foundation 41 accept-path identifiers, recomputes Foundation
40/41 challenge and response digests, and fails closed on mismatch, replay,
stale messages, malformed input, forbidden environments, and authority-flag
violations.

It does not open sockets, start nodes, mine, load wallets, mutate ledgers,
admit live peers, or activate a testnet.

## Module

- `coin/peer_admission_decision_envelope.py`

## Public APIs

1. `verify_peer_admission_decision_envelope_json`
2. `compute_peer_admission_envelope_id`
3. `build_peer_admission_decision_envelope`
4. `PeerAdmissionDecisionResult` (frozen)
5. `PeerAdmissionDecisionSession` (ephemeral lifecycle/replay helper)

## Dependencies reused (not duplicated)

| Helper | Source |
|---|---|
| `validate_disposable_handshake_identity_binding` | Foundation 39 |
| `NETWORK_ID`, `PROTOCOL_VERSION`, `ENVIRONMENT` | Foundation 39 |
| `build_peer_identity` | Foundation 41 |
| `compute_peer_handshake_challenge_id` | Foundation 41 |
| `compute_peer_handshake_response` | Foundation 41 |
| Handshake profile string | Foundation 41 `PROFILE` |

## Validation ordering (17 steps)

1. Parse/size/UTF-8/JSON/duplicate-key/top-level/schema/order/type;
   `handshake_version` mismatch → `schema_invalid`
2. `envelope_version_unsupported`
3. Forbidden environments → `historical_import_forbidden`
4. Other non-`DISPOSABLE_TEST` → `environment_invalid`
5. Foundation 39 identity binding + expected digest/chain equality
6. Peer identity derivation
7–8. Handshake accept report/message/session binding
9–12. Challenge/response recomputation and message-id binding
13. Decision candidate only
14. Lifetime `[1, 3600]` → else `schema_invalid`
15. Premature/stale/replay (`replay_set` read-only)
16. `execution_authorized` then `admission_authorized` must be JSON `false`
17. Envelope ID recomputation

Both authority flags are `False` on every result path. `detail` is always empty.

## Stable-code coverage

All 27 Foundation 42 stable codes are implemented and asserted through the
public API (`internal_error` via narrow monkeypatch of `_parse`).

## Tests

- `tests/test_peer_admission_decision_envelope.py`

Coverage groups: success path, determinism, identity mismatch, forbidden
environment precedence, generic invalid environment, binding mismatches,
replay/freshness (including non-mutation of `replay_set`), lifetime bounds,
malformed matrix, lifecycle, authority flags, static hygiene, economics
immutability, and complete stable-code coverage.

## Explicit non-scope

- no CLI, no `coin/__init__.py` export
- no M3 transport, listeners, discovery, or synchronization
- no peer persistence, signing, wallet, transactions, ledger mutation
- no MAIN admission, historical import, or canonical-state reuse
- no Leap28/Nova reuse
- no protected economic or protocol changes

## Changed-file scope

1. `coin/peer_admission_decision_envelope.py`
2. `tests/test_peer_admission_decision_envelope.py`
3. `docs/foundation43_peer_admission_decision_envelope_v0.1.md`

## Non-authorization statement

Successful verification is offline disposable admission-**candidate** evidence
only. It is not permission to spend L28, not live peer admission, and not
authorization to start a node, network, miner, wallet, or testnet.
`execution_authorized` and `admission_authorized` remain false.
