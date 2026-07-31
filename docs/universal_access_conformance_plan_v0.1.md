# Universal Access Interface — Deterministic Conformance Plan v0.1

**Foundation:** 80 (specification-only candidate)

**Status:** Specification only (documentation; non-activation; non-implementation)

**Plan version:** `universal-access-conformance-plan/v0.1`

**Authoritative interface input:** `docs/universal_access_interface_v0.1.md`
(Foundation 79; interface profile `l28-universal-ai-access-interface/v0.1`)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Baseline commit:** `39bce2b61de0d91800f75fc57059f6454f5f21af`

**Branch:** `foundation80-deterministic-conformance-plan`

**Normative subordination:** This document is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md) and to Foundation 79. On conflict,
Protocol v1.0.0 prevails over Foundation 79; Foundation 79 prevails over this
plan for interface contracts. This plan MUST NOT redefine settlement, issuance,
supply, consensus height authority, or `validate_transaction`.

---

## 1. Purpose and non-activation

### 1.1 Purpose

Foundation 80 defines a **deterministic conformance plan**: fixture format,
case format, validation rules, positive/negative/boundary/fail-closed case
catalog, coverage matrix, and deferred machine-readable layout for the
Universal Access Interface — so future adapters and runners can prove
byte-stable, fail-closed behavior without implementing those adapters here.

### 1.2 Explicit non-activation

Foundation 80:

- does not implement fixtures, schemas, or test runners;
- does not implement REST, OpenAPI, MCP, Python SDK, or TypeScript SDK adapters;
- does not implement signing, settlement, wallets, networking, mining, or services;
- does not mutate ledgers;
- does not authorize real funds movement;
- does not activate hosted endpoints or autonomous spend.

This candidate creates exactly one markdown specification document.

---

## 2. Conformance scope and terminology

### 2.1 Scope

**In scope (planning only):**

| Area | Plan content |
|---|---|
| Envelope & encoding | Strict JSON, field order, types, unknown-field policy |
| Operations catalog | Every Foundation 79 operation (§4), including deferred and forbidden |
| Economic invariants | Protected Protocol constants and no-override rules |
| Boundary controls | Amount, expiry, nonce, replay, idempotency, limits, audit ids |
| Adapter neutrality | Shared expectations for future REST/MCP/Python/TypeScript |
| Safety | No secrets, no real keys/addresses, no env-derived authority |

**Out of scope (deferred to later authorized foundations):**

- Creating files under a fixture directory
- Machine-readable JSON Schema / fixture packs
- Executable test harnesses
- Adapter implementations
- Ledger, wallet, mining, or networking activation

### 2.2 Terminology

| Term | Meaning |
|---|---|
| Fixture | Deterministic fictional input bundle with fixed identifiers and times |
| Case | One planned assertion tuple: fixture + operation + expected outcome |
| Positive case | Expected success path under Foundation 79 contracts |
| Negative case | Expected fail-closed rejection with a stable error/validation code |
| Boundary case | Edge values at documented limits (expiry equality, max length, etc.) |
| Canonical bytes | Exact-order UTF-8 JSON bytes used for digests (CanonUaii) |
| Disposable address | Fictional public identity never used for production funds |
| Plan ID | Stable case identifier in this document (`UAI-CONF-…`) |

---

## 3. Versioning and deterministic execution rules

### 3.1 Versioning

| Item | Value |
|---|---|
| Plan document | `universal-access-conformance-plan/v0.1` |
| Interface profile under test | `l28-universal-ai-access-interface/v0.1` |
| Protocol | `1.0.0` |
| Case-ID namespace | `UAI-CONF/v0.1` |

Future plan revisions MUST bump the plan version and MUST NOT silently redefine
case IDs. Deprecated IDs remain listed as superseded.

### 3.2 Deterministic execution rules (for future runners)

When a later foundation implements a runner, it MUST:

1. Use only caller-supplied times from fixture fields (no system clock, no TZ defaults, no process-environment time).
2. Parse JSON strictly: reject `NaN`, `Infinity`, duplicate keys, non-UTF-8, and non-JSON types.
3. Enforce exact field order for envelopes and objects as specified by Foundation 79.
4. Reject unknown fields unless a later authorized profile explicitly allows them (this profile: reject).
5. Compare expected public outcomes by canonical public fields only.
6. Keep `execution_authorized=false` on all request/response paths defined here.
7. Never load private keys, credentials, production balances, or historical-ledger mutation inputs.
8. Produce identical public results for identical canonical request bytes across adapters.

---

## 4. Fixture format

### 4.1 Logical fixture object (exact conceptual order)

Planned machine-readable fixtures (deferred; not created in Foundation 80) MUST
use this conceptual key order:

1. `fixture_id` — string; unique; pattern `fx-uai-v01-NNNN`
2. `plan_version` — `"universal-access-conformance-plan/v0.1"`
3. `interface_profile` — `"l28-universal-ai-access-interface/v0.1"`
4. `description` — short public string
5. `fixed_clock` — object with `verification_time`, `created_at`, `expires_at` (Unix seconds ints)
6. `identities` — object of disposable public identities only
7. `ledger_view` — optional fictional public ledger snapshot (balances, height); never production state
8. `request` — complete request envelope or fragment under test
9. `supporting_objects` — optional quotes, payment requests, receipts, evidence objects
10. `safety` — object asserting absence of secrets and production material

### 4.2 Safety assertions (required on every fixture)

Every fixture MUST declare and every future runner MUST verify:

| Assertion | Rule |
|---|---|
| `contains_private_keys` | MUST be `false` |
| `contains_credentials` | MUST be `false` |
| `contains_production_addresses` | MUST be `false` |
| `contains_environment_values` | MUST be `false` |
| `mutates_historical_ledger` | MUST be `false` |
| `uses_real_balances_or_transactions` | MUST be `false` |

Fixtures MUST NEVER contain real keys, credentials, balances, transactions,
production addresses, environment values, or canonical historical-ledger
mutations.

### 4.3 Disposable identity pool (fictional only)

| Alias | Disposable public identity |
|---|---|
| `payer_a` | `l28test1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpayer` |
| `payee_b` | `l28test1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpayee` |
| `observer` | `l28test1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqobsrv` |

Reserved identities such as `COINBASE` and `__MINT__` appear only in negative
cases that expect `reserved_identity_forbidden` (or equivalent fail-closed).

### 4.4 Fixed timestamps and nonces

| Name | Value |
|---|---:|
| `T0` | `1700000000` |
| `T_EXPIRE` | `1700000300` |
| `T_QUOTE_EXPIRE` | `1700000200` |
| `T_VERIFY` | `1700000100` |
| `T_EXPIRED` | `1700000400` |
| `NONCE_A` | `nonce-uai-conf-a` |
| `NONCE_B` | `nonce-uai-conf-b` |
| `REQUEST_ID_A` | `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` |
| `REQUEST_ID_B` | `bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb` |

---

## 5. Case format

### 5.1 Logical case object (exact conceptual order)

1. `case_id` — unique; pattern `UAI-CONF-v0.1-<AREA>-<POL>-<NNN>`
2. `fixture_id` — references §4
3. `operation` — Foundation 79 operation name, or `envelope` / `invariant` for cross-cutting
4. `polarity` — `"positive"` \| `"negative"` \| `"boundary"` \| `"fail_closed"`
5. `request` — request bytes or structured object under test
6. `expected` — success result fields and/or error object
7. `canonical_bytes_note` — how canonical bytes/hash are derived (CanonUaii)
8. `expected_digest_role` — which id fields must match digests (`quote_id`, `report_id`, etc.)
9. `safety_assertions` — subset of §4.2
10. `adapter_expectation` — identical public outcome across REST/MCP/Python/TypeScript

### 5.2 Case-ID ordering rules

1. Sort by `AREA` code alphabetically within the published catalog tables.
2. Within an area, sort by polarity group: `POS`, then `NEG`, then `BND`, then `FCL`.
3. Within a polarity group, sort by numeric suffix ascending (`001`, `002`, …).
4. Case IDs MUST be unique across the entire plan version.
5. Future additions append new numeric suffixes; they MUST NOT reorder existing IDs.

### 5.3 Expected response / error shape

Success expectations reference Foundation 79 response envelope fields
(`ok`, `code`, `result`, `execution_authorized=false`, `report_id`, …).

Failure expectations reference Foundation 79 error object fields
(`code`, `message`, optional public `detail`) and MUST remain free of secrets,
paths, and stack traces.

---

## 6. Encoding and schema validation rules

Future runners MUST enforce:

| Rule | Requirement |
|---|---|
| Strict JSON parse | Reject non-UTF-8, truncated JSON, `NaN`, `Infinity` |
| Duplicate-key rejection | Reject objects with duplicate keys |
| Canonical encoding | Exact Foundation 79 field order; CanonUaii for digests |
| Field types | Integers for amounts and Unix seconds; lowercase hex digests |
| Required fields | Missing required fields → `schema_invalid` (fail closed) |
| Optional fields | Only where Foundation 79 marks optional; else reject |
| Unknown-field policy | Reject unknown keys at envelope and params levels |
| Deterministic ordering | Arrays that are sets of digests MUST be compared after documented sort rules where Foundation 79 requires order; otherwise exact order |

Illustrative envelope fragment (fictional; non-executing):

```json
{
  "interface_profile": "l28-universal-ai-access-interface/v0.1",
  "operation": "discover_capabilities",
  "request_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "created_at": 1700000000,
  "expires_at": 1700000300,
  "nonce": "nonce-uai-conf-a",
  "execution_authorized": false,
  "params": {
    "include_adapter_declarations": true
  }
}
```

Illustrative fail-closed error fragment:

```json
{
  "code": "schema_invalid",
  "message": "request envelope failed schema validation",
  "detail": {
    "reason": "unknown_field",
    "field": "private_key"
  }
}
```

---

## 7. Protected Protocol and economic invariants

Every conformance suite MUST preserve L28 Protocol v1.0.0 and these protected
facts (MUST NOT redefine or override):

| Fact | Value |
|---|---:|
| Hard cap | `28,000,000 L28` |
| Emission schedule ceiling | `11,130,000 L28` |
| Historically mined | `2,824,584 L28` |
| Treasury locked | `500,000 L28` |
| Circulating snapshot | `2,324,584 L28` |

Additional frozen rules that cases MUST assert:

- Coinbase is the only issuance mechanism.
- Canonical height is consensus-derived; missing required state fails closed.
- Historical evidence is immutable.
- Adapters and callers have **no authority** to override validation, supply,
  issuance, height, or consensus.
- Sole transfer/coinbase validation authority remains
  `validate_transaction` in `coin/tx_validation.py`.

Invariant fixture fragment (fictional public constants only):

```json
{
  "protocol_version": "1.0.0",
  "hard_cap_l28": 28000000,
  "emission_ceiling_l28": 11130000,
  "historically_mined_l28": 2824584,
  "treasury_locked_l28": 500000,
  "circulating_snapshot_l28": 2324584,
  "issuance_mechanism": "coinbase_only",
  "height_authority": "consensus_derived",
  "historical_evidence": "immutable",
  "adapter_override_allowed": false
}
```

---

## 8. Planned case catalog

Polarity codes in IDs: `POS` (positive), `NEG` (negative), `BND` (boundary),
`FCL` (fail-closed). Counts below are planned cases for a future suite; this
foundation does not implement them.

### 8.1 Envelope and encoding (`ENV`)

| case_id | polarity | Summary | Expected |
|---|---|---|---|
| `UAI-CONF-v0.1-ENV-POS-001` | positive | Well-formed envelope with exact order | `ok=true`; echo profile/operation/request_id; `execution_authorized=false` |
| `UAI-CONF-v0.1-ENV-NEG-001` | negative | Unsupported `interface_profile` | `interface_profile_unsupported` |
| `UAI-CONF-v0.1-ENV-NEG-002` | negative | Unknown operation name | `operation_unsupported` |
| `UAI-CONF-v0.1-ENV-NEG-003` | negative | Duplicate JSON key in envelope | `schema_invalid` |
| `UAI-CONF-v0.1-ENV-NEG-004` | negative | Unknown envelope field | `schema_invalid` |
| `UAI-CONF-v0.1-ENV-NEG-005` | negative | `execution_authorized=true` | fail closed (`schema_invalid` or authority denial) |
| `UAI-CONF-v0.1-ENV-NEG-006` | negative | Secret field `private_key` present | `secret_material_forbidden` |
| `UAI-CONF-v0.1-ENV-BND-001` | boundary | `expires_at == created_at + 1` | accepted structurally if else valid |
| `UAI-CONF-v0.1-ENV-BND-002` | boundary | `expires_at <= created_at` | `schema_invalid` |
| `UAI-CONF-v0.1-ENV-BND-003` | boundary | Nonce length 256 UTF-8 bytes | accepted if else valid |
| `UAI-CONF-v0.1-ENV-BND-004` | boundary | Nonce length 257 or contains NUL | `schema_invalid` |
| `UAI-CONF-v0.1-ENV-FCL-001` | fail_closed | Malformed / truncated JSON | reject; no coercion |
| `UAI-CONF-v0.1-ENV-FCL-002` | fail_closed | Uppercase hex in `request_id` | reject; no case repair |

### 8.2 `discover_capabilities` (`CAP`)

| case_id | polarity | Summary | Expected |
|---|---|---|---|
| `UAI-CONF-v0.1-CAP-POS-001` | positive | Discover without adapter declarations | operations list; deferred adapters omitted/empty |
| `UAI-CONF-v0.1-CAP-POS-002` | positive | Discover with adapter declarations | adapters listed as `deferred` metadata only |
| `UAI-CONF-v0.1-CAP-NEG-001` | negative | Wrong params type / missing boolean | `schema_invalid` |
| `UAI-CONF-v0.1-CAP-NEG-002` | negative | Capability claims `signing` supported | reject capability forgery / fail closed |
| `UAI-CONF-v0.1-CAP-FCL-001` | fail_closed | Response would set `spend_authorized=true` | forbidden; conformance fails the implementation |

### 8.3 `get_protocol_status` (`PST`)

| case_id | polarity | Summary | Expected |
|---|---|---|---|
| `UAI-CONF-v0.1-PST-POS-001` | positive | Status snapshot with Protocol `1.0.0` | echoes protected profile; `execution_authorized=false` |
| `UAI-CONF-v0.1-PST-NEG-001` | negative | Request attempts to override hard cap | `adapter_override_forbidden` |
| `UAI-CONF-v0.1-PST-FCL-001` | fail_closed | Missing consensus/protocol state when required | fail closed; no invented status |

### 8.4 `get_balance` (`BAL`)

| case_id | polarity | Summary | Expected |
|---|---|---|---|
| `UAI-CONF-v0.1-BAL-POS-001` | positive | Balance for disposable `payer_a` with height | non-negative int; currency `L28`; no secrets |
| `UAI-CONF-v0.1-BAL-NEG-001` | negative | Reserved identity `COINBASE` | `reserved_identity_forbidden` |
| `UAI-CONF-v0.1-BAL-NEG-002` | negative | Empty address | `identity_invalid` |
| `UAI-CONF-v0.1-BAL-FCL-001` | fail_closed | `require_canonical_height=true` and height missing | fail closed |
| `UAI-CONF-v0.1-BAL-FCL-002` | fail_closed | Response includes private key material | suite failure (`secret_material_forbidden`) |

Balance request fragment:

```json
{
  "interface_profile": "l28-universal-ai-access-interface/v0.1",
  "operation": "get_balance",
  "request_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "created_at": 1700000000,
  "expires_at": 1700000300,
  "nonce": "nonce-uai-conf-b",
  "execution_authorized": false,
  "params": {
    "address": "l28test1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpayer",
    "require_canonical_height": true
  }
}
```

### 8.5 `create_quote` (`QUO`)

| case_id | polarity | Summary | Expected |
|---|---|---|---|
| `UAI-CONF-v0.1-QUO-POS-001` | positive | Valid quote params; `rejectable=true` | quote object; `quote_id` = CanonUaii digest; spend/exec false |
| `UAI-CONF-v0.1-QUO-NEG-001` | negative | `amount <= 0` | `amount_invalid` |
| `UAI-CONF-v0.1-QUO-NEG-002` | negative | `currency != "L28"` | `currency_invalid` |
| `UAI-CONF-v0.1-QUO-NEG-003` | negative | `max_amount < amount` | `amount_invalid` |
| `UAI-CONF-v0.1-QUO-NEG-004` | negative | `rejectable=false` | `schema_invalid` |
| `UAI-CONF-v0.1-QUO-BND-001` | boundary | `quote_expires_at` equal envelope `expires_at` | accepted if within lifetime rules |
| `UAI-CONF-v0.1-QUO-BND-002` | boundary | `quote_expires_at` after envelope expiry | `quote_expiration_invalid` |
| `UAI-CONF-v0.1-QUO-BND-003` | boundary | Spending-limit fields in `service_terms` only informational | quote ok; still `spend_authorized=false` |
| `UAI-CONF-v0.1-QUO-FCL-001` | fail_closed | Expired quote used after `T_EXPIRED` | reject; no repair |

Quote public fragment:

```json
{
  "quote_profile": "l28-uaii-quote/v0.1",
  "payer_identity": "l28test1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpayer",
  "payee_identity": "l28test1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpayee",
  "service_id": "svc.demo.echo",
  "service_params": {
    "units": 1
  },
  "amount": 28,
  "currency": "L28",
  "purpose": "conformance-quote",
  "quote_expires_at": 1700000200,
  "quote_nonce": "nonce-uai-conf-a",
  "max_amount": 28,
  "rejectable": true,
  "service_terms": {
    "per_transaction_limit": 100,
    "cumulative_maximum": 1000
  },
  "spend_authorized": false,
  "execution_authorized": false
}
```

### 8.6 `create_unsigned_payment_request` (`UPR`)

| case_id | polarity | Summary | Expected |
|---|---|---|---|
| `UAI-CONF-v0.1-UPR-POS-001` | positive | Binding matches quote fields | unsigned request; spend/exec false |
| `UAI-CONF-v0.1-UPR-NEG-001` | negative | `quote_id` mismatch vs quote bytes | fail closed / `schema_invalid` |
| `UAI-CONF-v0.1-UPR-NEG-002` | negative | Amount differs from quote | mismatched amount reject |
| `UAI-CONF-v0.1-UPR-NEG-003` | negative | Asset/currency mismatch | `currency_invalid` |
| `UAI-CONF-v0.1-UPR-BND-001` | boundary | Payment expiry at quote expiry | accepted if rules allow equality |
| `UAI-CONF-v0.1-UPR-FCL-001` | fail_closed | Incomplete payment object (missing nonce) | reject; no coercion |

### 8.7 `validate_payment` (`VAL`)

| case_id | polarity | Summary | Expected |
|---|---|---|---|
| `UAI-CONF-v0.1-VAL-POS-001` | positive | Structurally consistent binding | `validation_status=accepted` or documented structural accept; spend/exec/ledger flags false |
| `UAI-CONF-v0.1-VAL-NEG-001` | negative | Conflicting evidence (quote vs payment) | `validation_status=rejected` |
| `UAI-CONF-v0.1-VAL-NEG-002` | negative | Invalid hash / digest mismatch | reject |
| `UAI-CONF-v0.1-VAL-FCL-001` | fail_closed | Unauthorized override of `validate_transaction` | `adapter_override_forbidden` |
| `UAI-CONF-v0.1-VAL-FCL-002` | fail_closed | Claims `ledger_mutated=true` | forbidden; conformance fails implementation |

Validation response fragment:

```json
{
  "validation_status": "rejected",
  "validation_code": "amount_mismatch",
  "quote_id": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "payment_request_id": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
  "spend_authorized": false,
  "execution_authorized": false,
  "ledger_mutated": false,
  "transaction_submitted": false
}
```

### 8.8 `get_payment_receipt` (`RCP`)

| case_id | polarity | Summary | Expected |
|---|---|---|---|
| `UAI-CONF-v0.1-RCP-POS-001` | positive | Bind public payment/service receipt fields | receipt profile distinct from signed-receipt; flags false |
| `UAI-CONF-v0.1-RCP-NEG-001` | negative | Incomplete receipt (missing audit id) | `schema_invalid` |
| `UAI-CONF-v0.1-RCP-FCL-001` | fail_closed | Treat F56 unsigned receipt as F64 signed receipt | reject conflation |

### 8.9 `verify_signed_receipt` (`VSR`)

| case_id | polarity | Summary | Expected |
|---|---|---|---|
| `UAI-CONF-v0.1-VSR-POS-001` | positive | Complete signed-facts object; empty evidence objects | verification compose; all grant flags false |
| `UAI-CONF-v0.1-VSR-NEG-001` | negative | `signature_invalid` public material | `signature_invalid` |
| `UAI-CONF-v0.1-VSR-NEG-002` | negative | Replay: `receipt_id` in `accepted_receipt_ids` | fail-closed replay status; precedence before expiration |
| `UAI-CONF-v0.1-VSR-NEG-003` | negative | Conflicting governance vs authorization evidence | fail closed |
| `UAI-CONF-v0.1-VSR-BND-001` | boundary | `verification_time` equal `expires_at` | documented boundary (reject or accept per F70 rules; must be deterministic) |
| `UAI-CONF-v0.1-VSR-BND-002` | boundary | Approval-threshold fields present as public evidence only | never implicit grant |
| `UAI-CONF-v0.1-VSR-BND-003` | boundary | Signature metadata present (alg profile, public key id only) | accepted if schema-valid; no private key bytes |
| `UAI-CONF-v0.1-VSR-FCL-001` | fail_closed | Missing `verification_time` (would require system clock) | reject |
| `UAI-CONF-v0.1-VSR-FCL-002` | fail_closed | Incomplete signed receipt | reject |

### 8.10 `create_refund_request` (deferred) (`RFR`)

| case_id | polarity | Summary | Expected |
|---|---|---|---|
| `UAI-CONF-v0.1-RFR-POS-001` | positive | Schema-valid deferred refund request object (message only) | object accepted as **deferred/non-executing** message shape; flags false |
| `UAI-CONF-v0.1-RFR-NEG-001` | negative | Operation invoked as executable settlement | `operation_unsupported` or deferred-non-executing reject |
| `UAI-CONF-v0.1-RFR-NEG-002` | negative | Amount/asset mismatch vs original | reject |
| `UAI-CONF-v0.1-RFR-FCL-001` | fail_closed | Attempt to mint supply via refund | fail closed; no ledger mutation |

Deferred refund request fragment:

```json
{
  "refund_request_profile": "l28-uaii-refund-request/v0.1",
  "original_receipt_id": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
  "original_quote_id": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
  "payer_identity": "l28test1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpayer",
  "payee_identity": "l28test1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpayee",
  "asset_id": "L28",
  "amount": 28,
  "refund_reason": "conformance-deferred-refund",
  "refund_nonce": "nonce-uai-conf-a",
  "refund_expires_at": 1700000200,
  "spend_authorized": false,
  "execution_authorized": false,
  "ledger_mutated": false
}
```

### 8.11 `create_refund_receipt` (deferred) (`RRC`)

| case_id | polarity | Summary | Expected |
|---|---|---|---|
| `UAI-CONF-v0.1-RRC-POS-001` | positive | Schema-valid deferred refund receipt with status `deferred` | message shape only; `settlement_finalized=false` |
| `UAI-CONF-v0.1-RRC-NEG-001` | negative | Claims `settlement_finalized=true` | reject |
| `UAI-CONF-v0.1-RRC-FCL-001` | fail_closed | Incomplete refund receipt | reject |

### 8.12 Forbidden operations and overrides (`FOR`)

| case_id | polarity | Summary | Expected |
|---|---|---|---|
| `UAI-CONF-v0.1-FOR-NEG-001` | negative | Operation `sign_and_broadcast` (or equivalent) | `operation_unsupported` |
| `UAI-CONF-v0.1-FOR-NEG-002` | negative | Autonomous spend operation | `operation_unsupported` |
| `UAI-CONF-v0.1-FOR-FCL-001` | fail_closed | Adapter attempts supply/height override | `adapter_override_forbidden` |

### 8.13 Idempotency, audit identifiers, and limits (`CTL`)

| case_id | polarity | Summary | Expected |
|---|---|---|---|
| `UAI-CONF-v0.1-CTL-POS-001` | positive | Identical canonical public inputs → equivalent public outcomes | deterministic equivalence |
| `UAI-CONF-v0.1-CTL-NEG-001` | negative | Audit id wrong length / uppercase | reject |
| `UAI-CONF-v0.1-CTL-BND-001` | boundary | Audit ids are 64 lowercase hex | accept |
| `UAI-CONF-v0.1-CTL-BND-002` | boundary | Spending limits / approval thresholds informational only | never grant spend |
| `UAI-CONF-v0.1-CTL-FCL-001` | fail_closed | Replay after accept using retained id set | fail closed |

### 8.14 Economic invariant cases (`ECO`)

| case_id | polarity | Summary | Expected |
|---|---|---|---|
| `UAI-CONF-v0.1-ECO-POS-001` | positive | Public status/constants echo exact protected values | hard cap `28,000,000 L28`; emission `11,130,000 L28`; mined `2,824,584 L28`; treasury `500,000 L28`; circulating `2,324,584 L28` |
| `UAI-CONF-v0.1-ECO-NEG-001` | negative | Request redefines hard cap | `adapter_override_forbidden` |
| `UAI-CONF-v0.1-ECO-NEG-002` | negative | Non-coinbase issuance claim | fail closed |
| `UAI-CONF-v0.1-ECO-FCL-001` | fail_closed | Mutation of immutable historical evidence | fail closed |

---

## 9. Coverage matrix

Every Foundation 79 operation and invariant maps to ≥1 positive and ≥1 negative
planned case.

| Foundation 79 item | Positive case(s) | Negative / fail-closed case(s) |
|---|---|---|
| Envelope / encoding rules | `ENV-POS-001` | `ENV-NEG-001`…`006`, `ENV-FCL-001`…`002` |
| `discover_capabilities` | `CAP-POS-001`, `CAP-POS-002` | `CAP-NEG-001`, `CAP-NEG-002`, `CAP-FCL-001` |
| `get_protocol_status` | `PST-POS-001` | `PST-NEG-001`, `PST-FCL-001` |
| `get_balance` | `BAL-POS-001` | `BAL-NEG-001`, `BAL-NEG-002`, `BAL-FCL-001`, `BAL-FCL-002` |
| `create_quote` | `QUO-POS-001` | `QUO-NEG-001`…`004`, `QUO-FCL-001` |
| `create_unsigned_payment_request` | `UPR-POS-001` | `UPR-NEG-001`…`003`, `UPR-FCL-001` |
| `validate_payment` | `VAL-POS-001` | `VAL-NEG-001`, `VAL-NEG-002`, `VAL-FCL-001`, `VAL-FCL-002` |
| `get_payment_receipt` | `RCP-POS-001` | `RCP-NEG-001`, `RCP-FCL-001` |
| `verify_signed_receipt` | `VSR-POS-001` | `VSR-NEG-001`…`003`, `VSR-FCL-001`, `VSR-FCL-002` |
| `create_refund_request` (deferred) | `RFR-POS-001` | `RFR-NEG-001`, `RFR-NEG-002`, `RFR-FCL-001` |
| `create_refund_receipt` (deferred) | `RRC-POS-001` | `RRC-NEG-001`, `RRC-FCL-001` |
| Forbidden signing/broadcast/autonomous spend | (absence asserted via `CAP-POS-*`) | `FOR-NEG-001`, `FOR-NEG-002` |
| Hard cap `28,000,000 L28` | `ECO-POS-001` | `ECO-NEG-001` |
| Emission ceiling `11,130,000 L28` | `ECO-POS-001` | `ECO-NEG-001` |
| Historically mined `2,824,584 L28` | `ECO-POS-001` | `ECO-FCL-001` |
| Treasury locked `500,000 L28` | `ECO-POS-001` | `ECO-NEG-001` |
| Circulating snapshot `2,324,584 L28` | `ECO-POS-001` | `ECO-NEG-001` |
| Coinbase-only issuance | `ECO-POS-001` | `ECO-NEG-002` |
| Consensus-derived height | `BAL-POS-001`, `PST-POS-001` | `BAL-FCL-001`, `PST-FCL-001` |
| Immutable historical evidence | `ECO-POS-001` | `ECO-FCL-001` |
| No adapter/caller override authority | `CTL-POS-001` | `FOR-FCL-001`, `VAL-FCL-001`, `PST-NEG-001` |
| Replay / expiry / idempotency / limits / audit ids | `CTL-POS-001`, `CTL-BND-*`, `VSR-POS-001` | `VSR-NEG-002`, `CTL-NEG-001`, `CTL-FCL-001`, `QUO-BND-*` |

**Coverage-matrix result (plan):** COMPLETE — every Foundation 79 operation and
listed invariant has ≥1 positive and ≥1 negative (or fail-closed) planned case.

---

## 10. Planned case counts by operation

| Operation / area | POS | NEG | BND | FCL | Total |
|---|---:|---:|---:|---:|---:|
| Envelope (`ENV`) | 1 | 6 | 4 | 2 | 13 |
| `discover_capabilities` | 2 | 2 | 0 | 1 | 5 |
| `get_protocol_status` | 1 | 1 | 0 | 1 | 3 |
| `get_balance` | 1 | 2 | 0 | 2 | 5 |
| `create_quote` | 1 | 4 | 3 | 1 | 9 |
| `create_unsigned_payment_request` | 1 | 3 | 1 | 1 | 6 |
| `validate_payment` | 1 | 2 | 0 | 2 | 5 |
| `get_payment_receipt` | 1 | 1 | 0 | 1 | 3 |
| `verify_signed_receipt` | 1 | 3 | 3 | 2 | 9 |
| `create_refund_request` | 1 | 2 | 0 | 1 | 4 |
| `create_refund_receipt` | 1 | 1 | 0 | 1 | 3 |
| Forbidden ops (`FOR`) | 0 | 2 | 0 | 1 | 3 |
| Controls (`CTL`) | 1 | 1 | 2 | 1 | 5 |
| Economics (`ECO`) | 1 | 2 | 0 | 1 | 4 |
| **Plan total** | **14** | **32** | **13** | **18** | **77** |

---

## 11. Adapter-neutral test expectations

Future REST/OpenAPI, MCP, Python, and TypeScript adapters MUST, for the same
canonical request bytes:

1. Produce equivalent public `ok`/`code`/`result`/`error` fields.
2. Preserve CanonUaii digests (`quote_id`, `payment_request_id`, `receipt_id`, `report_id`, `audit_id`).
3. Keep `execution_authorized=false` and reject secret material identically.
4. Map transport errors to Foundation 79 stable codes without inventing alternate validation authorities.
5. Remain reusable: one fixture pack drives all adapters; adapters MUST NOT fork case semantics.

Adapters MUST NOT mint supply, override `validate_transaction`, or treat demo
approvals as settlement.

---

## 12. Deferred machine-readable layout (NOT created by Foundation 80)

The following paths are **proposed only**. Foundation 80 MUST NOT create them.

```text
# DEFERRED — do not create in Foundation 80
tests/uai_conformance/v0.1/
  README.md                         # deferred
  schemas/
    request_envelope.schema.json    # deferred
    response_envelope.schema.json   # deferred
    fixtures.schema.json            # deferred
    cases.schema.json               # deferred
  fixtures/
    fx-uai-v01-0001.json            # deferred
    ...
  cases/
    UAI-CONF-v0.1-ENV-POS-001.json  # deferred
    ...
  expected/
    ...                             # deferred
```

Creating schemas, fixture files, or runners requires a later explicit
authorization distinct from Foundation 80.

---

## 13. Security boundaries

1. Signing stays local inside an isolated signer boundary when later composed.
2. Private keys MUST NEVER enter prompts, tool arguments, UAII params, APIs,
   logs, adapters, receipts, fixtures, or hosted services.
3. Only public keys, public key ids, signatures, digests, and disposable public
   identities MAY appear in fixtures.
4. Balance and capability cases MUST NOT disclose private material.
5. Simulated or demo approvals are not payment, settlement, or spend
   authorization.
6. Fail closed on missing consensus/ledger state, malformed input, expired
   quotes, replay attempts, mismatched assets/amounts, invalid hashes,
   incomplete receipts, and unauthorized overrides.

---

## 14. Explicit Foundation 80 limits

Foundation 80 does **not**:

- implement fixtures, schemas, or test runners;
- implement REST, MCP, SDKs, signing, settlement, wallets, networking, mining,
  or services;
- mutate ledgers;
- stage or commit machine-readable artifacts beyond this single markdown plan
  (commit authorization is separate from this candidate).

---

## 15. Document control

| Item | Value |
|---|---|
| Foundation | 80 |
| Path | `docs/universal_access_conformance_plan_v0.1.md` |
| Baseline | `39bce2b61de0d91800f75fc57059f6454f5f21af` |
| Authoritative input | `docs/universal_access_interface_v0.1.md` |
| Planned case total | 77 |
| Implementation in this candidate | none (documentation only) |
