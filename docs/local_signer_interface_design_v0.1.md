# Canonical Local Signer Interface Design v0.1

**Foundation:** 117

**Status:** `DEFINED_DESIGN_ONLY`

**Document version:** `local-signer-interface-design/v0.1`

**Interface profile:** `l28-local-signer-interface/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Required parent:** `821b98e9d48f5dc1b7e5d1e26dd4ce803a7ac1ae`

**Branch:** `foundation117-local-signer-interface-design`

**Implementation:** none

**Runtime, signer, wallet, key, signature, RPC, network, broadcast, submission,
ledger mutation, settlement, deployment, testnet, or infrastructure
activation:** none

**Normative subordination:** This design is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md), Foundations 111–113, Foundation 116,
and the canonical Universal Access Interface v0.1. On conflict, Protocol
v1.0.0 prevails. This document defines a future public boundary only. It does
not create an executable interface, add a UAII operation, authorize a signer,
or resolve a Foundation116 security gate.

---

## 1. Purpose and scope

Foundation117 closes Foundation116 finding F116-G01 at the **design-contract
level only**. It defines one versioned, deterministic, public-only contract for
evaluating whether a proposed L28 transaction could reach the edge of a future
isolated local signer.

The only operation defined by this profile is:

`evaluate_signer_eligibility`

The operation evaluates public evidence and returns public decision evidence.
It does not invoke a signer. An eligible result means only that the supplied
public projection passed this contract's modeled gates. It is not permission to
sign, spend, submit, broadcast, mutate a ledger, settle, or activate runtime.

| Design item | Status |
|---|---|
| Interface identity, exact schemas, serialization, digests, and stable codes | `DEFINED_DESIGN_ONLY` |
| Authenticated evidence mechanisms | `GAP_REQUIRES_FUTURE_WORK` |
| Key custody and lifecycle | `GAP_REQUIRES_FUTURE_WORK` |
| Atomic replay and economic-control state | `GAP_REQUIRES_FUTURE_WORK` |
| Trusted production time | `GAP_REQUIRES_FUTURE_WORK` |
| Audit durability, service hardening, and runtime integration | `GAP_REQUIRES_FUTURE_WORK` |
| Signer implementation, invocation, runtime, or activation | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |

## 2. Authority model

### 2.1 Fixed authority order

1. L28 Protocol v1.0.0 remains the sole consensus, issuance, supply,
   canonical-height, historical-ledger, and native-settlement authority.
2. `coin.tx_validation.validate_transaction` remains the mandatory L28
   transfer/coinbase validation authority.
3. Local authorization may restrict a proposed transaction but cannot make an
   invalid transaction valid.
4. Signer eligibility may report an inactive public projection only. It cannot
   invoke a signer or confer signing authority.
5. A future signature, if separately authorized in a later milestone, would
   not itself be validation, consensus, settlement, issuance, or canonical
   height.

### 2.2 Required separations

**Authorization is not validation.** `authorization_status="allowed"` cannot
replace `validation_status="accepted"` from the mandatory delegate.

**Signer eligibility is not signer invocation.**
`eligibility_status="eligible_public_projection"` MUST coexist with
`signer_invocation_status="not_invoked"` and every non-execution flag in
Section 9 set to `false`.

A Protocol rejection, unavailable required context, missing gate, mismatched
binding, or unresolved required evidence blocks eligibility. No local policy,
operator, approval, receipt, Harness/Evals report, Bitcoin observation, or
adapter may override that result.

## 3. Relationship to UAII and public interfaces

This contract is a separate future profile. It does not modify profile
`l28-universal-ai-access-interface/v0.1` and does not add signing to UAII.

UAII continues to expose its canonical discovery, status, balance, quote,
unsigned-payment-request, validation, and receipt operations. Signing,
broadcast, and autonomous spend remain forbidden UAII v0.1 operations.

This interface MAY consume canonical public identifiers and evidence derived
from UAII quotes, unsigned payment requests, validation responses, and receipts
when exact bindings are supplied. It MUST NOT:

- reinterpret a quote or unsigned payment request as spend authority;
- treat `validate_payment` as a second validator;
- treat `verify_signed_receipt` as proof of a new payment or signer authority;
- expose secrets through UAII, adapters, prompts, logs, or hosted services; or
- let MCP, REST/OpenAPI, SDKs, Harness/Evals, or Bitcoin become signer,
  validation, settlement, or custody authorities.

No transport adapter is defined or authorized here.

## 4. Interface identity, versioning, and compatibility

| Constant | Exact value |
|---|---|
| `interface_profile` | `l28-local-signer-interface/v0.1` |
| `interface_version` | `0.1` |
| `operation` | `evaluate_signer_eligibility` |
| protocol version binding | `1.0.0` |
| asset | `L28` |
| design status | `DEFINED_DESIGN_ONLY` |

Compatibility rules:

1. A request MUST use the exact profile, version, and operation above.
2. Unknown profiles or versions fail with `interface_profile_unsupported`.
3. Unknown operations fail with `operation_unsupported`.
4. Unknown, missing, duplicate, reordered, or wrong-type properties fail with
   `schema_invalid`.
5. A field addition, removal, reorder, type change, status/code semantic change,
   digest change, or authority change requires a new interface profile. It MUST
   NOT be silently introduced into v0.1.
6. A conforming v0.1 evaluator MUST NOT negotiate down, repair input, ignore
   extensions, coerce types, or infer defaults.
7. Publication of a compatible design revision does not make the profile
   executable. Runtime requires a separately authorized implementation profile
   and completion of Foundation116 gates.

## 5. Canonical request envelope

### 5.1 Exact top-level fields

Every request contains exactly these required fields in this order:

1. `interface_profile`
2. `interface_version`
3. `operation`
4. `request_id`
5. `idempotency_key`
6. `created_at`
7. `expires_at`
8. `nonce`
9. `caller_identity_evidence`
10. `operator_authorization_evidence`
11. `authorization_evidence`
12. `economic_policy`
13. `approvals`
14. `replay_evidence`
15. `time_evidence`
16. `proposed_transaction`
17. `protocol_validation_binding`
18. `authority_assertions`
19. `non_execution`
20. `request_digest`

### 5.2 Shared scalar rules

- `request_id`, `idempotency_key`, evidence identifiers, binding identifiers,
  and digests are exactly 64 lowercase hexadecimal characters unless a schema
  below explicitly permits `""` for unavailable evidence.
- `created_at` and `expires_at` are exact JSON integer Unix seconds;
  `expires_at > created_at`.
- `nonce` is a non-empty string of at most 256 UTF-8 bytes and contains no NUL.
- Amounts and counts are exact JSON integers. Booleans are not integers.
- Identities are exact, public, non-empty strings with no normalization or case
  folding. Reserved sender identities remain subject to Protocol validation.
- No request field may contain a private key, seed, mnemonic, xprv, wallet
  secret, keystore, credential, RPC credential, production secret, or a locator
  capable of loading one.

### 5.3 `caller_identity_evidence` exact fields

1. `evidence_profile` — exact
   `l28-local-signer-caller-identity-evidence/v0.1`
2. `evidence_id`
3. `caller_id`
4. `caller_public_identity`
5. `caller_public_key_id` — public identifier only; `""` if unavailable
6. `authentication_status` — `verified`, `unverified`, or `unavailable`
7. `scope_request_id` — exact request binding
8. `issued_at`
9. `expires_at`
10. `public_evidence_only` — MUST be `true`

`authentication_status="verified"` is only a public claim in this design.
The production mechanism that can establish that status remains
`GAP_REQUIRES_FUTURE_WORK`. Until separately specified and verified,
production use MUST fail closed rather than trust this claim.

### 5.4 `operator_authorization_evidence` exact fields

1. `evidence_profile` — exact
   `l28-local-signer-operator-authorization-evidence/v0.1`
2. `evidence_id`
3. `operator_id`
4. `operator_public_identity`
5. `authentication_status` — `verified`, `unverified`, or `unavailable`
6. `decision` — `approved`, `denied`, or `unavailable`
7. `request_id`
8. `intent_id`
9. `policy_id`
10. `payer_id`
11. `payee_id`
12. `asset_id` — exact `L28`
13. `maximum_amount`
14. `created_at`
15. `expires_at`
16. `independent_security_review_id` — public identifier or `""`
17. `scope_matches`
18. `public_evidence_only` — MUST be `true`

An eligible projection requires an approved, current, exact-scope operator
claim. The authenticity, issuance, revocation, and administration of that claim
remain future security work and are not implemented here.

### 5.5 `authorization_evidence` exact fields

1. `evidence_profile` — exact
   `l28-local-signer-authorization-evidence/v0.1`
2. `authorization_id`
3. `authorization_status` — `allowed`, `denied`, `pending`, or `unavailable`
4. `intent_id`
5. `request_id`
6. `policy_id`
7. `payer_id`
8. `payee_id`
9. `asset_id` — exact `L28`
10. `amount`
11. `evaluator_id`
12. `authentication_status` — `verified`, `unverified`, or `unavailable`
13. `created_at`
14. `expires_at`
15. `public_evidence_only` — MUST be `true`

Authorization evidence binds local policy evaluation only. It cannot bind or
replace the Protocol-validation result.

### 5.6 `economic_policy` exact fields

1. `policy_profile` — exact `l28-local-signer-economic-policy/v0.1`
2. `policy_id`
3. `policy_status` — `active`, `inactive`, or `unavailable`
4. `authentication_status` — `verified`, `unverified`, or `unavailable`
5. `asset_id` — exact `L28`
6. `per_transaction_limit`
7. `cumulative_limit`
8. `prior_authorized_total`
9. `window_start`
10. `window_end`
11. `approval_threshold`
12. `authorized_approver_ids` — ordered distinct public identities
13. `operator_authorization_required` — MUST be `true`
14. `unlimited_spend_allowed` — MUST be `false`
15. `protocol_override_allowed` — MUST be `false`
16. `runtime_authorized` — MUST be `false`

Limit checks use exact integer arithmetic. An amount equal to the relevant
limit may pass locally. An amount above either limit fails closed. Missing,
inactive, unauthenticated, malformed, stale, or contradictory policy evidence
never means unlimited spend.

### 5.7 `approvals[]` exact fields

Each approval contains exactly:

1. `approval_id`
2. `approver_id`
3. `approver_public_identity`
4. `authentication_status` — `verified`, `unverified`, or `unavailable`
5. `decision` — `approved` or `denied`
6. `request_id`
7. `intent_id`
8. `policy_id`
9. `approved_amount`
10. `created_at`
11. `expires_at`
12. `public_evidence_only` — MUST be `true`

The array preserves declared order. Approver identities MUST be distinct and
MUST appear in `economic_policy.authorized_approver_ids`. Duplicate approvers
count zero additional times. The production authentication mechanism for
approvals remains unresolved.

### 5.8 `replay_evidence` exact fields

1. `evidence_profile` — exact `l28-local-signer-replay-evidence/v0.1`
2. `evidence_id`
3. `available`
4. `request_id`
5. `intent_id`
6. `idempotency_key`
7. `status` — `fresh`, `replayed`, `unavailable`, or `invalid`
8. `first_seen_at` — integer or `0` when fresh/unavailable
9. `retention_until`
10. `state_version`
11. `atomicity_evidence_id` — public identifier or `""`
12. `atomic_transition_status` — `not_implemented`, `verified`, or `unavailable`
13. `read_only` — MUST be `true` in this design

A replayed identifier rejects. Unavailable, invalid, stale, or contradictory
state blocks. This design reads a supplied projection only and performs no
atomic check-and-record transition. Production atomicity remains
`GAP_REQUIRES_FUTURE_WORK`.

### 5.9 `time_evidence` exact fields

1. `evidence_profile` — exact `l28-local-signer-time-evidence/v0.1`
2. `evidence_id`
3. `evaluation_time`
4. `source` — `caller_supplied_design_only`, `trusted_production`, or
   `unavailable`
5. `authentication_status` — `verified`, `unverified`, or `unavailable`
6. `intent_not_before`
7. `intent_expires_at`
8. `authorization_expires_at`
9. `approvals_expire_at`
10. `operator_evidence_expires_at`
11. `policy_window_start`
12. `policy_window_end`
13. `system_clock_read` — MUST be `false`
14. `network_clock_read` — MUST be `false`

Deterministic design evaluation uses supplied integer time only. This does not
select or authenticate a production clock. Trusted production-time authority,
skew, rollback, and outage policy remain `GAP_REQUIRES_FUTURE_WORK`.

### 5.10 `proposed_transaction` exact fields

1. `sender`
2. `receiver`
3. `amount`
4. `timestamp`
5. `nonce`
6. `type`
7. `coinbase`

An ordinary service payment uses `type="transfer"` and `coinbase=false`.
The interface cannot authorize coinbase or any issuance path. The exact object
bytes are bound to Section 5.11 by `transaction_input_sha256`.

### 5.11 `protocol_validation_binding` exact fields

1. `binding_profile` — exact
   `l28-local-signer-protocol-validation-binding/v0.1`
2. `delegate` — exact `coin.tx_validation.validate_transaction`
3. `invocation_required` — MUST be `true`
4. `available`
5. `invoked`
6. `status` — `accepted`, `rejected`, `pending`, `unavailable`, or
   `not_invoked`
7. `reason` — exact preserved Protocol reason or `""`
8. `transaction_input_sha256`
9. `validation_report_id` — public identifier or `""`
10. `ledger_context_id` — public identifier or `""`
11. `consensus_context_id` — public identifier or `""`
12. `issued_supply_context_id` — public identifier or `""`
13. `alternate_validator_supplied` — MUST be `false`
14. `override_requested` — MUST be `false`
15. `read_only` — MUST be `true`
16. `binding_digest`

An eligible public projection requires `available=true`, `invoked=true`,
`status="accepted"`, an exact transaction digest match, required authoritative
context bindings, and no alternate validator or override. `rejected`,
`pending`, `unavailable`, `not_invoked`, missing context, or any mismatch
blocks. The Protocol reason MUST be preserved without repair or translation
into authorization success.

Foundation117 does not call `validate_transaction`. It defines the evidence
binding that a later separately authorized implementation would have to prove.

## 6. Exact authority assertions

The request and response each contain an `authority_assertions` object with
exactly these fields and values in this order:

1. `protocol_version` — `1.0.0`
2. `l28_consensus_authority` — `true`
3. `l28_settlement_authority` — `true`
4. `validate_transaction_mandatory` — `true`
5. `authorization_equals_validation` — `false`
6. `eligibility_equals_invocation` — `false`
7. `signer_isolated_future_only` — `true`
8. `signer_may_override_protocol` — `false`
9. `issuance_override_allowed` — `false`
10. `supply_override_allowed` — `false`
11. `height_override_allowed` — `false`
12. `validation_override_allowed` — `false`
13. `consensus_override_allowed` — `false`
14. `history_override_allowed` — `false`
15. `settlement_override_allowed` — `false`
16. `historical_evidence_mutable` — `false`
17. `adapter_transport_only` — `true`
18. `harness_evals_advisory_only` — `true`
19. `bitcoin_external_evidence_only` — `true`
20. `blocked_security_decision_status` —
    `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

Any mismatch is `authority_assertion_invalid` and blocks evaluation before an
eligibility result.

## 7. Canonical response envelope

### 7.1 Exact top-level fields

Every response contains exactly these required fields in this order:

1. `interface_profile`
2. `interface_version`
3. `operation`
4. `request_id`
5. `ok`
6. `design_status`
7. `code`
8. `eligibility`
9. `validation_binding`
10. `public_audit_evidence`
11. `authority_assertions`
12. `non_execution`
13. `error`
14. `report_id`

`design_status` MUST be `DEFINED_DESIGN_ONLY`. `ok=true` means only that the
public request was evaluated to its defined deterministic outcome. It never
means signing, execution, submission, broadcast, settlement, or ledger
mutation occurred.

### 7.2 `eligibility` exact fields

1. `authorization_status` — `allowed`, `denied`, `pending`, or `unavailable`
2. `validation_status` — `accepted`, `rejected`, `pending`, `unavailable`, or
   `not_invoked`
3. `identity_status` — `verified`, `unverified`, or `unavailable`
4. `policy_status` — `active`, `inactive`, or `unavailable`
5. `limit_status` — `within_limit`, `exceeded`, or `unavailable`
6. `approval_status` — `threshold_met`, `threshold_not_met`, or `unavailable`
7. `replay_status` — `fresh`, `replayed`, or `unavailable`
8. `expiration_status` — `active`, `expired`, `not_yet_valid`, or `unavailable`
9. `operator_status` — `approved`, `denied`, `mismatch`, or `unavailable`
10. `eligibility_status` — `eligible_public_projection`, `blocked`, or
    `not_evaluated`
11. `signer_invocation_status` — MUST be `not_invoked`
12. `signing_authorized` — MUST be `false`
13. `spend_authorized` — MUST be `false`
14. `settlement_authorized` — MUST be `false`
15. `execution_authorized` — MUST be `false`

### 7.3 `validation_binding` exact response fields

1. `delegate`
2. `transaction_input_sha256`
3. `validation_report_id`
4. `validation_status`
5. `protocol_reason`
6. `binding_digest`
7. `binding_preserved` — boolean

The values echo the accepted or blocking validation evidence without invoking
the delegate in this design.

### 7.4 `public_audit_evidence` exact fields

1. `evidence_profile` — exact
   `l28-local-signer-eligibility-audit/v0.1`
2. `audit_id`
3. `eligibility_receipt_id`
4. `request_id`
5. `request_digest`
6. `intent_id`
7. `transaction_input_sha256`
8. `caller_evidence_id`
9. `operator_evidence_id`
10. `authorization_id`
11. `policy_id`
12. `approval_ids` — ordered public identifiers
13. `replay_evidence_id`
14. `time_evidence_id`
15. `validation_report_id`
16. `decision_code`
17. `evaluation_time`
18. `settlement_evidence_status` — MUST be `not_supplied`
19. `signature_evidence_status` — MUST be `not_created`
20. `public_evidence_only` — MUST be `true`

This is public audit/eligibility evidence only. It is not a UAII signed receipt,
transaction receipt, signature, settlement proof, ledger record, Protocol
history, operator credential, or authorization grant. Foundation117 creates no
such evidence instance.

### 7.5 `error` exact fields

1. `code`
2. `message`
3. `field`
4. `evidence_id`

On a non-error result, every field is `""`. On failure, `code` matches the
top-level code, `message` is a safe public string, and the remaining fields are
public references or `""`. Errors MUST NOT contain secret values, host paths,
stack traces, environment values, wallet references, or infrastructure detail.

## 8. Stable fail-closed taxonomy and precedence

### 8.1 Defined non-executing result codes

| Code | Meaning | Status |
|---|---|---|
| `signer_eligible_public_projection` | All modeled public gates pass; signer remains uninvoked | `DEFINED_DESIGN_ONLY` |
| `signer_eligibility_blocked` | A defined non-error gate outcome blocks eligibility | `DEFINED_DESIGN_ONLY` |

### 8.2 Stable rejection and blocked codes

| Code | Meaning |
|---|---|
| `schema_invalid` | Missing, unknown, duplicate, reordered, or wrong-type field |
| `interface_profile_unsupported` | Profile/version mismatch |
| `operation_unsupported` | Operation is not `evaluate_signer_eligibility` |
| `canonical_digest_mismatch` | Request, transaction, binding, audit, or report digest mismatch |
| `secret_material_forbidden` | Secret, wallet, credential, keystore, or secret locator supplied |
| `authority_assertion_invalid` | Fixed authority assertion changed |
| `protocol_override_forbidden` | Input attempts to change Protocol authority or economics |
| `identity_evidence_unavailable` | Required caller identity evidence absent/unavailable |
| `identity_evidence_unauthenticated` | Required identity claim is not authenticated under approved future policy |
| `authorization_denied` | Local authorization explicitly denied |
| `authorization_unavailable` | Required authorization evidence missing/pending/unavailable |
| `spending_policy_unavailable` | Policy, window, asset, or limit evidence invalid/unavailable |
| `per_transaction_limit_exceeded` | Amount exceeds the per-transaction limit |
| `cumulative_limit_exceeded` | Prior authorized total plus amount exceeds cumulative limit |
| `approval_threshold_not_met` | Too few distinct authorized approvals |
| `duplicate_approval` | A duplicate approver is present |
| `approval_policy_unavailable` | Approval policy or authenticated approver evidence unavailable |
| `replay_detected` | Request, intent, or idempotency key is already retained |
| `replay_state_unavailable` | Required replay evidence is absent, stale, invalid, or inconsistent |
| `artifact_expired` | A required artifact is expired |
| `not_yet_valid` | A required artifact is not yet valid |
| `evaluation_time_unavailable` | Required time evidence is absent or untrusted |
| `operator_authorization_denied` | Operator explicitly denied |
| `operator_authorization_mismatch` | Operator evidence does not bind the exact scope |
| `operator_gate_unavailable` | Required authenticated operator/security-review evidence unavailable |
| `authority_binding_invalid` | Authorization, transaction, validation, or evidence bindings conflict |
| `validation_override_forbidden` | Alternate validator or validation override supplied |
| `protocol_validation_rejected` | Mandatory Protocol validation rejected; reason preserved |
| `protocol_validation_pending` | Mandatory Protocol validation is incomplete |
| `protocol_validation_unavailable` | Delegate or required Protocol context is unavailable |
| `audit_lineage_invalid` | Required public audit lineage is missing/conflicting |
| `signer_invocation_forbidden` | Request or result attempts signer invocation |
| `execution_forbidden` | Request claims signing, wallet, submission, broadcast, mutation, or settlement |
| `future_security_decision_required` | Input assumes an unresolved security gate or production decision |
| `internal_failure` | Safe fail-closed response for an otherwise unclassified evaluator failure |

### 8.3 First-failure precedence

A future conforming evaluator MUST stop at the first applicable failure:

1. UTF-8/JSON/size/duplicate/schema/order/type failure;
2. secret or forbidden custody material;
3. profile/version/operation mismatch;
4. canonical digest mismatch;
5. authority assertion, protected-economics, or Protocol override attempt;
6. signer-invocation or execution claim;
7. attempted assumption of an unresolved future security decision;
8. caller identity/authentication failure;
9. replay/idempotency failure;
10. expiration/time-evidence failure;
11. policy or spending-limit failure;
12. approval-threshold failure;
13. operator-authorization failure;
14. authorization/binding failure;
15. mandatory Protocol-validation rejection, pending state, or unavailability;
16. audit-lineage failure; and
17. deterministic eligible or blocked public projection.

Unknown, partial, stale, contradictory, or unauthenticated required evidence
fails closed. The evaluator MUST NOT repair data, choose a fallback authority,
assume fresh replay state, assume trusted time, assume unlimited spend, invent
approvals, or invoke a signer as recovery.

## 9. Exact non-execution object

The request and response each contain a `non_execution` object with exactly
these fields in this order. Every value MUST be JSON `false`:

1. `signer_invocation_requested`
2. `signer_invoked`
3. `signing_attempted`
4. `signature_created`
5. `wallet_access_requested`
6. `wallet_accessed`
7. `transaction_submitted`
8. `broadcast_attempted`
9. `rpc_connected`
10. `network_connected`
11. `replay_state_mutated`
12. `economic_control_state_mutated`
13. `ledger_mutated`
14. `settlement_attempted`
15. `settlement_finalized`
16. `consensus_modified`
17. `execution_authorized`

Any `true` value fails with `execution_forbidden` or
`signer_invocation_forbidden`. These fields are explicit contract assertions;
this documentation does not produce runtime proof.

## 10. Canonical serialization and digests

`CanonLsi(x)` means exact UTF-8 JSON bytes using:

1. one JSON object and no trailing data;
2. exact property order declared by this document at every object level;
3. no duplicate, missing, or unknown properties;
4. `ensure_ascii=false`, separators `(",", ":")`, `sort_keys=false`, and
   `allow_nan=false` semantics;
5. exact JSON integers in the safe range `-9007199254740991` through
   `9007199254740991`; no floats, `NaN`, `Infinity`, bytes, tuples, sets, or
   comments;
6. exact string code points with no Unicode normalization, case folding, or
   hidden coercion;
7. array order preserved; approval and identifier ordering checked by the
   relevant schema rules; and
8. lowercase 64-character hexadecimal digests and identifiers.

Domain separators are exact ASCII followed by one NUL byte:

| Purpose | Domain bytes |
|---|---|
| Request | `L28-LOCAL-SIGNER-INTERFACE-V0.1-REQUEST\x00` |
| Transaction binding | `L28-LOCAL-SIGNER-INTERFACE-V0.1-TRANSACTION\x00` |
| Validation binding | `L28-LOCAL-SIGNER-INTERFACE-V0.1-VALIDATION\x00` |
| Audit evidence | `L28-LOCAL-SIGNER-INTERFACE-V0.1-AUDIT\x00` |
| Response report | `L28-LOCAL-SIGNER-INTERFACE-V0.1-REPORT\x00` |

Digest formulas:

```text
transaction_input_sha256 = hex_lower(
  SHA-256(TRANSACTION_DOMAIN || CanonLsi(proposed_transaction))
)

binding_digest = hex_lower(
  SHA-256(VALIDATION_DOMAIN || CanonLsi(protocol_validation_binding
    with binding_digest=""))
)

request_digest = hex_lower(
  SHA-256(REQUEST_DOMAIN || CanonLsi(complete request
    with request_digest=""))
)

audit_id = hex_lower(
  SHA-256(AUDIT_DOMAIN || CanonLsi(public_audit_evidence
    with audit_id="" and eligibility_receipt_id=""))
)

eligibility_receipt_id = hex_lower(
  SHA-256(AUDIT_DOMAIN || ASCII("receipt") || 0x00 ||
    CanonLsi(public_audit_evidence with eligibility_receipt_id=""))
)

report_id = hex_lower(
  SHA-256(REPORT_DOMAIN || CanonLsi(complete response with report_id=""))
)
```

The file or transport framing LF, if any, is not part of canonical bytes.
Digest success proves deterministic binding only; it does not authenticate
evidence, validate a signature, authorize execution, or prove settlement.

## 11. Protected Protocol and economic facts

This design preserves exactly:

| Fact | Exact value |
|---|---:|
| Hard cap | `28,000,000 L28` |
| Emission ceiling | `11,130,000 L28` |
| Historically mined | `2,824,584 L28` |
| Treasury locked | `500,000 L28` |
| Circulating snapshot | `2,324,584 L28` |
| Halving interval | `210,000` |
| Reward schedule | `28 → 14 → 7 → 3 → 1 → 0` |
| Historical mined-through entry | `100,877` |
| Next canonical height after bootstrap | `100,878` |

Coinbase remains the only issuance mechanism. Canonical height remains
consensus-derived. Missing required consensus, ledger, height, supply, or
historical state fails closed. Historical evidence remains immutable.

This interface cannot recalculate, override, reinterpret, mint, allocate, or
mutate any protected fact.

## 12. Unresolved future security gates

### 12.1 `GAP_REQUIRES_FUTURE_WORK`

| Gate | Required future decision/evidence; not selected here |
|---|---|
| Authenticated identities and evidence | Identity proof, policy/operator/approval authentication, provenance, issuer authority, revocation, anti-forgery, and administration |
| Key custody and lifecycle | Generation/import policy, storage boundary, permitted algorithms/material, rotation, revocation, backup/recovery, destruction, compromise response, and verification |
| Atomic replay and economic state | Atomic check-and-record, idempotency, cumulative-spend accounting, approval consumption, concurrency, persistence, crash recovery, retention, and rollback |
| Trusted production time | Clock source, authentication, skew, rollback, outage, monotonicity, and expiry behavior |
| Audit durability | Persistence, tamper evidence, retention, privacy/redaction, access control, verification, recovery, and receipt authenticity |
| Service hardening | Request-size/depth limits, rate/resource limits, process isolation, denial-of-service controls, secure errors, monitoring, and failure handling |
| Runtime integration assurance | Production evaluator, exact `validate_transaction` delegation proof, adversarial/fault/recovery/end-to-end tests, deployment boundary, operator runbook, and independent security review |

Foundation117 defines field positions and fail-closed expectations for these
areas but does not select or implement their production mechanisms.

### 12.2 `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

The following remain blocked:

1. any signer implementation, invocation, runtime integration, deployment, or
   activation until every applicable Foundation116 gate is decided, specified,
   verified, independently reviewed, and separately operator-authorized;
2. production proof architecture;
3. Bitcoin confirmation count; and
4. observer quorum and independence.

This design supplies no default, range, fallback, architecture, count, quorum,
custody mechanism, or production policy for a blocked item. Bitcoin remains
external evidence only. Harness/Evals remains advisory only.

## 13. Conformance requirements for later milestones

A later separately authorized specification/test milestone for this design
would have to prove, without signer invocation:

1. exact request and response schemas and field order;
2. rejection of duplicate, unknown, missing, reordered, and wrong-type fields;
3. profile/version compatibility and unknown-operation rejection;
4. independent recomputation of every Section 10 digest;
5. complete evidence bindings to request, intent, policy, parties, amount, and
   proposed transaction;
6. authorization and validation remain distinct;
7. eligibility and signer invocation remain distinct;
8. mandatory exact `coin.tx_validation.validate_transaction` binding with
   rejection/unavailability preserved;
9. spending, approval, replay, expiration, and operator gates fail closed;
10. exact authority assertions and protected economics;
11. every Section 9 value remains false;
12. public/disposable evidence only and no secret lookup or echo;
13. receipt/audit output remains evidence only;
14. Harness/Evals advisory-only and Bitcoin external-evidence-only isolation;
   and
15. no implementation, network, wallet, signer, broadcast, settlement, or
   production-state interaction.

Foundation117 does not add those tests or fixtures.

## 14. Explicit non-activation conclusion

**This milestone defines only the future public signer boundary.** It defines
the identity, schemas, bindings, deterministic serialization, stable outcomes,
authority assertions, and non-execution evidence for a possible future
eligibility interface.

**It authorizes zero signing or runtime behavior.** No signer is invoked; no
key, wallet, signature, RPC, network, transaction submission, broadcast,
ledger mutation, settlement, deployment, testnet, or infrastructure is created
or activated.

**Implementation remains blocked pending the Foundation116 security gates and
separate operator authorization.** Completing this design does not satisfy
custody, authenticated evidence, atomic state, trusted time, audit durability,
service hardening, runtime integration, independent review, deployment, or
activation gates.

## 15. Document control

| Field | Value |
|---|---|
| Foundation | 117 |
| Parent | `821b98e9d48f5dc1b7e5d1e26dd4ce803a7ac1ae` |
| Path | `docs/local_signer_interface_design_v0.1.md` |
| Status | `DEFINED_DESIGN_ONLY` |
| Interface profile | `l28-local-signer-interface/v0.1` |
| Operations defined | `evaluate_signer_eligibility` only |
| UAII v0.1 modified | no |
| Protocol v1.0.0 modified | no |
| Protected economics modified | no |
| Runtime/interface code | none |
| Tests/fixtures/dependencies | none |
| Key/wallet/signature activity | none |
| RPC/network/broadcast/submission | none |
| Ledger/settlement/deployment/testnet/infrastructure | none |
| Next milestone begun | no |
