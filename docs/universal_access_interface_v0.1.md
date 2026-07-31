# Universal Access Interface v0.1

**Foundation:** 79 (specification-only candidate)

**Status:** Specification only (documentation; non-activation; non-implementation)

**Interface profile:** `l28-universal-ai-access-interface/v0.1`

**Document version:** `universal-access-interface/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Baseline commit:** `995a4585705e750846b5e0259c485a7d22ca05b2`

**Branch:** `foundation79-universal-access-interface-spec`

**Normative subordination:** This document is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md). On conflict, Protocol v1.0.0 prevails.
This document consolidates and extends the Universal AI Access Interface (UAII)
surface defined across Foundations 56–78 for agent-facing discovery, quote,
payment proposal, validation, receipt verification, and deferred refund
messaging. It MUST NOT redefine settlement, issuance, supply, consensus height
authority, or `validate_transaction`.

**Related locked contracts (consumed, not replaced):**

- `PROTOCOL.md` — settlement and issuance authority
- `coin/tx_validation.py` — sole transfer/coinbase validation authority
- `docs/foundation56_universal_ai_access_interface_specification_v0.1.md`
- Foundations 57–63 — UAII reference-core, limits, and processing
- Foundations 64–78 — isolated signing, signed-receipt verification, and
  inert authorization/eligibility proposal chain
- Historical evidence and protected economic constants — immutable

---

## 1. Purpose, scope, trust model, and versioning

### 1.1 Purpose

Foundation 79 defines one **canonical, transport-neutral Universal Access
Interface** so software agents can discover capabilities, inquire balances,
exchange signed quotes, propose unsigned payments, validate proposals,
exchange signed receipts, and (deferred) exchange refund messages — without
embedding private keys in prompts, APIs, logs, adapters, or hosted services.

### 1.2 Scope

**In scope (specification):**

1. One deterministic JSON request/response envelope
2. Capability discovery and protocol-status reporting
3. Balance inquiry without private-material exposure
4. Signed quotes and unsigned payment requests
5. Validation requests and deterministic validation responses
6. Signed receipts and verification composition
7. Deferred refund-request and refund-receipt message shapes
8. Replay protection, expiration, idempotency, approval thresholds, spending
   limits, and audit identifiers
9. Adapter-neutral binding rules for future REST/OpenAPI, MCP, Python SDK, and
   TypeScript SDK adapters
10. Conformance requirements and deferred implementation work

**Out of scope / non-activation:**

This specification does **not** activate settlement, wallets, mining,
networking, adapters, hosted services, or ledger mutation. It does **not**
authorize spending, broadcasting, key custody, or autonomous execution.

### 1.3 Trust model

| Party | Trust assumption |
|---|---|
| Caller / agent | Supplies public identities and public artifacts only |
| Local UAII processor | Sole protocol processor for interface evaluation |
| Isolated local signer | Sole private-key boundary for signatures (F64+) |
| `validate_transaction` | Sole L28 transfer/coinbase validator |
| Adapters | Must map 1:1 to this interface; MUST NOT override economics or validation |
| Hosted services / models | MUST NEVER receive private keys, seeds, or credentials |

Successful interface evaluation is **evidence**, not permission to spend,
settle, mine, mutate supply, or start a runtime.

### 1.4 Normative language

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted
as described in RFC 2119 and RFC 8174 when, and only when, they appear in
uppercase as shown here.

### 1.5 Versioning

| Constant | Value |
|---|---|
| `interface_profile` | `l28-universal-ai-access-interface/v0.1` |
| Document version | `universal-access-interface/v0.1` |
| Reported protocol version | `1.0.0` |
| Currency | `L28` |

Breaking changes require a new interface profile string. Additive deferred
operations MUST NOT silently become executable without a later authorized
implementation foundation.

---

## 2. Preserved Protocol and economic invariants

Every conforming implementation MUST preserve L28 Protocol v1.0.0 and these
protected facts (MUST NOT redefine or override):

| Fact | Value |
|---|---:|
| Hard cap | `28,000,000 L28` |
| Emission schedule ceiling | `11,130,000 L28` |
| Historically mined | `2,824,584 L28` |
| Treasury locked | `500,000 L28` |
| Circulating snapshot | `2,324,584 L28` |

Additional frozen rules:

- Coinbase is the only issuance mechanism.
- Canonical height is consensus-derived; missing required state fails closed.
- Historical evidence is immutable.
- Adapters and callers have **no authority** to override validation, supply,
  issuance, height, or consensus.
- Sole transfer/coinbase validation authority remains
  `validate_transaction` in `coin/tx_validation.py`.

---

## 3. Canonical deterministic JSON envelope

### 3.1 Encoding rules

For all Universal Access Interface objects:

1. UTF-8 JSON only
2. Exact field order as specified (MUST NOT reorder)
3. No `NaN`, `Infinity`, bytes, tuples, sets, or non-JSON types
4. Integers for amounts and Unix seconds MUST be exact JSON numbers in the
   safe integer range `-9007199254740991` … `9007199254740991`
5. Digests and identifiers that are hex strings MUST be lowercase
6. Canonical digests for UAII objects use CanonUaii exact-order serialization
   (Foundation 56 / `coin.uaii_json.canon_uaii`)

### 3.2 Request envelope (exact order)

1. `interface_profile` — string; MUST equal `l28-universal-ai-access-interface/v0.1`
2. `operation` — string; MUST be a known operation (§4)
3. `request_id` — 64 lowercase hex
4. `created_at` — Unix seconds (int)
5. `expires_at` — Unix seconds (int); MUST be greater than `created_at`
6. `nonce` — non-empty string (≤ 256 UTF-8 bytes; no NUL)
7. `execution_authorized` — boolean; MUST be `false`
8. `params` — object; exact keys for the operation

### 3.3 Response envelope (exact order)

1. `ok` — boolean
2. `code` — stable string code
3. `interface_profile` — echoed profile (or recovered unsupported profile)
4. `operation` — echoed operation when recoverable
5. `request_id` — echoed when recoverable
6. `result` — object on success; empty object or omitted fields only as defined
   by the processor contract
7. `error` — object on failure (§11); MUST NOT appear on success
8. `execution_authorized` — boolean; MUST be `false`
9. `report_id` — 64 lowercase hex audit identifier for the response

Fail-closed rule: malformed, incomplete, contradictory, noncanonical, or
authority-violating requests MUST be rejected. Processors MUST NOT guess,
coerce, or repair attacker-controlled fields.

---

## 4. Operations catalog

| Operation | Status in this profile | Purpose |
|---|---|---|
| `discover_capabilities` | supported | Capability and adapter discovery |
| `get_protocol_status` | supported | Protocol/profile status snapshot |
| `get_balance` | supported | Public balance inquiry |
| `create_quote` | supported | Deterministic quote object |
| `create_unsigned_payment_request` | supported | Unsigned payment proposal |
| `validate_payment` | supported | Deterministic validation response |
| `get_payment_receipt` | supported | Payment/service receipt binding |
| `verify_signed_receipt` | supported | Signed-receipt verification (F64–F78 composition) |
| `create_refund_request` | deferred | Refund request message (non-executing) |
| `create_refund_receipt` | deferred | Refund receipt message (non-executing) |
| Signing / broadcast / autonomous spend | forbidden | Never offered as UAII operations |

Unknown operations MUST fail closed (`operation_unsupported`).

---

## 5. Capability discovery

### 5.1 `discover_capabilities` params (exact order)

1. `include_adapter_declarations` — boolean

### 5.2 Success result (minimum public fields)

1. `interface_profile`
2. `protocol_version` — `"1.0.0"`
3. `currency` — `"L28"`
4. `operations` — array of supported operation names
5. `capabilities` — array of `{capability_id, operation_or_wildcard, status}`
6. `adapter_declarations` — array; empty when not requested
7. `execution_authorized` — `false`
8. `signing_authorized` — `false`
9. `spend_authorized` — `false`

Capability statuses: `supported` | `deferred` | `forbidden`.

Deferred adapters MUST be declared only as metadata:

- `adapter.mcp`
- `adapter.rest_openapi`
- `adapter.python_sdk`
- `adapter.typescript_sdk`

each with status `deferred` until a later authorized adapter foundation.

---

## 6. Balance inquiry

### 6.1 `get_balance` params (exact order)

1. `address` — public identity string (non-empty; not reserved)
2. `require_canonical_height` — boolean

### 6.2 Success result (minimum)

1. `address`
2. `balance` — non-negative int
3. `currency` — `"L28"`
4. `canonical_height` — int when available; fail closed if required and missing
5. `ledger_state_id` — 64 hex binding digest
6. `execution_authorized` — `false`

MUST NOT return private keys, seeds, credentials, wallet handles, or secret
material. Reserved identities such as `COINBASE` and `__MINT__` MUST be
rejected.

---

## 7. Signed quotes

### 7.1 `create_quote` params (exact order)

1. `payer_identity`
2. `payee_identity`
3. `service_id`
4. `service_params` — object
5. `amount` — positive int
6. `currency` — MUST be `"L28"`
7. `purpose` — non-empty string
8. `quote_expires_at` — Unix seconds within envelope lifetime
9. `quote_nonce` — non-empty string
10. `max_amount` — int ≥ `amount`
11. `rejectable` — MUST be `true`
12. `service_terms` — object

### 7.2 Quote object (exact order)

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
14. `service_terms_hash` — 64 hex CanonUaii digest of `service_terms`
15. `spend_authorized` — MUST be `false`
16. `execution_authorized` — MUST be `false`

`quote_id` is the 64 hex CanonUaii digest of the quote object. External
signatures over quotes, when present, MUST be produced only by an isolated
local signer using public verification material.

Spending limits and approval thresholds MAY appear inside `service_terms` as
public policy fields (for example `per_transaction_limit`,
`cumulative_maximum`) but NEVER authorize spend by themselves.

---

## 8. Unsigned payment requests

### 8.1 `create_unsigned_payment_request` params (exact order)

1. `quote`
2. `quote_id`
3. `payer_identity`
4. `payee_identity`
5. `amount`
6. `currency`
7. `purpose`
8. `service_id`
9. `service_terms_hash`
10. `payment_nonce`
11. `payment_expires_at`

### 8.2 Unsigned payment request object (exact order)

1. `payment_request_profile` — `"l28-uaii-unsigned-payment-request/v0.1"`
2. `quote_id`
3. `payer_identity`
4. `payee_identity`
5. `amount`
6. `currency`
7. `purpose`
8. `service_id`
9. `service_terms_hash`
10. `payment_nonce`
11. `payment_expires_at`
12. `quote_expires_at`
13. `quote_nonce`
14. `spend_authorized` — MUST be `false`
15. `execution_authorized` — MUST be `false`

An unsigned payment request proposes a payment. It MUST NOT authorize spending,
settlement, broadcast, or ledger mutation.

---

## 9. Validation requests and responses

### 9.1 `validate_payment` purpose

Deterministically evaluate whether a proposed payment binding is structurally
consistent and, when composed with Protocol validation, whether a proposed
transfer would be acceptable under `validate_transaction`.

### 9.2 Deterministic validation response fields (minimum)

1. `validation_status` — `"accepted"` | `"rejected"`
2. `validation_code` — stable code string
3. `quote_id`
4. `payment_request_id`
5. `spend_authorized` — MUST be `false`
6. `execution_authorized` — MUST be `false`
7. `ledger_mutated` — MUST be `false`
8. `transaction_submitted` — MUST be `false`

Validation evidence is not settlement finality.

---

## 10. Signed receipts

### 10.1 Receipt profile

Signed receipts use Foundation 64/66/67 profile
`l28-uaii-signed-receipt/v0.1` with PureEd25519
(`signer_algorithm_profile` = `ed25519-pure/v0.1`).

### 10.2 `verify_signed_receipt` params (exact order)

1. `signed_receipt` — complete signed-facts object
2. `accepted_receipt_ids` — array of previously accepted receipt ids (replay set)
3. `verification_time` — caller-supplied Unix seconds (no implicit system clock)
4. `governance_approval_evidence` — object; `{}` means not supplied
5. `authorization_response_evidence` — object; `{}` means not supplied

### 10.3 Verification composition (informational)

A successful verification MAY compose replay, expiration, acceptance,
transition proposal, application-boundary eligibility, governance evaluation,
authorization-request proposal, authorization-response evaluation,
application-authorization eligibility, and application-authorization request
proposal results from Foundations 67–78. Those nested objects remain inert and
MUST NOT be interpreted as grants, submissions, applications, or executions.

Always-false flags in public success results include (non-exhaustive):
`signing_authorized`, `spend_authorized`, `settlement_authorized`,
`ledger_mutated`, `execution_authorized`, `transition_applied`,
`application_authorized`, `authorization_granted`, `authorization_active`.

---

## 11. Refund requests and refund receipts (deferred)

Refund messaging is specified for future interoperability. Implementations of
this profile MUST treat the following operations as **deferred** and MUST NOT
execute refunds, mint supply, or mutate ledgers.

### 11.1 Deferred refund request object (exact order)

1. `refund_request_profile` — `"l28-uaii-refund-request/v0.1"`
2. `original_receipt_id` — 64 hex
3. `original_quote_id` — 64 hex
4. `payer_identity`
5. `payee_identity`
6. `asset_id` — `"L28"`
7. `amount` — positive int
8. `refund_reason` — non-empty string
9. `refund_nonce`
10. `refund_expires_at`
11. `spend_authorized` — MUST be `false`
12. `execution_authorized` — MUST be `false`
13. `ledger_mutated` — MUST be `false`

### 11.2 Deferred refund receipt object (exact order)

1. `refund_receipt_profile` — `"l28-uaii-refund-receipt/v0.1"`
2. `refund_request_id` — 64 hex
3. `original_receipt_id` — 64 hex
4. `refund_status` — `"proposed"` | `"rejected"` | `"deferred"`
5. `amount`
6. `asset_id` — `"L28"`
7. `payer_identity`
8. `payee_identity`
9. `audit_id` — 64 hex
10. `spend_authorized` — MUST be `false`
11. `execution_authorized` — MUST be `false`
12. `ledger_mutated` — MUST be `false`
13. `settlement_finalized` — MUST be `false`

Refund receipts MUST NOT claim settlement finality or supply changes.

---

## 12. Replay, expiration, idempotency, limits, and audit identifiers

| Control | Rule |
|---|---|
| Replay protection | Receipt ids in `accepted_receipt_ids` MUST cause fail-closed rejection/replay status; replay precedence remains before expiration (F69–F71) |
| Expiration | Envelope `expires_at`, quote expiry, payment expiry, and receipt `expires_at` evaluated with explicit caller-supplied times only |
| Idempotency | Identical canonical public inputs MUST yield equivalent public outcomes without retained mutable processor state across calls |
| Approval thresholds | Represented only as public evidence / policy fields; never implicit grants |
| Spending limits | `max_amount`, per-transaction, and cumulative fields are informational unless a later authorized settlement path applies Protocol validation |
| Audit identifiers | `request_id`, `quote_id`, `payment_request_id`, `receipt_id`, `report_id`, and deferred `audit_id` MUST be 64 lowercase hex digests or verified public ids |

System clock reads, timezone defaults, environment variables, filesystem
secrets, and network time MUST NOT be used as hidden authority for these
controls.

---

## 13. Error objects and fail-closed behavior

### 13.1 Error object (exact order when present)

1. `code` — stable machine code
2. `message` — safe public string (no secrets, paths, or stack traces)
3. `detail` — optional public structured object; MUST NOT contain secrets

### 13.2 Representative stable codes

| Code | Meaning |
|---|---|
| `schema_invalid` | Missing/extra/wrong-type/noncanonical fields |
| `interface_profile_unsupported` | Profile mismatch |
| `operation_unsupported` | Unknown or deferred-as-unsupported operation |
| `secret_material_forbidden` | Private/credential fields present |
| `identity_invalid` / `reserved_identity_forbidden` | Identity problems |
| `amount_invalid` / `currency_invalid` | Economic field problems |
| `quote_expiration_invalid` | Quote lifetime invalid |
| `signature_invalid` | Public signature verification failed |
| `adapter_override_forbidden` | Adapter attempted to override validation/economics |

Fail closed on ambiguity. Do not coerce booleans, repair hex case, invent
missing ids, or treat simulated/demo approvals as real settlement.

---

## 14. Adapter-neutral behavior

Future adapters (REST/OpenAPI, MCP, Python SDK, TypeScript SDK) MUST:

1. Map 1:1 to this canonical JSON envelope and operation contracts
2. Preserve exact field order and CanonUaii digests
3. Keep `execution_authorized=false` unless a later Protocol-authorized path
   exists (none in this specification)
4. Refuse to accept or forward private keys, seeds, mnemonics, keystore blobs,
   or credential headers into model context or logs
5. Produce equivalent public results for equivalent canonical request bytes

Adapters MUST NOT create alternate validation authorities, mint supply, or
override `validate_transaction`.

---

## 15. Security boundaries

1. Signing stays local inside an isolated signer boundary (Foundation 64).
2. Private keys MUST NEVER enter prompts, tool arguments, UAII params, APIs,
   logs, adapters, receipts, or hosted services.
3. Only public keys, public key ids, signatures, digests, and public
   identities MAY cross process boundaries.
4. Balance inquiry and capability discovery MUST NOT disclose private
   material.
5. Simulated or demo approvals (including offline demo artifacts) are not
   payment, settlement, or spend authorization.

---

## 16. Example JSON messages (disposable fictional values only)

All examples use fixed fictional identities and fixed Unix seconds. They are
non-normative illustrations and MUST NOT be treated as live network traffic,
funded accounts, or production credentials.

### 16.1 Capability discovery request

```json
{
  "interface_profile": "l28-universal-ai-access-interface/v0.1",
  "operation": "discover_capabilities",
  "request_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "created_at": 1700000000,
  "expires_at": 1700000300,
  "nonce": "demo-nonce-discover-001",
  "execution_authorized": false,
  "params": {
    "include_adapter_declarations": true
  }
}
```

### 16.2 Balance inquiry request

```json
{
  "interface_profile": "l28-universal-ai-access-interface/v0.1",
  "operation": "get_balance",
  "request_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "created_at": 1700000000,
  "expires_at": 1700000300,
  "nonce": "demo-nonce-balance-001",
  "execution_authorized": false,
  "params": {
    "address": "agent-buyer-public-001",
    "require_canonical_height": true
  }
}
```

### 16.3 Quote fragment (public fields)

```json
{
  "quote_profile": "l28-uaii-quote/v0.1",
  "payer_identity": "agent-buyer-public-001",
  "payee_identity": "agent-seller-public-001",
  "service_id": "l28.demo.sha256.v0.1",
  "service_params": {
    "request_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
  },
  "amount": 1,
  "currency": "L28",
  "purpose": "universal_access_example",
  "quote_expires_at": 1700000600,
  "quote_nonce": "demo-quote-nonce-001",
  "max_amount": 1,
  "rejectable": true,
  "service_terms": {
    "per_transaction_limit": 1,
    "cumulative_maximum": 1,
    "simulation_only": true
  },
  "service_terms_hash": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
  "spend_authorized": false,
  "execution_authorized": false
}
```

### 16.4 Unsigned payment request fragment

```json
{
  "payment_request_profile": "l28-uaii-unsigned-payment-request/v0.1",
  "quote_id": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
  "payer_identity": "agent-buyer-public-001",
  "payee_identity": "agent-seller-public-001",
  "amount": 1,
  "currency": "L28",
  "purpose": "universal_access_example",
  "service_id": "l28.demo.sha256.v0.1",
  "service_terms_hash": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
  "payment_nonce": "demo-payment-nonce-001",
  "payment_expires_at": 1700000600,
  "quote_expires_at": 1700000600,
  "quote_nonce": "demo-quote-nonce-001",
  "spend_authorized": false,
  "execution_authorized": false
}
```

### 16.5 Validation response fragment

```json
{
  "validation_status": "rejected",
  "validation_code": "execution_not_authorized",
  "quote_id": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
  "payment_request_id": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
  "spend_authorized": false,
  "execution_authorized": false,
  "ledger_mutated": false,
  "transaction_submitted": false
}
```

### 16.6 Deferred refund request fragment

```json
{
  "refund_request_profile": "l28-uaii-refund-request/v0.1",
  "original_receipt_id": "1111111111111111111111111111111111111111111111111111111111111111",
  "original_quote_id": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
  "payer_identity": "agent-buyer-public-001",
  "payee_identity": "agent-seller-public-001",
  "asset_id": "L28",
  "amount": 1,
  "refund_reason": "service_output_disputed_example",
  "refund_nonce": "demo-refund-nonce-001",
  "refund_expires_at": 1700000900,
  "spend_authorized": false,
  "execution_authorized": false,
  "ledger_mutated": false
}
```

### 16.7 Error object fragment

```json
{
  "code": "secret_material_forbidden",
  "message": "Private or credential material is forbidden in interface requests.",
  "detail": {
    "field": "params"
  }
}
```

---

## 17. Conformance requirements

A conforming Universal Access Interface implementation MUST:

1. Accept only the profile `l28-universal-ai-access-interface/v0.1`
2. Enforce exact envelope and object field orders
3. Keep `execution_authorized=false` for all operations defined here
4. Reject secret/credential fields
5. Preserve Protocol economic constants and coinbase-only issuance
6. Use `validate_transaction` as the sole transfer/coinbase validator when
   Protocol validation is invoked
7. Treat deferred refund operations as non-executable
8. Keep signing private keys outside UAII request/response bytes
9. Provide stable error codes and fail closed on ambiguity
10. Remain adapter-neutral: adapters map to this JSON, not the reverse

---

## 18. Deferred implementation work

Later separately authorized work MAY include:

- Executable refund processing under Protocol rules (no supply minting)
- Adapter foundations for REST/OpenAPI, MCP, Python SDK, and TypeScript SDK
- Persistent replay stores with explicit authority boundaries
- Hosted public endpoints (still without private-key custody)
- Broader multi-party escrow flows

None of the above is authorized by Foundation 79 alone.

---

## 19. Explicit non-activation statement

Foundation 79 is a **specification-only candidate**. It:

- does not activate settlement;
- does not activate wallets;
- does not activate mining;
- does not activate networking;
- does not activate adapters;
- does not activate hosted services;
- does not mutate ledgers;
- does not authorize real funds movement;
- does not grant spend, broadcast, or autonomous execution rights.

---

## 20. Document control

| Item | Value |
|---|---|
| Foundation | 79 |
| Path | `docs/universal_access_interface_v0.1.md` |
| Baseline | `995a4585705e750846b5e0259c485a7d22ca05b2` |
| Implementation in this candidate | none (documentation only) |
