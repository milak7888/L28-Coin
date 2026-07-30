# Foundation 77 — Transition-Application Authorization Eligibility Proposal

- **Status:** implemented (pure inert eligibility proposal; never authorizes)
- **Baseline:** `23a30747a7e791f955b63ff91de6cea29c29b735` (Foundation 76 on main)
- **Branch:** `foundation77-transition-application-authorization-eligibility-proposal`
- **Normative parents:** Foundation 64; Foundation 66–76

## 1. Normative evidence and proposal vocabulary

| Item | Value | Evidence |
|---|---|---|
| Nested result | `transition_application_authorization_eligibility_proposal` | Continues F72–F76 nested result style |
| Status | `eligible` \| `not_eligible` | Parallel to F73 boundary eligibility |
| Derivation | F72–F76 result chain only | No new caller-supplied fields |
| Scope | sole `add_accepted_receipt_id` | F72–F76 contract |

Exact proposal field order
(`TRANSITION_APPLICATION_AUTHORIZATION_ELIGIBILITY_PROPOSAL_FIELDS`):

1. `transition_application_authorization_eligibility_status`
2. `transition_application_authorization_eligibility_reason`
3. `receipt_id`
4. `transition_kind`
5. `approval_id`
6. `authorization_response_id`
7. `application_authorization_proposed`
8. `application_authorization_requested`
9. `authorization_issued`
10. `authorization_granted`
11. `authorization_active`
12. `application_authorized`
13. `application_executed`
14. `transition_applied`
15. `state_mutated`
16. `persistent_state_created`

Reason codes:

| Reason | When |
|---|---|
| `""` | Eligible |
| `acceptance_not_accepted` | F71 not `accepted` |
| `transition_not_applicable` | F72 not applicable / wrong kind |
| `boundary_ineligible` | F73 not eligible |
| `governance_approval_not_satisfied` | F74 not satisfied |
| `authorization_request_not_proposed` | F75 not proposed |
| `authorization_response_not_satisfied` | F76 not satisfied / not supplied |
| `authorization_response_id_missing` | Satisfied path but empty response id |
| `eligibility_inconsistent` | Cross-foundation / inert-flag inconsistency |

`eligible` means a future separately governed application-authorization decision
*could* be considered — **not** a proposal submission, request, grant, activation,
application, or execution.

## 2. Derivation prerequisites

All required for `eligible`:

- F71 `acceptance_decision` = `accepted`
- F72 `proposal_status` = `applicable`; kind = `add_accepted_receipt_id`
- F73 `application_boundary_status` = `eligible`
- F74 evaluation status = `satisfied` with empty reason
- F75 proposal status = `proposed`
- F76 evaluation status = `satisfied` with empty reason
- Non-empty canonical `receipt_id`, `approval_id`, `authorization_response_id`
- Cross-foundation ids/kind consistent; every auth/application/execution/mutation
  flag remains `false`

F76 `authorized` evidence remains caller-supplied evidence only; F77 never treats
it as issued, granted, active, or application authorization.

## 3. Behavior matrix

| Case | Status / reason |
|---|---|
| Satisfied F76 + every prior prerequisite | `eligible` / `""` |
| F76 not_satisfied / not_supplied | `not_eligible` / `authorization_response_not_satisfied` |
| F75 not_proposed | `not_eligible` / `authorization_request_not_proposed` |
| F74 not satisfied/supplied | `not_eligible` / `governance_approval_not_satisfied` or prior |
| F73 ineligible / F72 non-applicable | corresponding reason |
| Replayed / expired | F71 rejection precedence; F77 `acceptance_not_accepted` |
| Inconsistent inert flags / ids | `eligibility_inconsistent` or id-missing |
| Crypto/schema receipt failure | existing error; no F67–F77 result |

## 4. Pure function and UAII integration

### Symbols (`coin/uaii_signed_receipt.py`)

- `TRANSITION_APPLICATION_AUTHORIZATION_ELIGIBILITY_PROPOSAL_FIELDS`
- `transition_application_authorization_eligibility_proposal_from_evaluation`
- `propose_signed_receipt_transition_application_authorization_eligibility`

### Request params

Unchanged (exact F76 order):

1. `signed_receipt`
2. `accepted_receipt_ids`
3. `verification_time`
4. `governance_approval_evidence`
5. `authorization_response_evidence`

### Success result

Nested `transition_application_authorization_eligibility_proposal` after the F76
evaluation, plus top-level inert flags
`transition_application_authorization_eligibility_proposed_only`,
`application_authorization_proposed`, `application_authorization_requested`.

## 5. Precedence

F67 → F69 → F70 → F71 → F72 → F73 → F74 → F75 → F76 → F77

Rejection, replay, and expiration precedence remain unchanged. F76 response
evidence cannot override an F75 `not_proposed` outcome, and F77 cannot become
`eligible` when any prior gate fails.

## 6. Distinctions

| Concept | Owner | Meaning |
|---|---|---|
| Acceptance | F71 | Informational accept/reject |
| Transition proposal | F72 | Inert applicable proposal |
| Boundary eligibility | F73 | Structural application-boundary eligibility |
| Governance evaluation | F74 | Caller approval evidence consistency |
| Authorization-request proposal | F75 | Inert future-request proposal |
| Authorization-response evaluation | F76 | Caller response evidence consistency |
| Application-authorization eligibility | F77 | Inert future app-auth eligibility |
| Authorization grant / application / execution | deferred | Never produced by F77 |

## 7. Fail-closed and deferred

**Fail-closed:** missing, null, wrong-type, empty, unexpected, duplicate,
ambiguous, contradictory, or noncanonical facts → `not_eligible` or existing
schema/crypto error.

**Implemented:** pure derivation; UAII result wiring; always-false inert flags.

**Deferred:** authority identity, tokens, signatures, lifecycle, endpoints,
policy engines, expiry rules, execution interfaces, persistence, transition
application.

## 8. Changed paths and symbols

| Path | Change |
|---|---|
| `coin/uaii_signed_receipt.py` | F77 proposal derivation + compose |
| `coin/uaii_reference_core.py` | Minimal `verify_signed_receipt` wiring |
| `tests/test_uaii_signed_receipt_authorization_eligibility.py` | F77 focused tests |
| `tests/test_uaii_verify_signed_receipt.py` | Result-key / eligibility expectations |
| `tests/test_uaii_signed_receipt_acceptance.py` | Leading result-key prefix |
| `docs/foundation77_transition_application_authorization_eligibility_proposal.md` | This record |

## 9. Invariants

- `transition_application_authorization_eligibility_proposed_only=true`
- `application_authorization_proposed=false`
- `application_authorization_requested=false`
- `authorization_requested=false`
- `authorization_submitted=false`
- `authorization_issued=false`
- `authorization_granted=false`
- `authorization_active=false`
- `application_authorized=false`
- `application_executed=false`
- `transition_applied=false`
- `acceptance_state_mutated=false`
- `accepted_receipt_ids_mutated=false`
- `receipt_recorded=false`
- `persistent_state_created=false`
- `system_clock_read=false`
- `implicit_time_used=false`
- `signing_authorized=false`
- `persistent_keys_created=false`
- `private_material_exposed=false`
- `spend_authorized=false`
- `settlement_authorized=false`
- `transaction_submission_authorized=false`
- `ledger_mutated=false`
- `adapters_activated=false`
- `runtime_activated=false`
