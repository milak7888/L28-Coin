# Foundation 70 — Signed-Receipt Expiration Verification

- **Status:** implemented (pure caller-supplied verification-time classification)
- **Baseline:** `b36afbfaa22ef6c36c173071025cf844fe45a532` (Foundation 69 on main)
- **Branch:** `foundation70-signed-receipt-expiration-verification`
- **Normative parents:** Foundation 64; Foundation 57 skew; Foundation 66–69

## 1. Foundation 64 evidence

| Fact | Normative source |
|---|---|
| Expiration field | `expires_at` integer Unix seconds; MUST be `> created_at` (F64 §6.2) |
| Timestamp representation | Exact JSON integers; not bool/string/float (F64 §3 / §6.2; F56/F57) |
| Timezone | Unix seconds are timezone-independent instants (UTC epoch) |
| Verifier step | F64 §9.1.12 — “Expiry / skew checks (Foundation 57 `300` seconds)” |
| Skew constant | `UAII_CLOCK_SKEW_TOLERANCE_SECONDS = 300` (F64 §10.5; F57) |
| Style | Envelope-style wall-clock comparison (F64 §10.5) |
| Error code (hard-fail path) | `expired` — “Past expiry under skew rules” (F64 §9.2) |

### Equality / boundary rule (locked)

Envelope-style Foundation 57 rule applied to receipt `expires_at`:

```text
expired  iff  verification_time > expires_at + 300
valid    otherwise
```

Therefore:

- `verification_time == expires_at` → **valid**
- `verification_time == expires_at + 300` → **valid**
- `verification_time == expires_at + 301` → **expired**

No additional grace period beyond the normative 300-second skew is introduced.

## 2. Pure functions and UAII contract

### Symbols (`coin/uaii_signed_receipt.py`)

- `validate_verification_time`
- `expiration_status_for_verified_facts`
- `classify_signed_receipt_expiration`
- `classify_signed_receipt_replay_and_expiration`
- `RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS = 300`
- `MAX_UNIX_SECONDS = 9007199254740991`

### Canonical `verification_time`

Exact Python `int` (not `bool`) Unix seconds in `[0, MAX_UNIX_SECONDS]`.

### UAII `verify_signed_receipt` params (exact order)

| # | Field |
|---|---|
| 1 | `signed_receipt` |
| 2 | `accepted_receipt_ids` |
| 3 | `verification_time` |

### Success result additions

| Field | Values |
|---|---|
| `expiration_status` | `valid` \| `expired` |
| `expires_at` | from verified facts |
| `verification_time` | echoed validated caller time |

## 3. Precedence

1. Cryptographic / integrity verification (Foundation 67).
2. Replay classification (Foundation 69) against `accepted_receipt_ids`.
3. Expiration classification against explicit `verification_time`.

Malformed time fails closed with `schema_invalid` after / as part of the pure
time validator (never via implicit clock). Integrity failures always precede
expiration classification.

## 4. Caller-supplied-time boundary

- No `datetime.now`, `datetime.utcnow`, `time.time`, `date.today`, env time, or
  filesystem/network time.
- No default “now.”
- No retained or cached evaluation time.

## 5. Implemented vs deferred

**Implemented:** pure expiration classification; UAII wiring; boundary tests;
replay preserved.

**Deferred:** hard-fail mapping of `expired` → UAII `ok=false` / code `expired`
(classification only in this slice); approval expiry; quote expiry paths;
settlement; adapters; persistent state.

## 6. Invariants

| Flag | Value |
|---|---|
| `system_clock_read` | `false` |
| `implicit_time_used` | `false` |
| `persistent_expiration_state_created` | `false` |
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
| `coin/uaii_signed_receipt.py` | Pure expiration classification |
| `coin/uaii_reference_core.py` | Accept `verification_time`; return `expiration_status` |
| `tests/test_uaii_signed_receipt_expiration.py` | Focused Foundation 70 suite |
| `tests/test_uaii_verify_signed_receipt.py` | Updated params/result expectations |
| `tests/test_uaii_signed_receipt_replay.py` | Updated UAII params |
| `docs/foundation70_signed_receipt_expiration_verification.md` | This record |

## 8. Tests executed

Recorded by the Foundation 70 validation run (F70 suite, F66–F69 receipt/UAII
suites, protocol conformance / protected economics).

## 9. Document history

| Version | Change |
|---|---|
| 0.1 | Pure expiration classification with explicit verification_time |
