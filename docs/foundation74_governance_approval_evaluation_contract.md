# Foundation 74 — Governance-Approval Evaluation Contract

- **Status:** implemented (pure caller-supplied evidence evaluation; never grants)
- **Baseline:** `11409c37c40c2ad7c2c163e91b28c4c0229a0350` (Foundation 73 on main)
- **Branch:** `foundation74-governance-approval-evaluation-contract`
- **Normative parents:** Foundation 64; Foundation 66–73

## 1. Normative evidence and caller-supplied schema

| Item | Value | Evidence |
|---|---|---|
| Optional object | empty `{}` = not supplied | UAII `proposed_transfer` empty-object convention (F56) |
| `approval_id` | 64 lowercase hex | F64 `ApprovalDecision.approval_id` |
| `approval_decision` | `approved` \| `rejected` | F64 §8.1 `decision` enum |
| `approval_transition_kind` | must equal F72 `add_accepted_receipt_id` | F72 proposal |
| `approval_scope` | sole supported: `add_accepted_receipt_id` | Same F72 kind; no invented governance role |
| Subject | `approval_subject_receipt_id` = verified F64 `receipt_id` | F64 / F73 boundary |

Exact evidence field order (`GOVERNANCE_APPROVAL_EVIDENCE_FIELDS`):

1. `approval_id`
2. `approval_subject_receipt_id`
3. `approval_transition_kind`
4. `approval_decision`
5. `approval_scope`

No authority identity, credentials, signatures, tokens, or execution fields.

## 2. Evaluation vocabulary

| Field | Values |
|---|---|
| `governance_approval_evaluation_status` | `satisfied` \| `not_satisfied` \| `not_supplied` |
| `governance_approval_evaluation_reason` | `""` \| `approval_not_supplied` \| `boundary_ineligible` \| `approval_rejected` \| `receipt_id_mismatch` \| `transition_kind_mismatch` \| `approval_scope_mismatch` \| `approval_inconsistent` |
| `approval_id` | validated id or `""` |
| `approval_granted` | always `false` |
| `application_authorized` | always `false` |
| `application_executed` | always `false` |
| `transition_applied` | always `false` |
| `state_mutated` | always `false` |
| `persistent_state_created` | always `false` |

`satisfied` means supplied evidence is internally consistent with an eligible
boundary — **not** an authorization grant.

## 3. Behavior matrix

| Case | Status / reason |
|---|---|
| Eligible + matching `approved` | `satisfied` / `""` |
| Eligible + `rejected` | `not_satisfied` / `approval_rejected` |
| Eligible + receipt/kind/scope mismatch | corresponding mismatch reason |
| Ineligible + any evidence | `not_satisfied` / `boundary_ineligible` |
| Empty evidence `{}` | `not_supplied` / `approval_not_supplied` |
| Malformed evidence | `schema_invalid` (raise) |
| Crypto/schema receipt failure | existing error; no evaluation |

## 4. Pure function and UAII integration

### Symbols (`coin/uaii_signed_receipt.py`)

- `SUPPORTED_GOVERNANCE_APPROVAL_SCOPE`
- `GOVERNANCE_APPROVAL_EVIDENCE_FIELDS`
- `GOVERNANCE_APPROVAL_EVALUATION_FIELDS`
- `validate_governance_approval_evidence`
- `governance_approval_evaluation_from_boundary`
- `evaluate_signed_receipt_governance_approval`

### Request params (exact order)

1. `signed_receipt`
2. `accepted_receipt_ids`
3. `verification_time`
4. `governance_approval_evidence`

### Success result

Nested `governance_approval_evaluation` after the F73 boundary object, plus
top-level inert flags `approval_granted`, `approval_issued`,
`authorization_granted`, `caller_supplied_approval_evaluated_only`.

## 5. Precedence

1. F67 verification
2. F69 replay
3. F70 expiration
4. F71 acceptance
5. F72 proposal
6. F73 application boundary
7. F74 governance-approval evaluation

When evidence is present: `boundary_ineligible` precedes mismatch/rejection
reasons (caller evidence cannot override F73).

## 6. Evidence vs satisfied vs authorized vs executed

| Concept | Foundation 74 meaning |
|---|---|
| Caller evidence | Explicit public fields only |
| `satisfied` | Consistency check passed |
| Authorization / execution / apply | Always false; deferred |

## 7. Implemented vs deferred

**Implemented:** optional evidence param; pure evaluation; UAII wiring;
fail-closed schema/mismatch; inert flags.

**Deferred:** approval issuance, authority attestation, persistence, apply
execution, policy engines, adapters, runtime activation.

## 8. Paths

| Path | Role |
|---|---|
| `coin/uaii_signed_receipt.py` | Pure evaluation |
| `coin/uaii_reference_core.py` | Param/result integration |
| `tests/test_uaii_signed_receipt_governance_approval.py` | Focused Foundation 74 suite |
| Existing UAII receipt tests | Updated 4th-param helpers / result keys |
| `docs/foundation74_governance_approval_evaluation_contract.md` | This record |

## 9. Tests executed

- `tests.test_uaii_signed_receipt_governance_approval`
- Foundation 66–73 receipt / UAII suites
- Reference-core / protocol-conformance / protected economics

## 10. Invariants

| Flag | Value |
|---|---|
| `caller_supplied_approval_evaluated_only` | `true` |
| `approval_issued` | `false` |
| `approval_granted` | `false` |
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
