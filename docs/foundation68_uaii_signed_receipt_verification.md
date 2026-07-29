# Foundation 68 — UAII Signed-Receipt Verification

- **Status:** implemented (one named UAII verification operation)
- **Baseline:** `a40aead65e3cfbd93f1a4d7d2a62a1629d076440` (Foundation 67 on main)
- **Branch:** `foundation68-uaii-signed-receipt-verification`
- **Normative parents:** Foundation 64 contract; Foundation 66 schema/material; Foundation 67 Ed25519 verify

## 1. Operation contract

| Item | Value |
|---|---|
| Operation name | `verify_signed_receipt` |
| Capability id | `uaii.verify_signed_receipt` |
| Capability status | `supported` |
| Success code | `signed_receipt_verified` |
| Processor | `process_uaii_request` only |

### Request `params` (exact order)

| # | Field | Type |
|---|---|---|
| 1 | `signed_receipt` | object — complete Foundation 64/67 27-field signed facts |

Missing, unexpected, non-object, or schema-invalid `signed_receipt` → fail closed with the
Foundation 64/UAII code from Foundation 66/67 (`schema_invalid`, `digest_mismatch`,
`signature_invalid`, `algorithm_unsupported`, `receipt_id_invalid`, etc.).

### Success `result` (exact order)

| Field | Rule |
|---|---|
| `verification_status` | `"verified"` |
| `receipt_profile` | from verified facts |
| `receipt_id` | public id |
| `signed_payload_digest` | public digest |
| `signer_algorithm_profile` | `ed25519-pure/v0.1` |
| `signer_public_key_id` | public |
| `signer_public_key` | public |
| `settlement_status` | public |
| `payer_public_identity` | public |
| `provider_public_identity` | public |
| `asset_id` | `"L28"` |
| `amount` | integer |
| `purpose` | `signed_receipt` |
| `correlation_id` / `request_id` / `quote_id` | public identifiers |
| auth flags | all `false` |

UAII response envelope format is unchanged (`ok`, `code`, `detail`, `report_id`, …).

## 2. Paths and symbols

| Path | Change |
|---|---|
| `coin/uaii_reference_core.py` | Register/dispatch `_op_verify_signed_receipt` |
| `tests/test_uaii_verify_signed_receipt.py` | Focused Foundation 68 suite |
| `tests/test_uaii_reference_core.py` | Operations-count / membership update |
| `docs/foundation68_uaii_signed_receipt_verification.md` | This record |

Symbols: `verify_signed_receipt` in `OPERATIONS` / `CAPABILITIES`;
`VERIFY_SIGNED_RECEIPT_PARAMS`; `_op_verify_signed_receipt`; imports
`verify_signed_receipt_facts`, `F64ReceiptSchemaError`.

`get_payment_receipt` is **not** extended (Foundation 56 unsigned citation remains distinct).

## 3. Delegation boundary

```text
UAII process_uaii_request
  -> _op_verify_signed_receipt (params schema only)
  -> coin.uaii_signed_receipt.verify_signed_receipt_facts  (F67)
       -> F66 schema / CanonUaii reconstruction / digest / receipt_id
       -> PureEd25519 public verify
```

UAII does **not** reimplement schema, canonicalization, digest, receipt-ID,
identity-binding, or Ed25519 logic. M2M canonicalize is not used.

## 4. Public-data and private-material boundaries

- Request/response carry public signed-receipt fields only.
- No private keys, seeds, PEM, signer callables, or signing APIs in this operation.
- Signing remains capability-forbidden (`uaii.signing` status `forbidden`).
- Disposable in-memory keys appear only inside tests when constructing fixtures.

## 5. Implemented vs deferred

**Implemented:** named UAII verification operation; discoverability; fail-closed
delegation to Foundation 67; deterministic public result.

**Deferred:** signing through UAII, receipt creation, status transitions, replay
state, approval execution, spend/settle, adapters (REST/MCP/SDK/CLI), networking,
runtime services.

## 6. Invariants

| Flag | Value |
|---|---|
| `signing_authorized` | `false` |
| `persistent_keys_created` | `false` |
| `private_material_exposed` | `false` |
| `spend_authorized` | `false` |
| `settlement_authorized` | `false` |
| `ledger_mutated` | `false` |
| `adapters_activated` | `false` |
| `runtime_activated` | `false` |

## 7. Tests executed

Recorded by the Foundation 68 validation run: focused F68 suite, F66/F67 receipt
suites, UAII reference-core / resource-limit suites, protocol conformance /
protected economics.

## 8. Document history

| Version | Change |
|---|---|
| 0.1 | Integrate `verify_signed_receipt` through UAII |
