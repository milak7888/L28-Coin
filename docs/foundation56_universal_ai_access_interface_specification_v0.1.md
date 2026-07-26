# Foundation 56 Universal AI Access Interface Specification v0.1

**Status:** Specification only (documentation; non-activation)

**Profile / `interface_profile`:** `l28-universal-ai-access-interface/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Base commit:** `b88519c6a2cc22ee734fc01c285230e278fc6852`

**Branch:** `foundation56-universal-ai-access-interface-specification`

**Normative subordination:** This document is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md). On conflict, Protocol v1.0.0 prevails.
This interface is also subordinate to existing L28 M2M Protocol v0.1
coordination rules for quote/payment/receipt semantics and MUST NOT redefine
settlement, issuance, or transfer validity.

**Related locked contracts (consumed, not replaced):**

- `PROTOCOL.md` — settlement and issuance authority
- `coin/tx_validation.py` — sole L28 transfer/coinbase validation authority
  (`validate_transaction`, `compute_tx_id`, protected economic constants)
- `docs/m2m/protocol_v0.1.md`, `docs/m2m/message_schema_v0.1.md`,
  `docs/m2m/interoperability_profile_v0.1.md` — M2M coordination semantics
- Foundation 55 and earlier disposable/offline foundations — envelope hygiene
  patterns (`ok` / `code` / `detail` / `report_id` / `execution_authorized=false`)

## 1. Purpose, status, terminology, and non-goals

### 1.1 Purpose

Foundation 56 defines one **transport-neutral canonical JSON interface** that
AI agents can discover and invoke before MCP, REST/OpenAPI, Python SDK, or
TypeScript SDK adapters exist.

This specification locks:

1. a single request/response envelope;
2. seven canonical operations;
3. economic and security boundaries;
4. discovery metadata for future adapters;
5. the first non-executing agent-to-agent product flow;
6. future conformance obligations.

It does **not** implement any adapter, signer, network endpoint, ledger
mutation path, or runtime activation.

### 1.2 Normative language

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted
as described in RFC 2119 and RFC 8174 when, and only when, they appear in
uppercase as shown here.

### 1.3 Terminology

| Term | Meaning |
|---|---|
| UAII | Universal AI Access Interface defined by this profile |
| Interface request | Top-level JSON object invoking exactly one operation |
| Interface response | Top-level JSON object returning success or failure |
| Adapter | Future MCP / REST / SDK binding that maps to this canonical JSON |
| Settlement authority | L28 Protocol v1.0.0 + `validate_transaction` only |
| Coordination layer | L28 M2M Protocol v0.1 evidence classes and message semantics |
| Unsigned payment request | UAII object that proposes a payment; NEVER authorizes spending |
| External signing/settlement | Later-milestone actions outside this profile’s executable scope |

### 1.4 Non-goals

This specification MUST NOT:

- implement MCP, REST/OpenAPI, Python SDK, or TypeScript SDK adapters;
- implement a signer, keystore, wallet, or broadcast path;
- create a second ledger, consensus height source, or validation authority;
- redefine `validate_transaction` or Protocol economic constants;
- activate networking, peer discovery transport, mining, or public endpoints;
- introduce Leap28 / Nova / SovereignBrain dependencies;
- claim autonomous spending capability.

### 1.5 Non-authority statement

Successful UAII evaluation is **interface evidence** only. It is not permission
to spend L28, admit peers, spawn processes, mine, mutate supply, broadcast
transactions, or start a node, network, miner, wallet, or testnet.

Every conforming response MUST set `execution_authorized=false`.

## 2. Frozen dependency and authority chain

| Layer | Authority |
|---|---|
| Issuance, transfer validity, hard cap, emission, fail-closed ledger rules | L28 Protocol v1.0.0 / `coin/tx_validation.py` |
| M2M coordination message semantics (request/quote/auth/settle/receipt) | L28 M2M Protocol v0.1 |
| M2M canonical JSON + digests for M2M artifacts | L28-M2M Canonical JSON v0.1 |
| UAII transport-neutral operation surface | This Foundation 56 profile |
| Future adapters | Must map 1:1 to this profile; MUST NOT override validation or economics |

**Sole settlement validation authority:** `validate_transaction` in
`coin/tx_validation.py`. UAII `validate_payment` MAY compose structural checks
and MAY invoke or cite that authority; it MUST NOT invent alternate amount,
balance, reserved-sender, or coinbase rules.

## 3. Interface foundation

### 3.1 Profile and version

| Constant | Value |
|---|---|
| `interface_profile` | `l28-universal-ai-access-interface/v0.1` |
| `protocol_version` (reported) | `1.0.0` (L28 Protocol) |
| `m2m_protocol` (reported) | `L28-M2M` |
| `m2m_protocol_version` (reported) | `0.1` |
| `currency` | `L28` |
| Maximum encoded request size | `16384` UTF-8 bytes |
| Integer safe range (JSON amounts/timestamps) | `-9007199254740991` … `9007199254740991` |
| Transfer amount bounds (when citing L28 transfers) | `TxPolicy.min_tx_amount=1` … `TxPolicy.max_tx_amount=10_000_000_000` |

### 3.2 Canonical UTF-8 JSON rules (UAII objects)

For all UAII request and response objects defined in this profile:

1. Encoding MUST be UTF-8 without BOM.
2. Top-level value MUST be a JSON object.
3. Duplicate object keys MUST be rejected (`duplicate_key`).
4. Floats, `NaN`, and `Infinity` MUST be rejected (`json_invalid`).
5. Property names MUST match `^[a-z][a-z0-9_]*$`.
6. Unknown fields MUST be rejected (`schema_invalid`).
7. Field order MUST match the exact order declared for that object
   (`schema_invalid` on reorder).
8. Amounts, timestamps, heights, nonces used as protocol integers MUST be exact
   JSON integers (not bool, string, float, or null).
9. Canonical serialization for content-derived identifiers MUST use:
   - exact declared field order;
   - `sort_keys=false`;
   - compact separators `(",", ":")`;
   - `ensure_ascii=false`;
   - `allow_nan=false`;
   - UTF-8 bytes;
   - SHA-256 digest as lowercase hex.

**M2M artifact rule:** When a UAII object embeds or cites an M2M message, that
M2M message’s digests and signatures remain under
**L28-M2M Canonical JSON v0.1** and its domain prefixes. UAII MUST NOT invent a
third canonicalization for M2M envelopes.

### 3.3 Common request envelope

Exact fields in this order:

1. `interface_profile` — string; MUST equal this profile
2. `operation` — string; MUST be one of §4 operations
3. `request_id` — string; 64 lowercase hex client correlation id
4. `created_at` — integer Unix seconds `>= 0`
5. `expires_at` — integer Unix seconds; MUST be `> created_at`
6. `nonce` — string; non-empty anti-replay token for the caller within retention
7. `execution_authorized` — boolean; MUST be `false`
8. `params` — object; operation-specific params (§5)

Maximum encoded size: `16384` bytes.

### 3.4 Common response envelope

Exact fields in this order:

1. `ok` — boolean
2. `code` — string; stable code from §8
3. `interface_profile` — string; see recovery rules
4. `operation` — string; echoed when known; else empty
5. `request_id` — string; echoed when typed; else empty
6. `result` — object; operation result on success; empty object on failure
7. `execution_authorized` — boolean; MUST be `false` on every path
8. `report_id` — string; content-derived 64 hex on success; empty on failure
9. `detail` — string; MUST be empty on every success and every failure in v0.1

`interface_profile` recovery:

1. Success: exact profile string.
2. `interface_profile_unsupported`: echo recovered string when typed.
3. Later failure after conforming profile accepted: exact profile string.
4. Before typed profile available: empty string.

Success `report_id` MUST be the lowercase hex SHA-256 digest of the canonical
serialization of the accepted request envelope (§3.2 / §3.3).

### 3.5 Adapter-neutral semantics

1. MCP, REST/OpenAPI, Python SDK, and TypeScript SDK adapters MUST map to the
   same UAII request/response JSON objects.
2. Adapters MAY change transport framing only (HTTP headers, MCP tool names,
   SDK method names).
3. Adapters MUST NOT alter field order semantics, validation precedence,
   economic bounds, or authority flags.
4. Two conforming adapters given the same canonical request bytes MUST produce
   the same `code`, the same success `report_id`, and equivalent `result`
   objects under this profile.

### 3.6 Fail-closed unknown handling

| Condition | Code |
|---|---|
| Unknown/reordered/extra fields | `schema_invalid` |
| Unsupported `interface_profile` | `interface_profile_unsupported` |
| Unknown `operation` | `operation_unsupported` |
| Future adapter claiming override of Protocol validation | Forbidden; implementations MUST reject (`adapter_override_forbidden`) |

## 4. Canonical operations

Exactly these operations are defined in v0.1:

| `operation` | Purpose | Mutates ledger? |
|---|---|---|
| `discover_capabilities` | Return interface/capability metadata | No |
| `get_protocol_status` | Return frozen protocol/status constants | No |
| `get_balance` | Return authoritative local balance binding | No |
| `create_quote` | Build a canonical unsigned quote object | No |
| `create_unsigned_payment_request` | Build an unsigned payment proposal | No |
| `validate_payment` | Validate a proposed payment without mutation | No |
| `get_payment_receipt` | Return/bind a payment+service receipt object | No |

Unknown operations → `operation_unsupported`.

## 5. Exact operation contracts

### 5.0 Shared params rules

Unless stated otherwise:

- Addresses / identities are **opaque non-empty strings** under Protocol v1.0.0.
  The optional `L28`+40-hex binding used in some offline foundations is **not**
  elevated to Protocol consensus grammar by this profile.
- Identities MUST NOT equal reserved senders `COINBASE` or `__MINT__`
  (`reserved_identity_forbidden`).
- Amounts MUST be exact integers, `> 0` where required, and within transfer
  policy bounds when representing an L28 transfer amount.
- `currency` MUST equal `"L28"` when present.
- Secret-bearing keys listed in §6.5 MUST never appear at any nesting depth
  (`secret_material_forbidden`).

#### 5.0.1 Reusable params-object schema check

When an operation-local precedence list includes the step **params-object schema
(§5.0.1)**, that step means exactly all of the following as one atomic
first-failure unit (still reported as `schema_invalid` on defect):

1. `params` is a JSON object;
2. `params` field names and order match that operation’s Params list exactly;
3. no unknown `params` fields;
4. each declared `params` field has the declared JSON type.

This reusable definition does **not** replace operation-local lists. Every
operation in §5.1–§5.7 MUST still state its complete numbered precedence,
including this step where applicable. Code tables are not precedence.

### 5.1 `discover_capabilities`

#### Params (exact order)

1. `include_adapter_declarations` — boolean; MUST be present

#### Success `result` (exact order)

1. `interface_profile` — this profile
2. `protocol_version` — `"1.0.0"`
3. `m2m_protocol` — `"L28-M2M"`
4. `m2m_protocol_version` — `"0.1"`
5. `currency` — `"L28"`
6. `operations` — array of the seven operation name strings in §4 order
7. `capabilities` — array of capability objects (§7.1) in stable ascending
   `capability_id` order
8. `adapter_declarations` — array of adapter declaration objects (§7.2); empty
   array when `include_adapter_declarations` is `false`
9. `execution_authorized` — `false`
10. `signing_supported` — `false`
11. `broadcast_supported` — `false`
12. `autonomous_spend_supported` — `false`

#### Validation precedence (operation-local, after §8.2 steps 1–10)

1. params-object schema (§5.0.1)
2. `include_adapter_declarations` is boolean (`schema_invalid` if not)
3. Success → `capabilities_ok`

#### Codes

| Code | When |
|---|---|
| `capabilities_ok` | Success |
| Shared parse/schema/authority codes (§8) | As applicable |

### 5.2 `get_protocol_status`

#### Params

Empty object `{}` (no fields).

#### Success `result` (exact order)

1. `protocol_version` — `"1.0.0"`
2. `protocol_status` — `"FROZEN"`
3. `max_supply` — `28000000`
4. `emission_ceiling` — `11130000`
5. `historical_mined` — `2824584`
6. `halving_interval` — `210000`
7. `max_coinbase_reward` — `28`
8. `reward_schedule` — `[28, 14, 7, 3, 1]`
9. `currency` — `"L28"`
10. `architecture` — `"blockless_ledger"`
11. `validation_authority` — `"coin.tx_validation.validate_transaction"`
12. `execution_authorized` — `false`

These values are **reports of frozen Protocol facts**, not mutable parameters.

#### Validation precedence (operation-local, after §8.2 steps 1–10)

1. params-object schema (§5.0.1) for the empty object (zero fields; any field →
   `schema_invalid`)
2. Success → `protocol_status_ok`

#### Codes

| Code | When |
|---|---|
| `protocol_status_ok` | Success |

### 5.3 `get_balance`

#### Params (exact order)

1. `address` — string; non-empty opaque identity
2. `require_canonical_height` — boolean

#### Success `result` (exact order)

1. `address` — echoed
2. `balance` — integer `>= 0` from authoritative local ledger lookup
3. `currency` — `"L28"`
4. `canonical_height` — integer `>= 0` when available and required/returned
5. `ledger_state_id` — 64 lowercase hex binding of the consulted ledger snapshot
   identity (implementation-defined derivation MUST be deterministic for a
   given trusted snapshot; MUST NOT be a guess when state is unavailable)
6. `execution_authorized` — `false`

#### Validation precedence (operation-local, after §8.2 steps 1–10)

1. params-object schema (§5.0.1)
2. `address` is non-empty string (`address_invalid`)
3. `address` is not a reserved identity (`reserved_identity_forbidden`)
4. `require_canonical_height` is boolean (`schema_invalid` if not)
5. Authoritative ledger/consensus state is available
   (`ledger_state_unavailable`)
6. If `require_canonical_height` is `true`: canonical height is available
   (`canonical_height_unavailable`)
7. Success → `ok=true` with §5.3 success `result` fields populated

Balance results MUST bind authoritative ledger state. Implementations MUST NOT
fabricate balances from environment variables, caches without snapshot identity,
or adapter-local guesses.

#### Rejection / fail-closed

| Condition | Code |
|---|---|
| Empty/non-string address | `address_invalid` |
| Reserved identity | `reserved_identity_forbidden` |
| Ledger/consensus state unavailable | `ledger_state_unavailable` |
| `require_canonical_height=true` but height unavailable | `canonical_height_unavailable` |

### 5.4 `create_quote`

Builds a **UAII quote object** aligning with M2M `service_quote` semantics for
later mapping. v0.1 returns an **unsigned** quote object. Attaching an M2M or
other signature is an external/later-milestone act and is NOT performed here.

#### Params (exact order)

1. `payer_identity` — string; opaque non-empty; not reserved
2. `payee_identity` — string; opaque non-empty; not reserved; MUST ≠ payer
3. `service_id` — string; non-empty
4. `service_params` — object; MAY be empty; MUST NOT contain secrets
5. `amount` — integer; `> 0`; `<= max_tx_amount`
6. `currency` — string; `"L28"`
7. `purpose` — string; non-empty purpose label
8. `quote_expires_at` — integer; MUST be `> created_at` (envelope) and
   `<= expires_at` (envelope)
9. `quote_nonce` — string; non-empty; distinct anti-replay for this quote
10. `max_amount` — integer; `> 0`; MUST be `>= amount`
11. `rejectable` — boolean; MUST be `true` in v0.1
12. `service_terms` — object; MUST be present (MAY be empty object)

#### Success `result` (exact order)

1. `quote` — `UaiiQuote` object (§5.4.1)
2. `quote_id` — 64 hex; SHA-256 of canonical serialization of `quote`
3. `execution_authorized` — `false`
4. `spend_authorized` — `false`

#### 5.4.1 `UaiiQuote` fields (exact order)

1. `quote_profile` — `"l28-uaii-quote/v0.1"`
2. `payer_identity`
3. `payee_identity`
4. `service_id`
5. `service_params`
6. `amount`
7. `currency`
8. `purpose`
9. `quote_expires_at`
10. `quote_nonce`
11. `max_amount`
12. `rejectable`
13. `service_terms`
14. `service_terms_hash` — 64 hex SHA-256 of canonical `service_terms`
15. `spend_authorized` — `false`
16. `execution_authorized` — `false`

**Binding rule:** A conforming quote MUST bind payer, recipient, asset
(`currency=L28`), amount, purpose, service (`service_id` + terms hash),
expiration, and nonce as above.

**M2M mapping (normative for adapters):** Future adapters that emit M2M
`service_quote` messages MUST preserve `service_id`, integer `amount`,
`currency`, `quote_expires_at`, `rejectable=true`, and terms digest equality.
UAII `quote_id` is not an M2M `message_id`; adapters MUST document the mapping
without collapsing evidence classes.

#### Validation precedence (operation-local, after §8.2 steps 1–10)

1. params-object schema (§5.0.1)
2. `payer_identity` non-empty string (`identity_invalid`)
3. `payer_identity` not reserved (`reserved_identity_forbidden`)
4. `payee_identity` non-empty string (`identity_invalid`)
5. `payee_identity` not reserved (`reserved_identity_forbidden`)
6. `payer_identity` ≠ `payee_identity` (`quote_party_invalid`)
7. `service_id` non-empty string (`service_id_invalid`)
8. `service_params` is object (`schema_invalid`)
9. `amount` exact integer, `> 0`, `<= max_tx_amount` (`amount_invalid`)
10. `currency` equals `"L28"` (`currency_invalid`)
11. `purpose` non-empty string (`schema_invalid`)
12. `quote_expires_at` integer bounds vs envelope `created_at`/`expires_at`
    (`quote_expiration_invalid`)
13. `quote_nonce` non-empty string (`nonce_invalid`)
14. `max_amount` exact integer, `> 0`, and `>= amount` (`amount_invalid`)
15. `rejectable` is boolean `true` (`rejectable_invalid`)
16. `service_terms` is object (`schema_invalid`)
17. Success → `quote_created`

#### Codes

| Code | When |
|---|---|
| `quote_created` | Success |
| `amount_invalid` | Non-int / ≤0 / out of bounds / `amount > max_amount` |
| `currency_invalid` | Not `"L28"` |
| `identity_invalid` | Empty/non-string identity |
| `reserved_identity_forbidden` | Reserved sender identity |
| `quote_party_invalid` | Payer equals payee |
| `quote_expiration_invalid` | Expiration bounds violated |
| `service_id_invalid` | Empty/non-string |
| `rejectable_invalid` | Not boolean `true` |

### 5.5 `create_unsigned_payment_request`

Creates an **unsigned payment request**. This object NEVER authorizes spending,
signing, or broadcast.

#### Params (exact order)

1. `quote` — exactly the `UaiiQuote` object defined in §5.4.1 (no alternate
   shapes, flattened equivalents, aliases, or adapter-specific substitutions)
2. `quote_id` — 64 hex; MUST equal digest of provided `quote`
3. `payer_identity` — string; MUST equal quote payer
4. `payee_identity` — string; MUST equal quote payee
5. `amount` — integer; MUST equal quote amount
6. `currency` — `"L28"`
7. `purpose` — string; MUST equal quote purpose
8. `service_id` — string; MUST equal quote service_id
9. `payment_nonce` — string; non-empty; MUST NOT equal `quote_nonce`
10. `payment_expires_at` — integer; MUST be `> created_at`,
    `<= expires_at`, and `<= quote_expires_at`

#### Success `result` (exact order)

1. `unsigned_payment_request` — `UaiiUnsignedPaymentRequest` (§5.5.1)
2. `payment_request_id` — 64 hex digest of that object
3. `execution_authorized` — `false`
4. `spend_authorized` — `false`

#### 5.5.1 `UaiiUnsignedPaymentRequest` fields (exact order)

1. `payment_request_profile` — `"l28-uaii-unsigned-payment-request/v0.1"`
2. `quote_id`
3. `payer_identity`
4. `payee_identity`
5. `amount`
6. `currency`
7. `purpose`
8. `service_id`
9. `service_terms_hash` — MUST equal quote `service_terms_hash`
10. `payment_nonce`
11. `payment_expires_at`
12. `quote_expires_at` — echoed from quote
13. `quote_nonce` — echoed from quote
14. `spend_authorized` — `false`
15. `execution_authorized` — `false`

#### Validation precedence (operation-local, after §8.2 steps 1–10)

1. params-object schema (§5.0.1)
2. `quote` is exactly a §5.4.1 `UaiiQuote` object (exact fields/order/types;
   `schema_invalid` on any alternate shape)
3. `quote_id` is 64 lowercase hex and equals the digest of `quote`
   (`quote_binding_invalid`)
4. `payer_identity` equals quote payer (`quote_binding_invalid`)
5. `payee_identity` equals quote payee (`quote_binding_invalid`)
6. `amount` equals quote amount (`quote_binding_invalid`)
7. `currency` equals `"L28"` and equals quote currency (`currency_invalid` /
   `quote_binding_invalid`)
8. `purpose` equals quote purpose (`quote_binding_invalid`)
9. `service_id` equals quote service_id (`quote_binding_invalid`)
10. Envelope evaluation time has not reached `quote_expires_at` (`quote_expired`)
11. `payment_nonce` non-empty string (`nonce_invalid`)
12. `payment_nonce` ≠ quote `quote_nonce` (`nonce_reuse_invalid`)
13. `payment_expires_at` integer bounds vs envelope and quote expiration
    (`payment_expiration_invalid`)
14. Success → `unsigned_payment_request_created`

#### Codes

| Code | When |
|---|---|
| `unsigned_payment_request_created` | Success |
| `quote_binding_invalid` | Any cross-field inequality vs quote / quote_id |
| `quote_expired` | `created_at >= quote_expires_at` at evaluation |
| `payment_expiration_invalid` | Expiration bounds violated |
| `nonce_reuse_invalid` | `payment_nonce == quote_nonce` |
| Plus shared amount/identity/currency codes | As applicable |

### 5.6 `validate_payment`

Validates a proposed payment **without mutating ledger state**.

May validate:

1. UAII unsigned payment request + quote bindings;
2. optional proposed L28 transfer fields for structural/`validate_transaction`
   compatibility checks when supplied.

MUST NOT add transactions to the ledger.

#### Params (exact order)

1. `quote` — exactly the `UaiiQuote` object defined in §5.4.1
2. `quote_id` — 64 hex
3. `unsigned_payment_request` — `UaiiUnsignedPaymentRequest`
4. `payment_request_id` — 64 hex
5. `proposed_transfer` — object; MAY be empty object if only UAII binding checks
   are requested
6. `check_ledger_balance` — boolean

`proposed_transfer` when non-empty MUST use exact fields in this order:

1. `sender` — string
2. `receiver` — string
3. `amount` — integer
4. `timestamp` — integer
5. `nonce` — integer
6. Optional additional Protocol-legal transfer fields are **not** permitted in
   v0.1 beyond these five; unknown fields → `schema_invalid`

#### Success `result` (exact order)

1. `payment_valid` — boolean `true`
2. `quote_id`
3. `payment_request_id`
4. `payer_identity`
5. `payee_identity`
6. `amount`
7. `currency`
8. `validate_transaction_invoked` — boolean
9. `validate_transaction_ok` — boolean; `false` when not invoked
10. `proposed_tx_id` — 64 hex when transfer validated; else empty
11. `ledger_mutated` — `false`
12. `execution_authorized` — `false`
13. `spend_authorized` — `false`

#### Validation precedence (operation-local, after §8.2 steps 1–10)

1. params-object schema (§5.0.1)
2. `quote` is exactly a §5.4.1 `UaiiQuote` object (`schema_invalid`)
3. `quote_id` is 64 lowercase hex and equals the digest of `quote`
   (`quote_binding_invalid`)
4. `unsigned_payment_request` is exactly a §5.5.1 object (`schema_invalid`)
5. `payment_request_id` is 64 lowercase hex and equals the digest of
   `unsigned_payment_request` (`payment_binding_invalid`)
6. Cross-object binds: payer, payee, amount, currency, purpose, service_id,
   service_terms_hash, quote_id, and echoed quote expiration/nonce fields
   (`quote_binding_invalid` / `payment_binding_invalid`)
7. Quote expiration vs evaluation time (`quote_expired`)
8. Payment expiration vs evaluation time (`payment_expired`)
9. Payment nonce non-empty and ≠ quote nonce (`nonce_invalid` /
   `nonce_reuse_invalid`)
10. If `proposed_transfer` is non-empty: exact five-field schema; then
    sender/receiver/amount bind to payer/payee/amount; then invoke
    `validate_transaction` rules without ledger append
    (`schema_invalid` / `payment_binding_invalid` /
    `payment_validation_failed`)
11. If `check_ledger_balance` is `true`: authoritative balance ≥ amount
    (`insufficient_balance` or `ledger_state_unavailable`)
12. Success → `payment_validation_ok` with `ledger_mutated=false`

#### Codes

| Code | When |
|---|---|
| `payment_validation_ok` | Success |
| `payment_binding_invalid` | UAII payment↔quote inequality |
| `payment_expired` | Payment request expired |
| `quote_expired` | Quote expired |
| `insufficient_balance` | Balance check failed |
| `payment_validation_failed` | `validate_transaction` would reject |
| `ledger_state_unavailable` | Required ledger state missing |

### 5.7 `get_payment_receipt`

Returns a receipt binding quote, payment, service result, parties, amount, and
ledger evidence. In v0.1 this operation **constructs/verifies a receipt object
from supplied evidence**; it does not perform settlement.

#### Params (exact order)

1. `quote_id` — 64 hex
2. `payment_request_id` — 64 hex
3. `payer_identity` — string
4. `payee_identity` — string
5. `amount` — integer
6. `currency` — `"L28"`
7. `service_id` — string
8. `service_result_hash` — 64 hex
9. `l28_tx_id` — 64 hex; cited settlement record id
10. `l28_sender` — string; MUST equal payer
11. `l28_receiver` — string; MUST equal payee
12. `l28_amount` — integer; MUST equal amount
13. `l28_timestamp` — integer
14. `verification_status` — string; MUST be `"verified"` for success in v0.1
15. `completed_at` — integer
16. `receipt_nonce` — string; non-empty

#### Success `result` (exact order)

1. `receipt` — `UaiiPaymentReceipt` (§5.7.1)
2. `receipt_id` — 64 hex digest of `receipt`
3. `execution_authorized` — `false`

#### 5.7.1 `UaiiPaymentReceipt` fields (exact order)

1. `receipt_profile` — `"l28-uaii-payment-receipt/v0.1"`
2. `quote_id`
3. `payment_request_id`
4. `payer_identity`
5. `payee_identity`
6. `amount`
7. `currency`
8. `service_id`
9. `service_result_hash`
10. `l28_tx_id`
11. `l28_sender`
12. `l28_receiver`
13. `l28_amount`
14. `l28_timestamp`
15. `verification_status`
16. `completed_at`
17. `receipt_nonce`
18. `completion_assertion` — `"provider_asserted_complete"`
19. `execution_authorized` — `false`

**Normative clarifications:**

- Receipt is provider/service completion + settlement citation binding, not
  objective proof of service correctness (same evidence-class distinction as
  M2M `service_receipt`).
- `verification_status` alone is insufficient for adapters; independent L28
  re-verification remains required before treating settlement as accepted.
- This operation MUST NOT mutate ledger state.

#### Validation precedence (operation-local, after §8.2 steps 1–10)

1. params-object schema (§5.0.1)
2. `quote_id` is 64 lowercase hex (`schema_invalid`)
3. `payment_request_id` is 64 lowercase hex (`schema_invalid`)
4. `payer_identity` non-empty string (`identity_invalid`)
5. `payee_identity` non-empty string (`identity_invalid`)
6. `amount` exact integer `> 0` within transfer bounds (`amount_invalid`)
7. `currency` equals `"L28"` (`currency_invalid`)
8. `service_id` non-empty string (`service_id_invalid`)
9. `service_result_hash` is 64 lowercase hex (`schema_invalid`)
10. `l28_tx_id` is 64 lowercase hex (`settlement_citation_invalid`)
11. `l28_sender` equals `payer_identity` (`receipt_binding_invalid`)
12. `l28_receiver` equals `payee_identity` (`receipt_binding_invalid`)
13. `l28_amount` equals `amount` (`receipt_binding_invalid`)
14. `l28_timestamp` exact integer (`settlement_citation_invalid`)
15. `verification_status` equals `"verified"` (`verification_status_invalid`)
16. `completed_at` exact integer (`schema_invalid`)
17. `receipt_nonce` non-empty string (`nonce_invalid`)
18. Success → `payment_receipt_ok`

#### Codes

| Code | When |
|---|---|
| `payment_receipt_ok` | Success |
| `receipt_binding_invalid` | Cross-field inequalities |
| `verification_status_invalid` | Not `"verified"` |
| `settlement_citation_invalid` | Tx id/parties/amount/timestamp malformed |

## 6. Economic and security boundaries

### 6.1 Integer amounts only

All amount fields MUST be exact JSON integers. Floating-point amounts are
forbidden everywhere in this profile.

### 6.2 Quote bindings

Quotes MUST bind payer, recipient, asset (`L28`), amount, purpose, service,
expiration, and nonce (§5.4).

### 6.3 Unsigned payment requests never authorize spending

`create_unsigned_payment_request` and any UAII payment object MUST carry
`spend_authorized=false` and `execution_authorized=false`. Presence of a valid
unsigned payment request MUST NOT be treated as wallet authorization, signer
invocation, or settlement.

### 6.4 Balance and validation non-mutation

- `get_balance` is read-only and MUST bind authoritative ledger state + height
  when required.
- `validate_payment` MUST set `ledger_mutated=false` and MUST NOT call ledger
  append APIs.

### 6.5 Secret material prohibition

Reject with `secret_material_forbidden` if any of the following names appear at
any nesting depth in a request:

- `private_key`, `secret_key`, `seed`, `seed_phrase`, `mnemonic`, `password`,
  `passphrase`, `credential`, `api_key`, `authorization_bearer`,
  `signing_key`, `keystore`, `wallet_secret`
- any key equal to an environment-variable name pattern matching
  `^[A-Z][A-Z0-9_]*$` when used as a JSON object key inside `params` or nested
  objects (adapters MUST pass values, not env var names, if ever authorized by
  a later foundation)

Requests MUST NOT contain private keys, seed phrases, secrets, credentials,
signer material, or environment-variable names.

### 6.6 Forbidden activations

Implementations of this profile MUST NOT:

- sign transactions;
- broadcast transactions;
- activate wallets, miners, networking, or nodes;
- perform autonomous spending;
- perform discretionary minting or supply modification;
- load Leap28/Nova private orchestration surfaces.

### 6.7 Adapter non-override

Future adapters cannot override canonical validation or economic rules. Any
adapter flag attempting to set `execution_authorized=true`, skip
`validate_transaction`, alter `max_supply`, or widen amount bounds MUST cause
fail-closed rejection (`adapter_override_forbidden` or the matching shared
code).

### 6.8 Protected economic facts (must remain unchanged)

| Fact | Value |
|---|---|
| `L28_MAX_SUPPLY` | `28_000_000` |
| `L28_EMISSION_CEILING` | `11_130_000` |
| `L28_HISTORICAL_MINED` | `2_824_584` |
| `L28_HALVING_INTERVAL` | `210_000` |
| `L28_MAX_COINBASE_REWARD` | `28` |
| `L28_REWARD_SCHEDULE` | `(28, 14, 7, 3, 1)` then 0 |

## 7. Discovery and interoperability

### 7.1 Capability object (exact field order)

1. `capability_id` — string; stable id
2. `operation` — string; one of §4 or `"*"` for profile-wide
3. `status` — string; `"supported"` / `"deferred"` / `"forbidden"`
4. `description` — string; non-secret short text

v0.1 required capability ids (minimum set):

| `capability_id` | `status` |
|---|---|
| `uaii.discover_capabilities` | `supported` |
| `uaii.get_protocol_status` | `supported` |
| `uaii.get_balance` | `supported` |
| `uaii.create_quote` | `supported` |
| `uaii.create_unsigned_payment_request` | `supported` |
| `uaii.validate_payment` | `supported` |
| `uaii.get_payment_receipt` | `supported` |
| `uaii.signing` | `forbidden` |
| `uaii.broadcast` | `forbidden` |
| `uaii.autonomous_spend` | `forbidden` |
| `adapter.mcp` | `deferred` |
| `adapter.rest_openapi` | `deferred` |
| `adapter.python_sdk` | `deferred` |
| `adapter.typescript_sdk` | `deferred` |

This capability metadata is **not** peer/network discovery and MUST NOT enable
automatic network discovery.

### 7.2 Adapter declaration object (exact field order)

1. `adapter_id` — string (`mcp`, `rest_openapi`, `python_sdk`, `typescript_sdk`)
2. `adapter_status` — `"deferred"` in v0.1 for all four
3. `canonical_profile` — this interface profile
4. `must_preserve_field_order` — `true`
5. `must_preserve_codes` — `true`
6. `must_delegate_settlement_validation` — `true`
7. `may_override_economics` — `false`

### 7.3 Future adapter conformance requirements

Each future adapter foundation MUST prove:

1. byte-equivalent canonical request acceptance for the same logical operation;
2. identical stable `code` selection under §8 precedence;
3. identical success `report_id` for identical accepted request bytes;
4. rejection of secret material and `execution_authorized=true`;
5. no ledger mutation from UAII validation/quote/payment-request operations;
6. settlement checks delegate to `validate_transaction` / Protocol only.

## 8. Shared stable codes and validation precedence

### 8.1 Shared codes

| Code | Meaning |
|---|---|
| `input_type_invalid` | Payload type not JSON text/bytes |
| `input_too_large` | Encoded size `> 16384` |
| `encoding_invalid` | Invalid UTF-8 |
| `json_invalid` | Malformed JSON / non-finite number |
| `duplicate_key` | Duplicate JSON object key |
| `invalid_top_level` | Top-level value not an object |
| `schema_invalid` | Missing/unknown/reordered/wrong-type fields |
| `interface_profile_unsupported` | Profile mismatch |
| `operation_unsupported` | Unknown operation |
| `execution_authorized_invalid` | `execution_authorized` not boolean `false` |
| `secret_material_forbidden` | Forbidden secret/env key present |
| `adapter_override_forbidden` | Adapter attempted to override economics/validation |
| `request_expired` | Envelope `expires_at` exceeded |
| `nonce_invalid` | Empty/non-string nonce |
| `internal_error` | Sanitized unexpected failure |
| Plus per-operation success/failure codes in §5 | |

### 8.2 Shared first-failure precedence

A conforming evaluator MUST stop at the first failure:

1. Unsupported payload type
2. Size `> 16384`
3. Invalid UTF-8
4. Malformed JSON / non-finite / duplicate key / non-object top-level
5. Top-level schema/field-order/type errors (`schema_invalid`)
6. Unsupported interface profile
7. Unsupported operation
8. `execution_authorized` not `false`
9. Secret-material scan
10. Envelope freshness (`created_at`/`expires_at`/`nonce`)
11. Operation-local precedence for the selected operation: the complete numbered
    list under that operation’s **Validation precedence** subsection in
    §5.1–§5.7 (including any referenced §5.0.1 step). The evaluator MUST apply
    that full list after steps 1–10 and MUST NOT treat §5 code tables as
    precedence order.
12. Unexpected exception → `internal_error`
13. Success

Every failure path MUST return empty `report_id` and empty `detail`.

## 9. First product flow (non-executing contract)

Normative non-executing flow for Agent A (requester) and Agent B (provider):

```
1. Agent A -> discover_capabilities on Agent B
2. Agent A -> get_protocol_status (optional compatibility check)
3. Agent B -> create_quote (unsigned quote object; binds parties/amount/service)
4. Agent A -> create_unsigned_payment_request (bound to quote; spend_authorized=false)
5. Agent A -> validate_payment (no ledger mutation)
6. [EXTERNAL / LATER MILESTONE] isolated signing + L28 settlement
7. Agent A/B cite verified settlement evidence (l28_tx_id + parties + amount)
8. Agent A -> get_payment_receipt (binds quote, payment, service result, ledger evidence)
9. Agent A receives service result hash + receipt_id
```

v0.1 locks steps 1–5 and 7–9 as UAII operations. Step 6 is explicitly outside
this profile: no signer, broadcast, wallet activation, or autonomous spend is
authorized here.

Signed-quote transport (M2M signed `service_quote` envelopes) MAY wrap the
UAII quote in a later foundation; v0.1 `create_quote` itself returns unsigned
canonical quote JSON only.

## 10. Explicit exclusions

Foundation 56 MUST NOT create or authorize:

1. MCP server implementation
2. REST/OpenAPI implementation
3. Python or TypeScript SDK implementation
4. Signer or keystore
5. Transaction signing or broadcast
6. Public endpoint or testnet
7. Ledger, wallet, consensus, mining, supply, or historical-evidence changes
8. Leap28 or Nova dependencies
9. Modifications to `PROTOCOL.md`, `coin/tx_validation.py`, `coin/l28_coin.py`,
   or `coin/__init__.py`
10. Modifications to Foundation 55 lifecycle integration contracts

## 11. Future conformance obligations (Foundation 57+)

A future implementation foundation MUST provide tests proving at least:

1. Canonical serialization and exact field ordering for every request/response
2. Stable codes and shared/operation precedence
3. Amount and address/identity validation (including reserved identities)
4. Quote expiration rejection
5. Nonce and replay rejection (`payment_nonce != quote_nonce`; empty nonce)
6. Cross-object bindings (quote ↔ payment ↔ receipt ↔ proposed transfer)
7. Receipt integrity (`receipt_id` digest; party/amount/tx binds)
8. Adapter equivalence fixtures (same canonical bytes → same codes/report_id)
9. Secret-material rejection
10. Protected economic facts unchanged
11. Historical-evidence preservation (no rewrite of mined/supply snapshots)
12. `execution_authorized=false` and `spend_authorized=false` on all success paths
13. `validate_payment` never mutates ledger state
14. Temporary harness-only state for any balance tests; no production wallet use

## 12. Protected-file and protocol non-effects

Foundation 56 MUST NOT modify:

- `PROTOCOL.md` and Protocol v1.0.0 economic constants
- `coin/tx_validation.py` protected facts and `validate_transaction`
- historical continuity manifests/archives
- `coin/l28_coin.py` or `coin/__init__.py`
- Foundation 55 modules/tests/docs
- M2M normative docs except by explicit later authorized foundations

## 13. Unresolved specification decisions

The following remain explicitly unresolved and MUST NOT be silently guessed by
implementers:

1. **Trusted ledger snapshot identity algorithm** for `ledger_state_id`
   (deterministic requirement is locked; concrete preimage formula is deferred).
2. **Skew tolerance** for envelope/quote expiration evaluation (M2M allows
   receiver-configured skew; UAII v0.1 requires integer comparisons but does
   not lock a skew constant).
3. **Optional `L28`+40-hex address binding** remains non-Protocol; whether a
   later profile adds an optional strict mode is deferred.
4. **Mapping of UAII `quote_id` / `payment_request_id` to M2M `message_id`**
   values in signed envelopes is deferred to an adapter/M2M-bridge foundation.
5. **Retention window** for nonce replay databases is deferred (nonce
   non-emptiness and payment≠quote nonce are locked).
6. **Multi-party / escrow / refund** flows remain out of scope (same as M2M).

## 14. Non-authorization statement

Publication of this specification is not permission to spend L28, operate a
public network, activate wallets or miners, deploy MCP/REST endpoints, or claim
autonomous AI spending. Foundation 55 and all earlier contracts remain in force.

---

**End of Foundation 56 Universal AI Access Interface Specification v0.1**
