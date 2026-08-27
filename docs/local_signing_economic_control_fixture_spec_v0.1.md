# Local Signing / Economic Control Fixture Specification v0.1

**Foundation:** 113

**Status:** documentation and fixture specification only / non-activating

**Fixture specification version:**
`local-signing-economic-control-fixture-spec/v0.1`

**Fixture schema:** `l28-local-signing-economic-control-fixture/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Parent:** `06ceb9a6654b674136828402444978e3c6099d39`

**Branch:** `foundation113-local-signing-economic-control-fixture-spec`

**Authoritative inputs:**

- `docs/local_signing_economic_control_architecture_review_v0.1.md`
  (Foundation 111)
- `docs/local_signing_economic_control_conformance_plan_v0.1.md`
  (Foundation 112; 56 planned cases)

**Implementation:** none

**Fixtures created:** none

**Tests or runtime code created:** none

**Normative subordination:** This specification is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md), Foundation 111, Foundation 112, and the
canonical Universal Access Interface. On conflict, Protocol v1.0.0 prevails.
This specification defines the exact shape and expected semantics of future
fictional offline fixtures. It does not authorize creation of those fixtures,
implement a runner, create custody, invoke a signer, or activate settlement.

---

## 1. Purpose and non-activation

Foundation 113 specifies one deterministic machine-readable fixture format for
all 56 Foundation 112 local-signing/economic-control cases. Each future fixture
will describe public fictional input, a deterministic expected result, authority
assertions, non-execution flags, safety assertions, and canonical digests.

The schema represents a **non-signing conformance boundary**. A passing fixture
would prove only that an offline evaluator preserves authority separation and
fails closed. It would not prove key custody, wallet safety, signature validity,
transaction submission, L28 settlement, production readiness, or operator
authorization for runtime activation.

Foundation 113 does not:

- create JSON fixtures;
- add tests, schemas as executable files, dependencies, or runtime code;
- generate, import, request, expose, store, or use keys;
- create or import wallets;
- sign or broadcast;
- connect to RPC, P2P, HTTP, or any network;
- implement or invoke a signer runtime;
- submit a transaction, mutate a ledger, or activate settlement; or
- alter Protocol v1.0.0, `validate_transaction`, consensus, issuance, supply,
  history, canonical height, or protected economic facts.

---

## 2. Preserved authority and economic invariants

Every future fixture MUST preserve these authority facts:

1. L28 Protocol v1.0.0 remains the sole consensus, issuance, canonical-height,
   history, and native settlement authority.
2. `coin.tx_validation.validate_transaction` remains mandatory for every
   proposed L28 transaction.
3. Authorization is not validation. An `allowed` authorization result cannot
   replace an `accepted` Protocol-validation result.
4. A signature, if a later milestone ever permits one, is not validation,
   consensus, settlement, issuance, or canonical height.
5. The signer remains a future isolated authority only and is never invoked by
   this fixture profile.
6. Harness/Evals output is advisory only and removable without changing L28
   core semantics.
7. Bitcoin material is labeled external evidence only and has zero authority
   over L28 signing, validation, settlement, issuance, supply, height, history,
   or consensus.
8. Missing, stale, malformed, conflicting, or unavailable required evidence
   fails closed.

Protected economic facts are immutable fixture assertions:

| Field | Exact value |
|---|---:|
| `hard_cap_l28` | `28000000` |
| `emission_ceiling_l28` | `11130000` |
| `historically_mined_l28` | `2824584` |
| `treasury_locked_l28` | `500000` |
| `circulating_snapshot_l28` | `2324584` |
| `halving_interval` | `210000` |
| `reward_schedule` | `[28,14,7,3,1,0]` |
| `historical_mined_through_entry` | `100877` |
| `next_canonical_height_after_bootstrap` | `100878` |

No fixture may recalculate, round, migrate, replace, or reinterpret these
values. Disposable fixture balances and heights are never canonical evidence.

---

## 3. Fixture and case identifiers

### 3.1 Case ID

Foundation 112 case identifiers are immutable and retain this exact grammar:

`LSEC-CONF-v0.1-<FAMILY>-<POS|NEG|BND|FCL>-<NNN>`

Allowed families are exactly:

`ISO`, `AUT`, `VAL`, `KEY`, `LIM`, `APR`, `RPL`, `EXP`, `AUD`, `OPR`, `EXT`,
and `ECO`.

### 3.2 Fixture ID

Each case maps one-to-one to one future fixture ID:

`fx-lsec-v01-<family-lower>-<class-lower>-<nnn>`

Examples:

- `LSEC-CONF-v0.1-ISO-POS-001` → `fx-lsec-v01-iso-pos-001`
- `LSEC-CONF-v0.1-LIM-BND-002` → `fx-lsec-v01-lim-bnd-002`
- `LSEC-CONF-v0.1-ECO-FCL-001` → `fx-lsec-v01-eco-fcl-001`

Fixture IDs and case IDs MUST be unique, MUST NOT be reused, and MUST NOT be
renumbered silently. One fixture MUST NOT claim coverage for multiple cases.

---

## 4. Canonical JSON and deterministic serialization

Future fixtures MUST use the following deterministic rules:

1. UTF-8 JSON without BOM.
2. One top-level JSON object.
3. Exact property order at every object level as specified below.
4. No duplicate or unknown properties.
5. No floats, `NaN`, `Infinity`, bytes, tuples, sets, comments, or trailing data.
6. Exact built-in JSON integers for amounts, counts, heights, and Unix seconds;
   booleans are not integers.
7. Lowercase hexadecimal SHA-256 identifiers of exactly 64 characters.
8. Strings are emitted without Unicode normalization or hidden coercion.
9. Compact serialization uses `ensure_ascii=false`, separators `(",", ":")`,
   `sort_keys=false`, and `allow_nan=false` semantics.
10. Object order is schema order, not lexical key order.
11. Arrays preserve declared order. Approval identities MUST additionally be
    distinct and sorted by `approver_id` unless the case intentionally tests
    duplication or ordering rejection.
12. All time evaluation uses fixture-supplied integers; no system, environment,
    RPC, network, timezone, or filesystem clock is permitted.

Canonical fixture digest:

`fixture_sha256 = SHA-256(canonical UTF-8 bytes of the complete fixture with canonical.fixture_sha256 set to "")`

Canonical input digest:

`input_sha256 = SHA-256(canonical UTF-8 bytes of input)`

Expected report identifier:

`report_id = SHA-256("L28-LSEC-CONFORMANCE-V0.1\x00" || canonical UTF-8 bytes of expected without report_id)`

Every digest is lowercase hexadecimal. A future fixture file SHOULD end with
exactly one LF; the LF is not part of the canonical JSON digest.

---

## 5. Exact top-level fixture schema

Every future fixture MUST contain exactly these fields in this order:

1. `fixture_schema`
2. `fixture_spec_version`
3. `plan_version`
4. `fixture_id`
5. `case_id`
6. `family`
7. `class`
8. `description`
9. `fixed_clock`
10. `public_identities`
11. `input`
12. `expected`
13. `authority_assertions`
14. `safety_assertions`
15. `canonical`

### 5.1 Top-level field requirements

| Field | Type | Required rule |
|---|---|---|
| `fixture_schema` | string | Exact `l28-local-signing-economic-control-fixture/v0.1` |
| `fixture_spec_version` | string | Exact `local-signing-economic-control-fixture-spec/v0.1` |
| `plan_version` | string | Exact `local-signing-economic-control-conformance-plan/v0.1` |
| `fixture_id` | string | Section 3.2 grammar; matches `case_id` components |
| `case_id` | string | Exact Foundation 112 ID from Section 14 inventory |
| `family` | string | Exact lowercase family name from Section 6 |
| `class` | string | `positive`, `negative`, `boundary`, or `fail_closed` |
| `description` | string | Non-empty public description; no paths, hosts, or secrets |
| `fixed_clock` | object | Exact Section 5.2 shape |
| `public_identities` | object | Exact Section 5.3 shape; fictional only |
| `input` | object | Exact Section 6 shape |
| `expected` | object | Exact Section 7 shape |
| `authority_assertions` | object | Exact Section 8 shape; fixed values |
| `safety_assertions` | object | Exact Section 9 shape; fixed values |
| `canonical` | object | Exact Section 10 shape |

### 5.2 `fixed_clock` exact order

1. `evaluation_time`
2. `created_at`
3. `not_before`
4. `expires_at`
5. `replay_retention_until`

All fields are exact non-negative integers. `not_before <= evaluation_time` and
`evaluation_time < expires_at` on ordinary positive cases. Boundary and
negative cases vary only the field named by their case profile.

### 5.3 `public_identities` exact order

1. `payer_id`
2. `payee_id`
3. `operator_id`
4. `approver_ids`
5. `signer_public_key_id`

All identities are fictional non-empty strings. `approver_ids` is an array of
fictional public identifiers. `signer_public_key_id` is public metadata only;
it MUST NOT contain a public-key byte string, signature, private material, or a
reference that can load a wallet.

---

## 6. Exact `input` schema

Every fixture `input` contains exactly these objects in this order, even when a
case marks one object unavailable or intentionally invalid:

1. `intent`
2. `policy`
3. `approvals`
4. `replay_view`
5. `expiration_view`
6. `operator_authorization`
7. `protocol_validation`
8. `advisory_evidence`
9. `receipt_audit_evidence`
10. `case_probe`

Unavailable inputs use the explicit `available=false` field within the relevant
object. They MUST NOT be omitted except when the fixture intentionally tests a
missing-property parser failure; such a fixture stores the canonical valid
projection here and identifies the omitted target through `case_probe` so the
runner constructs the malformed candidate in memory without changing fixture
schema.

### 6.1 `intent` exact order

1. `intent_profile` — exact `l28-local-signing-intent-fixture/v0.1`
2. `intent_id` — 64 lowercase hex
3. `request_id` — 64 lowercase hex
4. `payer_id` — matches `public_identities.payer_id`
5. `payee_id` — matches `public_identities.payee_id`
6. `asset_id` — exact `L28`
7. `amount` — exact positive integer
8. `purpose` — non-empty public string
9. `created_at` — exact Unix-second integer
10. `not_before` — exact Unix-second integer
11. `expires_at` — exact Unix-second integer
12. `nonce` — non-empty public nonce
13. `proposed_transaction` — exact Section 6.1.1 object

#### 6.1.1 `proposed_transaction` exact order

1. `sender`
2. `receiver`
3. `amount`
4. `timestamp`
5. `nonce`
6. `type`
7. `coinbase`

Ordinary service-payment fixtures use `type="transfer"` and `coinbase=false`.
The `ECO-NEG-002` case intentionally varies the reserved/coinbase identity
through `case_probe`; it still cannot issue value and must be rejected through
mandatory Protocol validation.

### 6.2 `policy` exact order

1. `available` — boolean
2. `policy_id` — 64 lowercase hex or `""` when unavailable
3. `asset_id` — exact `L28` or `""` when unavailable
4. `per_transaction_limit` — non-negative integer
5. `cumulative_limit` — non-negative integer
6. `prior_authorized_total` — non-negative integer
7. `window_start` — non-negative integer Unix seconds
8. `window_end` — non-negative integer Unix seconds
9. `approval_threshold` — non-negative integer
10. `authorized_approver_ids` — array of distinct fictional public IDs
11. `operator_authorization_required` — boolean
12. `signer_boundary_authorized` — boolean; remains false in this profile unless
    a case models public eligibility, never signer invocation
13. `protocol_override_allowed` — MUST be false
14. `unlimited_spend_allowed` — MUST be false

`prior_authorized_total + intent.amount` is evaluated with exact integers and
without mutation. No policy field represents a Protocol balance or supply.

### 6.3 `approvals[]` exact order

Each public approval-evidence object contains:

1. `approval_id` — 64 lowercase hex
2. `approver_id` — fictional public identity
3. `intent_id` — exact intent binding
4. `policy_id` — exact policy binding
5. `approved_amount` — exact positive integer
6. `decision` — `approved` or `denied`
7. `created_at` — Unix seconds
8. `expires_at` — Unix seconds
9. `public_evidence_id` — 64 lowercase hex

Approval evidence contains no signature bytes, key material, wallet reference,
credential, or implicit authority. Duplicated `approver_id` values never count
twice.

### 6.4 `replay_view` exact order

1. `available` — boolean
2. `view_id` — 64 lowercase hex or `""` when unavailable
3. `intent_id` — exact intent ID
4. `request_id` — exact request ID
5. `status` — `absent`, `present`, `evicted`, `unavailable`, or `invalid`
6. `first_seen_at` — non-negative integer or `0` when absent/unavailable
7. `retention_until` — non-negative integer
8. `read_only` — MUST be true

Fixture evaluation never records, evicts, updates, or persists replay state.
`present` at or before `retention_until` is a replay rejection. At the exact
retention boundary, `present` remains a replay rejection for `RPL-BND-001`.

### 6.5 `expiration_view` exact order

1. `evaluation_time` — exact fixture-supplied Unix seconds
2. `intent_not_before`
3. `intent_expires_at`
4. `quote_expires_at`
5. `payment_expires_at`
6. `approvals_expire_at`
7. `operator_evidence_expires_at`
8. `clock_source` — exact `fixture_supplied`
9. `system_clock_read` — MUST be false
10. `network_clock_read` — MUST be false

The first failing required artifact controls the stable expiration result. The
selected `EXP-BND-001` fixture sets `evaluation_time == quote_expires_at`; under
the inherited UAII quote boundary the quote is expired and the expected code is
`artifact_expired`. No fixture defines consensus time.

### 6.6 `operator_authorization` exact order

1. `available` — boolean
2. `evidence_id` — 64 lowercase hex or `""` when unavailable
3. `operator_id` — fictional public operator identity
4. `decision` — `approved`, `denied`, or `unavailable`
5. `intent_id` — exact intent binding or `""` when unavailable
6. `policy_id` — exact policy binding or `""` when unavailable
7. `payer_id`
8. `payee_id`
9. `asset_id`
10. `maximum_amount` — non-negative integer
11. `created_at` — Unix seconds
12. `expires_at` — Unix seconds
13. `independent_security_review_id` — 64 lowercase hex or `""`
14. `scope_matches` — boolean

Operator evidence is public fixture evidence only. It is not a credential,
signature, spend, validation, broadcast, or settlement authorization.

### 6.7 `protocol_validation` exact order

1. `delegate` — exact `coin.tx_validation.validate_transaction`
2. `available` — boolean
3. `invocation_required` — MUST be true for a complete proposed transaction
4. `invoked` — expected delegate-invocation assertion
5. `transaction_input_sha256` — 64 lowercase hex or `""` if unavailable
6. `status` — `accepted`, `rejected`, `pending`, `unavailable`, or `not_invoked`
7. `reason` — stable Protocol reason or `""`
8. `alternate_validator_supplied` — boolean
9. `override_requested` — boolean
10. `ledger_context_available` — boolean
11. `consensus_context_available` — boolean
12. `issued_supply_context_available` — boolean
13. `read_only` — MUST be true

For every accepted complete flow, `invoked=true` and `status=accepted` are
required. A policy allow with `status=rejected`, `pending`, or `unavailable`
cannot reach signer eligibility. Protocol reason codes are preserved rather
than rewritten as local authorization success.

### 6.8 `advisory_evidence` exact order

1. `harness_evals_present` — boolean
2. `harness_evals_report_id` — 64 lowercase hex or `""`
3. `harness_evals_effect` — MUST be `advisory_only`
4. `bitcoin_evidence_present` — boolean
5. `bitcoin_evidence_id` — 64 lowercase hex or `""`
6. `bitcoin_effect` — MUST be `external_evidence_only`
7. `authority_claimed` — MUST be false except an intentional negative probe
8. `removal_changes_core_result` — MUST be false

No Bitcoin fixture field may select production proof architecture, confirmation
count, or observer quorum. Those decisions remain blocked under Section 13.

### 6.9 `receipt_audit_evidence` exact order

1. `available` — boolean
2. `audit_profile` — exact `l28-local-signing-economic-control-audit-fixture/v0.1`
3. `audit_id` — 64 lowercase hex or `""`
4. `intent_id`
5. `policy_id`
6. `authorization_status`
7. `validation_status`
8. `replay_status`
9. `expiration_status`
10. `approval_status`
11. `operator_status`
12. `settlement_evidence_status` — `not_supplied`, `verified_external_to_fixture`,
    or `unverified_claim`
13. `public_receipt_id` — 64 lowercase hex or `""`
14. `lineage_id` — 64 lowercase hex or `""`
15. `claims_signature_created` — MUST be false except negative probe
16. `claims_broadcast` — MUST be false except negative probe
17. `claims_ledger_mutation` — MUST be false except negative probe
18. `claims_consensus_change` — MUST be false except negative probe

Only public IDs, statuses, and digests are permitted. Receipt/audit evidence is
not L28 history, validation, settlement, custody, or authorization by itself.

### 6.10 `case_probe` exact order

1. `probe_kind` — stable public probe label
2. `target_path` — fixture-schema logical path, never a host filesystem path
3. `operation` — `none`, `replace`, `omit`, `duplicate`, `reorder`, or `claim`
4. `public_value` — JSON scalar/object/array containing public fictional data only
5. `public_marker` — `""` or exact
   `DISPOSABLE-FORBIDDEN-MARKER-NOT-A-KEY`

`case_probe` makes negative and malformed candidates deterministic without
placing real secret material or environment-derived values in a fixture.

---

## 7. Exact `expected` result schema

Every expected result contains exactly these fields in order:

1. `ok` — boolean
2. `outcome` — `accept`, `reject`, or `blocked`
3. `code` — stable code from Section 11
4. `case_id` — exact echo
5. `family` — exact lowercase family
6. `authorization_status` — `allowed`, `denied`, `pending`, or `not_evaluated`
7. `validation_status` — `accepted`, `rejected`, `pending`, `unavailable`, or
   `not_invoked`
8. `signer_edge_status` — `eligible_public_projection`, `blocked`, or `not_reached`
9. `limit_status` — `within_limit`, `exceeded`, `unavailable`, or `not_evaluated`
10. `approval_status` — `threshold_met`, `threshold_not_met`, `unavailable`, or
    `not_evaluated`
11. `replay_status` — `fresh`, `replayed`, `unavailable`, or `not_evaluated`
12. `expiration_status` — `active`, `expired`, `not_yet_valid`, `unavailable`, or
    `not_evaluated`
13. `operator_status` — `approved`, `denied`, `mismatch`, `unavailable`, or
    `not_evaluated`
14. `audit_status` — `public_evidence_valid`, `invalid`, `unavailable`, or
    `not_evaluated`
15. `protocol_reason` — exact preserved Protocol reason or `""`
16. `detail` — MUST be `""`; no secret, path, stack, host, or environment detail
17. `report_id` — 64 lowercase hex under Section 4, or `""` for pre-report failure
18. `non_execution` — exact Section 7.1 object

`ok=true` means only that the offline case's expected conformance outcome is an
accept outcome. It never means a transaction was signed, submitted, broadcast,
settled, or recorded.

### 7.1 `non_execution` exact order and values

1. `signing_attempted` — false
2. `signature_created` — false
3. `wallet_accessed` — false
4. `transaction_submitted` — false
5. `broadcast_attempted` — false
6. `rpc_connected` — false
7. `network_connected` — false
8. `replay_state_mutated` — false
9. `ledger_mutated` — false
10. `settlement_finalized` — false
11. `consensus_modified` — false
12. `execution_authorized` — false

All values MUST be JSON false on every POS, NEG, BND, and FCL case.

---

## 8. Exact `authority_assertions` schema

Every fixture contains these fields in order with these exact values:

1. `l28_consensus_authority` — true
2. `l28_settlement_authority` — true
3. `validate_transaction_mandatory` — true
4. `authorization_equals_validation` — false
5. `signer_isolated_future_only` — true
6. `signer_may_override_protocol` — false
7. `harness_evals_advisory_only` — true
8. `bitcoin_external_evidence_only` — true
9. `adapter_transport_only` — true
10. `issuance_override_allowed` — false
11. `supply_override_allowed` — false
12. `height_override_allowed` — false
13. `history_override_allowed` — false
14. `validation_override_allowed` — false
15. `consensus_override_allowed` — false
16. `historical_evidence_mutable` — false
17. `protected_economic_facts` — exact Section 2 object in table order
18. `blocked_security_decision_status` — exact
    `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

A mismatch in any assertion is `authority_assertion_invalid` and fails closed.

---

## 9. Exact `safety_assertions` schema

Every fixture contains these fields in order, all false except where stated:

1. `contains_private_keys` — false
2. `contains_seed_phrases` — false
3. `contains_mnemonics` — false
4. `contains_xprv` — false
5. `contains_wallet_secrets` — false
6. `contains_credentials` — false
7. `contains_rpc_credentials` — false
8. `contains_production_addresses` — false
9. `contains_real_balances_or_transactions` — false
10. `contains_environment_values` — false
11. `generates_or_imports_keys` — false
12. `creates_or_imports_wallets` — false
13. `signs` — false
14. `broadcasts` — false
15. `connects_network` — false
16. `mutates_replay_state` — false
17. `mutates_ledger` — false
18. `activates_settlement` — false
19. `changes_protocol_or_economics` — false
20. `public_fictional_data_only` — true

The disposable forbidden marker defined in Section 6.10 is not secret material.
A future runner MUST inspect structure and values without scanning environment,
wallet, keychain, browser, SSH, or Bitcoin Core configuration.

---

## 10. Exact `canonical` schema

1. `algorithm` — exact `sha256-utf8-exact-order-json`
2. `field_order_enforced` — true
3. `input_sha256` — 64 lowercase hex
4. `expected_report_id` — 64 lowercase hex or `""`
5. `fixture_sha256` — 64 lowercase hex

Future fixture materialization MUST independently recompute all three digests.
A mismatch is `canonical_digest_mismatch` and fails before semantic acceptance.

---

## 11. Stable result and rejection codes

No future runner may invent, coerce, alias, or silently replace codes in this
profile. The stable set is:

### 11.1 Accept/boundary codes

| Code | Meaning |
|---|---|
| `isolated_boundary_ok` | Public projection reaches the inactive signer edge |
| `public_metadata_ok` | Public identifier/digest metadata only |
| `authorization_validation_separated` | Separate authorization and validation statuses preserved |
| `protocol_validation_pending` | Authorization allowed but validation not complete; remains blocked |
| `protocol_validation_accepted` | Mandatory delegate accepted read-only candidate |
| `public_custody_boundary_ok` | Public-only custody boundary preserved |
| `spending_limits_ok` | Local limits satisfied without spend |
| `approval_threshold_met` | Distinct public approvals meet threshold |
| `replay_fresh` | Read-only replay view reports absent |
| `expiration_active` | All required fixture-supplied lifetimes active |
| `audit_evidence_ok` | Deterministic public audit evidence valid |
| `operator_gate_satisfied` | Scoped public operator evidence accepted |
| `external_evidence_advisory` | Advisory/external evidence has no authority |
| `protected_economics_preserved` | Protected facts exactly preserved |

### 11.2 Rejection/fail-closed codes

| Code | Meaning |
|---|---|
| `schema_invalid` | Missing, extra, reordered, or wrong-type property |
| `canonical_digest_mismatch` | Canonical digest or report ID mismatch |
| `authority_assertion_invalid` | Fixed authority/economic assertion changed |
| `signer_authority_forbidden` | Non-signer subsystem claims signing authority |
| `signer_not_authorized` | Future signer boundary lacks separate authorization |
| `authority_binding_invalid` | Authorization and validation evidence conflated/conflicting |
| `protocol_validation_rejected` | Mandatory Protocol validation rejects; reason preserved |
| `validation_override_forbidden` | Alternate validator or override supplied |
| `protocol_validation_unavailable` | Mandatory delegate/context unavailable |
| `secret_material_forbidden` | Forbidden secret/custody property probe present |
| `custody_boundary_violation` | Custody assigned outside future isolated signer |
| `per_transaction_limit_exceeded` | Intent amount exceeds local per-transaction cap |
| `cumulative_limit_exceeded` | Prior total plus intent exceeds cumulative cap |
| `spending_policy_unavailable` | Required limit/policy evidence invalid or unavailable |
| `approval_threshold_not_met` | Too few distinct authorized approvals |
| `duplicate_approval` | Same approver counted more than once |
| `approval_policy_unavailable` | Threshold/approver authority invalid or unavailable |
| `replay_detected` | Identifier present within retention, including exact boundary |
| `replay_state_unavailable` | Replay view unavailable, malformed, stale, or inconsistent |
| `artifact_expired` | First required artifact expired |
| `not_yet_valid` | Required artifact not yet valid |
| `evaluation_time_unavailable` | Caller-supplied evaluation time absent/invalid |
| `settlement_claim_unverified` | Receipt claims settlement without independent evidence |
| `audit_authority_forbidden` | Audit claims signing, mutation, broadcast, or consensus authority |
| `audit_lineage_invalid` | Audit lineage missing or conflicting |
| `operator_authorization_denied` | Operator evidence explicitly denies |
| `operator_authorization_mismatch` | Operator scope does not bind exact intent/policy/parties/amount |
| `operator_gate_unavailable` | Required operator/security-review evidence unavailable |
| `advisory_authority_forbidden` | Harness/Evals advisory output claims authority |
| `external_evidence_authority_forbidden` | Bitcoin/external evidence claims L28 authority |
| `future_security_decision_required` | Blocked production proof/confirmation/quorum value attempted |
| `protocol_override_forbidden` | Signer/policy attempts to alter Protocol/economics/history |
| `ledger_state_unavailable` | Required canonical ledger/supply/height/history binding absent |

For `ECO-NEG-002`, the outer code is `protocol_validation_rejected` and
`protocol_reason` preserves the exact `validate_transaction` rejection (for
example `reserved_sender_misuse`) supplied by the locked future fixture.

---

## 12. Expected invariants by family

| Family | Required input focus | Expected invariant across POS/NEG/BND/FCL |
|---|---|---|
| `ISO` | Public signer-edge projection and signer-boundary authorization | Future signer remains inactive, isolated, and subordinate |
| `AUT` | Separate policy authorization and Protocol-validation evidence | Authorization never equals or overrides validation |
| `VAL` | Exact mandatory delegate, input digest, context availability, result | `validate_transaction` invoked when complete; rejection/unavailability blocks |
| `KEY` | Public IDs and forbidden-property probes only | No key/wallet access; secret input rejected without echo |
| `LIM` | Per-transaction/cumulative limits, prior total, window | Exact integer boundaries; unknown never means unlimited |
| `APR` | Threshold, authorized approvers, distinct public approval evidence | Only distinct valid approvals count; threshold does not authorize settlement |
| `RPL` | Read-only status, IDs, first-seen and retention times | Present within retention rejects; unavailable never means fresh |
| `EXP` | Fixture-supplied evaluation and artifact lifetimes | No implicit clock; first expiration/not-before failure wins |
| `AUD` | Public lineage, audit/receipt IDs and non-authority claims | Evidence is deterministic and cannot rewrite history or claim settlement |
| `OPR` | Explicit scope-matching public operator/security-review evidence | Missing/denied/mismatched gate blocks; approval is not validation |
| `EXT` | Harness/Evals advisory and Bitcoin external-evidence labels | Core result independent of advisory evidence; no external authority |
| `ECO` | Protected facts and authoritative ledger/consensus context | No signer/policy override of issuance, supply, height, history, validation, consensus |

All families preserve every Section 7.1 false flag.

---

## 13. Fail-closed precedence

A future runner MUST stop at the first applicable failure in this order:

1. fixture byte/encoding/JSON failure → `schema_invalid`;
2. duplicate, unknown, missing, reordered, or wrong-type field → `schema_invalid`;
3. canonical digest/report mismatch → `canonical_digest_mismatch`;
4. secret/custody probe → `secret_material_forbidden` or
   `custody_boundary_violation`;
5. authority/protected-fact mismatch → `authority_assertion_invalid` or
   `protocol_override_forbidden`;
6. blocked external security-decision attempt →
   `future_security_decision_required`;
7. replay failure;
8. expiration/not-before failure;
9. spending-limit failure;
10. approval-threshold failure;
11. operator-authorization failure;
12. authorization/validation binding failure;
13. mandatory `validate_transaction` rejection/unavailability;
14. audit/receipt lineage or authority failure; and
15. deterministic accept/boundary result.

The runner MUST NOT repair input, infer missing authority, assume unlimited
spend, assume absent replay, read implicit time, invent an approval threshold,
replace a Protocol reason, or call a signer as a fallback.

The following remain exactly:

`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

- production proof architecture;
- Bitcoin confirmation count; and
- observer quorum.

No fixture may define a default, range, threshold, or fallback value for those
items.

---

## 14. Complete 56-fixture inventory and mapping

The inventory below is exhaustive. `Expected code` is the outer fixture result;
`protocol_reason` is additionally required where stated.

### 14.1 `ISO` — isolated signer boundary

| Case ID | Fixture ID | Class | Input profile / probe | Expected code | Required invariant |
|---|---|---|---|---|---|
| `LSEC-CONF-v0.1-ISO-POS-001` | `fx-lsec-v01-iso-pos-001` | POS | All public gates satisfied; signer edge modeled only | `isolated_boundary_ok` | Eligible public projection; signer not invoked |
| `LSEC-CONF-v0.1-ISO-NEG-001` | `fx-lsec-v01-iso-neg-001` | NEG | Adapter/Harness claims signer authority | `signer_authority_forbidden` | No delegation or custody transfer |
| `LSEC-CONF-v0.1-ISO-BND-001` | `fx-lsec-v01-iso-bnd-001` | BND | Public key ID, identities, and digests only | `public_metadata_ok` | Public metadata grants no signing authority |
| `LSEC-CONF-v0.1-ISO-FCL-001` | `fx-lsec-v01-iso-fcl-001` | FCL | `signer_boundary_authorized=false` | `signer_not_authorized` | Absence is never default-allow |

### 14.2 `AUT` — authorization versus validation

| Case ID | Fixture ID | Class | Input profile / probe | Expected code | Required invariant |
|---|---|---|---|---|---|
| `LSEC-CONF-v0.1-AUT-POS-001` | `fx-lsec-v01-aut-pos-001` | POS | Authorization allowed; validation accepted | `authorization_validation_separated` | Separate statuses; no execution |
| `LSEC-CONF-v0.1-AUT-NEG-001` | `fx-lsec-v01-aut-neg-001` | NEG | Authorization allowed; validation rejected | `protocol_validation_rejected` | Protocol reason preserved; signer edge blocked |
| `LSEC-CONF-v0.1-AUT-BND-001` | `fx-lsec-v01-aut-bnd-001` | BND | Authorization allowed; validation pending | `protocol_validation_pending` | Authorization alone remains blocked |
| `LSEC-CONF-v0.1-AUT-FCL-001` | `fx-lsec-v01-aut-fcl-001` | FCL | Contradictory authorization/validation binding | `authority_binding_invalid` | Neither status inferred |

### 14.3 `VAL` — mandatory Protocol validation

| Case ID | Fixture ID | Class | Input profile / probe | Expected code | Required invariant |
|---|---|---|---|---|---|
| `LSEC-CONF-v0.1-VAL-POS-001` | `fx-lsec-v01-val-pos-001` | POS | Exact transaction delegated and accepted | `protocol_validation_accepted` | Mandatory delegate invoked read-only |
| `LSEC-CONF-v0.1-VAL-NEG-001` | `fx-lsec-v01-val-neg-001` | NEG | Alternate validator/override supplied | `validation_override_forbidden` | No alternate authority |
| `LSEC-CONF-v0.1-VAL-BND-001` | `fx-lsec-v01-val-bnd-001` | BND | Amount equals local maximum; Protocol accepts | `protocol_validation_accepted` | Local boundary cannot waive validation |
| `LSEC-CONF-v0.1-VAL-FCL-001` | `fx-lsec-v01-val-fcl-001` | FCL | Delegate or required context unavailable | `protocol_validation_unavailable` | No signer attempt or fallback |

### 14.4 `KEY` — key custody separation

| Case ID | Fixture ID | Class | Input profile / probe | Expected code | Required invariant |
|---|---|---|---|---|---|
| `LSEC-CONF-v0.1-KEY-POS-001` | `fx-lsec-v01-key-pos-001` | POS | Approved public identities/digests only | `public_custody_boundary_ok` | No wallet/key access |
| `LSEC-CONF-v0.1-KEY-NEG-001` | `fx-lsec-v01-key-neg-001` | NEG | Forbidden-property probe with disposable marker | `secret_material_forbidden` | Marker not echoed; no secret lookup |
| `LSEC-CONF-v0.1-KEY-BND-001` | `fx-lsec-v01-key-bnd-001` | BND | Valid public key ID only | `public_metadata_ok` | Identifier grants no authority |
| `LSEC-CONF-v0.1-KEY-FCL-001` | `fx-lsec-v01-key-fcl-001` | FCL | External subsystem designated custodian | `custody_boundary_violation` | No forwarding outside isolated future signer |

### 14.5 `LIM` — spending limits

| Case ID | Fixture ID | Class | Input profile / probe | Expected code | Required invariant |
|---|---|---|---|---|---|
| `LSEC-CONF-v0.1-LIM-POS-001` | `fx-lsec-v01-lim-pos-001` | POS | Amount below both limits | `spending_limits_ok` | No spend/signature/settlement |
| `LSEC-CONF-v0.1-LIM-NEG-001` | `fx-lsec-v01-lim-neg-001` | NEG | Amount above per-transaction limit | `per_transaction_limit_exceeded` | Exact integer comparison |
| `LSEC-CONF-v0.1-LIM-NEG-002` | `fx-lsec-v01-lim-neg-002` | NEG | Prior total plus amount above cumulative cap | `cumulative_limit_exceeded` | No rollover or mutation |
| `LSEC-CONF-v0.1-LIM-BND-001` | `fx-lsec-v01-lim-bnd-001` | BND | Amount equals per-transaction limit | `spending_limits_ok` | Equality passes locally; validation mandatory |
| `LSEC-CONF-v0.1-LIM-BND-002` | `fx-lsec-v01-lim-bnd-002` | BND | Prior total plus amount equals cumulative cap | `spending_limits_ok` | Equality passes; no implicit increase |
| `LSEC-CONF-v0.1-LIM-FCL-001` | `fx-lsec-v01-lim-fcl-001` | FCL | Policy/limit/window unavailable or inconsistent | `spending_policy_unavailable` | Unknown never means unlimited |

### 14.6 `APR` — approval thresholds

| Case ID | Fixture ID | Class | Input profile / probe | Expected code | Required invariant |
|---|---|---|---|---|---|
| `LSEC-CONF-v0.1-APR-POS-001` | `fx-lsec-v01-apr-pos-001` | POS | Distinct valid approvals exceed threshold | `approval_threshold_met` | Other gates remain required |
| `LSEC-CONF-v0.1-APR-NEG-001` | `fx-lsec-v01-apr-neg-001` | NEG | Distinct approvals below threshold | `approval_threshold_not_met` | No implicit approval |
| `LSEC-CONF-v0.1-APR-NEG-002` | `fx-lsec-v01-apr-neg-002` | NEG | Duplicate approver counted twice | `duplicate_approval` | Duplicate never increases count |
| `LSEC-CONF-v0.1-APR-BND-001` | `fx-lsec-v01-apr-bnd-001` | BND | Distinct approvals equal threshold | `approval_threshold_met` | Threshold does not authorize settlement |
| `LSEC-CONF-v0.1-APR-FCL-001` | `fx-lsec-v01-apr-fcl-001` | FCL | Threshold/approver authority unavailable | `approval_policy_unavailable` | Threshold never invented |

### 14.7 `RPL` — replay protection

| Case ID | Fixture ID | Class | Input profile / probe | Expected code | Required invariant |
|---|---|---|---|---|---|
| `LSEC-CONF-v0.1-RPL-POS-001` | `fx-lsec-v01-rpl-pos-001` | POS | Identifier absent | `replay_fresh` | Read-only; no recording |
| `LSEC-CONF-v0.1-RPL-NEG-001` | `fx-lsec-v01-rpl-neg-001` | NEG | Identifier present within retention | `replay_detected` | Reuse rejected |
| `LSEC-CONF-v0.1-RPL-BND-001` | `fx-lsec-v01-rpl-bnd-001` | BND | Present at exact retention boundary | `replay_detected` | Boundary inclusive for retained presence |
| `LSEC-CONF-v0.1-RPL-FCL-001` | `fx-lsec-v01-rpl-fcl-001` | FCL | Replay view unavailable/invalid/stale | `replay_state_unavailable` | Unknown never means fresh |

### 14.8 `EXP` — expiration controls

| Case ID | Fixture ID | Class | Input profile / probe | Expected code | Required invariant |
|---|---|---|---|---|---|
| `LSEC-CONF-v0.1-EXP-POS-001` | `fx-lsec-v01-exp-pos-001` | POS | All artifact lifetimes active | `expiration_active` | Fixture-supplied time only |
| `LSEC-CONF-v0.1-EXP-NEG-001` | `fx-lsec-v01-exp-neg-001` | NEG | Selected required artifact expired | `artifact_expired` | First failing artifact controls result |
| `LSEC-CONF-v0.1-EXP-NEG-002` | `fx-lsec-v01-exp-neg-002` | NEG | Intent not yet valid | `not_yet_valid` | No early authorization |
| `LSEC-CONF-v0.1-EXP-BND-001` | `fx-lsec-v01-exp-bnd-001` | BND | Evaluation equals quote expiry | `artifact_expired` | Inherited quote boundary applied exactly |
| `LSEC-CONF-v0.1-EXP-FCL-001` | `fx-lsec-v01-exp-fcl-001` | FCL | Evaluation time unavailable/implicit | `evaluation_time_unavailable` | No system/network clock |

### 14.9 `AUD` — receipts and audit evidence

| Case ID | Fixture ID | Class | Input profile / probe | Expected code | Required invariant |
|---|---|---|---|---|---|
| `LSEC-CONF-v0.1-AUD-POS-001` | `fx-lsec-v01-aud-pos-001` | POS | Public audit binds all completed checks | `audit_evidence_ok` | Evidence only; no history/settlement claim |
| `LSEC-CONF-v0.1-AUD-NEG-001` | `fx-lsec-v01-aud-neg-001` | NEG | Receipt claims unverified settlement | `settlement_claim_unverified` | Receipt cannot create settlement truth |
| `LSEC-CONF-v0.1-AUD-NEG-002` | `fx-lsec-v01-aud-neg-002` | NEG | Audit claims signing/broadcast/mutation/consensus | `audit_authority_forbidden` | Audit has no execution authority |
| `LSEC-CONF-v0.1-AUD-BND-001` | `fx-lsec-v01-aud-bnd-001` | BND | Identical canonical input repeated | `audit_evidence_ok` | Identical body/report ID bytes |
| `LSEC-CONF-v0.1-AUD-FCL-001` | `fx-lsec-v01-aud-fcl-001` | FCL | Lineage missing/conflicting | `audit_lineage_invalid` | No repair or invented lineage |

### 14.10 `OPR` — operator authorization gates

| Case ID | Fixture ID | Class | Input profile / probe | Expected code | Required invariant |
|---|---|---|---|---|---|
| `LSEC-CONF-v0.1-OPR-POS-001` | `fx-lsec-v01-opr-pos-001` | POS | Current exact-scope operator evidence | `operator_gate_satisfied` | Gate satisfied; signer remains inactive |
| `LSEC-CONF-v0.1-OPR-NEG-001` | `fx-lsec-v01-opr-neg-001` | NEG | Operator decision denied | `operator_authorization_denied` | Denial blocks |
| `LSEC-CONF-v0.1-OPR-NEG-002` | `fx-lsec-v01-opr-neg-002` | NEG | Evidence binds different scope | `operator_authorization_mismatch` | Exact intent/policy/parties/amount required |
| `LSEC-CONF-v0.1-OPR-BND-001` | `fx-lsec-v01-opr-bnd-001` | BND | Exact max amount and lifetime scope | `operator_gate_satisfied` | Equality passes; validation mandatory |
| `LSEC-CONF-v0.1-OPR-FCL-001` | `fx-lsec-v01-opr-fcl-001` | FCL | Evidence/security review missing/stale/unverifiable | `operator_gate_unavailable` | Absence is not consent |

### 14.11 `EXT` — external subsystem non-authority

| Case ID | Fixture ID | Class | Input profile / probe | Expected code | Required invariant |
|---|---|---|---|---|---|
| `LSEC-CONF-v0.1-EXT-POS-001` | `fx-lsec-v01-ext-pos-001` | POS | Labeled Harness/Evals advisory report | `external_evidence_advisory` | Removal leaves core result unchanged |
| `LSEC-CONF-v0.1-EXT-NEG-001` | `fx-lsec-v01-ext-neg-001` | NEG | Harness score claims signing/limit/settlement authority | `advisory_authority_forbidden` | Advisory only |
| `LSEC-CONF-v0.1-EXT-NEG-002` | `fx-lsec-v01-ext-neg-002` | NEG | Bitcoin observation claims L28 authority | `external_evidence_authority_forbidden` | Bitcoin external evidence only |
| `LSEC-CONF-v0.1-EXT-BND-001` | `fx-lsec-v01-ext-bnd-001` | BND | Advisory/Bitcoin evidence absent | `external_evidence_advisory` | L28 core semantics identical |
| `LSEC-CONF-v0.1-EXT-FCL-001` | `fx-lsec-v01-ext-fcl-001` | FCL | Production proof/confirmation/quorum value attempted | `future_security_decision_required` | Blocked status unchanged |

### 14.12 `ECO` — Protocol and economic non-interference

| Case ID | Fixture ID | Class | Input profile / probe | Expected code | Required invariant |
|---|---|---|---|---|---|
| `LSEC-CONF-v0.1-ECO-POS-001` | `fx-lsec-v01-eco-pos-001` | POS | Exact protected facts echoed | `protected_economics_preserved` | No override permitted |
| `LSEC-CONF-v0.1-ECO-NEG-001` | `fx-lsec-v01-eco-neg-001` | NEG | Signer/policy attempts Protocol/economic override | `protocol_override_forbidden` | L28 remains authority |
| `LSEC-CONF-v0.1-ECO-NEG-002` | `fx-lsec-v01-eco-neg-002` | NEG | Reserved sender/coinbase service-payment probe | `protocol_validation_rejected` | Protocol reason preserved; no issuance |
| `LSEC-CONF-v0.1-ECO-BND-001` | `fx-lsec-v01-eco-bnd-001` | BND | Local cap equals protected economic value | `spending_limits_ok` | Local policy does not redefine economics |
| `LSEC-CONF-v0.1-ECO-FCL-001` | `fx-lsec-v01-eco-fcl-001` | FCL | Ledger/supply/height/history context unavailable | `ledger_state_unavailable` | State never inferred or synthesized |

Inventory total: **56 fixtures planned**, exactly matching Foundation 112.

---

## 15. Future materialization acceptance criteria

A later separately authorized fixture milestone may claim conformance only if:

1. exactly the 56 Section 14 JSON fixtures exist, with no extra case IDs;
2. every fixture/case mapping and POS/NEG/BND/FCL class matches this inventory;
3. every object uses the exact schema order and stable code defined here;
4. canonical digests and report identifiers recompute independently;
5. all authority and protected-economic assertions match exactly;
6. mandatory `validate_transaction` delegation assertions are proven for every
   complete proposed transaction;
7. all non-execution and safety flags retain their required values;
8. fixtures contain public fictional data only;
9. malformed/negative probes use disposable markers, not real secrets;
10. no runner reads system time, environment state, wallets, keys, RPC, or
    network state; and
11. identical canonical inputs produce identical public outcomes.

Passing those criteria still would not authorize keys, wallets, signing,
broadcast, networking, settlement, runtime implementation, or production use.

---

## 16. Explicit non-activation statement

Foundation 113 creates only this specification document. It creates no JSON
fixture, executable schema, test, runtime code, key, wallet, signature,
transaction, receipt, audit record, replay record, network connection, or
settlement state.

Nothing in this document changes:

- authorization versus validation separation;
- mandatory `validate_transaction` delegation;
- L28 consensus or settlement authority;
- the future isolated status of any signer;
- Harness/Evals advisory-only status;
- Bitcoin external-evidence-only status;
- Protocol v1.0.0 or protected economic facts; or
- `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

---

## 17. Document control

| Field | Value |
|---|---|
| Foundation | 113 |
| Parent | `06ceb9a6654b674136828402444978e3c6099d39` |
| Path | `docs/local_signing_economic_control_fixture_spec_v0.1.md` |
| Status | documentation/fixture specification only; non-activating |
| Source reviews | Foundations 111 and 112 |
| Planned fixture count | 56 |
| JSON fixtures created | none |
| Tests / runtime code added | none |
| Keys / wallets / signatures | none |
| Broadcast / RPC / network | none |
| Settlement activation | none |
| Protocol v1.0.0 | unchanged |
| `validate_transaction` | unchanged and mandatory |
| Protected economic facts | unchanged |
| Harness/Evals | advisory only |
| Bitcoin | external evidence only |
| Production proof / confirmation / quorum | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
