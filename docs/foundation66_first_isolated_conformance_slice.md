# Foundation 66 — First Isolated Conformance Slice

- **Status:** implemented (documentation + pure data-contract slice)
- **Baseline:** `e12a77853501976a74d9229f0f522a48005d5676` (Foundation 65 on main)
- **Branch:** `foundation66-first-isolated-conformance-slice`
- **Normative parents:** Foundation 64 (signed-receipt contract); Foundation 65 (implementation map)

## 1. Authority boundaries (unchanged)

| Authority | Rule |
|---|---|
| Foundation 64 | Sole normative signed-receipt contract |
| Foundation 65 | Implementation map / readiness plan |
| UAII (`process_uaii_request`) | Sole protocol processor |
| `validate_transaction` | Sole transaction-validation authority |
| CanonUaii (`coin.uaii_json.canon_uaii`) | Sole F64 canonicalization path |
| M2M `canonicalize` / `ReplayRegistry` | **Forbidden** as F64 authorities |

## 2. Resolved Foundation 65 questions

### Q-65-1 — Module names and ownership

**Decision:** Place the first F64 receipt data-contract slice in:

| Path | Ownership |
|---|---|
| `coin/uaii_signed_receipt.py` | Pure schema validation + deterministic receipt-material construction |
| `tests/test_uaii_signed_receipt.py` | Focused conformance tests for this slice |
| `docs/foundation66_first_isolated_conformance_slice.md` | This decision record |

**Evidence:**

- Foundation 65 §9.1 proposed future path label `coin/uaii_signed_receipt.py`.
- Existing UAII package layout (`coin/uaii_json.py`, `coin/uaii_reference_core.py`,
  `coin/uaii_resource_limits.py`) is the repository-native home for UAII-adjacent
  pure helpers.
- Extending `coin/` avoids a parallel subsystem.

**Ownership limits for this module:**

- MAY own exact field-order schema checks and CanonUaii-based digest / receipt-ID
  / replay-key **material** construction.
- MUST NOT become an alternate UAII processor, transaction validator, signer
  authority, replay store, or ledger authority.

Signer (`uaii_isolated_signer`) and separate approval-engine modules remain
deferred; approval/replay **object** schemas live in this module for the data
slice only.

### Q-65-2 — UAII operation versus external API

**Decision:** Keep UAII as the sole protocol entry point. **Do not** extend
`get_payment_receipt` for Foundation 64 signed receipts. A future **named UAII
operation** (under separate authorization) is required before signed-receipt
protocol traffic is accepted; Foundation 66 adds **no** UAII operation and
**no** REST/MCP/SDK/CLI/adapter endpoint.

**Evidence:**

- `coin/uaii_reference_core.py` `OPERATIONS` and `_op_get_payment_receipt` emit
  profile `l28-uaii-payment-receipt/v0.1` (Foundation 56 unsigned citation
  receipt).
- Foundation 64 §6.5: F56 unsigned payment receipt is distinct; adapters MUST
  NOT treat it as an F64 signed receipt.
- Foundation 65 map labels F56 receipt **EXISTING** / distinct and F64 signed
  receipt **MISSING**.

Extending `get_payment_receipt` would create a dual-profile collision inside one
operation. An external-only non-UAII API would create a second protocol
processor. Both are rejected.

### Q-65-3 — Replay and approval transport

**Decision:** Treat `ApprovalDecision` (21 fields + nested §8.5 object) and
`F64SigningReplayKeyMaterial` (13 fields) as **explicit request/response data
objects** governed by Foundation 64. External systems MAY supply already-evaluated
evidence; UAII (when later wired) owns protocol interpretation and fail-closed
results. Foundation 66 validates object schemas and can compute the
deterministic `replay_key` digest bytes only.

**Forbidden now and later as F64 authorities:**

- M2M canonicalization for F64 material
- Promoting `coin.m2m_replay_registry.ReplayRegistry` into F64 ownership
- Creating a Foundation 64 database, persistent replay store, or approval service

**Future boundary:** external state may prove uniqueness / supply approval
objects; protocol fail-closed codes (including missing capability →
`replay_detected`) remain under the F64/UAII contract, not under M2M store
semantics.

## 3. Implemented slice

| Capability | Status |
|---|---|
| Exact 24-field unsigned facts schema | Implemented |
| Exact 27-field signed facts schema (final + empty-id intermediate) | Implemented |
| Exact 21-field `ApprovalDecision` + nested 10-field cumulative object | Implemented |
| Exact 13-field replay-material schema | Implemented |
| Missing / unexpected field rejection; exact types; null rules | Implemented |
| Deterministic ordering; CanonUaii canonical bytes | Implemented |
| `signable_bytes` / `signed_payload_digest` construction | Implemented (hash only) |
| Non-circular `receipt_id` material construction | Implemented (hash only) |
| `replay_key` digest material construction | Implemented (hash only; no store) |

Primary symbols in `coin/uaii_signed_receipt.py`:

- `validate_unsigned_facts`, `validate_signed_facts`,
  `validate_signed_facts_empty_receipt_id`
- `validate_approval_decision`, `validate_replay_key_material`
- `approved_canonical_payload`, `build_signable_bytes`,
  `compute_signed_payload_digest`
- `build_signed_facts_empty_id`, `compute_receipt_id`, `compute_replay_key`,
  `unsigned_facts_from_signed`
- `F64ReceiptSchemaError`

## 4. Explicitly deferred (not in Foundation 66)

- Key generation; signing; signature verification; signer selection
- Status-transition enforcement beyond enum membership
- Nonce/replay **state**, approval **execution**, spending controls
- Transaction submission; settlement; ledger mutation
- UAII operation registration; adapters; networking; services; testnets
- Wiring into `process_uaii_request`

## 5. Future integration boundary

Later authorized foundations may:

1. Add a named UAII operation that accepts/returns F64 objects validated by this
   module.
2. Add an isolated signer module that signs `signable_bytes` only after an
   approved `ApprovalDecision`.
3. Call an **external** replay/approval capability, mapping absence to exact
   `replay_detected`, without owning durable F64 state.

They MUST NOT bypass `canon_uaii`, `process_uaii_request`, or
`validate_transaction` authorities.

## 6. Invariants (this milestone)

| Flag | Value |
|---|---|
| `execution_authorized` | `false` |
| `signing_authorized` | `false` |
| `spend_authorized` | `false` |
| `settlement_authorized` | `false` |
| `ledger_mutated` | `false` |
| `private_material_exposed` | `false` |
| `runtime_activated` | `false` |

## 7. Tests executed

| Suite | Result |
|---|---|
| `tests/test_uaii_signed_receipt.py` | 27 passed |
| `tests/test_uaii_reference_core.py` + `tests/test_uaii_resource_limits.py` | 45 passed (combined with F66: 72) |
| `tests/test_protocol_conformance.py` | 42 passed |
| Protected economics constants (`tx_validation` hard cap / emission / mined / halving / rewards / heights) | unchanged |

## 8. Document history

| Version | Change |
|---|---|
| 0.1 | Resolve Q-65-1..3; first isolated pure data-contract slice |
