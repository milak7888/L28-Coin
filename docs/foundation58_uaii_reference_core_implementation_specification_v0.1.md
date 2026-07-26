# Foundation 58 UAII Reference Core Implementation Specification v0.1

**Status:** Specification only (documentation; non-activation; non-implementation)

**Profile / `implementation_spec_profile`:**
`l28-uaii-reference-core-implementation/v0.1`

**Parent UAII contract:** Foundation 56 —
`l28-universal-ai-access-interface/v0.1`
(`docs/foundation56_universal_ai_access_interface_specification_v0.1.md`)

**Parent reference-core contracts:** Foundation 57 —
`l28-uaii-reference-core-contract/v0.1`
(`docs/foundation57_uaii_reference_core_contract_specification_v0.1.md`)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Base commit:** `36f683c761d78534483f371345ccab9e9a061495`

**Branch:** `foundation58-uaii-reference-core-implementation-specification`

**Normative subordination:** On conflict, Protocol v1.0.0 prevails; then
Foundation 56; then Foundation 57; then this implementation specification.
This document MUST NOT redefine settlement, issuance, supply, consensus height
authority, tip authority, M2M `message_id` derivation, or UAII schemas.

## 1. Purpose and scope

Foundation 58 specifies how a future **deterministic, non-executing UAII
reference core** MUST be structured and behave so that future MCP,
REST/OpenAPI, Python, and TypeScript adapters can call one shared core without
changing protocol meaning.

It defines package boundaries, a transport-neutral API, a first-failure
pipeline, context interfaces, dispatch for the seven Foundation 56 operations,
error mapping, resource/safety limits (where evidenced), concurrency rules,
adapter neutrality, and a conformance plan.

It does **not** create, edit, import, scaffold, or execute implementation code,
adapters, signers, ledgers, replay stores, bridges, or runtimes.

### 1.1 Explicit exclusions

Out of scope and unresolved for later foundations:

- Core implementation modules or package scaffolds
- MCP, REST/OpenAPI, Python SDK, TypeScript SDK implementation
- Signing, keystores, wallets, custody
- Transaction broadcast or settlement execution
- Replay-state mutation or persistence
- Escrow, refund execution, multi-party settlement
- Blockchain bridges; Bitcoin, Ethereum, Monero, stablecoins, cross-chain,
  liquidity, custody, or exchange integration
- Nodes, miners, networks, testnets, deployment, services, or production
  activation
- Leap28 / Nova dependencies

### 1.2 Normative language

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted
as described in RFC 2119 / RFC 8174 when, and only when, they appear in
uppercase as shown here.

## 2. Authority and invariants

1. Foundation 56 remains the parent UAII contract (seven operations; 16384-byte
   envelope; exact-order UAII JSON; `sort_keys=false` content digests; common
   request/response envelopes).
2. Foundation 57 remains authoritative for the five resolved reference-core
   contracts: `ledger_state_id`, expiration/skew, addresses, UAII↔M2M
   correlation, and nonce/replay.
3. L28 Protocol v1.0.0 remains frozen.
4. `validate_transaction` in `coin/tx_validation.py` remains the **sole
   settlement-validation authority**.
5. The reference core MUST NOT create a second ledger, consensus mechanism,
   canonical-height source, supply authority, address authority, replay
   authority, or validation authority.
6. Every operation remains `execution_authorized=false`.
7. Unsigned payment objects remain `spend_authorized=false`.
8. Read-only validation remains `ledger_mutated=false`.
9. No operation MAY sign, broadcast, mine, settle, store secrets, mutate replay
   state, append ledger state, or change economic constants.
10. Protocol tip binding remains deferred (Foundation 57 §4.3). The core MUST
    NOT invent tip semantics, lexicographic-max tip selection, `LEDGER-TIP`
    domains, or accepted-ID-set digests.

### 2.1 Protected economic facts (unchanged)

| Fact | Value | Evidence |
|---|---|---|
| Hard cap | `28_000_000` | `PROTOCOL.md`, `coin/tx_validation.py`, F56/F57 |
| Emission ceiling | `11_130_000` | same |
| Historically mined | `2_824_584` | `tx_validation.L28_HISTORICAL_MINED` |
| Treasury locked | `500_000` | `docs/m2m/protocol_v0.1.md` §2; F57 |
| Circulating snapshot | `2_324_584` | `docs/m2m/protocol_v0.1.md` §2; F57 |

## 3. Future logical package boundary (non-creating)

A future implementation foundation MAY materialize a logical package. This
section defines responsibilities only. **No files are created by this
specification.**

Suggested logical module names (non-normative labels; actual paths deferred):

| Logical component | Responsibility |
|---|---|
| Public core entry | Single `process_uaii_request` surface (§4) |
| Envelope parser / size gate | Bytes/type/`16384`/UTF-8/JSON/duplicate-key |
| Secret-material rejector | Foundation 56 §6.5 scan at every nesting depth |
| Exact-order UAII canonicalizer | Foundation 56 §3.2 `CanonUaii` |
| Operation schema registry | Seven F56 schemas + ordered fields only |
| Identifier derivation | `report_id` / object digests per F56 |
| Ledger-state snapshot reader | Read-only F57 `UaiiLedgerStateBinding` inputs |
| Time source | UTC Unix integer seconds; F57 skew/expiry |
| Replay-state reader | Read-only F57 replay-key lookup |
| Protocol-validation delegate | `validate_transaction` semantics only |
| Stable result builder | F56 §3.4 response envelope; empty `detail` |
| Conformance-vector fixtures | Golden vectors for future tests (§12) |

### 3.1 Component contracts

For each component below: mutation policy is **read-only / non-mutating** unless
stated. Forbidden for all: signing, broadcast, wallet/network IO, filesystem
writes, dynamic imports, plugin loading, env-secret reads, ledger append, replay
recording.

#### 3.1.1 Public core entry

- **Inputs:** `request_bytes`, `context` (§4)
- **Outputs:** UAII response envelope object (§4.3)
- **Dependencies:** All subordinate components
- **Forbidden:** Alternate APIs that rename operations or bypass the pipeline
- **Failures:** Map to one stable `code` via §8; never raise secrets

#### 3.1.2 Envelope parser and byte-size gate

- **Inputs:** raw `request_bytes`
- **Outputs:** UTF-8 text → JSON value with duplicate-key detection evidence
- **Dependencies:** None (pure parse)
- **Forbidden:** Truncation, silent coercion, BOM acceptance
- **Failures:** `input_type_invalid`, `input_too_large`, `encoding_invalid`,
  `json_invalid`, `duplicate_key`, `invalid_top_level`

#### 3.1.3 Secret-material rejection

- **Inputs:** parsed JSON tree
- **Outputs:** accept / reject
- **Dependencies:** Foundation 56 §6.5 forbidden key set
- **Forbidden:** Logging secret values
- **Failures:** `secret_material_forbidden`

#### 3.1.4 Exact-order UAII canonicalizer

- **Inputs:** accepted UAII object graphs
- **Outputs:** UTF-8 canonical bytes (`sort_keys=false`, separators
  `(",", ":")`, `ensure_ascii=false`, `allow_nan=false`)
- **Dependencies:** Foundation 56 §3.2
- **Forbidden:** M2M canonicalize for UAII objects; Unicode normalization;
  float emission
- **Failures:** Treat non-canonicalizable graphs as `schema_invalid` /
  `json_invalid` only under existing codes (no new code)

#### 3.1.5 Operation schema registry

- **Inputs:** `operation` string + `params` object
- **Outputs:** schema match / ordered-field validation result
- **Dependencies:** Foundation 56 §4–§5 only
- **Forbidden:** Aliases, eighth operation, unknown fields
- **Failures:** `operation_unsupported`, `schema_invalid`, operation codes

#### 3.1.6 Identifier derivation

- **Inputs:** canonical UAII bytes for request/objects
- **Outputs:** 64 lowercase hex SHA-256 digests
- **Dependencies:** Foundation 56 identifier rules; F57 domains where cited
- **Forbidden:** Adapter-local id schemes; uppercase hex
- **Failures:** If derivation stage not reached → omit/empty per §8.2

#### 3.1.7 Ledger-state snapshot reader interface

- **Inputs:** capture-once context handle
- **Outputs:** authoritative fields for `UaiiLedgerStateBinding` (F57 §4.4)
- **Dependencies:** Existing ledger/Protocol lookups only
- **Forbidden:** Tip inference; inventing height/supply; set digests
- **Failures:** `ledger_state_unavailable` (and F56
  `canonical_height_unavailable` when that F56 condition applies)

#### 3.1.8 Time source interface

- **Inputs:** none (or frozen test injection via context)
- **Outputs:** `T_eval` as UTC Unix integer seconds
- **Dependencies:** Foundation 57 §5
- **Forbidden:** Replacing Protocol/ledger validation
- **Failures:** Malformed time types → existing F56/F57 codes

#### 3.1.9 Replay-state read interface

- **Inputs:** `replay_key` (F57 §8.3)
- **Outputs:** present / absent within retention; or unavailable
- **Dependencies:** Foundation 57 §8
- **Forbidden:** Recording, eviction APIs, cleanup, persistence writes
- **Failures:** `replay_state_unavailable`, `nonce_replay`, `nonce_invalid`

#### 3.1.10 Protocol-validation delegate interface

- **Inputs:** proposed transfer fields / Protocol-legal validation arguments
- **Outputs:** accept/reject + Protocol reason code mapping to F56
  `payment_validation_failed` / related codes
- **Dependencies:** `validate_transaction` semantics only
- **Forbidden:** Weakening, reordering, or replacing Protocol rules; ledger
  mutation
- **Failures:** Unavailable delegate → fail closed (§5.4)

#### 3.1.11 Stable result builder

- **Inputs:** pipeline outcome
- **Outputs:** Foundation 56 §3.4 response fields in exact order
- **Dependencies:** F56 recovery rules for `interface_profile` / empties
- **Forbidden:** Non-empty `detail` in v0.1; stack traces; paths; secrets;
  inventing a `get_balance` success `code` token (§8.2)
- **Failures:** Builder defects → `internal_error` only (no diagnostics or
  environment disclosure)
- **`get_balance` success:** `ok=true`, `operation="get_balance"`, §5.3
  `result` shape preserved; `code` MUST be `""` (no separate success code)

#### 3.1.12 Conformance-vector fixtures

- **Inputs:** none at runtime
- **Outputs:** future golden vectors (§12)
- **Dependencies:** This spec + F56/F57
- **Forbidden:** Executable production paths
- **Failures:** N/A (test-time only)

## 4. Public reference-core API

### 4.1 Function contract

Exactly one transport-neutral entry point:

```
process_uaii_request(request_bytes, context) -> result
```

No eighth operation and no alternate request shape are authorized.

### 4.2 `request_bytes`

| Constraint | Rule | Evidence |
|---|---|---|
| Type | UTF-8 text as `str` **or** raw `bytes` only | F56 `input_type_invalid` |
| Length | UTF-8 byte length `L` with `0 <= L <= 16384` accepted for size gate; `L > 16384` → `input_too_large` | F56 §3.1 / §8.1 |
| Encoding | UTF-8 without BOM | F56 §3.2 |
| Top-level | JSON object after parse | F56 §3.2 / `invalid_top_level` |

Empty payload is not a success path; it fails under existing parse/schema codes
after size acceptance (`L == 0` is `<= 16384` but not a valid request object).

### 4.3 `context` (capture-once)

`context` MUST be captured once per request before pipeline step 12 and MUST NOT
be refreshed mid-request. Exact logical fields:

1. `ledger_state` — authoritative ledger-state reader (§5.1); required when the
   selected operation needs balance/state/`ledger_state_id`
2. `t_eval` — evaluation time as UTC Unix integer seconds (§5.2); required for
   envelope/quote/payment time checks
3. `replay_state` — read-only replay reader (§5.3); required when envelope
   nonce/replay checks are enforced for the selected path
4. `protocol_validate` — Protocol-validation delegate (§5.4); required when
   `validate_payment` supplies a non-empty `proposed_transfer`
5. `capability_config` — optional read-only profile metadata for
   `discover_capabilities` capability lists; MUST NOT enable signing/broadcast/
   autonomous spend; MUST NOT override economics

Unavailable required context parts fail closed with the matching stable code
(`ledger_state_unavailable`, `replay_state_unavailable`, or §5.4 unavailable
mapping)—never with invented state.

### 4.4 Result envelope (Foundation 56 §3.4 order preserved)

`result` MUST be a JSON object with exactly these fields in this order:

1. `ok` — boolean
2. `code` — string; stable code from F56 §8 / §5 or F57 §10
3. `interface_profile` — string; F56 recovery rules
4. `operation` — string; echoed when known; else `""`
5. `request_id` — string; echoed when typed; else `""`
6. `result` — object; operation success object; `{}` on failure
7. `execution_authorized` — boolean; MUST be `false`
8. `report_id` — string; 64 hex on success; `""` on failure
9. `detail` — string; MUST be `""` on every path in v0.1

Additional authority echoes when present inside operation `result` objects
remain as defined by Foundation 56 (e.g. `spend_authorized=false`,
`ledger_mutated=false`, `ledger_state_id`).

MUST NOT include secrets, private keys, stack traces, filesystem paths, raw
exception text, environment details, or private diagnostics.

Successful `get_balance` is distinguished by `ok=true` together with
`operation="get_balance"` and a Foundation 56 §5.3 success `result`. It MUST
NOT introduce a separate success `code` string (§8.2).

## 5. Context interfaces (non-implementing protocols)

### 5.1 Ledger-state reader

Supplies only authoritative existing state sufficient to populate Foundation 57
`UaiiLedgerStateBinding` exact fields in order:

1. `binding_profile` = `"l28-uaii-ledger-state-binding/v0.1"`
2. `protocol_version` = `"1.0.0"`
3. `currency` = `"L28"`
4. `max_supply` = `28000000`
5. `emission_ceiling` = `11130000`
6. `historical_mined` = `2824584`
7. `canonical_height` — integer `>= 0`
8. `issued_supply` — integer `>= 0`
9. `canonical_issuance_ready` — boolean `true` at bind time
10. `accepted_tx_count` — integer `>= 0` (cardinality only)

```
ledger_state_id = hex_lower(
  SHA-256(
    b"L28-UAII-V0.1-LEDGER-STATE\x00" || CanonUaii(UaiiLedgerStateBinding)
  )
)
```

MUST NOT infer tip semantics. Missing, malformed, inconsistent, unavailable, or
issuance-unready required state → `ledger_state_unavailable`.

### 5.2 Time source

- Returns UTC Unix integer seconds.
- Preserves `UAII_CLOCK_SKEW_TOLERANCE_SECONDS = 300` (Foundation 57).
- Envelope expiry: `T_eval > expires_at + 300` → `request_expired`.
- Future skew: `created_at > T_eval + 300` → `request_not_yet_valid`.
- Quote/payment expiry remain Foundation 56 inclusive `T_eval >= …`.
- MUST NOT replace ledger or Protocol validation.

### 5.3 Replay-state reader

- Read-only lookup using Foundation 57 replay-key:

```
replay_key = hex_lower(
  SHA-256(b"L28-UAII-V0.1-REPLAY\x00" || CanonUaii(UaiiReplayKeyMaterial))
)
```

- Retention observational horizon: `expires_at + 300`.
- Missing/unavailable required store → `replay_state_unavailable`.
- Present key within retention → `nonce_replay`.
- MUST NOT record, evict, clean up, persist, or otherwise mutate replay state.
  Recording remains unauthorized (Foundation 57 §8.5).

### 5.4 Protocol-validation delegate

- MUST call existing `validate_transaction` semantics only.
- MUST NOT weaken, reinterpret, reorder, or replace Protocol results.
- MUST NOT mutate the canonical ledger during UAII read-only validation.
- If the delegate is required and unavailable/unconfigured → fail closed as
  `payment_validation_failed` when a proposed transfer is being validated
  (Foundation 56 maps Protocol rejection to that code). The core MUST NOT
  invent a new “delegate missing” code unless a later authorized foundation
  adds one; until then, unavailable required delegation is treated as
  validation failure fail-closed under `payment_validation_failed`.

## 6. Deterministic processing pipeline

### 6.1 Outer first-failure sequence

A conforming reference core MUST stop at the first failure:

1. Raw byte type and `16384`-byte size validation
2. UTF-8 decoding
3. JSON parse and duplicate-key rejection (and non-finite / non-object top-level)
4. Secret-material rejection (Foundation 56 §6.5; ordered early per Foundation 57
   §9)
5. Profile and version validation (`interface_profile`)
6. Operation validation (one of the seven names)
7. Exact ordered-field/schema validation (envelope §3.3 +
   `execution_authorized=false`)
8. Primitive-type, integer-only, and bounds validation for envelope integers /
   nonce grammar (Foundation 56 + Foundation 57 nonce UTF-8 1..256 / no NUL)
9. UAII exact-order canonicalization readiness for identifier stages
10. UAII identifier derivation points that are safe pre-operation-local (e.g.
    typed `request_id` echo; success `report_id` only after full acceptance)
11. Cross-object binding validation when the operation supplies bound objects
12. Authoritative ledger-state acquisition and binding when required
13. Time, not-yet-valid, skew, and expiration checks (Foundation 57 §5)
14. Nonce/replay read checks (Foundation 57 §8)
15. Protocol `validate_transaction` delegation where required
16. Operation-local precedence application for remaining operation-specific
    steps (Foundation 56 §5.1–§5.7)
17. Stable result construction

Unexpected exceptions after these stages → `internal_error` (Foundation 56
§8.2).

### 6.2 Reconciliation with Foundation 56 §8.2

| F56 §8.2 step | F58 outer handling |
|---|---|
| 1 Unsupported payload type | Outer 1 |
| 2 Size `> 16384` | Outer 1 |
| 3 Invalid UTF-8 | Outer 2 |
| 4 JSON / duplicate / non-object | Outer 3 |
| 5 Top-level schema/order/type | Outer 7–8 (envelope) |
| 6 Unsupported profile | Outer 5 |
| 7 Unsupported operation | Outer 6 |
| 8 `execution_authorized` not `false` | Outer 7 |
| 9 Secret-material scan | Outer 4 (earlier; Foundation 57 §9 lock for reference core) |
| 10 Envelope freshness / nonce | Outer 8 (nonce grammar) + Outer 13–14 (F57 time/replay) |
| 11 Operation-local lists | Outer 11–16 as required by each §5 list |
| 12 `internal_error` | After outer stages |
| 13 Success | Outer 17 |

**Secret-material ordering note:** Foundation 56 §8.2 lists secret scan after
profile/operation/`execution_authorized`. Foundation 57 §9 and this reference-core
implementation specification require secret rejection before profile/operation
acceptance. For the UAII reference core, Outer 4 prevails. Adapters MUST still
treat `secret_material_forbidden` as authoritative; they MUST NOT depend on
observing profile/operation echoes before secret rejection.

### 6.3 Operation-local precedence retention

After outer steps that establish a typed, schema-valid envelope and selected
operation, the core MUST apply the **complete numbered Validation precedence**
list under Foundation 56 §5.1–§5.7 for that operation, without reordering that
list’s relative checks.

Where Foundation 56 places ledger, quote/payment expiry, or
`validate_transaction` inside an operation-local list, those checks remain in
that list’s relative order. Outer steps 12–15 are the shared machinery those
local steps invoke; they MUST NOT run for operations that do not require them,
and MUST NOT be used to skip earlier local schema/binding steps.

Outer failures that occur before a safe operation-local stage (Outer 1–8 for
envelope, and Outer 4 secrets) retain precedence over all operation-local
codes.

## 7. Canonical data and identifiers

### 7.1 Preserved rules

- UAII exact-order UTF-8 JSON (Foundation 56 §3.2)
- M2M Canonical JSON v0.1 only for M2M artifacts
- Lowercase hexadecimal SHA-256 identifiers
- Foundation 57 `ledger_state_id`, UAII↔M2M correlation, and replay domains /
  formulas
- No aliases, alternate field orders, adapter substitutions, floats, implicit
  coercion, Unicode normalization, or unknown fields

### 7.2 Pseudocode (non-executable)

```
function CanonUaii(obj):
  # Foundation 56 §3.2 — exact declared field order; sort_keys=false
  return UTF8(JSON_COMPACT(obj, separators=(",", ":"),
                           ensure_ascii=false, allow_nan=false))

function hex_lower(digest_bytes):
  return lowercase_hex(digest_bytes)  # length 64 for SHA-256

function report_id(accepted_request_envelope):
  return hex_lower(SHA256(CanonUaii(accepted_request_envelope)))

function ledger_state_id(binding):  # binding = UaiiLedgerStateBinding
  return hex_lower(SHA256(b"L28-UAII-V0.1-LEDGER-STATE\x00" ||
                          CanonUaii(binding)))

function uaii_m2m_correlation_id(corr):
  return hex_lower(SHA256(b"L28-UAII-V0.1-M2M-CORRELATION\x00" ||
                          CanonUaii(corr)))

function replay_key(material):
  return hex_lower(SHA256(b"L28-UAII-V0.1-REPLAY\x00" ||
                          CanonUaii(material)))
```

M2M envelopes continue to use `coin/m2m_verifier.canonicalize` / L28-M2M
Canonical JSON v0.1 and M2M domains; UAII MUST NOT substitute `CanonUaii` for
M2M digests.

## 8. Seven-operation dispatch

Exactly seven operations (Foundation 56 §4 names verbatim):

1. `discover_capabilities`
2. `get_protocol_status`
3. `get_balance`
4. `create_quote`
5. `create_unsigned_payment_request`
6. `validate_payment`
7. `get_payment_receipt`

No aliases. Schemas and success `result` shapes remain Foundation 56 §5.

| Operation | Request schema | Success `result` | Ledger | Time | Replay read | Protocol delegate | Forbidden side effects |
|---|---|---|---|---|---|---|---|
| `discover_capabilities` | F56 §5.1 Params | F56 §5.1 | No | Envelope (outer) | Envelope (outer) | No | No signing/network |
| `get_protocol_status` | F56 §5.2 empty `{}` | F56 §5.2 | No | Envelope | Envelope | No | No mutation |
| `get_balance` | F56 §5.3 | F56 §5.3 (includes `ledger_state_id`) | Yes | Envelope | Envelope | No | No fabricated balances |
| `create_quote` | F56 §5.4 | F56 §5.4 + `UaiiQuote` | No | Envelope + quote expiry rules in §5.4 list | Envelope | No | Unsigned only |
| `create_unsigned_payment_request` | F56 §5.5 | F56 §5.5 + payment object | No | Envelope + quote/payment expiry in §5.5 list | Envelope | No | `spend_authorized=false` |
| `validate_payment` | F56 §5.6 | F56 §5.6 | If balance check | Envelope + quote/payment expiry in §5.6 list | Envelope | If `proposed_transfer` non-empty | `ledger_mutated=false` |
| `get_payment_receipt` | F56 §5.7 | F56 §5.7 + receipt | Citation only; no append | Envelope + `completed_at` rules in §5.7 list | Envelope | No settlement | No settlement execution |

Each row’s operation-local validation precedence remains the numbered list in
Foundation 56 §5.1–§5.7.

### 8.1 Permitted read-only outputs

Only Foundation 56 success `result` fields and the common response envelope.
`ledger_state_id` MUST use Foundation 57’s formula when returned.

### 8.2 Success code inventory (evidenced)

| Operation | Success `code` | Evidence |
|---|---|---|
| `discover_capabilities` | `capabilities_ok` | F56 §5.1 |
| `get_protocol_status` | `protocol_status_ok` | F56 §5.2 |
| `get_balance` | **None — formally waived** (§8.2.1) | F56 §5.3 |
| `create_quote` | `quote_created` | F56 §5.4 |
| `create_unsigned_payment_request` | `unsigned_payment_request_created` | F56 §5.5 |
| `validate_payment` | `payment_validation_ok` | F56 §5.6 |
| `get_payment_receipt` | `payment_receipt_ok` | F56 §5.7 |

#### 8.2.1 `get_balance` success treatment (formal waiver)

Foundation 56 §5.3 authoritatively defines successful `get_balance` using
`ok=true` and the exact success `result` field order, without naming a stable
success `code`. Foundation 58 MUST NOT invent a new success code (including
but not limited to `balance_ok`).

On successful `get_balance`:

1. Outer envelope `ok` MUST be `true`.
2. Outer envelope `operation` MUST be `"get_balance"`.
3. Outer envelope `code` MUST be `""` (empty string) — no success-code token.
4. Outer envelope `result` MUST match Foundation 56 §5.3 exact field order and
   semantics (including `ledger_state_id` via Foundation 57 when bound).
5. Failure paths MUST continue to use stable error codes only
   (`address_invalid`, `reserved_identity_forbidden`,
   `ledger_state_unavailable`, `canonical_height_unavailable`, shared parse /
   schema / authority codes, etc.).

Adapters MUST NOT synthesize, rename, or inject a `get_balance` success
`code`. Success identity is `ok` + `operation` + conforming §5.3 `result`.

## 9. Error and result contract

### 9.1 Reused stable codes

**Foundation 56 shared:** `input_type_invalid`, `input_too_large`,
`encoding_invalid`, `json_invalid`, `duplicate_key`, `invalid_top_level`,
`schema_invalid`, `interface_profile_unsupported`, `operation_unsupported`,
`execution_authorized_invalid`, `secret_material_forbidden`,
`adapter_override_forbidden`, `request_expired`, `nonce_invalid`,
`internal_error`, plus per-operation codes in F56 §5.

**Foundation 57 reference-core additions:** `request_not_yet_valid`,
`replay_state_unavailable`, `nonce_replay`, `uaii_m2m_id_collision`,
`uaii_m2m_mapping_mismatch`, `uaii_m2m_mapping_conflict`.

### 9.2 Pipeline → code mapping (first failure)

| Outer failure | Code |
|---|---|
| Bad payload type | `input_type_invalid` |
| `L > 16384` | `input_too_large` |
| Invalid UTF-8 | `encoding_invalid` |
| Malformed JSON / non-finite | `json_invalid` |
| Duplicate key | `duplicate_key` |
| Top-level not object | `invalid_top_level` |
| Secret key present | `secret_material_forbidden` |
| Bad profile | `interface_profile_unsupported` |
| Unknown operation | `operation_unsupported` |
| Envelope schema/order/type / `execution_authorized≠false` | `schema_invalid` / `execution_authorized_invalid` |
| Nonce grammar (F57) | `nonce_invalid` |
| Envelope time skew/expiry (F57) | `request_not_yet_valid` / `request_expired` |
| Replay store missing | `replay_state_unavailable` |
| Replay hit | `nonce_replay` |
| Ledger bind failure | `ledger_state_unavailable` |
| Operation-local failures | Exact F56 §5 codes for that operation |
| Unexpected exception | `internal_error` |

Single first-failure result only. Adapters MUST NOT substitute codes.
Adapters MUST NOT synthesize a `get_balance` success `code` (§8.2.1).

### 9.3 Identifier omission

- Before typed recovery: `operation`, `request_id`, `interface_profile` follow
  Foundation 56 empty/echo recovery rules.
- `report_id` MUST be `""` on every failure (Foundation 56 §8.2).
- Object ids (`quote_id`, etc.) appear only in success `result` shapes when
  Foundation 56 requires them; never invent ids after a failure.

### 9.4 Diagnostic prohibition

MUST NOT expose stack traces, filesystem paths, secrets, private keys, raw
validation internals, or environment details. `detail` remains `""`.

## 10. Resource and safety limits

### 10.1 Evidenced limits (locked)

| Limit | Value | Evidence |
|---|---|---|
| Maximum encoded request size | `16384` UTF-8 bytes | F56 §3.1 |
| JSON integer safe range (amounts/timestamps) | `-9007199254740991` … `9007199254740991` | F56 §3.1 |
| Transfer amount bounds when citing L28 transfers | `1` … `10_000_000_000` | F56 §3.1 / TxPolicy |
| UAII nonce UTF-8 byte length | `1` … `256`; NUL forbidden | F57 §8.2 |
| Clock skew tolerance | `300` seconds | F57 §5.3 |

### 10.2 Normative request-size-only policy (Foundation 58)

Foundation 58 adopts a **request-size-only** policy for the encoded request
envelope:

1. `request_bytes` maximum remains exactly `16384` UTF-8 bytes.
2. Foundation 58 does **not** invent numeric limits for JSON nesting depth,
   object-member count, array length, non-nonce string bytes, canonicalized
   bytes, or result bytes.
3. Those six numeric limits are **explicitly deferred** because Foundation
   56/57 and current repository behavior provide no authoritative UAII values.
4. They MUST NOT be treated as silently unlimited.
5. The `16384`-byte envelope already bounds received request allocation but
   does **not** resolve parser nesting, expansion, or result-size policy.

Parsers and evaluators MUST still reject, under existing stable codes:

- malformed input (`json_invalid`, `encoding_invalid`, …);
- duplicate keys (`duplicate_key`);
- unknown / reordered / wrong-type fields (`schema_invalid`);
- prohibited recursion / activation behavior (Foundation 56 §6.6 qualitative
  prohibitions; no invented depth number);
- any request exceeding `16384` bytes (`input_too_large`).

### 10.3 Deferred implementation prerequisites (formerly U-LIMIT-*)

The following are **formally deferred implementation prerequisites**, not
unresolved open decisions and not assigned unsupported numbers:

| Prerequisite | Topic | Status |
|---|---|---|
| Deferred-JSON-depth | Maximum JSON nesting depth | Deferred — no F56/F57/Protocol UAII value |
| Deferred-object-members | Maximum object member count | Deferred — no evidenced UAII value |
| Deferred-array-length | Maximum array length | Deferred — no evidenced UAII value |
| Deferred-string-bytes | Maximum non-nonce string byte length | Deferred — only nonce `256` and request `16384` evidenced |
| Deferred-canon-bytes | Maximum canonicalized byte length | Deferred — no evidenced UAII value |
| Deferred-result-bytes | Maximum result / diagnostic encoded size | Deferred — F56 forces `detail=""` but locks no max result size |

**Implementation authorization gate:** Every future implementation proposal
MUST, for each deferred prerequisite above:

1. define a finite numeric limit;
2. justify that value with implementation evidence;
3. test boundary-minus-one / boundary / boundary-plus-one;
4. obtain separate specification approval before implementation acceptance.

Until those finite limits receive separate specification approval, Foundation
58 authorizes **no** UAII reference-core implementation.

### 10.4 Hard safety prohibitions (qualitative; evidenced by F56 §6.6 / F57)

The core MUST NOT perform network IO, subprocess execution, filesystem writes,
dynamic import, plugin loading, code execution, or environment-secret access.
Prohibited recursion/activation behavior remains forbidden under Foundation 56
§6.6 without inventing a numeric depth constant in this foundation.

## 11. Concurrency and determinism

1. Processing is stateless and non-mutating with respect to ledger, replay
   stores, wallets, and networks.
2. Equivalent `request_bytes` plus identical captured `context` MUST produce
   byte-equivalent response envelopes (same field order and values).
3. Context is captured once per request (§4.3).
4. No global mutable state affecting validation outcomes.
5. No hidden caches that change codes, identifiers, or ordering.
6. Concurrent calls MUST NOT change ordering, identifiers, or first-failure
   results relative to their own captured contexts.
7. Replay checks remain observational only (no recording).

## 12. Adapter neutrality

MCP, REST/OpenAPI, Python SDK, and TypeScript SDK remain **future adapters
only** (Foundation 56 §7; capabilities `deferred`).

Adapters MUST:

1. pass identical request bytes (or byte-equivalent UTF-8) to
   `process_uaii_request`;
2. supply equivalent authoritative context;
3. preserve field order, codes, digests, size limit `16384`, and authority
   flags;
4. MUST NOT rename fields, coerce types, alter ordering, replace errors, derive
   different IDs, relax size limits, or add authority;
5. MUST NOT synthesize, rename, or inject a `get_balance` success `code`
   (§8.2.1).

Future adapter foundations MUST prove Foundation 56 §7.3 items 1–6 against this
core.

## 13. Conformance plan (future tests)

Future implementation foundations MUST prove at least:

1. Golden request/result vectors for all seven operations
2. Exact result-field ordering (response envelope + success `result`)
3. Maximum-size boundary: `16383`, `16384`, and `16385` bytes
4. Invalid UTF-8
5. Duplicate JSON keys
6. Unknown and reordered fields
7. Secret-material rejection
8. Integer/boolean/string confusion
9. Float and implicit-coercion rejection
10. UAII identifier determinism (`report_id` / object digests)
11. `ledger_state_id` determinism (F57 binding; no tip inference)
12. Missing/unready ledger-state → `ledger_state_unavailable`
13. No inferred tip semantics / no accepted-ID-set commitment
14. Timestamp and 300-second skew boundaries
15. Address acceptance/rejection (opaque; optional `l28_hex40` recognize-only)
16. UAII-to-M2M correlation rules (F57)
17. Replay-key and retention boundaries; duplicate nonce; unavailable replay
    state
18. Protocol-delegate unavailable/failure behavior
19. Cross-object binding
20. Stable outer and operation-local precedence
21. Byte-equivalent repeated results
22. Concurrent determinism
23. Adapter equivalence
24. Protected economics and historical-evidence preservation
25. No filesystem, network, signing, settlement, ledger, or replay mutation
26. Successful `get_balance`: `ok=true`, `operation="get_balance"`,
    `code=""`, exact Foundation 56 §5.3 `result` order; no invented success
    code; adapters do not inject a success code
27. Deferred §10.3 finite limits approved separately before implementation
    acceptance; each approved limit tested at boundary-minus-one / boundary /
    boundary-plus-one

## 14. Deferred prerequisites and implementation gate

There are **no** remaining unresolved decision IDs from the prior draft
(`U-LIMIT-JSON-DEPTH`, `U-LIMIT-OBJECT-MEMBERS`, `U-LIMIT-ARRAY-LENGTH`,
`U-LIMIT-STRING-BYTES`, `U-LIMIT-CANON-BYTES`, `U-LIMIT-RESULT-BYTES`,
`U-SUCCESS-GET-BALANCE`).

Resolved in this revision:

1. **Resource limits** — request-size-only policy (§10.2); six numeric limits
   formally deferred as implementation prerequisites (§10.3), not assigned
   unsupported numbers and not described as unlimited.
2. **`get_balance` success code** — formally waived (§8.2.1); Foundation 56
   §5.3 preserved; success via `ok` + `operation` + §5.3 `result`.

**Gate:** Foundation 58 authorizes no reference-core implementation until the
six deferred finite limits in §10.3 receive separate specification approval
with evidenced justifications and boundary tests.

## 15. Preservation and non-effects

This foundation MUST NOT modify:

- `PROTOCOL.md` or Protocol v1.0.0 economic constants
- `coin/tx_validation.py`, `coin/ledger.py`, `coin/l28_coin.py`,
  `coin/__init__.py`
- Foundation 55/56/57 document text
- M2M normative docs
- Historical continuity manifests/archives

Preserved locks remain in force:

- Profile `l28-universal-ai-access-interface/v0.1`
- Max request size `16384`
- Exactly seven UAII operations and seven operation-local precedence contracts
- Foundation 57 five resolved contracts and `UaiiLedgerStateBinding`
- No Protocol tip authority
- Dual canon: UAII exact-order JSON vs M2M Canonical JSON v0.1

## 16. Non-authorization statement

Publication of this specification is not permission to implement or activate a
UAII core, adapters, signers, wallets, miners, networks, bridges, replay
databases, or autonomous AI spending. Foundations 56 and 57 remain in force.
Per §10.3, Foundation 58 itself authorizes no reference-core implementation
until the six deferred finite parser/result limits receive separate
specification approval.

---

**End of Foundation 58 UAII Reference Core Implementation Specification v0.1**
