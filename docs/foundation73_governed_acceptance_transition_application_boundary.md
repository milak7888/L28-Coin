# Foundation 73 — Governed Acceptance-Transition Application Boundary

- **Status:** implemented (pure eligibility evaluation; never authorizes or executes)
- **Baseline:** `b84008a4491e7fd5eb784c9195bf063ade752a62` (Foundation 72 on main)
- **Branch:** `foundation73-governed-acceptance-transition-application-boundary`
- **Normative parents:** Foundation 64; Foundation 66–72

## 1. Normative evidence and boundary vocabulary

| Item | Value | Evidence |
|---|---|---|
| Gate | F71 `accepted` + F72 `applicable` add proposal | F71/F72 contracts |
| Status field | `application_boundary_status` | Prefer `eligible` \| `ineligible` |
| Reason field | `application_boundary_reason` | Empty when eligible; mirrors F71 `rejection_reason=""` |
| Reason values | `""` \| `replayed` \| `expired` \| `proposal_not_applicable` \| `proposal_inconsistent` | Reuse F71 rejection tokens; bound non-applicable/inconsistent tokens |
| Authorization | `application_authorized=false` always | UAII inert flags (`execution_authorized`, `spend_authorized`, …) |
| Execution | `application_executed=false` always | F72 `transition_applied=false`; no apply authority |
| Resulting replay term | `replayed` | F72 / F69 established vocabulary |

Eligibility is **not** approval, authorization, or execution. No authority identity,
approval token, or lifecycle is introduced.

## 2. Eligibility requirements

A proposal is `eligible` only when all hold:

1. `acceptance_decision == "accepted"` and `rejection_reason == ""`
2. `proposal_status == "applicable"`
3. `transition_kind == "add_accepted_receipt_id"`
4. verified non-empty hex-64 `receipt_id`
5. `expected_prior_replay_status == "fresh"`
6. `proposed_resulting_replay_status == "replayed"`
7. F72 precondition/effect tokens exact
8. `transition_applied == false` and `transition_proposed_only == true`
9. `replay_status == "fresh"` and `expiration_status == "valid"`

Otherwise `ineligible`. Schema/crypto failures remain existing errors with no
boundary object.

## 3. Behavior matrix

| Path | Boundary |
|---|---|
| verified + accepted + applicable | `eligible` (auth/exec still false) |
| replayed | `ineligible` / reason `replayed` |
| expired | `ineligible` / reason `expired` |
| replayed + expired | `ineligible` / reason `replayed` (F71 precedence) |
| inconsistent proposal facts | `ineligible` / `proposal_inconsistent` |
| schema/crypto failure | existing error; no boundary |

## 4. Pure function and UAII contract

### Symbols (`coin/uaii_signed_receipt.py`)

- `APPLICATION_BOUNDARY_RESULT_FIELDS`
- `application_boundary_from_proposed_acceptance`
- `evaluate_signed_receipt_acceptance_transition_application_boundary`

### Inputs (unchanged)

1. `signed_receipt`
2. `accepted_receipt_ids`
3. `verification_time`

Caller-supplied `approved` / `authorized` / `application_authorized` /
`application_executed` / authority fields are **not** accepted params and fail
closed under exact param-order validation.

### UAII success additions

Nested `acceptance_transition_application_boundary` after the proposal, plus
top-level inert flags:

- `application_authorized=false`
- `application_executed=false`
- `state_mutated=false`
- `persistent_state_created=false`
- `boundary_evaluated_only=true`

## 5. Precedence

1. F67 verification
2. F69 replay
3. F70 expiration
4. F71 acceptance
5. F72 proposal
6. F73 application boundary

## 6. Eligible vs authorized vs executed

| State | Meaning in Foundation 73 |
|---|---|
| `eligible` | Structurally presentable to a *future* separately governed applicator |
| `application_authorized` | Always `false` here |
| `application_executed` | Always `false` here |

## 7. Implemented vs deferred

**Implemented:** pure boundary evaluation; UAII wiring; fail-closed inconsistent
proposal handling; rejection of unexpected authorization params.

**Deferred:** any application authority; approval issuance; persistence; apply
execution; adapters; runtime activation.

## 8. Paths

| Path | Role |
|---|---|
| `coin/uaii_signed_receipt.py` | Pure boundary functions |
| `coin/uaii_reference_core.py` | Minimal `verify_signed_receipt` result integration |
| `tests/test_uaii_signed_receipt_application_boundary.py` | Focused Foundation 73 suite |
| `tests/test_uaii_verify_signed_receipt.py` | Updated result keys |
| `tests/test_uaii_signed_receipt_acceptance.py` | UAII key-prefix expectation |
| `docs/foundation73_governed_acceptance_transition_application_boundary.md` | This record |

## 9. Tests executed

- `tests.test_uaii_signed_receipt_application_boundary`
- Foundation 66–72 receipt / UAII suites
- Reference-core / protocol-conformance / protected economics

## 10. Invariants

| Flag | Value |
|---|---|
| `boundary_evaluated_only` | `true` |
| `application_authorized` | `false` |
| `application_executed` | `false` |
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
