# Foundation 71 — Signed-Receipt Acceptance Decision

- **Status:** implemented (pure composition of F67/F69/F70 outcomes)
- **Baseline:** `bbea83b3bc99345abde3921f090e28d20d2e008c` (Foundation 70 on main)
- **Branch:** `foundation71-signed-receipt-acceptance-decision`
- **Normative parents:** Foundation 64; Foundation 66–70

## 1. Normative decision vocabulary and evidence

| Item | Value | Evidence |
|---|---|---|
| Decision field | `acceptance_decision` | Foundation 71 composition; informational only |
| Vocabulary | `accepted` \| `rejected` | Prefer accepted/rejected; F64 uses similar reject language for verification outcomes (`verification_status` may be `rejected`); F71 does not invent a second settlement vocabulary |
| Public reason field | `rejection_reason` | Empty string when accepted; mirrors UAII `detail=""` convention for absent detail |
| Reason values | `""` \| `replayed` \| `expired` | Bound to existing F69/F70 classification tokens — no new protocol error codes |
| Crypto/schema failure | Existing F64/F67 fail-closed codes via UAII | No acceptance fields emitted on failure |

Foundation 71 does **not** authorize spend, settlement, transaction submission, or
ledger mutation. Acceptance is an informational verification decision only.

## 2. Exact decision matrix

| Crypto/schema | `replay_status` | `expiration_status` | `acceptance_decision` | `rejection_reason` |
|---|---|---|---|---|
| fail | — | — | *(not emitted)* | *(not emitted)* |
| verified | `fresh` | `valid` | `accepted` | `""` |
| verified | `replayed` | `valid` | `rejected` | `replayed` |
| verified | `fresh` | `expired` | `rejected` | `expired` |
| verified | `replayed` | `expired` | `rejected` | `replayed` |

## 3. Pure function and UAII result contract

### Symbols (`coin/uaii_signed_receipt.py`)

- `acceptance_decision_from_classifications`
- `decide_signed_receipt_acceptance`

### Inputs (exact)

1. `signed_receipt` — signed facts object
2. `accepted_receipt_ids` — caller-supplied list (Foundation 69)
3. `verification_time` — caller-supplied Unix seconds (Foundation 70)

### Composition path

`decide_signed_receipt_acceptance` calls
`classify_signed_receipt_replay_and_expiration` (F67 → F69 → F70), then
`acceptance_decision_from_classifications`. It does not reimplement schema,
canonicalization, Ed25519, replay membership, or expiration arithmetic.

### UAII `verify_signed_receipt`

- Operation name, params order, success code (`signed_receipt_verified`), and
  envelope behavior remain Foundation 68–70 exact.
- Success result additions (after `expiration_status`):

| Field | Values |
|---|---|
| `acceptance_decision` | `accepted` \| `rejected` |
| `rejection_reason` | `""` \| `replayed` \| `expired` |

No new UAII operation. `get_payment_receipt` is unchanged.

## 4. Precedence

1. Foundation 67 cryptographic / integrity verification (or schema errors).
2. Foundation 69 replay classification (`replay_status`).
3. Foundation 70 expiration classification (`expiration_status`).
4. Foundation 71 acceptance decision (`acceptance_decision` / `rejection_reason`).

When both replayed and expired: reason is `replayed` (replay before expiration).

## 5. Rejection reason behavior

- Emitted only on successful cryptographic verification paths that produce a
  success envelope.
- When `acceptance_decision == "accepted"`, `rejection_reason` is exactly `""`.
- When both reject conditions apply, only the higher-precedence reason is exposed
  (`replayed`); `expiration_status` remains independently visible as `expired`.

## 6. Informational-only acceptance boundary

`acceptance_decision == "accepted"` means the receipt verified cryptographically,
was classified `fresh`, and was classified `valid` under the caller-supplied time.
It does **not**:

- record the receipt into `accepted_receipt_ids`;
- authorize signing, spend, settlement, or transaction submission;
- mutate ledger or persistent state;
- activate adapters or runtime services.

## 7. Implemented vs deferred

**Implemented:** pure acceptance composition; UAII result fields; four-case matrix;
replayed+expired precedence; fail-closed crypto/schema paths without acceptance
fields.

**Deferred:** hard-fail mapping of rejection → UAII `ok=false` with F64 codes
(`replay_detected` / `expired`); persistent accept stores; approval execution;
settlement; adapters; runtime activation.

## 8. Paths

| Path | Role |
|---|---|
| `coin/uaii_signed_receipt.py` | Pure acceptance composition |
| `coin/uaii_reference_core.py` | Minimal existing-op result integration |
| `tests/test_uaii_signed_receipt_acceptance.py` | Focused Foundation 71 suite |
| `tests/test_uaii_verify_signed_receipt.py` | Updated result key expectations |
| `docs/foundation71_signed_receipt_acceptance_decision.md` | This record |

## 9. Tests executed

- `tests.test_uaii_signed_receipt_acceptance`
- Foundation 66–70 receipt / UAII suites
- Capability discovery / reference-core / protocol-conformance / protected economics

## 10. Invariants

| Flag | Value |
|---|---|
| `acceptance_state_mutated` | `false` |
| `receipt_recorded` | `false` |
| `system_clock_read` | `false` |
| `implicit_time_used` | `false` |
| `persistent_replay_storage_created` | `false` |
| `persistent_expiration_state_created` | `false` |
| `signing_authorized` | `false` |
| `persistent_keys_created` | `false` |
| `private_material_exposed` | `false` |
| `spend_authorized` | `false` |
| `settlement_authorized` | `false` |
| `transaction_submission_authorized` | `false` |
| `ledger_mutated` | `false` |
| `adapters_activated` | `false` |
| `runtime_activated` | `false` |
