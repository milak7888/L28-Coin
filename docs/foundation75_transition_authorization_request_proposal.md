# Foundation 75 — Transition-Authorization Request Proposal

- **Status:** implemented (pure inert proposal; never requested/granted/submitted)
- **Baseline:** `af1489c88ca058752f4c5f96aa3a8789ce9a1847` (Foundation 74 on main)
- **Branch:** `foundation75-transition-authorization-request-proposal`
- **Normative parents:** Foundation 64; Foundation 66–74

## 1. Normative evidence and vocabulary

| Item | Value | Evidence |
|---|---|---|
| Nested result | `transition_authorization_request_proposal` | Continues F72 nested proposal / F73–F74 nested evaluation style |
| Status | `proposed` \| `not_proposed` | Mirrors F72 applicable/not_applicable and F75 preferred vocabulary |
| Reason empty when proposed | `""` | F71/F74 empty-reason convention |
| Public fields when proposed | `receipt_id`, `transition_kind`, `approval_id` | Verified F64 id; F72 kind; F74 public approval id |
| Transition kind | `add_accepted_receipt_id` | F72 |
| No new request params | reuse F74 `governance_approval_evidence` | User: no additional caller authorization fields |

## 2. Derivation requirements

`proposed` only when all hold:

1. F71 `acceptance_decision == "accepted"`
2. F72 `proposal_status == "applicable"` and kind `add_accepted_receipt_id`
3. F73 boundary `eligible`
4. F74 status `satisfied` and reason `""`
5. non-empty validated hex-64 `approval_id`
6. inert flags remain false (`approval_granted`, `application_authorized`,
   `application_executed`, `transition_applied`, mutation/persistence)

Otherwise `not_proposed` with a deterministic reason.

## 3. Behavior matrix

| Case | Proposal |
|---|---|
| Eligible path + F74 satisfied | `proposed` / `""` (auth flags still false) |
| F74 not_supplied / not_satisfied | `not_proposed` / `governance_approval_not_satisfied` |
| Acceptance rejected (replay/expired) | `not_proposed` / `acceptance_not_accepted` |
| Inconsistent inert flags / ids | `not_proposed` / `proposal_inconsistent` or `approval_id_missing` |
| Crypto/schema failure | existing error; no F75 object |

## 4. Pure function and UAII contract

### Symbols (`coin/uaii_signed_receipt.py`)

- `TRANSITION_AUTHORIZATION_REQUEST_PROPOSAL_FIELDS`
- `transition_authorization_request_proposal_from_evaluation`
- `propose_signed_receipt_transition_authorization_request`

### Request params

Unchanged from Foundation 74 (four params). No new authorization/request fields.

### Success result

Nested `transition_authorization_request_proposal` after
`governance_approval_evaluation`, plus top-level inert flags:
`authorization_request_proposed_only`, `authorization_requested`,
`authorization_submitted`, `authorization_issued` (all false except
`authorization_request_proposed_only=true`).

## 5. Precedence

F67 → F69 → F70 → F71 → F72 → F73 → F74 → F75

## 6. Distinction

| Term | Meaning here |
|---|---|
| `proposed` | Serializable description for a *future* authority |
| requested / submitted / granted / authorized / executed / applied | Always false; deferred |

## 7. Implemented vs deferred

**Implemented:** pure derivation; UAII result wiring; fail-closed not_proposed paths.

**Deferred:** actual authorization request submission, grant, apply, persistence,
adapters, runtime activation, authority interfaces.

## 8. Paths

| Path | Role |
|---|---|
| `coin/uaii_signed_receipt.py` | Pure F75 proposal |
| `coin/uaii_reference_core.py` | Minimal result integration |
| `tests/test_uaii_signed_receipt_authorization_request.py` | Focused Foundation 75 suite |
| Existing verify/acceptance tests | Result-key expectations |
| `docs/foundation75_transition_authorization_request_proposal.md` | This record |

## 9. Tests executed

- `tests.test_uaii_signed_receipt_authorization_request`
- Foundation 66–74 receipt / UAII suites
- Reference-core / protocol-conformance / protected economics

## 10. Invariants

| Flag | Value |
|---|---|
| `authorization_request_proposed_only` | `true` |
| `authorization_requested` | `false` |
| `authorization_submitted` | `false` |
| `authorization_issued` | `false` |
| `authorization_granted` | `false` |
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
