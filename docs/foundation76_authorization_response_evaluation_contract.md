# Foundation 76 — Authorization-Response Evaluation Contract

- **Status:** implemented (pure caller-supplied response evaluation; never grants)
- **Baseline:** `4a26043f7e249395dfbd5c36c83baf5d0dee1857` (Foundation 75 on main)
- **Branch:** `foundation76-authorization-response-evaluation-contract`
- **Normative parents:** Foundation 64; Foundation 66–75

## 1. Normative evidence and caller-supplied schema

| Item | Value | Evidence |
|---|---|---|
| Optional object | empty `{}` = not supplied | F74 empty-object convention |
| Response id | 64 lowercase hex | Same public-id style as F64/F74 `approval_id` |
| Decision | `authorized` \| `denied` | Bounded enum parallel to F74 `approved`/`rejected` |
| Scope | sole supported `add_accepted_receipt_id` | F72–F75 contract |
| Binding fields | receipt id, transition kind, approval id | Must match F75 proposal |

Exact evidence field order (`AUTHORIZATION_RESPONSE_EVIDENCE_FIELDS`):

1. `authorization_response_id`
2. `authorization_request_receipt_id`
3. `authorization_request_transition_kind`
4. `authorization_request_approval_id`
5. `authorization_decision`
6. `authorization_scope`

No authority identity, credentials, signatures, tokens, or execution fields.

## 2. Evaluation vocabulary

| Field | Values |
|---|---|
| `authorization_response_evaluation_status` | `satisfied` \| `not_satisfied` \| `not_supplied` |
| `authorization_response_evaluation_reason` | `""` \| `authorization_response_not_supplied` \| `authorization_request_not_proposed` \| `authorization_denied` \| `receipt_id_mismatch` \| `transition_kind_mismatch` \| `approval_id_mismatch` \| `authorization_scope_mismatch` \| `authorization_response_inconsistent` |
| `authorization_response_id` | validated id or `""` |
| Issued/granted/active/applied flags | always `false` |

`satisfied` means supplied response evidence is internally consistent with a
`proposed` F75 object — **not** an authorization grant or activation.

## 3. Behavior matrix

| Case | Status / reason |
|---|---|
| F75 proposed + matching `authorized` | `satisfied` / `""` |
| F75 proposed + `denied` | `not_satisfied` / `authorization_denied` |
| Empty evidence `{}` | `not_supplied` / `authorization_response_not_supplied` |
| ID/kind/scope mismatch | corresponding mismatch reason |
| F75 `not_proposed` | `not_satisfied` / `authorization_request_not_proposed` |
| Malformed evidence | `schema_invalid` (raise) |
| Crypto/schema receipt failure | existing error; no evaluation |

## 4. Pure function and UAII integration

### Symbols (`coin/uaii_signed_receipt.py`)

- `AUTHORIZATION_RESPONSE_EVIDENCE_FIELDS`
- `AUTHORIZATION_RESPONSE_EVALUATION_FIELDS`
- `validate_authorization_response_evidence`
- `authorization_response_evaluation_from_request_proposal`
- `evaluate_signed_receipt_authorization_response`

### Request params (exact order)

1. `signed_receipt`
2. `accepted_receipt_ids`
3. `verification_time`
4. `governance_approval_evidence`
5. `authorization_response_evidence`

### Success result

Nested `authorization_response_evaluation` after the F75 proposal, plus
top-level inert flags `caller_supplied_authorization_response_evaluated_only`,
`authorization_response_issued`, `authorization_active`.

## 5. Precedence

F67 → F69 → F70 → F71 → F72 → F73 → F74 → F75 → F76

Caller response evidence cannot override an F75 `not_proposed` outcome.

## 6. Distinction

| Concept | Foundation 76 meaning |
|---|---|
| F75 `proposed` | Inert request description |
| Caller response evidence | Explicit public fields only |
| `satisfied` | Consistency check passed |
| Issued / granted / active / applied | Always false; deferred |

## 7. Implemented vs deferred

**Implemented:** optional response evidence param; pure evaluation; UAII wiring;
fail-closed mismatch/schema paths; inert flags.

**Deferred:** authorization issuance/activation, request submission, apply
execution, persistence, adapters, runtime activation, authority interfaces.

## 8. Paths

| Path | Role |
|---|---|
| `coin/uaii_signed_receipt.py` | Pure evaluation |
| `coin/uaii_reference_core.py` | Param/result integration |
| `tests/test_uaii_signed_receipt_authorization_response.py` | Focused Foundation 76 suite |
| Existing UAII receipt tests | Updated 5th-param helpers / result keys |
| `docs/foundation76_authorization_response_evaluation_contract.md` | This record |

## 9. Tests executed

- `tests.test_uaii_signed_receipt_authorization_response`
- Foundation 66–75 receipt / UAII suites
- Reference-core / protocol-conformance / protected economics

## 10. Invariants

| Flag | Value |
|---|---|
| `caller_supplied_authorization_response_evaluated_only` | `true` |
| `authorization_response_issued` | `false` |
| `authorization_requested` | `false` |
| `authorization_submitted` | `false` |
| `authorization_issued` | `false` |
| `authorization_granted` | `false` |
| `authorization_active` | `false` |
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
