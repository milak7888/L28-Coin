# Foundation 69 — Signed-Receipt Replay Verification

- **Status:** implemented (pure caller-supplied receipt_id membership classification)
- **Baseline:** `f4fd0fd9ee840b78836d038c09b8d2f0c35b8e34` (Foundation 68 on main)
- **Branch:** `foundation69-signed-receipt-replay-verification`
- **Normative parents:** Foundation 64; Foundation 66–68

## 1. Normative replay identifier

| Item | Value | Evidence |
|---|---|---|
| Identifier used by Foundation 69 | Foundation 64 `receipt_id` | F64 §6.2 / §6.2.4; immutable per receipt |
| Caller-supplied context | `accepted_receipt_ids`: list of previously accepted `receipt_id` values | External authority owns prior acceptances (F64 §10.4 store ownership) |
| Deferred F64 §10.3 uniqueness | Time-scoped `replay_key` over `F64SigningReplayKeyMaterial` | Requires clock (`expires_at + 300`) and external proving capability — out of F69 scope |

Foundation 69 does **not** invent a second receipt identity. It classifies membership of the
verified `receipt_id` against explicit caller context. Full F64 hard-fail
`replay_detected` for missing capability / previously-seen `replay_key` remains an
external-authority obligation.

## 2. Pure function and UAII contract

### Symbols (`coin/uaii_signed_receipt.py`)

- `validate_accepted_receipt_ids`
- `classify_signed_receipt_replay`
- `MAX_ACCEPTED_RECEIPT_IDS` (`256`, Foundation 60 L3)

### Classification order

1. `verify_signed_receipt_facts` (Foundation 67) — integrity/crypto first.
2. Validate `accepted_receipt_ids` (list; hex64 elements; no nulls; no duplicates;
   length `<= 256`).
3. Return `replay_status`: `fresh` if `receipt_id` absent from context, else `replayed`.

No mutation of the supplied list; no retained module state; no filesystem/DB/cache.

### UAII `verify_signed_receipt` params (exact order)

| # | Field | Type |
|---|---|---|
| 1 | `signed_receipt` | 27-field signed facts |
| 2 | `accepted_receipt_ids` | list of 64-hex `receipt_id` strings |

### Success result addition

| Field | Values |
|---|---|
| `replay_status` | `fresh` \| `replayed` (immediately after `verification_status`) |

Success code remains `signed_receipt_verified`. Replay classification is not settlement,
ledger acceptance, or persistent rejection history.

## 3. Error precedence

1. UAII envelope / params schema (`schema_invalid`, …).
2. Foundation 67 verification failures (`digest_mismatch`, `signature_invalid`,
   `receipt_id_invalid`, `algorithm_unsupported`, …) — **before** replay classification.
3. Replay-context schema failures (`schema_invalid`, `input_too_large`).

## 4. Caller-supplied-context boundary

- External systems supply `accepted_receipt_ids`.
- Foundation 69 never inserts, deletes, or persists those IDs.
- Empty list is valid and yields `fresh` for any cryptographically valid receipt.

## 5. Implemented vs deferred

**Implemented:** pure `receipt_id` membership classification after F67 verify; UAII
param/result wiring; fail-closed context validation.

**Deferred:** persistent replay stores; `replay_key` construction from approval
material for uniqueness; time/skew uniqueness windows; hard-fail mapping of
`replayed` → `replay_detected`; approval execution; settlement; adapters.

## 6. Invariants

| Flag | Value |
|---|---|
| `persistent_replay_storage_created` | `false` |
| `replay_state_mutated` | `false` |
| `signing_authorized` | `false` |
| `persistent_keys_created` | `false` |
| `private_material_exposed` | `false` |
| `spend_authorized` | `false` |
| `settlement_authorized` | `false` |
| `ledger_mutated` | `false` |
| `adapters_activated` | `false` |
| `runtime_activated` | `false` |

## 7. Paths

| Path | Role |
|---|---|
| `coin/uaii_signed_receipt.py` | Pure replay classification |
| `coin/uaii_reference_core.py` | Extend `verify_signed_receipt` params/result |
| `tests/test_uaii_signed_receipt_replay.py` | Focused Foundation 69 suite |
| `tests/test_uaii_verify_signed_receipt.py` | Updated for required `accepted_receipt_ids` |
| `docs/foundation69_signed_receipt_replay_verification.md` | This record |

## 8. Tests executed

Recorded by the Foundation 69 validation run (F69 suite, F66–F68 receipt/UAII
suites, protocol conformance / protected economics).

## 9. Document history

| Version | Change |
|---|---|
| 0.1 | Pure receipt_id replay classification after F67 verify |
