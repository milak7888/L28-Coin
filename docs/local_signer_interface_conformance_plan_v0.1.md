# Local Signer Interface Conformance Plan v0.1

**Foundation:** 118

**Status:** documentation and conformance planning only / non-activating

**Plan version:** `local-signer-interface-conformance-plan/v0.1`

**Interface under test:** `l28-local-signer-interface/v0.1`

**Authoritative interface input:**
`docs/local_signer_interface_design_v0.1.md` (Foundation117)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Required parent:** `01eb5620628ec33e0ea6c7aadbc39ba7ad8623c4`

**Branch:** `foundation118-local-signer-interface-conformance-plan`

**Implementation, fixtures, tests, schemas, runtime, or activation:** none

**Normative subordination:** This plan is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md), Foundations 111–117, and especially
Foundation117. On conflict, Protocol v1.0.0 prevails, then Foundation117, then
this plan. This document plans deterministic offline conformance only. It does
not redefine the interface or authorize implementation.

---

## 1. Purpose and scope

Foundation118 translates every normative Foundation117 boundary into an
exhaustive planned inventory of deterministic offline positive (`POS`),
negative (`NEG`), boundary (`BND`), and fail-closed (`FCL`) cases.

The future subject under test is a non-executing evaluator for the sole
Foundation117 operation, `evaluate_signer_eligibility`. A passing result may
report only `eligible_public_projection`. It MUST retain
`signer_invocation_status="not_invoked"` and every Section 5 non-execution
field as `false`.

This plan creates no fixtures, executable schemas, tests, runner, signer,
wallet, key, signature, RPC client, network connection, transaction submission,
broadcast, ledger mutation, settlement, deployment, testnet, DigitalOcean
resource, dependency, or runtime service.

## 2. Authority and immutable invariants

Every planned case preserves:

1. L28 Protocol v1.0.0 as sole issuance, supply, consensus, canonical-height,
   history, validation, and native-settlement authority.
2. `coin.tx_validation.validate_transaction` as the mandatory Protocol
   validation delegate.
3. Authorization is not Protocol validation.
4. Signer eligibility is not signer invocation.
5. Harness/Evals is advisory only; Bitcoin is external evidence only; adapters
   are transport only.
6. Missing, malformed, stale, unauthenticated, unavailable, contradictory, or
   authority-violating required evidence fails closed.

Protected facts remain exactly:

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
consensus-derived. Historical ledger and supply evidence remains immutable.

## 3. Deterministic case contract

### 3.1 Case identifiers

Case IDs are immutable and use:

`LSI-CONF-v0.1-<FAMILY>-<POS|NEG|BND|FCL>-<NNN>`

The 18 family codes are exactly:

`CMP`, `SCH`, `IDN`, `AUT`, `VAL`, `ELG`, `LIM`, `APR`, `RPL`, `EXP`, `OPR`,
`ATH`, `CAN`, `PRE`, `AUD`, `FWL`, `NEX`, and `GAT`.

IDs MUST be unique, MUST NOT be renumbered or reused, and remain ordered by
family as published, then POS, NEG, BND, FCL, then numeric suffix.

### 3.2 Case classes

| Class | Meaning |
|---|---|
| `POS` | Complete public inputs satisfy the named rule; outcome remains non-executing |
| `NEG` | Well-formed input violates one named rule and is rejected or blocked with the exact stable code |
| `BND` | Exact documented equality, length, order, or time boundary is evaluated deterministically |
| `FCL` | Missing, malformed, stale, unavailable, contradictory, or authority-violating evidence blocks without inference |

### 3.3 Required logical case fields

Every future materialized case MUST contain, in a later separately specified
schema, at least:

1. `case_id`;
2. `class`;
3. `input_focus`;
4. `expected_status`;
5. `expected_code`;
6. `required_invariant`;
7. `fail_closed_behavior`;
8. `authority_assertions`;
9. `non_execution_assertions`; and
10. deterministic public input references.

Foundation118 does not lock a fixture filesystem path or create that schema.

### 3.4 Deterministic execution rules

A future runner MUST use public fictional/disposable data, fixed integer times,
fixed exact-order JSON, fixed IDs/nonces, and read-only supplied evidence. It
MUST NOT read system/network time, environment variables, files containing
secrets, keys, wallets, RPC configuration, network state, or production state.
Identical canonical inputs MUST produce identical public outcomes.

Expected statuses in this plan are `eligible_public_projection`, `blocked`, or
`rejected`. Codes are exact Foundation117 stable codes. Status success never
means execution.

## 4. Common required assertions

Every case MUST assert the exact Foundation117 request/response authority
objects and MUST keep all override flags false. Every eligible case additionally
requires an exact accepted binding to
`coin.tx_validation.validate_transaction`; cases MUST NOT invoke that production
callable.

Every result MUST report `design_status="DEFINED_DESIGN_ONLY"` and preserve:

- `authorization_equals_validation=false`;
- `eligibility_equals_invocation=false`;
- `signer_isolated_future_only=true`;
- `signer_may_override_protocol=false`; and
- issuance, supply, height, validation, consensus, history, and settlement
  override flags all `false`.

## 5. Common non-execution assertions

Every POS, NEG, BND, and FCL case MUST assert all 17 Foundation117 fields are
JSON `false`:

`signer_invocation_requested`, `signer_invoked`, `signing_attempted`,
`signature_created`, `wallet_access_requested`, `wallet_accessed`,
`transaction_submitted`, `broadcast_attempted`, `rpc_connected`,
`network_connected`, `replay_state_mutated`,
`economic_control_state_mutated`, `ledger_mutated`, `settlement_attempted`,
`settlement_finalized`, `consensus_modified`, and `execution_authorized`.

Any true value fails closed under `execution_forbidden` or
`signer_invocation_forbidden`.

## 6. Exhaustive planned case inventory

Each row specifies the immutable ID, class, input focus, expected status/code,
and required invariant or fail-closed behavior.

### 6.1 Compatibility (`CMP`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-CMP-POS-001` | POS | Exact profile `l28-local-signer-interface/v0.1`, version `0.1`, sole operation | eligible_public_projection / `signer_eligible_public_projection` | Exact identity accepted; no negotiation or invocation |
| `LSI-CONF-v0.1-CMP-NEG-001` | NEG | Unsupported interface profile | rejected / `interface_profile_unsupported` | No fallback profile |
| `LSI-CONF-v0.1-CMP-NEG-002` | NEG | Unsupported interface version | rejected / `interface_profile_unsupported` | No downgrade or repair |
| `LSI-CONF-v0.1-CMP-FCL-001` | FCL | Unknown operation or attempted sign/broadcast operation | rejected / `operation_unsupported` | Only eligibility evaluation exists; no execution fallback |

### 6.2 Request and response schemas (`SCH`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-SCH-POS-001` | POS | Request has all 20 top-level fields and every nested object in exact F117 order | eligible_public_projection / `signer_eligible_public_projection` | Exact request schema preserved |
| `LSI-CONF-v0.1-SCH-POS-002` | POS | Response has all 14 top-level fields and exact nested eligibility, binding, audit, authority, non-execution, error fields | eligible_public_projection / `signer_eligible_public_projection` | Exact response schema preserved; empty error fields on success |
| `LSI-CONF-v0.1-SCH-NEG-001` | NEG | Request missing, unknown, duplicate, or reordered top-level/nested property | rejected / `schema_invalid` | Each deterministic mutation rejected; no ignored extension |
| `LSI-CONF-v0.1-SCH-NEG-002` | NEG | Request wrong type, boolean-as-integer, float, invalid hex, normalized/coerced identity, or forbidden null | rejected / `schema_invalid` | No coercion or normalization |
| `LSI-CONF-v0.1-SCH-NEG-003` | NEG | Response missing, unknown, duplicate, or reordered top-level/nested property | rejected / `schema_invalid` | Nonconforming response fails suite |
| `LSI-CONF-v0.1-SCH-NEG-004` | NEG | Response uses unknown status/code or leaks unsafe error detail | rejected / `schema_invalid` | Stable vocabulary; no secrets, paths, stack, environment, wallet, or infrastructure detail |
| `LSI-CONF-v0.1-SCH-BND-001` | BND | Nonce exactly 256 UTF-8 bytes and integers at safe-range boundary | eligible_public_projection / `signer_eligible_public_projection` | Exact valid boundary accepted without coercion |
| `LSI-CONF-v0.1-SCH-FCL-001` | FCL | Non-UTF-8, BOM, truncated JSON, trailing data, NUL nonce, or out-of-range integer | rejected / `schema_invalid` | Parse fails before semantic evaluation |

### 6.3 Public identity evidence (`IDN`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-IDN-POS-001` | POS | Exact caller/operator public identities and request/scope bindings | eligible_public_projection / `signer_eligible_public_projection` | Public evidence only; parties bind exactly |
| `LSI-CONF-v0.1-IDN-NEG-001` | NEG | Private key, seed, mnemonic, xprv, keystore, credential, wallet/RPC secret, or secret locator | rejected / `secret_material_forbidden` | Reject without lookup, forwarding, logging, or echo |
| `LSI-CONF-v0.1-IDN-NEG-002` | NEG | Caller/operator/request/intent/policy/payer/payee identity binding mismatch | rejected / `authority_binding_invalid` | No inferred identity equivalence |
| `LSI-CONF-v0.1-IDN-BND-001` | BND | Public key ID present with no key bytes or loadable locator | eligible_public_projection / `signer_eligible_public_projection` | Public identifier grants no custody/signing authority |
| `LSI-CONF-v0.1-IDN-FCL-001` | FCL | Required caller or operator identity evidence absent/unavailable | blocked / `identity_evidence_unavailable` | Absence is not consent |

### 6.4 Authorization and authorization/validation separation (`AUT`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-AUT-POS-001` | POS | Authorization allowed and independent Protocol validation accepted | eligible_public_projection / `signer_eligible_public_projection` | Separate allowed/accepted statuses; neither implies invocation |
| `LSI-CONF-v0.1-AUT-NEG-001` | NEG | Authorization explicitly denied | blocked / `authorization_denied` | Validation acceptance cannot override denial |
| `LSI-CONF-v0.1-AUT-NEG-002` | NEG | Authorization missing, pending, expired, or unavailable | blocked / `authorization_unavailable` | No default allow |
| `LSI-CONF-v0.1-AUT-BND-001` | BND | Authorization allowed while validation remains pending | blocked / `protocol_validation_pending` | Authorization is not validation |
| `LSI-CONF-v0.1-AUT-FCL-001` | FCL | Authorization and validation fields conflated or contradict exact transaction binding | rejected / `authority_binding_invalid` | Neither status inferred; signer edge not reached |

### 6.5 Mandatory Protocol validation (`VAL`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-VAL-POS-001` | POS | Exact transaction digest, delegate, accepted report, and authoritative context IDs | eligible_public_projection / `signer_eligible_public_projection` | Mandatory binding proven read-only without calling production runtime |
| `LSI-CONF-v0.1-VAL-NEG-001` | NEG | Canonical delegate rejects | blocked / `protocol_validation_rejected` | Exact Protocol reason preserved; authorization cannot override |
| `LSI-CONF-v0.1-VAL-NEG-002` | NEG | Alternate validator supplied or override requested | rejected / `validation_override_forbidden` | No second validation authority |
| `LSI-CONF-v0.1-VAL-NEG-003` | NEG | Transaction input digest or validation binding digest mismatches | rejected / `canonical_digest_mismatch` | No rebinding or repair |
| `LSI-CONF-v0.1-VAL-BND-001` | BND | All required ledger, consensus, and issued-supply context IDs present at exact schema minimum | eligible_public_projection / `signer_eligible_public_projection` | Minimum complete context still mandatory |
| `LSI-CONF-v0.1-VAL-FCL-001` | FCL | Delegate unavailable/not invoked or required context missing | blocked / `protocol_validation_unavailable` | No signer eligibility or fallback validator |

### 6.6 Eligibility versus invocation (`ELG`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-ELG-POS-001` | POS | All modeled gates pass | eligible_public_projection / `signer_eligible_public_projection` | `signer_invocation_status=not_invoked`; signing/spend/settlement/execution false |
| `LSI-CONF-v0.1-ELG-NEG-001` | NEG | Eligible projection claims signer requested or invoked | rejected / `signer_invocation_forbidden` | Eligibility never invokes signer |
| `LSI-CONF-v0.1-ELG-NEG-002` | NEG | Result claims signing, spend, settlement, or execution authorized | rejected / `execution_forbidden` | No grant follows eligibility |
| `LSI-CONF-v0.1-ELG-FCL-001` | FCL | Caller requests runtime signing as fallback | rejected / `signer_invocation_forbidden` | Stop without runtime contact |

### 6.7 Spending limits (`LIM`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-LIM-POS-001` | POS | Amount and prior total below both active authenticated limits | eligible_public_projection / `signer_eligible_public_projection` | Exact integers; no spend or state mutation |
| `LSI-CONF-v0.1-LIM-NEG-001` | NEG | Amount exceeds per-transaction limit | blocked / `per_transaction_limit_exceeded` | No implicit increase |
| `LSI-CONF-v0.1-LIM-NEG-002` | NEG | Prior authorized total plus amount exceeds cumulative limit | blocked / `cumulative_limit_exceeded` | No rollover or mutation |
| `LSI-CONF-v0.1-LIM-BND-001` | BND | Amount equals per-transaction limit and total equals cumulative limit | eligible_public_projection / `signer_eligible_public_projection` | Equality may pass locally; validation still mandatory |
| `LSI-CONF-v0.1-LIM-FCL-001` | FCL | Policy/asset/window/limit/prior-total unavailable, stale, malformed, inactive, or contradictory | blocked / `spending_policy_unavailable` | Unknown never means unlimited |

### 6.8 Approval thresholds (`APR`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-APR-POS-001` | POS | Distinct authenticated authorized approvals exceed threshold | eligible_public_projection / `signer_eligible_public_projection` | Other gates remain independent |
| `LSI-CONF-v0.1-APR-NEG-001` | NEG | Distinct valid approvals below threshold | blocked / `approval_threshold_not_met` | No implicit approval |
| `LSI-CONF-v0.1-APR-NEG-002` | NEG | Duplicate approver evidence | rejected / `duplicate_approval` | Duplicate adds zero count |
| `LSI-CONF-v0.1-APR-NEG-003` | NEG | Denied, wrong-scope, wrong-amount, or unauthorized approver evidence | blocked / `approval_policy_unavailable` | Invalid approval never counts |
| `LSI-CONF-v0.1-APR-BND-001` | BND | Distinct valid approvals equal threshold exactly | eligible_public_projection / `signer_eligible_public_projection` | Threshold does not authorize signing or settlement |
| `LSI-CONF-v0.1-APR-FCL-001` | FCL | Threshold or authorized-approver policy missing/contradictory | blocked / `approval_policy_unavailable` | Threshold never invented |

### 6.9 Replay and idempotency (`RPL`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-RPL-POS-001` | POS | Request, intent, and idempotency key all fresh in supplied read-only evidence | eligible_public_projection / `signer_eligible_public_projection` | No state mutation |
| `LSI-CONF-v0.1-RPL-NEG-001` | NEG | Request or intent already retained | blocked / `replay_detected` | Reuse rejected |
| `LSI-CONF-v0.1-RPL-NEG-002` | NEG | Idempotency key bound to conflicting request/intent | rejected / `authority_binding_invalid` | No cross-request aliasing |
| `LSI-CONF-v0.1-RPL-BND-001` | BND | Retained identifier evaluated exactly at retention boundary | blocked / `replay_detected` | Retained presence remains replay at boundary |
| `LSI-CONF-v0.1-RPL-FCL-001` | FCL | Replay view missing, stale, invalid, or inconsistent | blocked / `replay_state_unavailable` | Unknown never means fresh; no check-and-record mutation |

### 6.10 Expiration and time (`EXP`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-EXP-POS-001` | POS | Supplied integer evaluation time lies within all required lifetimes/windows | eligible_public_projection / `signer_eligible_public_projection` | No system/network clock read |
| `LSI-CONF-v0.1-EXP-NEG-001` | NEG | First required artifact expired | blocked / `artifact_expired` | First failing artifact controls result |
| `LSI-CONF-v0.1-EXP-NEG-002` | NEG | Intent or policy not yet valid | blocked / `not_yet_valid` | No early eligibility |
| `LSI-CONF-v0.1-EXP-BND-001` | BND | Evaluation time equals an expiry boundary | blocked / `artifact_expired` | Expiry boundary applied deterministically |
| `LSI-CONF-v0.1-EXP-BND-002` | BND | Evaluation time equals valid `not_before`/window start | eligible_public_projection / `signer_eligible_public_projection` | Inclusive start accepted when all else passes |
| `LSI-CONF-v0.1-EXP-FCL-001` | FCL | Time evidence unavailable/untrusted or would require implicit clock | blocked / `evaluation_time_unavailable` | No clock inference |

### 6.11 Operator authorization (`OPR`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-OPR-POS-001` | POS | Current approved exact-scope public operator claim | eligible_public_projection / `signer_eligible_public_projection` | Operator gate is necessary but not validation/invocation |
| `LSI-CONF-v0.1-OPR-NEG-001` | NEG | Operator decision denied | blocked / `operator_authorization_denied` | Denial blocks |
| `LSI-CONF-v0.1-OPR-NEG-002` | NEG | Request/intent/policy/parties/asset/amount scope mismatch | blocked / `operator_authorization_mismatch` | Exact scope required |
| `LSI-CONF-v0.1-OPR-NEG-003` | NEG | Operator evidence expired | blocked / `artifact_expired` | Expired authorization is unavailable authority |
| `LSI-CONF-v0.1-OPR-BND-001` | BND | Amount equals maximum and evaluation time equals valid start/last pre-expiry instant | eligible_public_projection / `signer_eligible_public_projection` | Exact allowed scope only |
| `LSI-CONF-v0.1-OPR-FCL-001` | FCL | Operator or required security-review evidence missing/unverifiable | blocked / `operator_gate_unavailable` | Absence is never consent |

### 6.12 Authenticated evidence (`ATH`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-ATH-POS-001` | POS | All public evidence claims `verified` under a fixed fictional design profile | eligible_public_projection / `signer_eligible_public_projection` | Design claim only; not production authentication proof |
| `LSI-CONF-v0.1-ATH-NEG-001` | NEG | Caller identity unverified/unavailable | blocked / `identity_evidence_unauthenticated` | No caller trust inference |
| `LSI-CONF-v0.1-ATH-NEG-002` | NEG | Operator evidence unverified | blocked / `operator_gate_unavailable` | Public claim cannot self-authenticate |
| `LSI-CONF-v0.1-ATH-NEG-003` | NEG | Economic-policy evidence unverified | blocked / `spending_policy_unavailable` | No policy authority inference |
| `LSI-CONF-v0.1-ATH-NEG-004` | NEG | Approval evidence unverified | blocked / `approval_policy_unavailable` | Unauthenticated approval never counts |
| `LSI-CONF-v0.1-ATH-FCL-001` | FCL | Input claims a production authentication mechanism or revocation policy is already selected | blocked / `future_security_decision_required` | Mechanism remains future work |

### 6.13 Canonical serialization and digests (`CAN`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-CAN-POS-001` | POS | Independently recomputed transaction, validation, request, audit, receipt, and report digests all match | eligible_public_projection / `signer_eligible_public_projection` | Exact F117 domains/preimages and lowercase SHA-256 |
| `LSI-CONF-v0.1-CAN-NEG-001` | NEG | Request digest mismatch | rejected / `canonical_digest_mismatch` | No repair |
| `LSI-CONF-v0.1-CAN-NEG-002` | NEG | Transaction or validation-binding digest mismatch | rejected / `canonical_digest_mismatch` | Exact transaction binding preserved |
| `LSI-CONF-v0.1-CAN-NEG-003` | NEG | Audit, eligibility-receipt, or report digest mismatch | rejected / `canonical_digest_mismatch` | Evidence/report lineage not invented |
| `LSI-CONF-v0.1-CAN-BND-001` | BND | Exact Unicode strings and ordered arrays serialize byte-stably without normalization/sorting | eligible_public_projection / `signer_eligible_public_projection` | CanonLsi exact-order bytes preserved |
| `LSI-CONF-v0.1-CAN-FCL-001` | FCL | Duplicate keys, unknown keys, `NaN`, `Infinity`, float, reordered object, or noncanonical hex | rejected / `schema_invalid` | Canonicalization never hides invalid input |

### 6.14 Failure precedence (`PRE`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-PRE-POS-001` | POS | One fully valid request evaluated twice | eligible_public_projection / `signer_eligible_public_projection` | Byte-equivalent public result/report |
| `LSI-CONF-v0.1-PRE-NEG-001` | NEG | Simultaneous replay, expiry, limit, operator, and validation failures | blocked / `replay_detected` | First applicable F117 precedence result wins |
| `LSI-CONF-v0.1-PRE-BND-001` | BND | Schema-invalid input also contains a secret-material field | rejected / `schema_invalid` | Schema failure precedes semantic secret handling; no multi-error reordering |
| `LSI-CONF-v0.1-PRE-FCL-001` | FCL | Otherwise unclassified deterministic evaluator failure | rejected / `internal_failure` | Safe public error; no fallback or leakage |

### 6.15 Audit and public receipt evidence (`AUD`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-AUD-POS-001` | POS | Exact 20-field public audit object binds all input evidence and decision | eligible_public_projection / `signer_eligible_public_projection` | Evidence only; settlement/signature statuses remain not supplied/not created |
| `LSI-CONF-v0.1-AUD-NEG-001` | NEG | Eligibility receipt claims signature or settlement evidence | rejected / `execution_forbidden` | Audit cannot create signature/settlement truth |
| `LSI-CONF-v0.1-AUD-NEG-002` | NEG | Audit claims ledger or historical-state mutation | rejected / `execution_forbidden` | Audit evidence cannot claim mutation |
| `LSI-CONF-v0.1-AUD-BND-001` | BND | Identical canonical inputs repeated | eligible_public_projection / `signer_eligible_public_projection` | Audit ID, eligibility receipt ID, and report ID byte-stable |
| `LSI-CONF-v0.1-AUD-FCL-001` | FCL | Required audit lineage/binding missing or conflicting | rejected / `audit_lineage_invalid` | No repair; not a UAII signed receipt or Protocol history |

### 6.16 Authority firewall and protected economics (`FWL`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-FWL-POS-001` | POS | Exact authority assertions and all protected facts | eligible_public_projection / `signer_eligible_public_projection` | L28 remains sole authority; all override flags false |
| `LSI-CONF-v0.1-FWL-NEG-001` | NEG | Issuance or supply override/mint attempt | rejected / `protocol_override_forbidden` | Coinbase-only issuance; caps unchanged |
| `LSI-CONF-v0.1-FWL-NEG-002` | NEG | Canonical-height or historical-ledger rewrite attempt | rejected / `protocol_override_forbidden` | Consensus height/history preserved |
| `LSI-CONF-v0.1-FWL-NEG-003` | NEG | Validation override or alternate validator attempt | rejected / `validation_override_forbidden` | No alternate validation authority |
| `LSI-CONF-v0.1-FWL-NEG-004` | NEG | Settlement override/finality claim | rejected / `protocol_override_forbidden` | Eligibility/audit is not settlement |
| `LSI-CONF-v0.1-FWL-NEG-005` | NEG | Historical evidence mutable or any exact authority assertion changed | rejected / `authority_assertion_invalid` | Immutable evidence and fixed assertions |
| `LSI-CONF-v0.1-FWL-NEG-006` | NEG | Consensus override attempt | rejected / `protocol_override_forbidden` | Signer interface cannot become consensus authority |
| `LSI-CONF-v0.1-FWL-BND-001` | BND | Local limit numerically equals a protected economic value | eligible_public_projection / `signer_eligible_public_projection` | Local number does not redefine Protocol economics |
| `LSI-CONF-v0.1-FWL-FCL-001` | FCL | Required canonical ledger/supply/height/history context unavailable | blocked / `protocol_validation_unavailable` | State never inferred or synthesized |

### 6.17 Non-execution assertions (`NEX`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-NEX-POS-001` | POS | All 17 request and response flags false | eligible_public_projection / `signer_eligible_public_projection` | No action occurred or was authorized |
| `LSI-CONF-v0.1-NEX-NEG-001` | NEG | Signer requested/invoked or signing/signature flag true | rejected / `signer_invocation_forbidden` | No signer or signature |
| `LSI-CONF-v0.1-NEX-NEG-002` | NEG | Wallet access, RPC, or network flag true | rejected / `execution_forbidden` | No custody/runtime/network behavior |
| `LSI-CONF-v0.1-NEX-NEG-003` | NEG | Submission, broadcast, state mutation, settlement, consensus, or execution flag true | rejected / `execution_forbidden` | No transaction/runtime effect |
| `LSI-CONF-v0.1-NEX-FCL-001` | FCL | A non-execution field missing, non-boolean, contradictory, or unavailable | rejected / `schema_invalid` | No inference of false; no continued evaluation |

### 6.18 Unresolved gates (`GAT`)

| Case ID | Class | Input focus | Expected status / code | Required invariant / fail-closed behavior |
|---|---|---|---|---|
| `LSI-CONF-v0.1-GAT-POS-001` | POS | Request/response declare `DEFINED_DESIGN_ONLY` and make no production decision | eligible_public_projection / `signer_eligible_public_projection` | Documentation-only boundary preserved |
| `LSI-CONF-v0.1-GAT-NEG-001` | NEG | Input selects custody/key-lifecycle architecture or claims custody implemented | blocked / `future_security_decision_required` | Custody remains unresolved/non-implemented |
| `LSI-CONF-v0.1-GAT-NEG-002` | NEG | Input selects production proof architecture, Bitcoin confirmation policy/count, or observer quorum | blocked / `future_security_decision_required` | Named Bitcoin decisions remain blocked |
| `LSI-CONF-v0.1-GAT-NEG-003` | NEG | Input claims authenticated evidence, atomic state, trusted time, audit durability, hardening, integration, or independent review completed without governed evidence | blocked / `future_security_decision_required` | F116/F117 gates remain unresolved |
| `LSI-CONF-v0.1-GAT-FCL-001` | FCL | Signer implementation/runtime/activation/deployment requested | blocked / `future_security_decision_required` | Stop before keys, wallets, runtime, network, broadcast, or settlement |

## 7. Requirement-to-case traceability

The inventory is exhaustive for Foundation117 v0.1. Each requested requirement
maps to the listed immutable family/cases:

| # | Requirement | Case coverage |
|---:|---|---|
| 1 | Interface/profile/version compatibility | `CMP-POS-001`, `CMP-NEG-001`–`002`, `CMP-FCL-001` |
| 2 | Exact request envelope/schema/order | `SCH-POS-001`, `SCH-NEG-001`–`002`, `SCH-BND-001`, `SCH-FCL-001` |
| 3 | Exact response envelope/schema/order | `SCH-POS-002`, `SCH-NEG-003`–`004`, `SCH-FCL-001` |
| 4 | Caller/operator/public identity evidence | all `IDN-*`; `OPR-*` |
| 5 | Authorization evidence | all `AUT-*`; `ATH-NEG-003` |
| 6 | Authorization != Protocol validation | `AUT-POS-001`, `AUT-NEG-001`, `AUT-BND-001`, `AUT-FCL-001` |
| 7 | Mandatory `validate_transaction` binding | all `VAL-*`; `FWL-NEG-003`, `FWL-FCL-001` |
| 8 | Eligibility != signer invocation | all `ELG-*`; `NEX-POS-001`, `NEX-NEG-001` |
| 9 | Spending limits | all `LIM-*`; `FWL-BND-001` |
| 10 | Approval thresholds and duplicate/invalid approvals | all `APR-*`; `ATH-NEG-004` |
| 11 | Replay/idempotency and missing state | all `RPL-*`; `PRE-NEG-001` |
| 12 | Expiration/time boundaries and unavailable time | all `EXP-*`; `OPR-NEG-003`, `OPR-BND-001` |
| 13 | Operator scope/expiry/mismatch | all `OPR-*` |
| 14 | Authenticated-evidence requirements | all `ATH-*`; `IDN-FCL-001`, `OPR-FCL-001` |
| 15 | Canonical serialization/digests | all `CAN-*`; `AUD-BND-001` |
| 16 | Stable fail-closed status/error precedence | all `PRE-*`; every NEG/FCL expected code |
| 17 | Audit/public receipt boundaries | all `AUD-*` |
| 18 | Authority firewall | all `FWL-*`; common Section 4 assertions |
| 19 | All non-execution assertions | all `NEX-*`; common Section 5 assertions on every case |
| 20 | Unresolved F116/F117 GAP/BLOCKED gates | all `GAT-*`; `RPL-FCL-001`, `EXP-FCL-001`, `ATH-FCL-001` |

Shortened IDs in this table retain the full prefix
`LSI-CONF-v0.1-`. No requirement relies on an unplanned case.

## 8. Planned case counts

| Family | POS | NEG | BND | FCL | Total |
|---|---:|---:|---:|---:|---:|
| Compatibility (`CMP`) | 1 | 2 | 0 | 1 | 4 |
| Schemas (`SCH`) | 2 | 4 | 1 | 1 | 8 |
| Identities (`IDN`) | 1 | 2 | 1 | 1 | 5 |
| Authorization (`AUT`) | 1 | 2 | 1 | 1 | 5 |
| Protocol validation (`VAL`) | 1 | 3 | 1 | 1 | 6 |
| Eligibility (`ELG`) | 1 | 2 | 0 | 1 | 4 |
| Limits (`LIM`) | 1 | 2 | 1 | 1 | 5 |
| Approvals (`APR`) | 1 | 3 | 1 | 1 | 6 |
| Replay (`RPL`) | 1 | 2 | 1 | 1 | 5 |
| Expiration (`EXP`) | 1 | 2 | 2 | 1 | 6 |
| Operator (`OPR`) | 1 | 3 | 1 | 1 | 6 |
| Authentication (`ATH`) | 1 | 4 | 0 | 1 | 6 |
| Canonical/digests (`CAN`) | 1 | 3 | 1 | 1 | 6 |
| Precedence (`PRE`) | 1 | 1 | 1 | 1 | 4 |
| Audit (`AUD`) | 1 | 2 | 1 | 1 | 5 |
| Firewall (`FWL`) | 1 | 6 | 1 | 1 | 9 |
| Non-execution (`NEX`) | 1 | 3 | 0 | 1 | 5 |
| Gates (`GAT`) | 1 | 3 | 0 | 1 | 5 |
| **Total** | **19** | **49** | **14** | **18** | **100** |

The total follows the distinct normative branches and boundary conditions
listed above; it is not derived from an earlier milestone's count.

## 9. Future suite acceptance criteria

A later separately authorized fixture/specification/test milestone may claim
coverage of this plan only if it proves:

1. exactly the 100 immutable Section 6 case IDs, with no duplicate or silently
   renumbered IDs;
2. the Section 8 class/family counts;
3. complete Section 7 requirement traceability;
4. exact Foundation117 request/response/nested schema and order;
5. independent digest recomputation using exact Foundation117 domains and
   preimages;
6. exact stable status/code and first-failure precedence;
7. exact authority, Protocol, economics, and non-execution assertions;
8. mandatory validation binding without importing/invoking production signer,
   wallet, network, RPC, broadcast, settlement, or submission code;
9. deterministic offline public/disposable data only; and
10. no claim of authenticated production evidence, atomic production state,
    trusted production time, durable production audit, runtime hardening, or
    production readiness.

Passing that future suite would prove only offline conformance to this design.

## 10. Unresolved gates

### 10.1 `GAP_REQUIRES_FUTURE_WORK`

- authenticated identities, authorization, policies, approvals, and operator
  evidence, including provenance, revocation, and administration;
- key custody and lifecycle architecture and verification;
- atomic replay, idempotency, cumulative-spend, approval-consumption,
  concurrency, persistence, recovery, retention, and rollback;
- trusted production time, skew, rollback, outage, and monotonicity;
- durable/tamper-evident/private audit and receipt storage;
- parser/resource/rate/process/DoS/monitoring/service hardening; and
- production integration, validation-delegation proof, adversarial/runtime
  testing, operations, and independent security review.

### 10.2 `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

The following remain explicitly blocked and unchanged:

- signer implementation, runtime, or activation;
- production proof architecture;
- Bitcoin confirmation count and confirmation/reorg policy;
- observer quorum and observer independence; and
- unresolved custody and runtime security gates from Foundation116.

This plan selects no architecture, count, quorum, custody mechanism, runtime
policy, or fallback value.

## 11. Explicit non-activation conclusion

Foundation118 defines conformance requirements only for the future public local
signer eligibility boundary. It authorizes zero signer invocation, signing,
wallet/key access, signature creation, RPC, network, submission, broadcast,
state mutation, settlement, deployment, testnet, DigitalOcean infrastructure,
or runtime behavior.

No fixture, test, schema file, dependency, or implementation is created.
Implementation remains blocked pending Foundation116/Foundation117 security
gates, independent review, and separate operator authorization.

## 12. Document control

| Field | Value |
|---|---|
| Foundation | 118 |
| Parent | `01eb5620628ec33e0ea6c7aadbc39ba7ad8623c4` |
| Path | `docs/local_signer_interface_conformance_plan_v0.1.md` |
| Plan version | `local-signer-interface-conformance-plan/v0.1` |
| Interface | `l28-local-signer-interface/v0.1` |
| Planned cases | 100 |
| Families | 18 |
| POS / NEG / BND / FCL | 19 / 49 / 14 / 18 |
| Fixtures/tests/schemas/runtime/dependencies | none |
| Protocol/economics changes | none |
| Activation | none |
| Commit/merge/push | none |
| Foundation119 begun | no |
