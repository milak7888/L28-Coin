# Foundation 57 UAII Reference Core Contract Specification v0.1

**Status:** Specification only (documentation; non-activation; non-implementation)

**Profile / `reference_core_profile`:**
`l28-uaii-reference-core-contract/v0.1`

**Parent UAII contract:** Foundation 56 —
`l28-universal-ai-access-interface/v0.1`
(`docs/foundation56_universal_ai_access_interface_specification_v0.1.md`)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Base commit:** `dc10e565db8ca5d2aa72b95b0bfcbbca60520336`

**Branch:** `foundation57-uaii-reference-core-contract-specification`

**Normative subordination:** This document is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md) and to Foundation 56. On conflict,
Protocol v1.0.0 prevails; then Foundation 56; then this reference-core contract.
This document MUST NOT redefine settlement, issuance, supply, consensus height
authority, or M2M envelope `message_id` derivation.

## 1. Purpose and scope

Foundation 57 resolves exactly five Foundation 56 §13 items that block a
deterministic, transport-neutral UAII **reference core**:

1. `ledger_state_id` preimage
2. Expiration and clock-skew rules
3. Address grammar decision for UAII v0.1
4. UAII identifier ↔ M2M `message_id` mapping rules
5. Nonce retention and replay policy

It defines schemas, domain separation, preimages, precedence, and conformance
obligations only. It does **not** implement UAII, adapters, signers, ledgers,
replay stores, bridges, or runtimes.

### 1.1 Explicitly unresolved / out of scope

The following remain unresolved or out of scope (Foundation 56 §13.6 and
product exclusions):

- Escrow
- Refund execution
- Multi-party settlement
- Blockchain bridges and adapters
- Bitcoin, Ethereum, Monero, stablecoin, cross-chain, liquidity, custody, or
  exchange integration
- Signed-quote implementation
- Signing, keystore, wallet, broadcast, node, miner, network, or testnet
- MCP, REST/OpenAPI, Python SDK, or TypeScript SDK implementation
- Leap28 / Nova dependencies

### 1.2 Normative language

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted
as described in RFC 2119 / RFC 8174 when, and only when, they appear in
uppercase as shown here.

## 2. Authority

1. Foundation 56 remains the parent UAII contract (seven operations; 16384-byte
   envelope; exact-order UAII JSON; `sort_keys=false` content digests).
2. `validate_transaction` in `coin/tx_validation.py` under Protocol v1.0.0
   remains the **sole settlement-validation authority**.
3. Reference-core decisions MUST NOT change supply, issuance, consensus,
   canonical height meaning, or historical evidence.
4. Every described UAII operation remains non-executing:
   `execution_authorized=false`.
5. Unsigned payment objects remain `spend_authorized=false`.
6. Read-only validation remains `ledger_mutated=false`.
7. L28-M2M Canonical JSON v0.1 remains the sole canonicalization authority for
   M2M envelopes and M2M digests (`docs/m2m/interoperability_profile_v0.1.md`,
   `coin/m2m_verifier.py`).
8. UAII exact-order UTF-8 JSON (Foundation 56 §3.2) remains the sole
   canonicalization authority for UAII objects and UAII digests defined here.

### 2.1 Protected economic facts (unchanged)

| Fact | Value | Evidence |
|---|---|---|
| Hard cap | `28_000_000` | `PROTOCOL.md`, `coin/tx_validation.py` |
| Emission ceiling | `11_130_000` | same |
| Historically mined | `2_824_584` | `tx_validation.L28_HISTORICAL_MINED` |
| Treasury locked | `500_000` | `docs/m2m/protocol_v0.1.md` §2 |
| Circulating snapshot | `2_324_584` | `docs/m2m/protocol_v0.1.md` §2 |

## 3. Shared deterministic primitives

### 3.1 Hex and digests

- SHA-256 output MUST be encoded as **64 lowercase hexadecimal characters**.
- Hex inputs that must be hex64 MUST match `^[0-9a-f]{64}$`.

### 3.2 UAII canonical bytes

`CanonUaii(x)` denotes UTF-8 bytes of JSON serialization of object `x` under
Foundation 56 §3.2:

- exact declared field order;
- `sort_keys=false`;
- separators `(",", ":")`;
- `ensure_ascii=false`;
- `allow_nan=false`.

### 3.3 M2M canonical bytes

`CanonM2m(x)` denotes L28-M2M Canonical JSON v0.1 bytes
(`coin/m2m_verifier.canonicalize` / interoperability profile §2): recursively
sorted keys; snake_case property names; no floats.

### 3.4 Domain separation (new UAII reference-core domains)

Exact ASCII/UTF-8 domain prefixes (including trailing NUL `0x00`):

| Purpose | Prefix bytes |
|---|---|
| Ledger state id | `L28-UAII-V0.1-LEDGER-STATE` + `0x00` |
| UAII↔M2M correlation | `L28-UAII-V0.1-M2M-CORRELATION` + `0x00` |
| Replay key | `L28-UAII-V0.1-REPLAY` + `0x00` |

These domains are **UAII reference-core** domains. They MUST NOT replace M2M
domains:

- `L28-M2M-V0.1-PAYLOAD\x00`
- `L28-M2M-V0.1-MESSAGE\x00`
- `L28-M2M-V0.1-SIGNATURE\x00`
- `L28-M2M-V0.1-REPLAY-EXCHANGE\x00`
- `L28-M2M-V0.1-REPLAY-TRANSCRIPT\x00`

### 3.5 Integer-only amounts and times

All amounts and all UAII timestamps in this contract MUST be exact JSON
integers. Floating-point values are forbidden.

## 4. Resolved contract 1 — `ledger_state_id` preimage

### 4.1 Evidence basis

| Binding input | Repository evidence |
|---|---|
| Canonical height | Protocol `H`; runtime `mint_height` / `canonical_height` lookups (`PROTOCOL.md`, `coin/ledger.py`, `coin/tx_validation.py`) |
| Issued supply | Protocol `IssuedSupply`; runtime `issued_supply` |
| Issuance readiness | `BlocklessLedger._canonical_issuance_ready` / fail-closed empty≠genesis (`PROTOCOL.md` Fail-Closed Rule; `ledger.py`) |
| Accepted-tx cardinality | `len(_seen_tx_ids)` (unordered `set[str]` replay index in `coin/ledger.py`); count only — not an ordered ledger tip |
| Protected supply reports | Hard cap / emission ceiling / historical mined frozen reports (`PROTOCOL.md`, `coin/tx_validation.py`) |
| No Protocol tip authority | Protocol v1.0.0, `ledger.py`, and `tx_validation.py` define no tip field, tip selector, or lexicographic-max tip rule |
| No prior `ledger_state_id` formula | Foundation 56 §13.1 deferred; no `L28-LEDGER-*` domain in-repo |

This section **defines** the missing UAII ledger-state evidence binding. It does
not create a second ledger, consensus rule, tip selector, or ordered accepted-ID
ledger.

### 4.2 Authoritative state requirement

Before computing `ledger_state_id`, a conforming reference core MUST obtain
authoritative local ledger/consensus lookups that Protocol validation would
require for fail-closed operation.

If any of the following is true, the operation MUST fail closed with
`ledger_state_unavailable` and MUST NOT invent a state id:

1. canonical issuance state is not ready (`canonical_issuance_ready=false`);
2. canonical height lookup is unavailable, malformed, or inconsistent;
3. issued supply lookup is unavailable, malformed, or inconsistent;
4. accepted-transaction index is unavailable (cardinality cannot be derived);
5. any required protected supply-report field is missing, malformed, or
   inconsistent with Protocol-frozen values;
6. any other required `UaiiLedgerStateBinding` field is missing, unavailable,
   malformed, or inconsistent.

Empty directory / zero counters without explicit trusted initialization MUST
fail closed (Protocol + `ledger.py`).

### 4.3 Protocol tip binding deferred

Protocol tip binding is **deferred**. The repository has no canonical tip
authority: `_seen_tx_ids` is an unordered set used for replay lookup, and
neither Protocol v1.0.0 nor `tx_validation.py` defines a tip field, tip
selector, lexicographic-maximum tip, insertion-order tip, or set-iteration tip.

Therefore this reference-core contract:

1. MUST NOT define, require, or encode `tip_tx_id`, `canonical_tip`, tip
   evidence ids, lexicographic-maximum accepted transaction ids, set iteration
   order, or insertion order as ledger-state evidence;
2. MUST NOT invent a digest over the accepted-ID set unless a separately
   authorized Protocol-governed commitment already exists (none exists in the
   current repository baseline);
3. MUST treat unavailable Protocol tip authority as a non-binding condition for
   `ledger_state_id` (tip is simply not part of the preimage), while still
   fail-closing on missing/unavailable/malformed/inconsistent/issuance-unready
   authoritative fields listed in §4.2.

A future Protocol-governed tip commitment MAY be added only by a separately
authorized contract. UAII MUST NOT infer tip semantics.

### 4.4 Ledger-state evidence object (`UaiiLedgerStateBinding`)

Exact fields in this order (JSON types as stated; integers are exact JSON
integers with no floats; booleans are exact JSON booleans):

1. `binding_profile` — string `"l28-uaii-ledger-state-binding/v0.1"`
2. `protocol_version` — string `"1.0.0"`
3. `currency` — string `"L28"`
4. `max_supply` — integer `28000000` (frozen report of Protocol hard cap;
   not mutable)
5. `emission_ceiling` — integer `11130000` (frozen report)
6. `historical_mined` — integer `2824584` (frozen report)
7. `canonical_height` — integer `>= 0` from authoritative height lookup
8. `issued_supply` — integer `>= 0` from authoritative supply lookup
9. `canonical_issuance_ready` — boolean; MUST be `true` at bind time
10. `accepted_tx_count` — integer `>= 0` equal to the cardinality of the
    authoritative accepted-ID state (for example `len(_seen_tx_ids)`). The
    accepted-ID set MUST NOT be serialized, ordered, iterated for tip
    selection, or otherwise exposed as an ordered ledger in this binding.

`CanonUaii(UaiiLedgerStateBinding)` uses Foundation 56 §3.2 exact-order JSON
(`sort_keys=false`; separators `(",", ":")`; `ensure_ascii=false`;
`allow_nan=false`).

### 4.5 `ledger_state_id` formula

```
ledger_state_id = hex_lower(
  SHA-256(
    b"L28-UAII-V0.1-LEDGER-STATE\x00" || CanonUaii(UaiiLedgerStateBinding)
  )
)
```

Domain bytes are exactly ASCII `L28-UAII-V0.1-LEDGER-STATE` followed by a
single NUL (`0x00`). The digest is 64 lowercase hex characters.

### 4.6 Genesis / empty / unready behavior

| State | Behavior |
|---|---|
| Issuance not ready / untrusted empty | Fail `ledger_state_unavailable`; no id |
| Any required authoritative field missing, unavailable, malformed, or inconsistent | Fail `ledger_state_unavailable`; no id |
| Issuance ready; all required fields available and consistent; `accepted_tx_count=0` | Allowed; compute `ledger_state_id` from §4.4 / §4.5 |
| Issuance ready; all required fields available and consistent; `accepted_tx_count>0` | Allowed; compute `ledger_state_id` from §4.4 / §4.5 using cardinality only (no tip/id ordering) |

## 5. Resolved contract 2 — Expiration and clock-skew rules

### 5.1 Evidence basis

- Foundation 56: timestamps are integer Unix seconds; `expires_at > created_at`.
- M2M message_schema §2.3: expired when local time **greater than** `expires_at`
  after skew; exact skew default is local policy; Protocol publishes no M2M skew
  constant.
- Foundation 56 quote path: expired when evaluation time
  `>= quote_expires_at`.
- No `MAX_SKEW` constant exists in-repo — this profile **locks** one for UAII
  reference-core determinism (does not amend Protocol or M2M peer policy).

### 5.2 Timestamp format and UTC normalization

1. All UAII time fields (`created_at`, `expires_at`, `quote_expires_at`,
   `payment_expires_at`, `completed_at`, and evaluation time) MUST be exact
   integers representing **Unix seconds in UTC** (POSIX time).
2. Sub-second fractions MUST NOT appear.
3. Boolean/string/float/null times MUST be rejected (`schema_invalid` /
   `json_invalid` as applicable under Foundation 56).

### 5.3 Skew-tolerance constant

```
UAII_CLOCK_SKEW_TOLERANCE_SECONDS = 300
```

Meaning: ±300 seconds inclusive tolerance for wall-clock comparisons in the
UAII reference core.

**Evidence note:** Value is a new UAII reference-core lock. It is not claimed as
a Protocol consensus constant. M2M remains free to use distinct local peer
policy outside UAII.

### 5.4 Evaluation time

Let `T_eval` be the reference core’s evaluation clock as integer Unix UTC
seconds. Wall-clock MUST NEVER replace `validate_transaction` or ledger
authority.

### 5.5 Inclusive / exclusive boundaries

| Object | Expired / invalid when | Bound |
|---|---|---|
| Envelope `expires_at` | `T_eval > expires_at + UAII_CLOCK_SKEW_TOLERANCE_SECONDS` | Exclusive past end of skewed expiry |
| Envelope future `created_at` | `created_at > T_eval + UAII_CLOCK_SKEW_TOLERANCE_SECONDS` | Reject as skewed/not-yet-valid |
| Quote `quote_expires_at` | `T_eval >= quote_expires_at` | Inclusive (Foundation 56) |
| Payment `payment_expires_at` | `T_eval >= payment_expires_at` | Inclusive |

Envelope skew applies only to envelope wall-clock checks. Quote/payment expiry
remain Foundation 56 inclusive comparisons against `T_eval` (no additional
skew expansion), preserving F56 locked quote language.

### 5.6 Time validation precedence (after Foundation 56 shared steps through
envelope freshness slot)

When performing UAII reference-core time checks, stop at first failure:

1. Malformed time types/bounds (`schema_invalid` / existing Foundation 56 codes)
2. `expires_at <= created_at` (`schema_invalid` / envelope freshness failure)
3. `created_at > T_eval + UAII_CLOCK_SKEW_TOLERANCE_SECONDS`
   (`request_not_yet_valid`)
4. `T_eval > expires_at + UAII_CLOCK_SKEW_TOLERANCE_SECONDS` (`request_expired`)
5. Operation-local quote/payment expiry rules (Foundation 56 §5 lists)

**New stable code for this profile:** `request_not_yet_valid` — envelope
`created_at` unreasonably far in the future beyond skew.

## 6. Resolved contract 3 — Address grammar

### 6.1 Evidence basis

- `PROTOCOL.md` treats account strings as protocol string fields; no `L28`+hex
  grammar is defined as consensus address format.
- M2M profiles state accounts remain opaque strings.
- Foundation 56 §5.0: opaque non-empty strings; `L28`+40-hex not elevated to
  Protocol grammar.
- Offline modules define optional form
  `ADDRESS_RE = ^L28[0-9a-f]{40}$`
  (`peer_handshake_identity_binding.py`, `creator_wallet_*.py`).

### 6.2 Decision (UAII v0.1)

UAII v0.1 MUST accept identities as **opaque non-empty strings** (Protocol-
compatible).

The optional `L28` + 40-lowercase-hex form is **recognized but not required**:

1. Any non-empty string identity that is not a reserved sender is acceptable.
2. If an identity matches `^L28[0-9a-f]{40}$`, a conforming reference core MAY
   label it `address_form="l28_hex40"` for metadata; acceptance MUST still be
   as an opaque identity.
3. UAII MUST NOT reject an identity solely because it is or is not in
   `l28_hex40` form.
4. UAII MUST NOT claim `l28_hex40` is Protocol consensus grammar.
5. Reserved identities `COINBASE` and `__MINT__` remain forbidden
   (`reserved_identity_forbidden`).
6. Empty / non-string identities → `address_invalid` / `identity_invalid` per
   Foundation 56 operation codes.
7. No case folding or Unicode normalization is applied to opaque identities.
   The `l28_hex40` recognition pattern requires lowercase hex as in existing
   offline `ADDRESS_RE` evidence.

**Normalization:** none beyond type/non-empty/reserved checks. Byte form for
opaque identities is the UTF-8 encoding of the exact JSON string contents.

## 7. Resolved contract 4 — UAII identifier to M2M `message_id` mapping

### 7.1 Evidence basis

M2M `message_id` (locked):

```
message_id = hex_lower(
  SHA-256(b"L28-M2M-V0.1-MESSAGE\x00" || CanonM2m(unsigned_envelope))
)
```

where `unsigned_envelope` excludes exactly `{message_id, signature}`
(`coin/m2m_verifier.py`).

UAII `quote_id` / `payment_request_id` / `receipt_id` use Foundation 56
`CanonUaii` without M2M MESSAGE domain.

Therefore UAII object ids MUST NOT be treated as M2M `message_id` values.

### 7.2 Non-collapse rule

1. A conforming adapter MUST compute M2M `message_id` only via the M2M MESSAGE
   formula.
2. An adapter MUST reject profiles that set
   `message_id == quote_id` or `message_id == payment_request_id` or
   `message_id == receipt_id` as a substitute for M2M derivation
   (`uaii_m2m_id_collision`).
3. UAII digests remain under `CanonUaii`; M2M digests remain under `CanonM2m`.

### 7.3 Correlation object (`UaiiM2mCorrelation`)

Exact fields in this order:

1. `correlation_profile` — `"l28-uaii-m2m-correlation/v0.1"`
2. `uaii_interface_profile` — `"l28-universal-ai-access-interface/v0.1"`
3. `uaii_object_kind` — one of
   `"quote"`, `"unsigned_payment_request"`, `"payment_receipt"`
4. `uaii_object_id` — 64 hex UAII object id
5. `m2m_protocol` — `"L28-M2M"`
6. `m2m_protocol_version` — `"0.1"`
7. `m2m_message_id` — 64 hex M2M `message_id` of the related signed/unsigned
   envelope being correlated (MUST match M2M derivation for that envelope)

### 7.4 Correlation id formula

```
uaii_m2m_correlation_id = hex_lower(
  SHA-256(
    b"L28-UAII-V0.1-M2M-CORRELATION\x00" || CanonUaii(UaiiM2mCorrelation)
  )
)
```

### 7.5 Mismatch / duplicate / cross-profile rejection

| Condition | Code |
|---|---|
| `m2m_message_id` does not equal recomputed M2M MESSAGE digest | `uaii_m2m_mapping_mismatch` |
| Same `uaii_object_id` correlated to two distinct `m2m_message_id` values | `uaii_m2m_mapping_conflict` |
| Same `m2m_message_id` correlated to two distinct `uaii_object_id` values | `uaii_m2m_mapping_conflict` |
| Wrong `uaii_object_kind` for object bytes | `uaii_m2m_mapping_mismatch` |
| Attempt to use UAII id as M2M `message_id` | `uaii_m2m_id_collision` |

Correlation metadata MUST NOT be treated as settlement evidence.

## 8. Resolved contract 5 — Nonce retention and replay policy

### 8.1 Evidence basis

- Foundation 56: envelope `nonce` non-empty; `payment_nonce ≠ quote_nonce`.
- M2M: nonce unique per sender within retention window; window numeric value
  undefined.
- M2M replay registry keys exchanges/message ids, not UAII envelope nonces
  (`coin/m2m_replay_registry.py`).

### 8.2 Nonce grammar

UAII envelope `nonce`, `quote_nonce`, `payment_nonce`, and `receipt_nonce`
MUST:

1. be JSON strings;
2. have UTF-8 byte length `L` where `1 <= L <= 256`;
3. contain no NUL (`U+0000`);
4. be compared using exact UTF-8 byte equality (no case folding).

Violations → `nonce_invalid`.

### 8.3 Replay-key composition

For an accepted envelope under evaluation, define `UaiiReplayKeyMaterial`
exact fields:

1. `replay_profile` — `"l28-uaii-replay/v0.1"`
2. `interface_profile` — `"l28-universal-ai-access-interface/v0.1"`
3. `operation` — envelope `operation`
4. `nonce` — envelope `nonce`

```
replay_key = hex_lower(
  SHA-256(b"L28-UAII-V0.1-REPLAY\x00" || CanonUaii(UaiiReplayKeyMaterial))
)
```

Scope: uniqueness of `replay_key` within the retention window for the
reference-core replay store.

Quote/payment object nonces (`quote_nonce`, `payment_nonce`) remain bound by
Foundation 56 inequality rules and are **additional** to envelope replay keys.
A future implementation foundation MAY also record object-nonce keys using the
same domain with `operation` set to
`"object:quote_nonce"` / `"object:payment_nonce"` and `nonce` set to that
object nonce; v0.1 reference-core conformance requires at least envelope
`replay_key` enforcement.

### 8.4 Retention window

For a request with envelope `expires_at`:

```
retention_deadline = expires_at + UAII_CLOCK_SKEW_TOLERANCE_SECONDS
```

A recorded `replay_key` MUST be retained until `T_eval > retention_deadline`,
after which it MAY be evicted.

This connects retention to quote/payment envelopes because those operations
require `payment_expires_at` / `quote_expires_at` ≤ envelope `expires_at`
(Foundation 56).

### 8.5 Replay behaviors

| Condition | Code / behavior |
|---|---|
| Replay store unavailable when check required | `replay_state_unavailable` (fail closed) |
| `replay_key` present and `T_eval <= retention_deadline` | `nonce_replay` (reject) |
| `replay_key` absent | allow time/schema success path to continue |
| `replay_key` past `retention_deadline` | treat as evicted (absent) |
| Validation-only path | MUST NOT mutate ledger; MUST set `ledger_mutated=false` |

**Recording** a nonce into a durable replay store is **not** authorized by this
specification. Checking against an available store is part of reference-core
evaluation; creating/updating store entries requires a later implementation
foundation authorization.

## 9. Reference-core processing model (non-implementing)

A conforming future UAII reference-core evaluator MUST apply this deterministic
sequence (first failure wins; aligns with Foundation 56 §8.2 and operation
lists):

1. Parse and size validation (`16384`, UTF-8, JSON, duplicate keys)
2. Secret-material rejection
3. Profile and operation validation
4. Schema and ordered-field validation (envelope + params)
5. Canonicalization (`CanonUaii` for UAII objects)
6. Identifier derivation (`report_id`, `quote_id`, … as Foundation 56)
7. Ledger-state binding (`ledger_state_id` when balance/state required) (§4)
8. Time and expiration checks (§5)
9. Nonce/replay checks (§8)
10. Protocol validation delegation (`validate_transaction` when required)
11. Stable result construction (`execution_authorized=false`,
    `spend_authorized=false` where applicable, `ledger_mutated=false` on
    validate paths)

## 10. Additional stable codes (reference-core)

These codes extend Foundation 56 for reference-core failures only:

| Code | Meaning |
|---|---|
| `request_not_yet_valid` | `created_at` beyond future skew bound |
| `replay_state_unavailable` | Required replay store missing |
| `nonce_replay` | Duplicate envelope replay key within retention |
| `uaii_m2m_id_collision` | UAII id misused as M2M `message_id` |
| `uaii_m2m_mapping_mismatch` | Correlation fields disagree with digests/kinds |
| `uaii_m2m_mapping_conflict` | One-to-many correlation conflict |

Existing Foundation 56 codes remain authoritative where applicable
(`ledger_state_unavailable`, `request_expired`, `nonce_invalid`, …).

## 11. Conformance obligations (future implementation foundations)

Future tests MUST prove at least:

1. Golden vectors for `ledger_state_id`, `replay_key`, and
   `uaii_m2m_correlation_id`
2. `ledger_state_id` determinism for fixed authoritative snapshots (height,
   supply, readiness, accepted-tx cardinality, protected supply reports)
3. Empty/unready/unavailable/inconsistent ledger → `ledger_state_unavailable`
4. Timestamp boundary and skew behavior (`300` seconds; envelope/quote bounds)
5. Address acceptance: opaque strings; `l28_hex40` optional recognition;
   reserved rejection
6. UAII↔M2M mapping non-collapse and mismatch/conflict codes
7. Replay-key determinism
8. Duplicate nonce → `nonce_replay`
9. Retention-boundary eviction behavior
10. Missing replay store → `replay_state_unavailable`
11. Cross-object quote/payment/receipt bindings (Foundation 56)
12. Stable validation precedence (Foundation 56 + §§5/8/9 here)
13. Adapter equivalence under identical canonical request bytes
14. Protected economics and historical-evidence preservation
15. Secret-material rejection

## 12. Preservation and non-effects

This foundation MUST NOT modify:

- `PROTOCOL.md` or Protocol v1.0.0 economic constants
- `coin/tx_validation.py`, `coin/ledger.py`, `coin/l28_coin.py`,
  `coin/__init__.py`
- Foundation 56 document text
- Foundation 55 lifecycle artifacts
- M2M normative docs (except by later explicit authorization)
- Historical continuity manifests/archives

Foundation 56 preserved locks remain in force:

- Profile `l28-universal-ai-access-interface/v0.1`
- Max request size `16384`
- Exactly seven operations and seven operation-local precedence contracts
- UAII exact-order JSON and M2M Canonical JSON v0.1 dual scoping

## 13. Decision evidence summary

| Decision | Locked value / rule | Evidence class |
|---|---|---|
| Ledger state domain | `L28-UAII-V0.1-LEDGER-STATE\x00` | New UAII domain (F56 §13.1 had none) |
| Ledger-state evidence fields | Protocol version, protected supply reports, `canonical_height`, `issued_supply`, `canonical_issuance_ready`, `accepted_tx_count` | `PROTOCOL.md`, `ledger.py`, `tx_validation.py` |
| Protocol tip binding | Deferred; no tip in `ledger_state_id` preimage | No tip field/selector in Protocol/`ledger.py`/`tx_validation.py`; `_seen_tx_ids` unordered |
| Height/supply/ready/count fields | From Protocol/ledger lookups; count = cardinality only | `PROTOCOL.md`, `ledger.py`, `tx_validation.py` |
| Skew constant | `300` seconds | New UAII lock; M2M/Protocol publish none |
| Envelope expiry compare | `T_eval > expires_at + 300` | Aligns M2M “greater than” + skew |
| Quote/payment expiry | Inclusive `T_eval >= …` | Foundation 56 |
| Address | Opaque required; `L28`+40hex optional recognize-only | Protocol opaque; offline `ADDRESS_RE` |
| M2M mapping | Correlation id; forbid id collapse | `m2m_verifier` MESSAGE formula |
| Replay retention | `expires_at + 300` | Connects to F56 envelope expiry + skew |
| Escrow/refund/multi-party | Still out of scope | Foundation 56 §13.6 |

## 14. Non-authorization statement

Publication of this specification is not permission to spend L28, operate a
network, activate wallets or miners, deploy adapters, record production replay
databases, or claim autonomous AI spending. Foundation 56 and earlier contracts
remain in force.

---

**End of Foundation 57 UAII Reference Core Contract Specification v0.1**
