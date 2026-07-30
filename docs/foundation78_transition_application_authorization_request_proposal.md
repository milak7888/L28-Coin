# Foundation 78 — Transition-Application Authorization Request Proposal

- **Status:** implemented (pure inert solicitation proposal; never submits or grants)
- **Baseline:** `eabd8746c318d79b64546fb2bb31787725f942cd` (Foundation 77 on main)
- **Branch:** `foundation78-transition-application-authorization-request-proposal`
- **Normative parents:** Foundation 64; Foundation 66–77

## 1. Normative derivation and proposal vocabulary

| Item | Value | Evidence |
|---|---|---|
| Nested result | `transition_application_authorization_request_proposal` | Continues F72–F77 nested result style |
| Status | `proposed` \| `not_proposed` | Parallel to F75 request-proposal status |
| Derivation | F77 eligibility object only | No new caller-supplied fields |
| Scope | sole `add_accepted_receipt_id` | `SUPPORTED_GOVERNANCE_APPROVAL_SCOPE` (F74–F77) |

Exact proposal field order
(`TRANSITION_APPLICATION_AUTHORIZATION_REQUEST_PROPOSAL_FIELDS`):

1. `transition_application_authorization_request_status`
2. `transition_application_authorization_request_reason`
3. `receipt_id`
4. `transition_kind`
5. `approval_id`
6. `authorization_response_id`
7. `authorization_scope`
8. `application_authorization_requested`
9. `application_authorization_submitted`
10. `authorization_issued`
11. `authorization_granted`
12. `authorization_active`
13. `application_authorized`
14. `application_executed`
15. `transition_applied`
16. `state_mutated`
17. `persistent_state_created`

Reason codes:

| Reason | When |
|---|---|
| `""` | Proposed |
| `application_authorization_not_eligible` | F77 not eligible |
| `receipt_id_missing` | Empty/noncanonical receipt id |
| `transition_kind_mismatch` | Kind ≠ `add_accepted_receipt_id` |
| `approval_id_missing` | Empty/noncanonical approval id |
| `authorization_response_id_missing` | Empty/noncanonical response id |
| `application_authorization_request_inconsistent` | Inert-flag / consistency failure |

`proposed` means a future separately governed authority *could* be asked — **not**
submission, issuance, grant, activation, application, or execution.

## 2. Prerequisites

All required for `proposed`:

- F77 status = `eligible` with empty reason
- Non-empty canonical `receipt_id`, `approval_id`, `authorization_response_id`
- `transition_kind` = `add_accepted_receipt_id`
- `authorization_scope` = `add_accepted_receipt_id`
- Every authorization/application/execution/mutation/persistence flag remains `false`

Earlier F72–F76 failures surface as F77 `not_eligible` and therefore F78
`not_proposed` / `application_authorization_not_eligible`.

## 3. Behavior matrix

| Case | Status / reason |
|---|---|
| F77 eligible + consistent ids/flags | `proposed` / `""` |
| F77 not eligible | `not_proposed` / `application_authorization_not_eligible` |
| F76/F75/F74/F73/F72 failure | `not_proposed` via F77 gate |
| Missing receipt/approval/response id | corresponding missing reason |
| Wrong transition kind | `transition_kind_mismatch` |
| Inconsistent inert flags | `application_authorization_request_inconsistent` |
| Replayed / expired | F71 precedence; F78 not proposed |
| Crypto/schema receipt failure | existing error; no F67–F78 result |

## 4. Pure function and UAII integration

### Symbols (`coin/uaii_signed_receipt.py`)

- `TRANSITION_APPLICATION_AUTHORIZATION_REQUEST_PROPOSAL_FIELDS`
- `transition_application_authorization_request_proposal_from_eligibility`
- `propose_signed_receipt_transition_application_authorization_request`

### Request params

Unchanged (exact F76–F77 order):

1. `signed_receipt`
2. `accepted_receipt_ids`
3. `verification_time`
4. `governance_approval_evidence`
5. `authorization_response_evidence`

### Success result

Nested `transition_application_authorization_request_proposal` after the F77
eligibility object, plus top-level inert flags
`application_authorization_request_proposed_only` and
`application_authorization_submitted`.

## 5. Precedence

F67 → F69 → F70 → F71 → F72 → F73 → F74 → F75 → F76 → F77 → F78

Replay, expiration, and earlier-foundation gates remain unchanged. Later evidence
cannot override earlier failures.

## 6. Distinctions

| Concept | Owner | Meaning |
|---|---|---|
| Application-authorization eligibility | F77 | Inert future eligibility |
| Application-authorization request proposal | F78 | Inert future solicitation proposal |
| Submission | deferred | Never performed by F78 |
| Authorization grant | deferred | Never produced by F78 |
| Application / execution | deferred | Never performed by F78 |

## 7. Fail-closed and deferred

**Fail-closed:** missing, null, wrong-type, empty, unexpected, ambiguous,
contradictory, or noncanonical facts → `not_proposed` or existing schema/crypto
error.

**Implemented:** pure derivation; UAII result wiring; always-false inert flags.

**Deferred:** authority identity, tokens, credentials, signatures, lifecycle,
endpoints, submission mechanisms, expiry rules, policy engines, execution
interfaces, persistence, transition application.

## 8. Changed paths and symbols

| Path | Change |
|---|---|
| `coin/uaii_signed_receipt.py` | F78 proposal derivation + compose |
| `coin/uaii_reference_core.py` | Minimal `verify_signed_receipt` wiring |
| `tests/test_uaii_signed_receipt_application_authorization_request.py` | F78 focused tests |
| `tests/test_uaii_verify_signed_receipt.py` | Result-key / proposal expectations |
| `tests/test_uaii_signed_receipt_acceptance.py` | Leading result-key prefix |
| `docs/foundation78_transition_application_authorization_request_proposal.md` | This record |

## 9. Invariants

- `application_authorization_request_proposed_only=true`
- `application_authorization_requested=false`
- `application_authorization_submitted=false`
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
