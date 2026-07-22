# L28 Disposable Peer Admission Decision Envelope Specification v0.1

**Foundation:** 42

**Status:** Offline specification only; non-activation

**Milestone label:** Disposable peer admission decision envelope (post–Foundation 41)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN) — immutable

**Depends on:** Foundation 38/39 disposable network identity and genesis binding;
Foundation 40/41 peer-handshake identity binding

## Purpose

Foundation 42 defines the locked offline specification for a **Disposable Peer
Admission Decision Envelope**: a deterministic, fail-closed JSON evidence object
that binds a successful Foundation 39 disposable-identity verification result to
a successful Foundation 41 handshake-accept verification result and records an
offline admission **decision candidate**.

This envelope is public offline evidence only. It does **not** open sockets,
create sessions, discover peers, start nodes, mutate ledgers, authorize spend,
or activate a testnet. For this specification milestone both
`execution_authorized` and `admission_authorized` MUST remain the JSON boolean
`false` on every conforming document and every success or failure path.

Success under this profile means only:
`decision = identity_bound_candidate` with both authority flags false.

## Decision-gate evidence

Repository search found **no** pre-existing Foundation 42 name, document, or
roadmap entry defining a different Foundation 42 scope. Canonical sequence
evidence used for this definition:

| Artifact | Role |
|---|---|
| `docs/disposable_network_identity_genesis_binding_v0.1.md` | Foundation 38 locked M1 identity/genesis spec |
| `docs/foundation39_disposable_network_identity_genesis_binding_v0.1.md` | Foundation 39 implementation record |
| `coin/disposable_network_identity_genesis_binding.py` | Foundation 39 verifier |
| `docs/peer_handshake_identity_binding_v0.1.md` | Foundation 40 locked handshake identity-binding spec |
| `docs/foundation41_peer_handshake_identity_binding_v0.1.md` | Foundation 41 implementation record |
| `coin/peer_handshake_identity_binding.py` | Foundation 41 validator |
| `docs/bounded_testnet_readiness_gap_audit_v0.1.md` | F37 readiness gaps; M3 remains transport/sync |

Selected scope (no conflicting repository definition):
**Disposable Peer Admission Decision Envelope Specification v0.1**.

This Foundation 42 scope does **not** implement Foundation 37/38 **M3**
transport, listeners, discovery, or synchronization. It only specifies an
offline decision envelope that a future Foundation 43 verifier may validate.

## Exclusions

Foundation 42 MUST NOT:

- implement production modules, tests, CLIs, or configuration files;
- open sockets, listeners, transports, or peer sessions;
- perform peer discovery, networking, or node runtime activation;
- persist live peer registries or session runtime state;
- perform signing, wallet access, transaction submission, payment, mining,
  consensus, ledger mutation, deployment, or testnet activation;
- authorize MAIN, historical import, or canonical-state reuse;
- introduce new dependencies or Leap28/Nova coupling;
- alter Protocol v1.0.0 protected economics;
- set `execution_authorized` or `admission_authorized` to `true`;
- implement M3+ transport/sync/propagation/reorg;
- leak exception text, stack traces, filesystem paths, secrets, or private keys
  into results, envelopes, reports, logs, or tests.

## Trust boundaries

| Boundary | Rule |
|---|---|
| Input trust | Caller-supplied JSON/bytes only; no filesystem discovery |
| Identity trust | Must re-bind Foundation 39 disposable identity tuple |
| Handshake trust | Must re-bind Foundation 41 accept-path report and message IDs |
| Challenge trust | Must recompute Foundation 40 challenge_id and response digests |
| Output trust | Sanitized stable codes and digests only; empty detail |
| Authority | Envelope success ≠ network admission, spend, or runtime |

Private keys, seeds, credentials, secrets, filesystem paths, and raw exception
text MUST NEVER appear in envelopes, reports, tests, or logs.

## Protected economic facts (immutable)

| Fact | Value | Evidence |
|---|---:|---|
| Hard cap | `28_000_000` | `coin/tx_validation.py` `L28_MAX_SUPPLY` |
| Emission ceiling | `11_130_000` | `coin/tx_validation.py` `L28_EMISSION_CEILING` |
| Halving interval | `210_000` | `coin/tx_validation.py` `L28_HALVING_INTERVAL` |
| Max coinbase reward | `28` | `coin/tx_validation.py` `L28_MAX_COINBASE_REWARD` |
| Reward schedule | `(28, 14, 7, 3, 1)` | `coin/tx_validation.py` `L28_REWARD_SCHEDULE` |

Admission envelopes MUST NOT carry balances, issuance, rewards, or reminting
claims. This specification MUST NOT change these facts.

## Public identifiers

| Identifier | Value |
|---|---|
| Profile | `l28-peer-admission-decision-envelope/v0.1` |
| Verifier profile | `l28-peer-admission-decision-envelope-verifier/v0.1` |
| Report profile | `l28-peer-admission-decision-envelope-report/v0.1` |
| Bound identity profile | `l28-disposable-network-identity-genesis-binding/v0.1` |
| Bound handshake profile | `l28-peer-handshake-identity-binding/v0.1` |
| Environment | `DISPOSABLE_TEST` |
| Network ID | `l28-disposable-test/v0.1` |
| Protocol version | `l28-protocol/1.0.0` |
| Decision value | `identity_bound_candidate` |
| Maximum encoded envelope size | `12288` bytes |
| Logical default lifetime | `60` |
| Logical lifetime range | `[1, 3600]` |

## Strict dependency on Foundations 39 and 41

A conforming future verifier MUST refuse verification unless the caller supplies
evidence derived from **successful** prior reports:

1. Foundation 39 disposable identity verification with `ok=true` and `code=ok`
   for the exact tuple
   `(network_id, chain_id, protocol_version, genesis_digest, environment=DISPOSABLE_TEST)`.
2. Foundation 41 handshake-accept verification with `ok=true` and `code=ok`
   for the same identity tuple and peer, producing
   `handshake_accept_report_id` and `handshake_accept_message_id`.

The verifier MUST re-check Foundation 39
`validate_disposable_handshake_identity_binding` against the envelope fields.
It MUST NOT trust caller booleans alone. Envelope `environment` values in
`{MAIN, CANONICAL, HISTORICAL, PRODUCTION}` fail closed with
`historical_import_forbidden` before any other environment code. Any other
non-`DISPOSABLE_TEST` environment fails with `environment_invalid`. Identity
tuple failures use the matching Foundation 39 stable codes. No permissive
fallback to MAIN, historical import, or canonical-state reuse is allowed.

## Inputs

A conforming future verifier MUST accept JSON text or bytes only and MUST
require the caller to supply:

1. Envelope payload (candidate or claimed envelope document).
2. `expected_genesis_digest` — Foundation 39 verified disposable genesis digest.
3. `expected_chain_id` — Foundation 39 recomputed disposable chain ID.
4. `expected_handshake_accept_report_id` — Foundation 41 accept-path `report_id`.
5. `expected_handshake_accept_message_id` — Foundation 41 accept `message_id`.
6. `expected_peer_id` — peer identity bound by the accept path.
7. `expected_session_id` — Foundation 41 accept `session_id`.
8. `expected_challenge_hex` — 64-hex challenge bytes from the accepted challenge.
9. `expected_challenge_message_id` — accepted challenge `message_id`.
10. `expected_response_message_id` — accepted response `message_id`.
11. `logical_now` — non-negative integer logical clock (offline vectors only).
12. `replay_set` — set of previously accepted envelope IDs and nonces.

Optional CLI (Foundation 43 only) MAY read one explicit regular-file path and
MUST reject directories and symbolic links. Foundation 42 itself performs no I/O
and ships no CLI.

## Outputs

`PeerAdmissionDecisionResult` MUST include at least these fields. Failure paths
MUST sanitize unset string fields to empty strings and MUST NEVER include
exception text:

- `ok: bool`
- `code: str`
- `decision: str` — empty on failure; on success exactly
  `identity_bound_candidate`
- `network_id: str`
- `chain_id: str`
- `genesis_digest: str`
- `protocol_version: str`
- `environment: str`
- `peer_id: str`
- `handshake_accept_report_id: str`
- `handshake_accept_message_id: str`
- `envelope_id: str`
- `checks: tuple[str, ...]`
- `detail: str` — MUST be empty string in v0.1
- `execution_authorized: bool` — MUST be `False` on every path
- `admission_authorized: bool` — MUST be `False` on every path
- `report_id: str`

## Exact envelope schema and field order

The admission decision envelope is one JSON object with exactly these fields in
this order:

1. `envelope_version`
2. `environment`
3. `network_id`
4. `chain_id`
5. `protocol_version`
6. `genesis_digest`
7. `peer_id`
8. `peer_public_key`
9. `peer_address`
10. `handshake_version`
11. `handshake_accept_message_id`
12. `handshake_accept_report_id`
13. `handshake_session_id`
14. `challenge`
15. `challenge_id`
16. `response`
17. `challenge_message_id`
18. `response_message_id`
19. `decision`
20. `issued_at_logical`
21. `expires_at_logical`
22. `nonce`
23. `execution_authorized`
24. `admission_authorized`
25. `envelope_id`

Unknown, missing, reordered, duplicated, or incorrectly typed fields fail
closed (`schema_invalid` or `duplicate_key`). Non-finite numbers and invalid
UTF-8 fail closed. Encoded payload size above `12288` bytes fails with
`input_too_large`.

### Field rules

| Field | Rule |
|---|---|
| `envelope_version` | Exact `l28-peer-admission-decision-envelope/v0.1` |
| `environment` | Exact `DISPOSABLE_TEST` |
| `network_id` | Exact `l28-disposable-test/v0.1` |
| `chain_id` | Exact expected disposable chain ID (64 lowercase hex) |
| `protocol_version` | Exact `l28-protocol/1.0.0` |
| `genesis_digest` | Exact expected disposable genesis digest (64 lowercase hex) |
| `peer_id` | Exact expected peer id (64 lowercase hex) |
| `peer_public_key` | 64 lowercase hex; peer derivation must match Foundation 40 rules |
| `peer_address` | `L28` + 40 lowercase hex; must match Foundation 40 derivation |
| `handshake_version` | Exact `l28-peer-handshake-identity-binding/v0.1` |
| `handshake_accept_message_id` | Exact expected accept message id |
| `handshake_accept_report_id` | Exact expected accept report id |
| `handshake_session_id` | Exact expected accept session id (64 lowercase hex) |
| `challenge` | Exact expected challenge hex (64 lowercase hex) |
| `challenge_id` | Must equal Foundation 40 `compute_peer_handshake_challenge_id` |
| `response` | Must equal Foundation 40 `compute_peer_handshake_response` |
| `challenge_message_id` | Exact expected challenge message id |
| `response_message_id` | Exact expected response message id |
| `decision` | Exact `identity_bound_candidate` |
| `issued_at_logical` | Exact non-negative integer |
| `expires_at_logical` | Exact integer `>` issued; see lifetime rule |
| `nonce` | 64 lowercase hex; unique within the verifier replay window |
| `execution_authorized` | JSON boolean `false` only |
| `admission_authorized` | JSON boolean `false` only |
| `envelope_id` | 64 lowercase hex; see identifier rule |

Environment classification MUST match Foundations 40/41:

1. If `environment` ∈ `{MAIN, CANONICAL, HISTORICAL, PRODUCTION}`, fail with
   `historical_import_forbidden`.
2. Else if `environment` ≠ `DISPOSABLE_TEST`, fail with `environment_invalid`.

Lifetime rule (matches Foundations 40/41): after accepting exact integer
`issued_at_logical` and `expires_at_logical` with `expires_at_logical` `>`
`issued_at_logical`, compute
`lifetime_seconds = expires_at_logical - issued_at_logical`.
`lifetime_seconds` MUST be an integer in `[1, 3600]` inclusive; otherwise fail
with `schema_invalid`. Empty network IDs and historical continuity digests as
genesis MUST fail closed via the matching identity codes.

## Dependency binding algorithm (normative)

A conforming Foundation 43 verifier MUST execute these checks in order and stop
at the first failure (deterministic first-failure precedence):

1. Parse and enforce size/UTF-8/JSON/duplicate-key/top-level/schema/order/type.
2. Reject unsupported `envelope_version` with `envelope_version_unsupported`.
3. If `environment` ∈ `{MAIN, CANONICAL, HISTORICAL, PRODUCTION}`, fail with
   `historical_import_forbidden`.
4. Else if `environment` ≠ `DISPOSABLE_TEST`, fail with `environment_invalid`.
5. Call Foundation 39 `validate_disposable_handshake_identity_binding` with the
   envelope’s `network_id`, `chain_id`, `protocol_version`, and
   `genesis_digest`; require `ok` and equality to expected identity values.
6. Require peer fields to satisfy Foundation 40 peer-identity derivation and
   equal `expected_peer_id`.
7. Require `handshake_accept_report_id` and `handshake_accept_message_id` to
   equal the caller-supplied Foundation 41 accept-path identifiers.
8. Require `handshake_session_id == expected_session_id`.
9. Require `challenge == expected_challenge_hex`.
10. Recompute `challenge_id` via Foundation 40
    `compute_peer_handshake_challenge_id(challenge_hex=challenge,
    session_id=handshake_session_id, genesis_digest=genesis_digest)` and require
    equality.
11. Recompute `response` via Foundation 40
    `compute_peer_handshake_response(challenge_hex=challenge,
    peer_public_key=peer_public_key, genesis_digest=genesis_digest,
    session_id=handshake_session_id)` and require equality.
12. Require `challenge_message_id` and `response_message_id` to equal expected
    values.
13. Require `decision == identity_bound_candidate`.
14. Require exact integer `issued_at_logical` ≥ `0` and exact integer
    `expires_at_logical` `>` `issued_at_logical`; compute
    `lifetime_seconds = expires_at_logical - issued_at_logical`; if
    `lifetime_seconds` is not an integer in `[1, 3600]`, fail with
    `schema_invalid`.
15. Enforce logical clock freshness (`message_premature` /
    `message_stale`) and replay uniqueness (`replay_detected`).
16. Require both authority flags are JSON `false`
    (`execution_authorized_invalid` / `admission_authorized_invalid`).
17. Recompute and bind `envelope_id` (`envelope_id_invalid` on mismatch).

Mismatch fails closed. No fallback, coercion, silent field dropping, or
exception leakage is permitted.

## Deterministic identifiers and canonical JSON

Canonical JSON for digests uses:

- UTF-8
- `ensure_ascii=false`
- `allow_nan=false`
- `sort_keys=true`
- separators `(",", ":")`

Wire acceptance requires exact schema field order. Digest canonicalization uses
sorted keys only after schema/order acceptance.

Let `PROFILE = l28-peer-admission-decision-envelope/v0.1`.

- `envelope_id` = hex(sha256(UTF8(PROFILE) || 0x00 || UTF8("envelope") || 0x00 ||
  canonical_json(envelope_without_envelope_id)))
- `report_id` = hex(sha256(UTF8(report_profile) || 0x00 ||
  canonical_json(report_body)))

`report_body` MUST be exactly this object with sorted-key canonicalization after
logical construction (implementation MAY build via mapping; digest MUST equal
the canonical form of these keys/values):

- `ok`
- `code`
- `decision`
- `network_id`
- `chain_id`
- `genesis_digest`
- `protocol_version`
- `environment`
- `peer_id`
- `handshake_accept_report_id`
- `handshake_accept_message_id`
- `envelope_id`
- `checks`
- `detail`
- `execution_authorized`
- `admission_authorized`
- `verifier_profile`

Identical accepted bytes MUST yield identical verification results and
`report_id` across repeated runs. Compact and pretty JSON that parse to the
same logical object MUST produce equal results after schema acceptance.
Nondeterministic clocks, randomness, unordered sets in digests, or floating
timestamps are forbidden in identifier construction.

## Lifecycle and deterministic state transitions

Offline conceptual states (no process activation):

| State | Meaning |
|---|---|
| `CREATED` | Local disposable identity available via Foundation 39 |
| `HANDSHAKE_ACCEPTED` | Foundation 41 accept path verified |
| `ENVELOPE_CANDIDATE` | Envelope constructed/bound |
| `ENVELOPE_VERIFIED` | Envelope verification succeeded |
| `REJECTED` | Verification failed closed |
| `EXPIRED` | Logical expiry reached |
| `CLOSED` | Cleanup complete |

Allowed transitions only:

- `CREATED` → `HANDSHAKE_ACCEPTED` | `REJECTED` | `CLOSED`
- `HANDSHAKE_ACCEPTED` → `ENVELOPE_CANDIDATE` | `REJECTED` | `CLOSED`
- `ENVELOPE_CANDIDATE` → `ENVELOPE_VERIFIED` | `REJECTED` | `EXPIRED` | `CLOSED`
- `ENVELOPE_VERIFIED` → `CLOSED`
- `REJECTED` → `CLOSED`
- `EXPIRED` → `CLOSED`

Any other transition fails closed with `lifecycle_invalid`.

`ENVELOPE_VERIFIED` proves only that a disposable identity-bound admission
**candidate** envelope is internally consistent. It does **not** authorize live
peer admission, transport, session persistence, or spend.

## Replay, stale, expired, mismatched, and malformed rejection

1. If `envelope_id` or `nonce` is present in `replay_set`, fail with
   `replay_detected`.
2. If `logical_now` `<` `issued_at_logical`, fail with `message_premature`.
3. If `logical_now` `>` `expires_at_logical`, fail with `message_stale`.
4. Unsupported `envelope_version` fails with `envelope_version_unsupported`.
5. Forbidden environments `{MAIN, CANONICAL, HISTORICAL, PRODUCTION}` fail with
   `historical_import_forbidden` before `environment_invalid`.
6. Out-of-range `lifetime_seconds` (not in `[1, 3600]`) fails with
   `schema_invalid`.
7. Malformed type/size/UTF-8/JSON/duplicate-key/unknown-field/order failures use
   the stable codes below (`schema_invalid` covers unknown and reordered fields).
8. Identity, handshake, peer, challenge, response, or decision mismatches use
   the matching binding codes.
9. Illegal lifecycle transitions use `lifecycle_invalid`.
10. No permissive repair, coercion, silent field dropping, hidden mutation, or
    exception leakage is allowed.

## Required success checks

On success, `checks` MUST equal this exact order:

1. `schema_exact`
2. `environment_disposable`
3. `network_id_bound`
4. `protocol_version_bound`
5. `chain_id_bound`
6. `genesis_digest_bound`
7. `peer_identity_bound`
8. `handshake_accept_bound`
9. `challenge_response_bound`
10. `decision_candidate_only`
11. `replay_fresh`
12. `execution_authorized_false`
13. `admission_authorized_false`

## Stable error-code registry

| Code | Meaning |
|---|---|
| `ok` | Verification succeeded |
| `input_type_invalid` | Unsupported payload type |
| `input_too_large` | Encoded size exceeds limit |
| `encoding_invalid` | Invalid UTF-8 |
| `json_invalid` | Malformed JSON or non-finite number |
| `duplicate_key` | Duplicate key at any depth |
| `invalid_top_level` | Top-level value is not an object |
| `schema_invalid` | Missing/unknown/reordered/wrong-type fields |
| `envelope_version_unsupported` | Unsupported envelope version |
| `environment_invalid` | Environment is not `DISPOSABLE_TEST` |
| `network_id_invalid` | Network ID is not disposable ID |
| `protocol_version_invalid` | Protocol version mismatch |
| `chain_id_invalid` | Chain ID mismatch / invalid |
| `genesis_digest_invalid` | Genesis digest mismatch / invalid |
| `peer_identity_invalid` | Peer id/address/public-key binding failure |
| `handshake_binding_invalid` | Handshake accept report/message/session binding failure |
| `challenge_binding_invalid` | Challenge/response recomputation or message-id binding failure |
| `decision_invalid` | Decision is not `identity_bound_candidate` |
| `replay_detected` | Duplicate envelope_id or nonce |
| `message_stale` | Logical expiry exceeded |
| `message_premature` | Logical now before issued_at |
| `historical_import_forbidden` | MAIN/historical/canonical identity reuse |
| `execution_authorized_invalid` | `execution_authorized` is not JSON `false` |
| `admission_authorized_invalid` | `admission_authorized` is not JSON `false` |
| `lifecycle_invalid` | Illegal state transition |
| `envelope_id_invalid` | Declared envelope_id ≠ recomputed |
| `internal_error` | Sanitized unexpected failure (`detail` remains empty) |

**Stable error-code count:** 27

## Required public APIs (Foundation 43 implementation contract)

1. `verify_peer_admission_decision_envelope_json(payload, *, expected_genesis_digest: str, expected_chain_id: str, expected_handshake_accept_report_id: str, expected_handshake_accept_message_id: str, expected_peer_id: str, expected_session_id: str, expected_challenge_hex: str, expected_challenge_message_id: str, expected_response_message_id: str, logical_now: int, replay_set: AbstractSet[str]) -> PeerAdmissionDecisionResult`
2. `compute_peer_admission_envelope_id(envelope_object: Mapping[str, Any]) -> str`
3. `build_peer_admission_decision_envelope(...)` — deterministic offline builder for fixtures only; MUST force both authority flags to `false`

These APIs MUST NOT open sockets, mutate ledgers, start nodes, or set either
authority flag to `true`.

## Foundation 43 acceptance tests (normative)

A conforming Foundation 43 implementation suite MUST include at least:

1. **Success path** — Foundation 39 genesis + Foundation 41 accept fixtures produce
   a verifying envelope with `decision=identity_bound_candidate`,
   `execution_authorized=false`, `admission_authorized=false`, and the exact
   13-item `checks` tuple.
2. **Determinism** — identical bytes verify twice with equal results/`report_id`.
3. **Identity mismatch** — `network_id=MAIN` fails closed with
   `network_id_invalid` (or the Foundation 39 identity code surfaced unchanged).
4. **Forbidden-environment precedence** — for each
   `environment ∈ {MAIN, CANONICAL, HISTORICAL, PRODUCTION}`, verification fails
   with exactly `historical_import_forbidden`. When a payload could otherwise
   also fail a later check, the forbidden-environment code MUST win (first
   failure).
5. **Generic invalid environment** — `environment` values other than
   `DISPOSABLE_TEST` and outside `{MAIN, CANONICAL, HISTORICAL, PRODUCTION}`
   (for example `OTHER`) fail with exactly `environment_invalid`.
6. **Handshake report mismatch** — wrong accept `report_id` fails with
   `handshake_binding_invalid`.
7. **Peer mismatch** — wrong `peer_id` fails with `peer_identity_invalid`.
8. **Challenge/response recomputation** — mutated `challenge_id` or `response`
   fails with `challenge_binding_invalid`.
9. **Replay** — resubmitting accepted `envelope_id` or `nonce` fails with
   `replay_detected`.
10. **Stale / premature** — `logical_now > expires_at_logical` →
    `message_stale`; `logical_now < issued_at_logical` → `message_premature`.
11. **Lifetime below 1** — `expires_at_logical <= issued_at_logical` or computed
    `lifetime_seconds < 1` fails with exactly `schema_invalid`.
12. **Lifetime above 3600** — `lifetime_seconds > 3600` fails with exactly
    `schema_invalid`.
13. **Malformed matrix** — type/size/UTF-8/JSON/duplicate-key/top-level/schema/
    unknown-field/order.
14. **Unsupported version** — foreign `envelope_version` fails with
    `envelope_version_unsupported`.
15. **Invalid transition** — illegal lifecycle transition fails with
    `lifecycle_invalid`.
16. **Authority flags** — `execution_authorized=true` →
    `execution_authorized_invalid`; `admission_authorized=true` →
    `admission_authorized_invalid`.
17. **Static hygiene** — no socket/network/Leap28/Nova/wallet imports; no
    exception text in results.
18. **All 27 stable codes** explicitly asserted through the public API
    (`internal_error` via narrow monkeypatch of an internal helper).

## Acceptance criteria (this specification)

PASS only if:

- the document defines complete schema, lifecycle, identifiers, limits, and
  stable errors;
- Foundation 39 and 41 dependencies are mandatory and fail-closed;
- challenge/response recomputation is mandatory via Foundation 40 helpers;
- `execution_authorized` and `admission_authorized` remain false;
- M3+ runtime/transport work is explicitly excluded;
- Protocol v1.0.0 economics are unchanged;
- no production code or tests are introduced by Foundation 42.

## Security boundary and non-authorization statement

A completed Foundation 42 specification, and any later successful verification
of an admission decision envelope under this profile, is offline disposable
admission-candidate evidence only. It is not permission to spend L28, not an
executable transaction, not a ledger command, not settlement finality, not
main-network genesis, not live peer admission, and not authorization to start a
node, network, miner, wallet, or testnet.

`execution_authorized` and `admission_authorized` MUST remain the JSON boolean
`false` on every conforming envelope and every success or failure result path.
