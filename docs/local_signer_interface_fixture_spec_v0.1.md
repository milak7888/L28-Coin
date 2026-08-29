# Local Signer Interface Fixture Specification v0.1

**Foundation:** 119

**Status:** documentation and future-fixture specification only / non-activating

**Fixture specification version:**
`local-signer-interface-fixture-spec/v0.1`

**Fixture schema:** `l28-local-signer-interface-fixture/v0.1`

**Plan:** `local-signer-interface-conformance-plan/v0.1`

**Interface:** `l28-local-signer-interface/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Required parent:** `d8a206c250ccbc278bf28c4a21c87110d46c1ce7`

**Branch:** `foundation119-local-signer-interface-fixture-spec`

**Implementation, JSON fixtures, executable schemas, tests, runner, runtime,
or activation:** none

**Normative subordination:** This specification is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md), Foundation116, Foundation117, and
Foundation118. On conflict, Protocol v1.0.0 prevails, then Foundation117, then
Foundation118, then this document. Foundation113 is used for structural
precedent only. This specification MUST NOT alter any Foundation118 case ID,
class, input focus, expected status, expected code, or invariant.

---

## 1. Purpose and non-activation

Foundation119 specifies the exact deterministic future JSON fixture contract
for all 100 immutable Foundation118 cases. It locks fixture identity, field
order, public fictional values, malformed-probe construction, expected response
shape, authority/non-execution assertions, digests, and the one-to-one
case-to-fixture inventory.

A future fixture is offline evidence only. It cannot prove production
authentication, custody, signer safety, runtime readiness, transaction
validation by a live process, signing, submission, broadcast, ledger mutation,
or settlement.

Foundation119 creates no JSON fixture and no executable artifact.

## 2. Preserved authority and economics

Every future fixture MUST preserve:

1. L28 Protocol v1.0.0 as sole issuance, supply, consensus, canonical-height,
   historical-ledger, validation, and native-settlement authority.
2. `coin.tx_validation.validate_transaction` as the mandatory Protocol
   validation delegate, represented by public binding evidence only and never
   invoked by fixture evaluation.
3. Authorization is not validation.
4. Signer eligibility is not signer invocation.
5. Harness/Evals is advisory only, Bitcoin is external evidence only, and
   adapters are transport only.

Protected economic assertions are exact:

| Field | Exact value |
|---|---:|
| `hard_cap_l28` | `28000000` (`28,000,000 L28`) |
| `emission_ceiling_l28` | `11130000` (`11,130,000 L28`) |
| `historically_mined_l28` | `2824584` (`2,824,584 L28`) |
| `treasury_locked_l28` | `500000` (`500,000 L28`) |
| `circulating_snapshot_l28` | `2324584` (`2,324,584 L28`) |
| `halving_interval` | `210000` (`210,000`) |
| `reward_schedule` | `[28,14,7,3,1,0]` (`28 → 14 → 7 → 3 → 1 → 0`) |
| `historical_mined_through_entry` | `100877` (`100,877`) |
| `next_canonical_height_after_bootstrap` | `100878` (`100,878`) |
| `issuance_mechanism` | `coinbase_only` |
| `canonical_height_authority` | `consensus_derived` |
| `historical_evidence_mutable` | `false` |

No fixture may recalculate, normalize, migrate, reinterpret, or override these
values. Disposable values are never canonical ledger evidence.

## 3. Fixture and case identities

### 3.1 Immutable case ID

The Foundation118 grammar remains:

`LSI-CONF-v0.1-<FAMILY>-<POS|NEG|BND|FCL>-<NNN>`

Families are exactly `CMP`, `SCH`, `IDN`, `AUT`, `VAL`, `ELG`, `LIM`, `APR`,
`RPL`, `EXP`, `OPR`, `ATH`, `CAN`, `PRE`, `AUD`, `FWL`, `NEX`, and `GAT`.

### 3.2 Fixture ID

Each case maps to exactly one fixture ID:

`fx-lsi-v01-<family-lower>-<class-lower>-<nnn>`

Example:

`LSI-CONF-v0.1-VAL-FCL-001` → `fx-lsi-v01-val-fcl-001`

Case and fixture IDs MUST be unique, MUST NOT be reused, and MUST NOT be
silently renumbered. The future filename MUST be `<fixture_id>.json`.
Foundation119 does not select or create the fixture directory.

## 4. Exact top-level fixture schema

Every future fixture contains exactly these properties in this order:

1. `fixture_schema`
2. `fixture_spec_version`
3. `plan_version`
4. `interface_profile`
5. `fixture_id`
6. `case_id`
7. `family`
8. `class`
9. `description`
10. `fixed_clock`
11. `public_identities`
12. `input`
13. `expected`
14. `authority_assertions`
15. `protected_economic_facts`
16. `safety_assertions`
17. `canonical`

Exact constants:

- `fixture_schema="l28-local-signer-interface-fixture/v0.1"`;
- `fixture_spec_version="local-signer-interface-fixture-spec/v0.1"`;
- `plan_version="local-signer-interface-conformance-plan/v0.1"`;
- `interface_profile="l28-local-signer-interface/v0.1"`;
- `family` is the lowercase case family;
- `class` is `positive`, `negative`, `boundary`, or `fail_closed`; and
- `description` is public, non-empty, and faithful to the exact Foundation118
  input focus and invariant.

## 5. Fixed fictional public data

### 5.1 `fixed_clock` exact order

1. `evaluation_time`
2. `created_at`
3. `not_before`
4. `expires_at`
5. `policy_window_start`
6. `policy_window_end`
7. `replay_retention_until`

Baseline integers are respectively `1700000100`, `1700000000`, `1700000000`,
`1700000300`, `1699999900`, `1700000400`, and `1700000500`. Cases vary only
the field named by their immutable F118 focus/probe.

### 5.2 `public_identities` exact order

1. `caller_id` — `caller-fixture-public-001`
2. `caller_public_identity` — `agent-caller-public-001`
3. `payer_id` — `agent-payer-public-001`
4. `payee_id` — `agent-payee-public-001`
5. `operator_id` — `operator-fixture-public-001`
6. `operator_public_identity` — `operator-public-identity-001`
7. `approver_ids` — ordered
   `["approver-public-001","approver-public-002","approver-public-003"]`
8. `signer_public_key_id` — `signer-public-key-id-disposable-001`

These are fictional public labels, not addresses with funds, keys, signatures,
credentials, wallet locators, or production identities.

### 5.3 Deterministic identifiers and nonces

All case-specific public 64-hex IDs are derived as:

```text
public_id(role) = hex_lower(
  SHA-256(
    b"L28-LOCAL-SIGNER-INTERFACE-FIXTURE-V0.1-ID\x00" ||
    UTF8(fixture_id) || b"\x00" || UTF8(role)
  )
)
```

`role` is one of the exact field paths that requires an ID. Equal bindings
reuse the same role/ID; distinct evidence uses distinct roles. Nonces are fixed
public strings `lsi-fixture-envelope-nonce-001` and
`lsi-fixture-transaction-nonce-001`, varied only by a named case probe.

## 6. Exact `input` and request schema

### 6.1 `input` exact order

1. `request`
2. `case_probe`

`request` is always the canonical valid projection. `case_probe` directs a
future runner to construct a test candidate in memory; malformed files are
never used to represent malformed-input cases.

### 6.2 Request top-level exact order

The embedded request contains exactly the 20 Foundation117 properties:

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

The profile/version/operation are exactly
`l28-local-signer-interface/v0.1`, `0.1`, and
`evaluate_signer_eligibility` in the canonical projection.

### 6.3 Request nested exact orders

`caller_identity_evidence`:

1. `evidence_profile`
2. `evidence_id`
3. `caller_id`
4. `caller_public_identity`
5. `caller_public_key_id`
6. `authentication_status`
7. `scope_request_id`
8. `issued_at`
9. `expires_at`
10. `public_evidence_only`

`operator_authorization_evidence`:

1. `evidence_profile`
2. `evidence_id`
3. `operator_id`
4. `operator_public_identity`
5. `authentication_status`
6. `decision`
7. `request_id`
8. `intent_id`
9. `policy_id`
10. `payer_id`
11. `payee_id`
12. `asset_id`
13. `maximum_amount`
14. `created_at`
15. `expires_at`
16. `independent_security_review_id`
17. `scope_matches`
18. `public_evidence_only`

`authorization_evidence`:

1. `evidence_profile`
2. `authorization_id`
3. `authorization_status`
4. `intent_id`
5. `request_id`
6. `policy_id`
7. `payer_id`
8. `payee_id`
9. `asset_id`
10. `amount`
11. `evaluator_id`
12. `authentication_status`
13. `created_at`
14. `expires_at`
15. `public_evidence_only`

`economic_policy`:

1. `policy_profile`
2. `policy_id`
3. `policy_status`
4. `authentication_status`
5. `asset_id`
6. `per_transaction_limit`
7. `cumulative_limit`
8. `prior_authorized_total`
9. `window_start`
10. `window_end`
11. `approval_threshold`
12. `authorized_approver_ids`
13. `operator_authorization_required`
14. `unlimited_spend_allowed`
15. `protocol_override_allowed`
16. `runtime_authorized`

Each `approvals[]` object:

1. `approval_id`
2. `approver_id`
3. `approver_public_identity`
4. `authentication_status`
5. `decision`
6. `request_id`
7. `intent_id`
8. `policy_id`
9. `approved_amount`
10. `created_at`
11. `expires_at`
12. `public_evidence_only`

`replay_evidence`:

1. `evidence_profile`
2. `evidence_id`
3. `available`
4. `request_id`
5. `intent_id`
6. `idempotency_key`
7. `status`
8. `first_seen_at`
9. `retention_until`
10. `state_version`
11. `atomicity_evidence_id`
12. `atomic_transition_status`
13. `read_only`

`time_evidence`:

1. `evidence_profile`
2. `evidence_id`
3. `evaluation_time`
4. `source`
5. `authentication_status`
6. `intent_not_before`
7. `intent_expires_at`
8. `authorization_expires_at`
9. `approvals_expire_at`
10. `operator_evidence_expires_at`
11. `policy_window_start`
12. `policy_window_end`
13. `system_clock_read`
14. `network_clock_read`

`proposed_transaction`:

1. `sender`
2. `receiver`
3. `amount`
4. `timestamp`
5. `nonce`
6. `type`
7. `coinbase`

Ordinary fixtures use `type="transfer"`, `coinbase=false`, and public fictional
parties. No case creates issuance.

`protocol_validation_binding`:

1. `binding_profile`
2. `delegate`
3. `invocation_required`
4. `available`
5. `invoked`
6. `status`
7. `reason`
8. `transaction_input_sha256`
9. `validation_report_id`
10. `ledger_context_id`
11. `consensus_context_id`
12. `issued_supply_context_id`
13. `alternate_validator_supplied`
14. `override_requested`
15. `read_only`
16. `binding_digest`

The canonical projection uses delegate
`coin.tx_validation.validate_transaction`, `invocation_required=true`,
`alternate_validator_supplied=false`, `override_requested=false`, and
`read_only=true`. Fixtures assert expected delegation; they MUST NOT import or
invoke production validation/runtime code.

## 7. Malformed and negative case probes

### 7.1 `case_probe` exact order

1. `probe_kind`
2. `target_path`
3. `operation`
4. `public_value`
5. `expected_precedence_rank`
6. `public_marker`

Allowed `operation` values are exactly `none`, `replace`, `omit`,
`insert_unknown`, `duplicate`, `reorder`, `truncate`, `encode_invalid`, and
`claim`.

`target_path` is a logical fixture/request/response path, never a host path.
`public_value` contains fictional JSON only. `public_marker` is `""` except
secret-boundary probes, which use exact
`DISPOSABLE-FORBIDDEN-MARKER-NOT-A-KEY`.

The runner MUST deep-copy the canonical projection, apply exactly one specified
probe (or the exact multi-failure probe required by F118 PRE cases), evaluate
the candidate, discard it, and leave fixture bytes/state unchanged. It MUST NOT
repair malformed input, read secrets, or echo forbidden marker values.

## 8. Exact `expected` and response schema

### 8.1 `expected` exact order

1. `status` — exact F118 `eligible_public_projection`, `blocked`, or `rejected`
2. `code` — exact F118 stable code
3. `response`

`expected.status` and `expected.code` MUST exactly match Section 14. A fixture
cannot alias or replace a code.

### 8.2 Response top-level exact order

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

`design_status` is always `DEFINED_DESIGN_ONLY`.

The exact response-status binding is:

| `expected.status` | `response.ok` | `eligibility.eligibility_status` | `error` |
|---|---|---|---|
| `eligible_public_projection` | true | `eligible_public_projection` | all four fields `""` |
| `blocked` | false | `blocked` | `error.code` equals `expected.code`; safe public remaining fields |
| `rejected` | false | `not_evaluated` | `error.code` equals `expected.code`; safe public remaining fields |

In all rows, response `code` equals `expected.code`. This fixture binding does
not change the Foundation117 status/code vocabulary.

### 8.3 Response nested exact orders

`eligibility`:

1. `authorization_status`
2. `validation_status`
3. `identity_status`
4. `policy_status`
5. `limit_status`
6. `approval_status`
7. `replay_status`
8. `expiration_status`
9. `operator_status`
10. `eligibility_status`
11. `signer_invocation_status`
12. `signing_authorized`
13. `spend_authorized`
14. `settlement_authorized`
15. `execution_authorized`

`signer_invocation_status` is always `not_invoked`; all four authorization
booleans are false.

`validation_binding`:

1. `delegate`
2. `transaction_input_sha256`
3. `validation_report_id`
4. `validation_status`
5. `protocol_reason`
6. `binding_digest`
7. `binding_preserved`

`public_audit_evidence`:

1. `evidence_profile`
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
12. `approval_ids`
13. `replay_evidence_id`
14. `time_evidence_id`
15. `validation_report_id`
16. `decision_code`
17. `evaluation_time`
18. `settlement_evidence_status`
19. `signature_evidence_status`
20. `public_evidence_only`

`settlement_evidence_status="not_supplied"`,
`signature_evidence_status="not_created"`, and
`public_evidence_only=true`. This is not a UAII signed receipt, signature,
settlement proof, ledger record, or Protocol history.

`error`:

1. `code`
2. `message`
3. `field`
4. `evidence_id`

On eligible success all are `""`. On blocked/rejected outcomes, the error code
matches `expected.code` and response `code`; all contents remain safe/public.

## 9. Exact authority and non-execution assertions

### 9.1 `authority_assertions` exact order/values

1. `protocol_version` — `1.0.0`
2. `l28_consensus_authority` — true
3. `l28_settlement_authority` — true
4. `validate_transaction_mandatory` — true
5. `authorization_equals_validation` — false
6. `eligibility_equals_invocation` — false
7. `signer_isolated_future_only` — true
8. `signer_may_override_protocol` — false
9. `issuance_override_allowed` — false
10. `supply_override_allowed` — false
11. `height_override_allowed` — false
12. `validation_override_allowed` — false
13. `consensus_override_allowed` — false
14. `history_override_allowed` — false
15. `settlement_override_allowed` — false
16. `historical_evidence_mutable` — false
17. `adapter_transport_only` — true
18. `harness_evals_advisory_only` — true
19. `bitcoin_external_evidence_only` — true
20. `blocked_security_decision_status` —
    `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

The identical object appears in the request, response, and fixture-level
assertion. Any mismatch is `authority_assertion_invalid`.

### 9.2 Exact 17-field `non_execution` order/values

1. `signer_invocation_requested` — false
2. `signer_invoked` — false
3. `signing_attempted` — false
4. `signature_created` — false
5. `wallet_access_requested` — false
6. `wallet_accessed` — false
7. `transaction_submitted` — false
8. `broadcast_attempted` — false
9. `rpc_connected` — false
10. `network_connected` — false
11. `replay_state_mutated` — false
12. `economic_control_state_mutated` — false
13. `ledger_mutated` — false
14. `settlement_attempted` — false
15. `settlement_finalized` — false
16. `consensus_modified` — false
17. `execution_authorized` — false

The identical object appears in request and response. All values remain false
for every POS, NEG, BND, and FCL fixture.

### 9.3 `safety_assertions` exact order/values

1. `public_fictional_data_only` — true
2. `contains_private_keys` — false
3. `contains_seeds_or_mnemonics` — false
4. `contains_xprv_or_keystore` — false
5. `contains_wallet_or_rpc_credentials` — false
6. `contains_production_secrets` — false
7. `contains_real_balances_or_transactions` — false
8. `reads_keys_or_wallets` — false
9. `reads_environment_or_system_clock` — false
10. `invokes_validate_transaction` — false
11. `implements_or_invokes_signer` — false
12. `connects_rpc_or_network` — false
13. `submits_or_broadcasts` — false
14. `mutates_state_or_ledger` — false
15. `settles_or_activates_runtime` — false
16. `changes_protocol_or_economics` — false

## 10. Canonical serialization and digests

### 10.1 Serialization

`CanonLsi` retains Foundation117 semantics for interface request/response
objects. `CanonFixture` applies the same exact-order UTF-8 JSON rules to the
fixture schema:

1. UTF-8 without BOM; one object; no trailing data;
2. exact declared property order at every level;
3. no missing, duplicate, unknown, or reordered fields;
4. `ensure_ascii=false`, separators `(",", ":")`, `sort_keys=false`, and
   `allow_nan=false` semantics;
5. exact safe-range JSON integers; booleans are not integers;
6. no floats, `NaN`, `Infinity`, bytes, tuples, sets, comments, normalization,
   case folding, or hidden coercion;
7. array order preserved; approval identities remain distinct/ordered except
   where a named probe creates a candidate; and
8. lowercase 64-hex digests/IDs.

One final LF is permitted in a fixture file and is excluded from canonical
bytes.

### 10.2 F117 digest preservation

These Foundation117 domains and formulas remain exact and MUST be recomputed
independently:

- `L28-LOCAL-SIGNER-INTERFACE-V0.1-TRANSACTION\x00` for
  `transaction_input_sha256`;
- `L28-LOCAL-SIGNER-INTERFACE-V0.1-VALIDATION\x00` for `binding_digest` with
  its field blank;
- `L28-LOCAL-SIGNER-INTERFACE-V0.1-REQUEST\x00` for `request_digest` with its
  field blank;
- `L28-LOCAL-SIGNER-INTERFACE-V0.1-AUDIT\x00` for `audit_id`, then
  `eligibility_receipt_id`, using the exact F117 blank-field/order rules; and
- `L28-LOCAL-SIGNER-INTERFACE-V0.1-REPORT\x00` for `report_id` with its field
  blank.

No fixture domain replaces or changes an F117 digest.

### 10.3 Fixture-only canonical metadata

`canonical` contains exactly:

1. `algorithm` — `sha256-utf8-exact-order-json`
2. `field_order_enforced` — true
3. `fixture_input_sha256`
4. `request_digest`
5. `transaction_input_sha256`
6. `validation_binding_digest`
7. `expected_audit_id`
8. `expected_eligibility_receipt_id`
9. `expected_report_id`
10. `expected_response_sha256`
11. `fixture_sha256`

Fixture-only domains are:

```text
FIXTURE_INPUT_DOMAIN =
  b"L28-LOCAL-SIGNER-INTERFACE-FIXTURE-V0.1-INPUT\x00"
EXPECTED_RESPONSE_DOMAIN =
  b"L28-LOCAL-SIGNER-INTERFACE-FIXTURE-V0.1-EXPECTED-RESPONSE\x00"
FIXTURE_DOMAIN =
  b"L28-LOCAL-SIGNER-INTERFACE-FIXTURE-V0.1-FIXTURE\x00"

fixture_input_sha256 = hex_lower(
  SHA-256(FIXTURE_INPUT_DOMAIN || CanonFixture(input))
)

expected_response_sha256 = hex_lower(
  SHA-256(EXPECTED_RESPONSE_DOMAIN || CanonLsi(expected.response))
)

fixture_sha256 = hex_lower(
  SHA-256(FIXTURE_DOMAIN || CanonFixture(complete fixture
    with canonical.fixture_sha256=""))
)
```

Fixture-only digests prove deterministic fixture binding only. They do not
authenticate evidence or prove signing/settlement.

## 11. Fail-closed precedence

A future runner MUST stop at the first applicable Foundation117 failure:

1. UTF-8/JSON/size/duplicate/schema/order/type;
2. secret/custody material;
3. profile/version/operation;
4. canonical digest;
5. authority/protected-economics/Protocol override;
6. signer invocation/execution claim;
7. unresolved future-security decision attempt;
8. caller identity/authentication;
9. replay/idempotency;
10. expiration/time;
11. policy/spending limit;
12. approvals;
13. operator authorization;
14. authorization/binding;
15. mandatory Protocol validation;
16. audit lineage; and
17. deterministic eligible/blocked public projection.

Case probes MUST preserve the exact F118 expected code even when a probe models
multiple failures (notably PRE cases). No runner may return a lower-precedence
code, aggregate alternate codes, repair the candidate, or invoke runtime as a
fallback.

## 12. Unresolved security gates

### 12.1 `GAP_REQUIRES_FUTURE_WORK`

- authenticated identity/policy/approval/operator evidence, provenance,
  revocation, and administration;
- key custody and lifecycle;
- atomic replay/idempotency/cumulative-spend/approval state, persistence,
  concurrency, retention, rollback, and recovery;
- trusted production time, skew, rollback, outage, and monotonicity;
- audit durability, privacy, access, tamper evidence, retention, and recovery;
- parser/resource/rate/process/DoS/monitoring/service hardening; and
- runtime integration assurance, validation-delegation proof, adversarial
  testing, operations, and independent security review.

### 12.2 `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

The following remain blocked and unchanged:

- signer implementation, runtime, or activation;
- production proof architecture;
- Bitcoin confirmation policy and count;
- observer quorum and observer independence; and
- unresolved custody and runtime security gates from Foundation116.

No fixture may select, infer, default, or claim completion of these gates.

## 13. Future materialization acceptance criteria

A later separately authorized materialization may claim conformance only if:

1. exactly the 100 Section 14 JSON fixtures exist, with no extras;
2. every case/fixture ID and class matches Section 14 exactly;
3. counts are POS 19, NEG 49, BND 14, FCL 18, total 100, across 18 families;
4. every fixture uses the exact top-level/nested property order;
5. each canonical projection is valid and each malformed candidate is produced
   only through `case_probe` in memory;
6. every Foundation117 and fixture-only digest recomputes independently;
7. every expected status/code matches Foundation118 exactly;
8. every Foundation118 input focus/invariant is preserved without semantic
   rewrite;
9. all authority assertions/economics are exact and all override flags false;
10. all 17 request/response non-execution fields are false;
11. public fictional/disposable data only is present;
12. no evaluator imports/invokes production validation, signer, wallet, key,
    RPC, network, submission, broadcast, ledger, settlement, deployment, or
    runtime code; and
13. unresolved GAP/BLOCKED gates remain unresolved.

Passing fixtures would prove offline deterministic conformance only.

## 14. Exhaustive 100-case fixture inventory

The input focus and required invariant for each ID remain exactly the
corresponding Foundation118 Section 6 row and are incorporated normatively by
reference. The table below locks the one-to-one mapping, class, expected status,
and expected code without rewriting those semantics.

| Case ID | Fixture ID | Class | Expected status | Expected code |
|---|---|---|---|---|
| `LSI-CONF-v0.1-CMP-POS-001` | `fx-lsi-v01-cmp-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-CMP-NEG-001` | `fx-lsi-v01-cmp-neg-001` | NEG | `rejected` | `interface_profile_unsupported` |
| `LSI-CONF-v0.1-CMP-NEG-002` | `fx-lsi-v01-cmp-neg-002` | NEG | `rejected` | `interface_profile_unsupported` |
| `LSI-CONF-v0.1-CMP-FCL-001` | `fx-lsi-v01-cmp-fcl-001` | FCL | `rejected` | `operation_unsupported` |
| `LSI-CONF-v0.1-SCH-POS-001` | `fx-lsi-v01-sch-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-SCH-POS-002` | `fx-lsi-v01-sch-pos-002` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-SCH-NEG-001` | `fx-lsi-v01-sch-neg-001` | NEG | `rejected` | `schema_invalid` |
| `LSI-CONF-v0.1-SCH-NEG-002` | `fx-lsi-v01-sch-neg-002` | NEG | `rejected` | `schema_invalid` |
| `LSI-CONF-v0.1-SCH-NEG-003` | `fx-lsi-v01-sch-neg-003` | NEG | `rejected` | `schema_invalid` |
| `LSI-CONF-v0.1-SCH-NEG-004` | `fx-lsi-v01-sch-neg-004` | NEG | `rejected` | `schema_invalid` |
| `LSI-CONF-v0.1-SCH-BND-001` | `fx-lsi-v01-sch-bnd-001` | BND | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-SCH-FCL-001` | `fx-lsi-v01-sch-fcl-001` | FCL | `rejected` | `schema_invalid` |
| `LSI-CONF-v0.1-IDN-POS-001` | `fx-lsi-v01-idn-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-IDN-NEG-001` | `fx-lsi-v01-idn-neg-001` | NEG | `rejected` | `secret_material_forbidden` |
| `LSI-CONF-v0.1-IDN-NEG-002` | `fx-lsi-v01-idn-neg-002` | NEG | `rejected` | `authority_binding_invalid` |
| `LSI-CONF-v0.1-IDN-BND-001` | `fx-lsi-v01-idn-bnd-001` | BND | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-IDN-FCL-001` | `fx-lsi-v01-idn-fcl-001` | FCL | `blocked` | `identity_evidence_unavailable` |
| `LSI-CONF-v0.1-AUT-POS-001` | `fx-lsi-v01-aut-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-AUT-NEG-001` | `fx-lsi-v01-aut-neg-001` | NEG | `blocked` | `authorization_denied` |
| `LSI-CONF-v0.1-AUT-NEG-002` | `fx-lsi-v01-aut-neg-002` | NEG | `blocked` | `authorization_unavailable` |
| `LSI-CONF-v0.1-AUT-BND-001` | `fx-lsi-v01-aut-bnd-001` | BND | `blocked` | `protocol_validation_pending` |
| `LSI-CONF-v0.1-AUT-FCL-001` | `fx-lsi-v01-aut-fcl-001` | FCL | `rejected` | `authority_binding_invalid` |
| `LSI-CONF-v0.1-VAL-POS-001` | `fx-lsi-v01-val-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-VAL-NEG-001` | `fx-lsi-v01-val-neg-001` | NEG | `blocked` | `protocol_validation_rejected` |
| `LSI-CONF-v0.1-VAL-NEG-002` | `fx-lsi-v01-val-neg-002` | NEG | `rejected` | `validation_override_forbidden` |
| `LSI-CONF-v0.1-VAL-NEG-003` | `fx-lsi-v01-val-neg-003` | NEG | `rejected` | `canonical_digest_mismatch` |
| `LSI-CONF-v0.1-VAL-BND-001` | `fx-lsi-v01-val-bnd-001` | BND | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-VAL-FCL-001` | `fx-lsi-v01-val-fcl-001` | FCL | `blocked` | `protocol_validation_unavailable` |
| `LSI-CONF-v0.1-ELG-POS-001` | `fx-lsi-v01-elg-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-ELG-NEG-001` | `fx-lsi-v01-elg-neg-001` | NEG | `rejected` | `signer_invocation_forbidden` |
| `LSI-CONF-v0.1-ELG-NEG-002` | `fx-lsi-v01-elg-neg-002` | NEG | `rejected` | `execution_forbidden` |
| `LSI-CONF-v0.1-ELG-FCL-001` | `fx-lsi-v01-elg-fcl-001` | FCL | `rejected` | `signer_invocation_forbidden` |
| `LSI-CONF-v0.1-LIM-POS-001` | `fx-lsi-v01-lim-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-LIM-NEG-001` | `fx-lsi-v01-lim-neg-001` | NEG | `blocked` | `per_transaction_limit_exceeded` |
| `LSI-CONF-v0.1-LIM-NEG-002` | `fx-lsi-v01-lim-neg-002` | NEG | `blocked` | `cumulative_limit_exceeded` |
| `LSI-CONF-v0.1-LIM-BND-001` | `fx-lsi-v01-lim-bnd-001` | BND | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-LIM-FCL-001` | `fx-lsi-v01-lim-fcl-001` | FCL | `blocked` | `spending_policy_unavailable` |
| `LSI-CONF-v0.1-APR-POS-001` | `fx-lsi-v01-apr-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-APR-NEG-001` | `fx-lsi-v01-apr-neg-001` | NEG | `blocked` | `approval_threshold_not_met` |
| `LSI-CONF-v0.1-APR-NEG-002` | `fx-lsi-v01-apr-neg-002` | NEG | `rejected` | `duplicate_approval` |
| `LSI-CONF-v0.1-APR-NEG-003` | `fx-lsi-v01-apr-neg-003` | NEG | `blocked` | `approval_policy_unavailable` |
| `LSI-CONF-v0.1-APR-BND-001` | `fx-lsi-v01-apr-bnd-001` | BND | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-APR-FCL-001` | `fx-lsi-v01-apr-fcl-001` | FCL | `blocked` | `approval_policy_unavailable` |
| `LSI-CONF-v0.1-RPL-POS-001` | `fx-lsi-v01-rpl-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-RPL-NEG-001` | `fx-lsi-v01-rpl-neg-001` | NEG | `blocked` | `replay_detected` |
| `LSI-CONF-v0.1-RPL-NEG-002` | `fx-lsi-v01-rpl-neg-002` | NEG | `rejected` | `authority_binding_invalid` |
| `LSI-CONF-v0.1-RPL-BND-001` | `fx-lsi-v01-rpl-bnd-001` | BND | `blocked` | `replay_detected` |
| `LSI-CONF-v0.1-RPL-FCL-001` | `fx-lsi-v01-rpl-fcl-001` | FCL | `blocked` | `replay_state_unavailable` |
| `LSI-CONF-v0.1-EXP-POS-001` | `fx-lsi-v01-exp-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-EXP-NEG-001` | `fx-lsi-v01-exp-neg-001` | NEG | `blocked` | `artifact_expired` |
| `LSI-CONF-v0.1-EXP-NEG-002` | `fx-lsi-v01-exp-neg-002` | NEG | `blocked` | `not_yet_valid` |
| `LSI-CONF-v0.1-EXP-BND-001` | `fx-lsi-v01-exp-bnd-001` | BND | `blocked` | `artifact_expired` |
| `LSI-CONF-v0.1-EXP-BND-002` | `fx-lsi-v01-exp-bnd-002` | BND | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-EXP-FCL-001` | `fx-lsi-v01-exp-fcl-001` | FCL | `blocked` | `evaluation_time_unavailable` |
| `LSI-CONF-v0.1-OPR-POS-001` | `fx-lsi-v01-opr-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-OPR-NEG-001` | `fx-lsi-v01-opr-neg-001` | NEG | `blocked` | `operator_authorization_denied` |
| `LSI-CONF-v0.1-OPR-NEG-002` | `fx-lsi-v01-opr-neg-002` | NEG | `blocked` | `operator_authorization_mismatch` |
| `LSI-CONF-v0.1-OPR-NEG-003` | `fx-lsi-v01-opr-neg-003` | NEG | `blocked` | `artifact_expired` |
| `LSI-CONF-v0.1-OPR-BND-001` | `fx-lsi-v01-opr-bnd-001` | BND | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-OPR-FCL-001` | `fx-lsi-v01-opr-fcl-001` | FCL | `blocked` | `operator_gate_unavailable` |
| `LSI-CONF-v0.1-ATH-POS-001` | `fx-lsi-v01-ath-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-ATH-NEG-001` | `fx-lsi-v01-ath-neg-001` | NEG | `blocked` | `identity_evidence_unauthenticated` |
| `LSI-CONF-v0.1-ATH-NEG-002` | `fx-lsi-v01-ath-neg-002` | NEG | `blocked` | `operator_gate_unavailable` |
| `LSI-CONF-v0.1-ATH-NEG-003` | `fx-lsi-v01-ath-neg-003` | NEG | `blocked` | `spending_policy_unavailable` |
| `LSI-CONF-v0.1-ATH-NEG-004` | `fx-lsi-v01-ath-neg-004` | NEG | `blocked` | `approval_policy_unavailable` |
| `LSI-CONF-v0.1-ATH-FCL-001` | `fx-lsi-v01-ath-fcl-001` | FCL | `blocked` | `future_security_decision_required` |
| `LSI-CONF-v0.1-CAN-POS-001` | `fx-lsi-v01-can-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-CAN-NEG-001` | `fx-lsi-v01-can-neg-001` | NEG | `rejected` | `canonical_digest_mismatch` |
| `LSI-CONF-v0.1-CAN-NEG-002` | `fx-lsi-v01-can-neg-002` | NEG | `rejected` | `canonical_digest_mismatch` |
| `LSI-CONF-v0.1-CAN-NEG-003` | `fx-lsi-v01-can-neg-003` | NEG | `rejected` | `canonical_digest_mismatch` |
| `LSI-CONF-v0.1-CAN-BND-001` | `fx-lsi-v01-can-bnd-001` | BND | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-CAN-FCL-001` | `fx-lsi-v01-can-fcl-001` | FCL | `rejected` | `schema_invalid` |
| `LSI-CONF-v0.1-PRE-POS-001` | `fx-lsi-v01-pre-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-PRE-NEG-001` | `fx-lsi-v01-pre-neg-001` | NEG | `blocked` | `replay_detected` |
| `LSI-CONF-v0.1-PRE-BND-001` | `fx-lsi-v01-pre-bnd-001` | BND | `rejected` | `schema_invalid` |
| `LSI-CONF-v0.1-PRE-FCL-001` | `fx-lsi-v01-pre-fcl-001` | FCL | `rejected` | `internal_failure` |
| `LSI-CONF-v0.1-AUD-POS-001` | `fx-lsi-v01-aud-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-AUD-NEG-001` | `fx-lsi-v01-aud-neg-001` | NEG | `rejected` | `execution_forbidden` |
| `LSI-CONF-v0.1-AUD-NEG-002` | `fx-lsi-v01-aud-neg-002` | NEG | `rejected` | `execution_forbidden` |
| `LSI-CONF-v0.1-AUD-BND-001` | `fx-lsi-v01-aud-bnd-001` | BND | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-AUD-FCL-001` | `fx-lsi-v01-aud-fcl-001` | FCL | `rejected` | `audit_lineage_invalid` |
| `LSI-CONF-v0.1-FWL-POS-001` | `fx-lsi-v01-fwl-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-FWL-NEG-001` | `fx-lsi-v01-fwl-neg-001` | NEG | `rejected` | `protocol_override_forbidden` |
| `LSI-CONF-v0.1-FWL-NEG-002` | `fx-lsi-v01-fwl-neg-002` | NEG | `rejected` | `protocol_override_forbidden` |
| `LSI-CONF-v0.1-FWL-NEG-003` | `fx-lsi-v01-fwl-neg-003` | NEG | `rejected` | `validation_override_forbidden` |
| `LSI-CONF-v0.1-FWL-NEG-004` | `fx-lsi-v01-fwl-neg-004` | NEG | `rejected` | `protocol_override_forbidden` |
| `LSI-CONF-v0.1-FWL-NEG-005` | `fx-lsi-v01-fwl-neg-005` | NEG | `rejected` | `authority_assertion_invalid` |
| `LSI-CONF-v0.1-FWL-NEG-006` | `fx-lsi-v01-fwl-neg-006` | NEG | `rejected` | `protocol_override_forbidden` |
| `LSI-CONF-v0.1-FWL-BND-001` | `fx-lsi-v01-fwl-bnd-001` | BND | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-FWL-FCL-001` | `fx-lsi-v01-fwl-fcl-001` | FCL | `blocked` | `protocol_validation_unavailable` |
| `LSI-CONF-v0.1-NEX-POS-001` | `fx-lsi-v01-nex-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-NEX-NEG-001` | `fx-lsi-v01-nex-neg-001` | NEG | `rejected` | `signer_invocation_forbidden` |
| `LSI-CONF-v0.1-NEX-NEG-002` | `fx-lsi-v01-nex-neg-002` | NEG | `rejected` | `execution_forbidden` |
| `LSI-CONF-v0.1-NEX-NEG-003` | `fx-lsi-v01-nex-neg-003` | NEG | `rejected` | `execution_forbidden` |
| `LSI-CONF-v0.1-NEX-FCL-001` | `fx-lsi-v01-nex-fcl-001` | FCL | `rejected` | `schema_invalid` |
| `LSI-CONF-v0.1-GAT-POS-001` | `fx-lsi-v01-gat-pos-001` | POS | `eligible_public_projection` | `signer_eligible_public_projection` |
| `LSI-CONF-v0.1-GAT-NEG-001` | `fx-lsi-v01-gat-neg-001` | NEG | `blocked` | `future_security_decision_required` |
| `LSI-CONF-v0.1-GAT-NEG-002` | `fx-lsi-v01-gat-neg-002` | NEG | `blocked` | `future_security_decision_required` |
| `LSI-CONF-v0.1-GAT-NEG-003` | `fx-lsi-v01-gat-neg-003` | NEG | `blocked` | `future_security_decision_required` |
| `LSI-CONF-v0.1-GAT-FCL-001` | `fx-lsi-v01-gat-fcl-001` | FCL | `blocked` | `future_security_decision_required` |

Inventory totals: POS 19, NEG 49, BND 14, FCL 18; total 100; families 18.

## 15. Explicit non-activation statement

Foundation119 creates only this document. It creates no JSON fixture,
executable schema, test, runner, dependency, signer, wallet, key, signature,
RPC/network connection, transaction submission, broadcast, ledger/replay state,
settlement, deployment, testnet, DigitalOcean resource, or runtime service.

It changes no F116–F118 artifact, Protocol rule, economic fact, consensus rule,
validation path, canonical height, historical evidence, or authority boundary.
Foundation120 is not authorized or started.

## 16. Document control

| Field | Value |
|---|---|
| Foundation | 119 |
| Parent | `d8a206c250ccbc278bf28c4a21c87110d46c1ce7` |
| Path | `docs/local_signer_interface_fixture_spec_v0.1.md` |
| Fixture schema | `l28-local-signer-interface-fixture/v0.1` |
| Fixture specification | `local-signer-interface-fixture-spec/v0.1` |
| Fixture ID grammar | `fx-lsi-v01-<family>-<class>-<nnn>` |
| Families | 18 |
| POS / NEG / BND / FCL | 19 / 49 / 14 / 18 |
| Total mappings | 100 |
| JSON fixtures/tests/executable schemas/runtime | none |
| Keys/wallets/signing/RPC/network/broadcast/settlement | none |
| Protocol/economics changes | none |
| Commit/merge/push | none |
