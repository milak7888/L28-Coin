# L28 Peer-Handshake Identity Binding v0.1

**Foundation:** 40

**Status:** Offline specification only; non-activation

**Milestone label:** M2 — peer-handshake identity binding only

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN) — immutable

**Depends on:** Foundation 38 locked identity/genesis binding;
Foundation 39 offline verifier surfaces

## Purpose

Foundation 40 defines the locked offline specification for **disposable
peer-handshake identity binding**. It specifies handshake message schemas,
canonical serialization, deterministic challenge/response binding, replay and
stale-message rejection, peer identity representation without wallet or payment
authority, fail-closed mismatch rules, version-negotiation limits, lifecycle
transitions, timeouts, idempotency, audit evidence, cleanup, reproducible test
vectors, public API contracts, acceptance criteria, and later-milestone
boundaries.

This document does **not** implement transport, sockets, listeners, peer
sessions, Core processes, mining, wallets, ledger mutation, or a testnet. It
grants **no execution authority**.

## Traceability

### Foundation 38 / 39 prerequisites (M1 complete)

| Artifact | Role |
|---|---|
| `docs/disposable_network_identity_genesis_binding_v0.1.md` | Locked M1 identity/genesis specification |
| `docs/foundation39_disposable_network_identity_genesis_binding_v0.1.md` | M1 implementation record |
| `coin/disposable_network_identity_genesis_binding.py` | Offline genesis/binding verifier and identity surfaces |
| `validate_disposable_handshake_identity_binding` | Existing fail-closed identity-tuple helper |
| `NETWORK_ID` = `l28-disposable-test/v0.1` | Mandatory disposable network ID |
| `PROTOCOL_VERSION` = `l28-protocol/1.0.0` | Mandatory protocol binding |
| `ENVIRONMENT` = `DISPOSABLE_TEST` | Mandatory environment class |

### Foundation 38 handshake binding requirements addressed here

Foundation 38 section **Peer handshake identity binding (future surface)**
requires that handshake and frames bind:

- `network_id` = `l28-disposable-test/v0.1`
- `chain_id` = recomputed disposable chain ID
- `protocol_version` = `l28-protocol/1.0.0`
- `genesis_digest` of the local disposable genesis document

and fail closed on mismatch without falling back to `MAIN` or historical
identity.

Foundation 38’s milestone table lists those frame/handshake obligations under
its **M3** row (P2P handshake/frames). Foundation 40 is the locked
**identity-binding message and verifier contract** for that obligation.
Foundation 40’s project milestone label is **M2 peer-handshake identity
binding** (next identity-binding deliverable after M1). It does **not**
implement or replace:

- Foundation 38 table **M2** disposable Core process lifecycle;
- Foundation 38 table **M3** transport codecs, listeners, or synchronization;
- Foundation 37 sequence M4–M5 propagation/reorg work.

### Related architecture evidence

- `docs/l28_core_p2p_architecture_v0.1.md` — future frames must bind protocol
  version, network identifier, message type, message id, peer identity
  evidence, nonce/replay id, timestamp/expiry, payload length/digest
- `docs/l28_core_p2p_security_profile_v0.1.json` — P2P security profile
  (declarative; non-activation)
- `docs/bounded_testnet_readiness_gap_audit_v0.1.md` — F37-07 / F37-12 gaps
- `docs/node_role_model_v0.1.md` / `coin/node_role_model.py` — inert role
  models; `LISTENING_RESERVED` unreachable
- `PROTOCOL.md` — Protocol v1.0.0; empty/clone state is not trusted genesis
- `coin/tx_validation.py` — protected economics (`L28_MAX_SUPPLY`,
  `L28_EMISSION_CEILING`, `L28_REWARD_SCHEDULE`, …)

## Public identifiers

| Identifier | Value |
|---|---|
| Profile | `l28-peer-handshake-identity-binding/v0.1` |
| Verifier profile | `l28-peer-handshake-identity-binding-verifier/v0.1` |
| Report profile | `l28-peer-handshake-identity-binding-report/v0.1` |
| Bound identity profile | `l28-disposable-network-identity-genesis-binding/v0.1` |
| Environment | `DISPOSABLE_TEST` |
| Network ID | `l28-disposable-test/v0.1` |
| Protocol version | `l28-protocol/1.0.0` |
| Handshake hello type | `handshake_hello` |
| Handshake challenge type | `handshake_challenge` |
| Handshake response type | `handshake_response` |
| Handshake accept type | `handshake_accept` |
| Handshake reject type | `handshake_reject` |
| Maximum encoded handshake message size | `8192` bytes |
| Maximum challenge bytes (decoded hex payload) | `32` bytes |
| Challenge lifetime (logical units) | `60` (test-vector seconds; no live clock authority) |

## Protected economic facts (immutable)

Foundation 40 MUST NOT alter Protocol v1.0.0 economics. Handshake messages MUST
NOT carry issuance, balances, rewards, or reminting claims. Economics remain:

| Fact | Value | Evidence |
|---|---:|---|
| Hard cap | `28_000_000` | `coin/tx_validation.py` `L28_MAX_SUPPLY` |
| Emission ceiling | `11_130_000` | `coin/tx_validation.py` `L28_EMISSION_CEILING` |
| Halving interval | `210_000` | `coin/tx_validation.py` `L28_HALVING_INTERVAL` |
| Max coinbase reward | `28` | `coin/tx_validation.py` `L28_MAX_COINBASE_REWARD` |
| Reward schedule | `(28, 14, 7, 3, 1)` | `coin/tx_validation.py` `L28_REWARD_SCHEDULE` |

## Non-goals

Foundation 40 does not:

- implement production modules, tests, CLIs, or configuration files;
- open sockets, listeners, or peer sessions;
- start Core/P2P processes or any node runtime;
- define full frame codecs beyond handshake identity messages;
- implement synchronization, gossip, confirmation, or reorg (M3–M5 transport /
  settlement tracks);
- load wallets, private keys, seeds, or credentials;
- authorize payments, transfers, mining, or deployment;
- import Leap28 or Nova identity, authority, state, or code;
- grant `execution_authorized=true` on any path.

## Mandatory identity binding

Every conforming handshake message MUST bind all of:

1. `environment` = `DISPOSABLE_TEST`
2. `network_id` = `l28-disposable-test/v0.1`
3. `protocol_version` = `l28-protocol/1.0.0`
4. `chain_id` = recomputed disposable chain ID from Foundation 38/39
5. `genesis_digest` = digest of the local verified disposable genesis document

Future implementations MUST invoke Foundation 39
`validate_disposable_handshake_identity_binding` (or an equivalent that applies
identical fail-closed rules) before accepting any handshake message as
identity-valid.

Mismatch on any field MUST fail closed. Fallback to `MAIN`, `CANONICAL`,
`HISTORICAL`, `PRODUCTION`, empty network IDs, continuity-manifest digests as
genesis, or Leap28/Nova labels is forbidden.

## Peer identity representation (non-authority)

A peer identity object is public evidence only:

    {
      "peer_id": "64 lowercase hexadecimal characters",
      "peer_public_key": "64 lowercase hexadecimal characters",
      "peer_address": "L28 followed by 40 lowercase hexadecimal characters"
    }

Rules:

- `peer_id` MUST equal lowercase hex SHA-256 over
  UTF-8(`l28-peer-handshake-identity-binding/v0.1`) || `0x00` ||
  UTF-8(`peer_public_key`).
- `peer_address` MUST equal `L28` + first 40 hex characters of
  SHA-256(raw 32-byte public key), matching the public derivation practice used
  by creator-wallet public identity docs
  (`docs/foundation28_creator_wallet_control_proof_contract_v0.1.md`).
- Peer identity MUST NOT imply wallet custody, spendability, balance, payment
  authority, mining rights, or ledger write authority.
- Private keys, seeds, and credentials MUST NEVER appear in handshake messages,
  reports, tests, or logs.

## Handshake message schemas

All handshake messages are one JSON object. Unknown, missing, reordered,
duplicated, or incorrectly typed fields fail closed. Duplicate JSON keys fail
at every depth. Non-finite numbers and invalid UTF-8 fail closed.

### Common header fields (exact prefix order)

Every handshake message begins with exactly these fields in this order:

1. `handshake_version`
2. `message_type`
3. `environment`
4. `network_id`
5. `chain_id`
6. `protocol_version`
7. `genesis_digest`
8. `message_id`
9. `session_id`
10. `peer`
11. `nonce`
12. `issued_at_logical`
13. `expires_at_logical`
14. `execution_authorized`

Common field rules:

| Field | Rule |
|---|---|
| `handshake_version` | Exact `l28-peer-handshake-identity-binding/v0.1` |
| `message_type` | One of the five handshake type strings |
| `environment` | Exact `DISPOSABLE_TEST` |
| `network_id` | Exact `l28-disposable-test/v0.1` |
| `chain_id` | Exact recomputed disposable chain ID (64 lowercase hex) |
| `protocol_version` | Exact `l28-protocol/1.0.0` |
| `genesis_digest` | Exact local disposable genesis digest (64 lowercase hex) |
| `message_id` | 64 lowercase hex; see message-id rule |
| `session_id` | 64 lowercase hex; constant for one handshake attempt |
| `peer` | Object matching peer-identity schema and field order |
| `nonce` | 64 lowercase hex; unique per message within session replay window |
| `issued_at_logical` | Exact non-negative integer (logical test clock) |
| `expires_at_logical` | Exact integer `>` `issued_at_logical` |
| `execution_authorized` | JSON boolean `false` only |

Nested `peer` field order is exactly: `peer_id`, `peer_public_key`,
`peer_address`.

### `handshake_hello`

Header fields followed by:

15. `supported_handshake_versions` — array of strings; MUST contain exactly
    `l28-peer-handshake-identity-binding/v0.1` as the sole element in v0.1
16. `capabilities` — array of strings; MUST be exactly `["identity_binding"]`

### `handshake_challenge`

Header fields followed by:

15. `challenge` — 64 lowercase hex characters encoding 32 challenge bytes
16. `challenge_id` — 64 lowercase hex; see challenge-id rule
17. `hello_message_id` — 64 lowercase hex; MUST equal the accepted hello
    `message_id`

### `handshake_response`

Header fields followed by:

15. `challenge_id` — must equal the challenge being answered
16. `response` — 64 lowercase hex; see response rule
17. `challenge_message_id` — must equal the challenge `message_id`

### `handshake_accept`

Header fields followed by:

15. `accepted_peer_id` — must equal the remote peer’s `peer_id`
16. `response_message_id` — must equal the accepted response `message_id`
17. `binding_checks` — array of strings; MUST equal the success-check tuple
    defined below

### `handshake_reject`

Header fields followed by:

15. `rejected_message_id` — message id being rejected
16. `reject_code` — stable sanitized code from the error table
17. `detail` — empty string only in v0.1 (no path/secret/exception leakage)

## Canonical serialization and digests

Canonical JSON for digests and identifiers uses:

- UTF-8
- `ensure_ascii=false`
- `allow_nan=false`
- `sort_keys=true`
- separators `(",", ":")`

Wire acceptance requires exact schema field order. Digest canonicalization uses
sorted keys only after schema/order acceptance.

### Domain separation

Let `PROFILE = l28-peer-handshake-identity-binding/v0.1`.

- `message_id` = hex(sha256(UTF8(PROFILE) || 0x00 || UTF8("message") || 0x00 ||
  canonical_json(message_without_message_id)))
- `challenge_id` = hex(sha256(UTF8(PROFILE) || 0x00 || UTF8("challenge") || 0x00 ||
  challenge_bytes || 0x00 || UTF8(session_id) || 0x00 || UTF8(genesis_digest)))
- `response` = hex(sha256(UTF8(PROFILE) || 0x00 || UTF8("response") || 0x00 ||
  challenge_bytes || 0x00 || UTF8(peer_public_key) || 0x00 ||
  UTF8(genesis_digest) || 0x00 || UTF8(session_id)))
- `report_id` = hex(sha256(UTF8(report_profile) || 0x00 ||
  canonical_json(report_body)))

`challenge_bytes` are the 32 raw bytes decoded from the `challenge` hex field.

These constructions are **identity-binding MACs over public material only**.
They are not signatures over spendable transactions and confer no payment
authority. A later foundation MAY add authenticated signatures without changing
Protocol v1.0.0 economics; v0.1 requires only the deterministic binding above.

## Deterministic challenge / response and replay rejection

1. Challenges MUST be exactly 32 bytes (64 hex chars).
2. For reproducible offline vectors, challenge bytes MUST equal
   sha256(UTF8(PROFILE) || 0x00 || UTF8("vector-challenge") || 0x00 ||
   UTF8(session_id) || 0x00 || UTF8(genesis_digest))[0:32].
3. A response is valid only when its `response` field equals the recomputed
   response digest for that challenge and peer public key.
4. Replay rejection: any `message_id` or `nonce` previously accepted in the
   active session replay set MUST fail closed with `replay_detected`.
5. Stale rejection: if logical now `>` `expires_at_logical`, fail closed with
   `message_stale`.
6. Premature rejection: if logical now `<` `issued_at_logical`, fail closed with
   `message_premature`.
7. Foundation 40 specifies logical clocks for offline vectors only. It does not
   authorize reading a live wall clock to claim current network time.

## Version negotiation (non-weakening)

1. `handshake_version` MUST equal this profile exactly.
2. `supported_handshake_versions` in hello MUST list only this profile in v0.1.
3. Unsupported or additional versions fail closed with
   `handshake_version_unsupported`.
4. Negotiation MUST NOT rewrite, bypass, or relax `protocol_version`
   `l28-protocol/1.0.0` or Protocol v1.0.0 economic invariants.
5. Downgrade to `MAIN` / historical / foreign profiles is forbidden.

## Lifecycle / state transitions

Offline verifier/session state machine (conceptual; no process activation):

| State | Meaning |
|---|---|
| `CREATED` | Local disposable identity loaded and verified via Foundation 39 |
| `HELLO_SENT` / `HELLO_RECEIVED` | Hello validated |
| `CHALLENGED` | Challenge validated and bound to hello |
| `RESPONDED` | Response validated and bound to challenge |
| `ACCEPTED` | Accept validated; identity binding complete |
| `REJECTED` | Reject emitted or received |
| `EXPIRED` | Logical expiry reached |
| `CLOSED` | Terminal cleanup complete |

Allowed transitions:

- `CREATED` → `HELLO_SENT` / `HELLO_RECEIVED`
- `HELLO_*` → `CHALLENGED` | `REJECTED` | `EXPIRED`
- `CHALLENGED` → `RESPONDED` | `REJECTED` | `EXPIRED`
- `RESPONDED` → `ACCEPTED` | `REJECTED` | `EXPIRED`
- any non-terminal → `CLOSED` after cleanup

`ACCEPTED` proves only that two disposable identity tuples and a challenge
response bound under this profile. It does **not** authorize ledger writes,
listening, mining, or spend.

## Timeouts, idempotency, audit evidence, cleanup

### Timeouts

- Default logical lifetime: `expires_at_logical = issued_at_logical + 60`.
- Lifetime MUST be in `[1, 3600]` logical units inclusive; otherwise
  `schema_invalid`.
- On expiry, transition to `EXPIRED` then `CLOSED`.

### Idempotency

- Re-validating identical accepted message bytes MUST return equal
  `ok` / `code` / checks / digests / `report_id`.
- Re-submitting an already-accepted `message_id` MUST fail as `replay_detected`
  once recorded in the session replay set.
- Compact and pretty JSON that parse to the same logical object MUST produce
  equal verification results after schema acceptance.

### Audit evidence

Successful and failed verifications MUST emit a sanitized report containing at
least:

- `ok`, `code`, `handshake_version`, `message_type`
- `network_id`, `chain_id`, `protocol_version`, `genesis_digest`
- `session_id`, `message_id` (empty on parse failures before id recovery)
- `checks` (success tuple or empty)
- `execution_authorized` = `false`
- `report_id`

Reports MUST NOT include private keys, seeds, credentials, filesystem paths,
raw exceptions, or Leap28/Nova identifiers.

### Cleanup

- Session replay sets and logical clocks are ephemeral and MUST be wipeable.
- Cleanup MUST NOT touch historical archives, continuity manifests, or
  non-`l28-disposable-test` directories
  (`docs/disposable_network_identity_genesis_binding_v0.1.md` reset rules).
- After cleanup, a new session requires a new `session_id` and full
  revalidation.

## Required success checks

On successful validation of a terminal `handshake_accept` path (and as
`binding_checks` on accept messages), `checks` MUST equal this exact order:

1. `schema_exact`
2. `environment_disposable`
3. `network_id_bound`
4. `protocol_version_bound`
5. `chain_id_bound`
6. `genesis_digest_bound`
7. `peer_identity_valid`
8. `challenge_response_bound`
9. `replay_fresh`
10. `execution_authorized_false`

## Stable error codes

| Code | Meaning |
|---|---|
| `ok` | Verification succeeded |
| `input_type_invalid` | Unsupported payload type |
| `input_too_large` | Encoded size exceeds 8192 bytes |
| `encoding_invalid` | Invalid UTF-8 |
| `json_invalid` | Malformed JSON or non-finite number |
| `duplicate_key` | Duplicate key at any depth |
| `invalid_top_level` | Top-level value is not an object |
| `schema_invalid` | Missing/unknown/reordered/wrong-type fields |
| `handshake_version_unsupported` | Version negotiation failure |
| `message_type_invalid` | Unknown or disallowed message type |
| `environment_invalid` | Environment is not `DISPOSABLE_TEST` |
| `network_id_invalid` | Network ID is not disposable ID |
| `protocol_version_invalid` | Protocol version mismatch |
| `chain_id_invalid` | Declared chain ID ≠ recomputed |
| `genesis_digest_invalid` | Genesis digest mismatch / invalid |
| `peer_identity_invalid` | Peer id/address/public-key binding failure |
| `challenge_invalid` | Challenge bytes/id invalid |
| `response_invalid` | Response digest mismatch |
| `binding_mismatch` | Cross-message session/hello/challenge binding failure |
| `replay_detected` | Duplicate message_id or nonce |
| `message_stale` | Logical expiry exceeded |
| `message_premature` | Logical now before issued_at |
| `historical_import_forbidden` | MAIN/historical/canonical identity reuse |
| `execution_authorized_invalid` | `execution_authorized` is not JSON `false` |
| `lifecycle_invalid` | Illegal state transition |
| `internal_error` | Sanitized unexpected failure |

## Required public APIs (future implementation contract)

A later implementing foundation MUST provide these offline public functions and
MUST NOT grant runtime activation from them:

1. `verify_peer_handshake_message_json(payload, *, expected_genesis_digest: str, expected_chain_id: str, logical_now: int, replay_set: AbstractSet[str]) -> PeerHandshakeResult`
2. `verify_peer_handshake_hello_json(...)` — typed wrapper over (1) for hello
3. `verify_peer_handshake_challenge_json(..., *, expected_hello_message_id: str) -> PeerHandshakeResult`
4. `verify_peer_handshake_response_json(..., *, expected_challenge: Mapping[str, Any]) -> PeerHandshakeResult`
5. `verify_peer_handshake_accept_json(..., *, expected_response_message_id: str, expected_peer_id: str) -> PeerHandshakeResult`
6. `compute_peer_handshake_message_id(message_object: Mapping[str, Any]) -> str`
7. `compute_peer_handshake_challenge_id(*, challenge_hex: str, session_id: str, genesis_digest: str) -> str`
8. `compute_peer_handshake_response(*, challenge_hex: str, peer_public_key: str, genesis_digest: str, session_id: str) -> str`

Identity preconditions MUST call Foundation 39
`validate_disposable_handshake_identity_binding` with the message’s
`network_id`, `chain_id`, `protocol_version`, and `genesis_digest`.

`PeerHandshakeResult` MUST include at least:

- `ok: bool`
- `code: str`
- `message_type: str`
- `network_id: str`
- `chain_id: str`
- `genesis_digest: str`
- `protocol_version: str`
- `session_id: str`
- `message_id: str`
- `checks: list[str] | tuple[str, ...]`
- `execution_authorized: bool` — MUST be `False` on every path
- `report_id: str`

Core verification accepts JSON text or bytes only. Optional CLI MAY read one
explicit regular-file path and MUST reject directories and symbolic links.
Foundation 40 itself performs no I/O.

## Reproducible test vectors (normative shapes)

Future tests MUST include at least:

1. **Vector A — success path:** build disposable genesis via Foundation 39;
   derive `chain_id` / `genesis_digest`; construct hello → challenge → response
   → accept with logical times `(0, 60)`; all verifications `ok`;
   `execution_authorized=false`.
2. **Vector B — determinism:** identical bytes verified twice yield equal
   results and `report_id`.
3. **Vector C — identity mismatch:** mutate `network_id` to `MAIN` →
   `network_id_invalid` or `historical_import_forbidden`.
4. **Vector D — digest mismatch:** wrong `genesis_digest` →
   `genesis_digest_invalid`.
5. **Vector E — replay:** accept once, resubmit same `message_id` →
   `replay_detected`.
6. **Vector F — stale:** `logical_now=61` with expiry `60` → `message_stale`.
7. **Vector G — malformed:** oversized, invalid UTF-8, duplicate keys,
   non-finite, wrong field order, unknown fields.
8. **Vector H — response forgery:** alter `response` hex → `response_invalid`.

Challenge bytes for Vector A MUST use the deterministic vector-challenge
formula above so independent implementations converge.

## Required test groups (future implementing suite)

1. Schema acceptance for all five message types
2. Identity binding to Foundation 38/39 disposable tuple
3. Challenge/response determinism and forgery rejection
4. Replay and stale/premature matrices
5. Historical/canonical/`MAIN` separation
6. Malformed/size/UTF-8/duplicate-key/schema-order matrices
7. Lifecycle/idempotency/cleanup
8. Non-activation and static hygiene (no sockets, Leap28/Nova, wallet loads)

## Acceptance criteria

PASS only if:

- every required test group succeeds;
- handshake messages bind disposable `network_id`, `chain_id`,
  `genesis_digest`, `l28-protocol/1.0.0`, and `DISPOSABLE_TEST`;
- Protocol v1.0.0 economics remain unchanged and unreferenced as mutable;
- `execution_authorized` is always `false`;
- no socket, node, miner, wallet, ledger mutation, or testnet activation
  occurs.

FAIL if any group fails, if MAIN/historical identity is accepted, if Leap28 or
Nova identity is reused, or if success implies execution authority.

## Milestone dependencies and boundaries

| Track item | Status under Foundation 40 |
|---|---|
| **M1** disposable network identity / genesis (F38/F39) | Prerequisite — must remain available |
| **M2 peer-handshake identity binding (this foundation)** | Specification only |
| Disposable Core process (F38 table M2 / F37 M2) | Out of scope — separate foundation |
| P2P transport / sync codecs (F38 table M3 / F37 M3) | Out of scope — must consume this binding later |
| Propagation / confirmation (F37 M4) | Out of scope |
| Fork / reorg (F37 M5) | Out of scope |

A future transport foundation MUST treat Foundation 40 messages as the
authoritative handshake identity-binding contract and MUST NOT weaken these
rules.

## Security boundary

This specification and any future offline verifier for it MUST NOT:

- open network connections or listeners;
- start nodes, miners, wallets, or deployments;
- access private keys, seeds, credentials, or secrets;
- read or mutate ledgers or historical continuity state as runtime balances;
- import Leap28 or Nova authority, state, or code;
- treat handshake acceptance as spend permission or settlement finality.

## Non-authorization statement

A completed Foundation 40 specification, and any later successful verification
of handshake messages under this profile, is offline disposable
peer-identity-binding evidence only. It is not permission to spend L28, not an
executable transaction, not a ledger command, not settlement finality, not
main-network genesis, and not authorization to start a node, network, miner,
wallet, or testnet.

`execution_authorized` MUST remain the JSON boolean `false` on every conforming
message and every success or failure result path.
