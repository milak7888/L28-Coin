# Foundation 72 — Signed-Receipt Acceptance Transition Proposal

- **Status:** implemented (pure inert proposal; never applied)
- **Baseline:** `b293de36dd2d83b68c76ce121cf9dfb8765eba0d` (Foundation 71 on main)
- **Branch:** `foundation72-signed-receipt-acceptance-transition-proposal`
- **Normative parents:** Foundation 64; Foundation 66–71

## 1. Normative evidence and proposal vocabulary

| Item | Value | Evidence |
|---|---|---|
| Gate | Foundation 71 `acceptance_decision == "accepted"` | F71 decision matrix |
| Replay context | Caller-supplied `accepted_receipt_ids` | F69; F64 §10.4 external store ownership |
| Prior status term | `fresh` | F69 `replay_status` |
| Resulting status term after hypothetical apply | `replayed` | F69 membership classification (not a new enum) |
| Applicability | `applicable` \| `not_applicable` | Explicit non-actionable form; mirrors UAII always-emit fields (F71 `rejection_reason=""`) |
| Transition kind | `add_accepted_receipt_id` \| `""` | Describes future external add of verified `receipt_id` only |
| Precondition token | `receipt_id_absent_from_accepted_receipt_ids` | Restates F69 fresh precondition |
| Effect token | `add_receipt_id_to_accepted_receipt_ids` | Describes proposed future membership update without performing it |
| Applied flag | `transition_applied=false` always | F64 creates no store; F71 does not record; UAII inert-proposal style (`proposed_transfer` validates, does not mutate) |

Foundation 72 does **not** invent a persistent store, lifecycle state machine, or
new acceptance authority. It serializes what an external state owner *could*
apply later.

## 2. Exact proposal schema

Field order (`ACCEPTANCE_TRANSITION_PROPOSAL_FIELDS`):

| # | Field | Applicable | Not applicable |
|---|---|---|---|
| 1 | `proposal_status` | `applicable` | `not_applicable` |
| 2 | `transition_kind` | `add_accepted_receipt_id` | `""` |
| 3 | `receipt_id` | verified F64 id | verified F64 id |
| 4 | `expected_prior_replay_status` | `fresh` | `""` |
| 5 | `proposed_resulting_replay_status` | `replayed` | `""` |
| 6 | `precondition` | `receipt_id_absent_from_accepted_receipt_ids` | `""` |
| 7 | `proposed_effect` | `add_receipt_id_to_accepted_receipt_ids` | `""` |
| 8 | `transition_applied` | `false` | `false` |
| 9 | `transition_proposed_only` | `true` | `true` |

No mutated collection, signature bytes, or private material.

## 3. Behavior matrix

| Path | Decision | Proposal |
|---|---|---|
| verified + fresh + valid | `accepted` | `applicable` add proposal for `receipt_id` |
| verified + replayed | `rejected` / `replayed` | `not_applicable` |
| verified + expired | `rejected` / `expired` | `not_applicable` |
| verified + replayed + expired | `rejected` / `replayed` (F71 precedence) | `not_applicable` |
| schema/crypto failure | existing error | no decision; no proposal |

## 4. Pure function and UAII integration

### Symbols (`coin/uaii_signed_receipt.py`)

- `ACCEPTANCE_TRANSITION_PROPOSAL_FIELDS`
- `acceptance_transition_proposal_from_decision`
- `propose_signed_receipt_acceptance_transition`

### Inputs (unchanged)

1. `signed_receipt`
2. `accepted_receipt_ids`
3. `verification_time`

### Composition

`propose_signed_receipt_acceptance_transition` →
`decide_signed_receipt_acceptance` (F71) →
`acceptance_transition_proposal_from_decision`.

### UAII `verify_signed_receipt`

Params and success code unchanged. Success result adds:

- nested `acceptance_transition_proposal` (after `rejection_reason`)
- top-level `transition_applied=false`
- top-level `transition_proposed_only=true`
- top-level `accepted_receipt_ids_mutated=false`

No new operation. `get_payment_receipt` unchanged.

## 5. Precedence

1. Foundation 67 verification
2. Foundation 69 replay
3. Foundation 70 expiration
4. Foundation 71 acceptance decision
5. Foundation 72 transition proposal

## 6. Propose versus apply

| Propose (this foundation) | Apply (deferred; external) |
|---|---|
| Emit deterministic proposal object | Insert `receipt_id` into a store |
| Leave `accepted_receipt_ids` unchanged | Mutate external accepted-ID set |
| `transition_applied=false` | Would set applied only under separate authority |

## 7. Implemented vs deferred

**Implemented:** pure proposal composition; UAII result wiring; accepted vs
not-applicable matrix; immutability/statelessness tests.

**Deferred:** applying the proposal; persistent stores; hard-fail UAII mapping;
settlement; adapters; runtime activation; lifecycle state machine.

## 8. Paths

| Path | Role |
|---|---|
| `coin/uaii_signed_receipt.py` | Pure proposal functions |
| `coin/uaii_reference_core.py` | Minimal existing-op result integration |
| `tests/test_uaii_signed_receipt_acceptance_transition.py` | Focused Foundation 72 suite |
| `tests/test_uaii_verify_signed_receipt.py` | Updated result key expectations |
| `tests/test_uaii_signed_receipt_acceptance.py` | UAII key-prefix expectation |
| `docs/foundation72_signed_receipt_acceptance_transition_proposal.md` | This record |

## 9. Tests executed

- `tests.test_uaii_signed_receipt_acceptance_transition`
- Foundation 66–71 signed-receipt / UAII suites
- Reference-core / protocol-conformance / protected economics

## 10. Invariants

| Flag | Value |
|---|---|
| `transition_proposed_only` | `true` |
| `transition_applied` | `false` |
| `acceptance_state_mutated` | `false` |
| `accepted_receipt_ids_mutated` | `false` |
| `receipt_recorded` | `false` |
| `persistent_state_created` | `false` |
| `system_clock_read` | `false` |
| `implicit_time_used` | `false` |
| `signing_authorized` | `false` |
| `persistent_keys_created` | `false` |
| `private_material_exposed` | `false` |
| `spend_authorized` | `false` |
| `settlement_authorized` | `false` |
| `transaction_submission_authorized` | `false` |
| `ledger_mutated` | `false` |
| `adapters_activated` | `false` |
| `runtime_activated` | `false` |
