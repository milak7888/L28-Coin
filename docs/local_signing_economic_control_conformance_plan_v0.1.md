# Local Signing / Economic Control Conformance Plan v0.1

**Foundation:** 112

**Status:** documentation and conformance planning only / non-activating

**Plan version:** `local-signing-economic-control-conformance-plan/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Parent:** `084945d348f9e76ded7bc7d87691e0b582a239b8`

**Branch:** `foundation112-local-signing-economic-control-conformance-plan`

**Authoritative architecture input:**
`docs/local_signing_economic_control_architecture_review_v0.1.md`
(Foundation 111)

**Implementation:** none

**Runtime activation:** none

**Normative subordination:** This plan is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md), Foundation 111, and the canonical
Universal Access Interface. On conflict, Protocol v1.0.0 prevails. This plan
defines future deterministic offline conformance cases only. It does not create
schemas, fixtures, tests, keys, wallets, signatures, transactions, runtime
interfaces, settlement authority, or production policy.

---

## 1. Purpose and scope

Foundation 112 plans a deterministic, offline conformance suite for a possible
future isolated local signer and its local economic controls. The suite would
prove that public authorization policy is evaluated before a signing attempt,
without treating authorization, a signature, or an audit record as L28
validation or settlement.

The future subject under test is an **isolated signer boundary**, not a wallet,
node, adapter, consensus component, or settlement service. The planned suite
must exercise public, fictional artifacts only and must never possess or use
private signing material.

In scope for planning:

1. signer-boundary isolation;
2. authorization versus validation separation;
3. mandatory `validate_transaction` delegation;
4. key-custody separation;
5. spending limits and approval thresholds;
6. replay and expiration controls;
7. receipt and audit evidence boundaries;
8. operator authorization gates; and
9. deterministic positive, negative, boundary, and fail-closed cases.

Out of scope:

- generating or importing keys;
- creating or importing wallets;
- signing or signature production;
- broadcasting or transaction submission;
- RPC, P2P, HTTP, or other network access;
- signer, wallet, adapter, ledger, node, or settlement runtime implementation;
- settlement activation or ledger mutation;
- tests, fixtures, schemas, dependencies, or runtime code; and
- changes to Protocol v1.0.0, consensus, validation, issuance, supply, height,
  history, or protected economic facts.

Passing a future suite would mean only that the tested offline decision surface
conforms to this plan. It would not authorize signing, spending, broadcast,
settlement, deployment, or production use.

---

## 2. Authority and invariant model

### 2.1 Authority ordering

| Authority or subsystem | Permitted role | Prohibited implication |
|---|---|---|
| L28 Protocol v1.0.0 | Settlement, consensus, issuance, supply, canonical height, and history authority | None may override it |
| `coin.tx_validation.validate_transaction` | Mandatory transfer and coinbase validation authority | Local policy cannot bypass or replace it |
| Future isolated signer | If separately authorized, may attempt a signature only after all local gates pass | A signature is not validation, settlement, height, consensus, or issuance |
| Operator authorization gate | Local prerequisite for a future signing attempt | Does not make an invalid transaction valid |
| Economic-control evaluator | Applies bounded local policy to public intent | Does not mutate ledger state or Protocol economics |
| Harness/Evals | Advisory evidence only | Cannot sign, authorize settlement, or control keys |
| Bitcoin observers/evidence | External evidence only | Cannot authorize L28 signing or replace L28 validation |
| Adapters | Transport-only mapping | Cannot become custody, signing, validation, or settlement authority |

### 2.2 Mandatory invariants

Every planned case must assert, where applicable:

- `authorization_status=allowed` is not validation success;
- `validation_status=accepted` is not settlement;
- `validate_transaction` remains mandatory for every proposed L28 transaction;
- signer output cannot override a validation rejection;
- signer and policy components cannot issue or mint L28;
- signer and policy components cannot alter supply, canonical height, consensus,
  history, or historical evidence;
- missing or contradictory required evidence fails closed;
- no planned result claims ledger mutation, transaction submission, broadcast,
  finality, or settlement;
- no secret material crosses the isolated custody boundary; and
- no optional subsystem becomes required by L28 core.

The protected facts remain unchanged:

| Fact | Preserved value |
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

---

## 3. Future subject-under-test boundary

This section names conceptual components solely so later conformance fixtures
can target one responsibility at a time. It does not authorize their creation.

| Conceptual component | Future input | Future public output | Must not do |
|---|---|---|---|
| Intent parser | Canonical public transaction intent | Strict parsed intent or stable rejection | Accept secrets, repair input, or sign |
| Authorization evaluator | Intent plus explicit policy and operator evidence | Allow/deny decision with reasons | Invoke consensus authority or imply validation |
| Spending-control evaluator | Amount, asset, limit window, prior authorized total | Deterministic within-limit/exceeded result | Change Protocol supply or balances |
| Approval-threshold evaluator | Ordered public approval evidence | Threshold-met/not-met result | Invent approvals or treat score as approval |
| Replay evaluator | Public request/intent identifiers and caller-supplied replay view | Fresh/replayed result | Mutate persistent state in this profile |
| Expiration evaluator | Caller-supplied evaluation time and expiries | Active/expired/not-yet-valid result | Read implicit system or network time |
| Protocol-validation delegate | Proposed transaction plus authoritative L28 context | Exact validation result | Replace or weaken `validate_transaction` |
| Audit-result builder | Public outcomes from completed checks | Deterministic non-secret evidence | Claim settlement, broadcast, or ledger mutation |
| Future isolated signer | A fully allowed and validated public signing request | Outside this conformance-plan scope | Be invoked by planned fixtures |

The conformance harness must substitute deterministic public decisions at the
signer edge. It must assert that no signing callable, private key API, wallet
API, broadcast API, or network client is imported or invoked.

---

## 4. Deterministic fixture and case model

### 4.1 Planned fixture rules

A later authorized fixture milestone should use:

- fixed fictional L28 identities;
- integer L28 amounts only;
- fixed caller-supplied Unix-second times;
- fixed public request, intent, policy, approval, and audit identifiers;
- deterministic read-only replay and validation views;
- exact field order and canonical JSON rules inherited from the applicable
  canonical interface; and
- explicit safety assertions showing no secrets, real wallets, production
  addresses, real balances, or network-derived values.

The future runner must not read the system clock, environment variables,
keychains, wallet directories, RPC configuration, browser storage, or network
state. Identical canonical inputs must produce identical public outcomes.

### 4.2 Case classes

| Class | Code | Meaning |
|---|---|---|
| Positive | `POS` | Complete public inputs satisfy the bounded rule; outcome remains non-executing |
| Negative | `NEG` | Well-formed input violates a policy or binding rule and is rejected |
| Boundary | `BND` | Exact limit, threshold, or time boundary is evaluated deterministically |
| Fail closed | `FCL` | Missing, malformed, unavailable, contradictory, or authority-violating evidence blocks progress |

Planned case identifier form:

`LSEC-CONF-v0.1-<FAMILY>-<POS|NEG|BND|FCL>-<NNN>`

### 4.3 Common expected outcome

Every successful evaluation is evidence only. Unless a case rejects before a
field can be derived, expected public results must preserve:

- `signing_attempted=false`;
- `signature_created=false`;
- `transaction_submitted=false`;
- `broadcast_attempted=false`;
- `ledger_mutated=false`;
- `settlement_finalized=false`;
- `consensus_modified=false`; and
- `execution_authorized=false`.

An authorization-positive case may report `authorization_status=allowed`, but
must still show that authorization alone did not invoke signing or settlement.

---

## 5. Planned conformance case families

### 5.1 Isolated signer boundary (`ISO`)

| Case ID | Class | Scenario | Expected outcome / invariant |
|---|---|---|---|
| `LSEC-CONF-v0.1-ISO-POS-001` | POS | Complete public signing-request projection reaches the signer edge after prior gates | Edge eligibility may be reported; signer is not invoked; all common non-execution flags remain false |
| `LSEC-CONF-v0.1-ISO-NEG-001` | NEG | Adapter or Harness/Evals claims signing authority | Reject `signer_authority_forbidden`; no delegation |
| `LSEC-CONF-v0.1-ISO-BND-001` | BND | Only public key id, public identity, and public digests cross the conceptual boundary | Accept public metadata only; no private material and no signature creation |
| `LSEC-CONF-v0.1-ISO-FCL-001` | FCL | Signer boundary unavailable or not separately authorized | Reject `signer_unavailable` or `signer_not_authorized`; never default-allow |

Family invariant: a future signer is isolated and subordinate. It cannot become
consensus, validation, settlement, issuance, or economic authority.

### 5.2 Authorization versus validation (`AUT`)

| Case ID | Class | Scenario | Expected outcome / invariant |
|---|---|---|---|
| `LSEC-CONF-v0.1-AUT-POS-001` | POS | Local policy allows an intent and Protocol validation accepts it | Report separate allowed and accepted statuses; no signing or settlement |
| `LSEC-CONF-v0.1-AUT-NEG-001` | NEG | Policy allows but Protocol validation rejects | Final outcome blocked with Protocol rejection preserved; signer edge not reached |
| `LSEC-CONF-v0.1-AUT-BND-001` | BND | Policy result is exactly allowed with no validation result yet | Remain pending/blocked for validation; authorization is not validation |
| `LSEC-CONF-v0.1-AUT-FCL-001` | FCL | Authorization and validation evidence are conflated or contradictory | Reject `authority_binding_invalid`; do not infer either status |

Family invariant: no authorization artifact, approval, signature, receipt,
evaluation score, or Bitcoin observation substitutes for Protocol validation.

### 5.3 Mandatory Protocol validation (`VAL`)

| Case ID | Class | Scenario | Expected outcome / invariant |
|---|---|---|---|
| `LSEC-CONF-v0.1-VAL-POS-001` | POS | Exact proposed transaction is delegated to `validate_transaction` and accepted | Record delegate invocation and accepted result; ledger remains unchanged |
| `LSEC-CONF-v0.1-VAL-NEG-001` | NEG | Caller supplies an alternate validator or override result | Reject `validation_override_forbidden` |
| `LSEC-CONF-v0.1-VAL-BND-001` | BND | Transaction amount equals the locally allowed maximum and Protocol accepts | Local boundary passes; Protocol result still independently mandatory |
| `LSEC-CONF-v0.1-VAL-FCL-001` | FCL | Protocol validator or required ledger/consensus context is unavailable | Reject `protocol_validation_unavailable`; no signing attempt |

Family invariant: `coin.tx_validation.validate_transaction` remains mandatory
and its rejection is preserved without repair, coercion, or fallback authority.

### 5.4 Key custody separation (`KEY`)

| Case ID | Class | Scenario | Expected outcome / invariant |
|---|---|---|---|
| `LSEC-CONF-v0.1-KEY-POS-001` | POS | Request contains only approved public identity and digest fields | Continue public evaluation; no key or wallet access |
| `LSEC-CONF-v0.1-KEY-NEG-001` | NEG | Request includes a private key, seed, mnemonic, xprv, wallet secret, credential, or keystore field | Reject `secret_material_forbidden`; do not echo the value |
| `LSEC-CONF-v0.1-KEY-BND-001` | BND | A valid public key identifier is present without private bytes | Accept identifier as public metadata only; it grants no signing authority |
| `LSEC-CONF-v0.1-KEY-FCL-001` | FCL | Adapter, Harness/Evals, Bitcoin observer, log, or hosted model is proposed as custodian | Reject `custody_boundary_violation`; no forwarding |

Family invariant: custody remains local to a future separately authorized signer
and is absent from all conformance fixtures and runner processes.

### 5.5 Spending limits (`LIM`)

| Case ID | Class | Scenario | Expected outcome / invariant |
|---|---|---|---|
| `LSEC-CONF-v0.1-LIM-POS-001` | POS | Positive integer amount is below per-transaction and cumulative local limits | Local limit check passes; no spend, signature, or settlement |
| `LSEC-CONF-v0.1-LIM-NEG-001` | NEG | Amount exceeds per-transaction limit | Reject `per_transaction_limit_exceeded` |
| `LSEC-CONF-v0.1-LIM-NEG-002` | NEG | Prior authorized total plus amount exceeds cumulative limit | Reject `cumulative_limit_exceeded` |
| `LSEC-CONF-v0.1-LIM-BND-001` | BND | Amount equals per-transaction limit exactly | Accept local boundary if all other gates pass; Protocol validation still required |
| `LSEC-CONF-v0.1-LIM-BND-002` | BND | Prior total plus amount equals cumulative limit exactly | Accept local boundary; no implicit increase or rollover |
| `LSEC-CONF-v0.1-LIM-FCL-001` | FCL | Limit, prior total, asset, or policy window is missing, malformed, stale, or inconsistent | Reject `spending_policy_unavailable`; never assume unlimited spend |

Family invariant: spending limits are local safety restrictions only. They
cannot increase balances, mint L28, or alter Protocol economic facts.

### 5.6 Approval thresholds (`APR`)

| Case ID | Class | Scenario | Expected outcome / invariant |
|---|---|---|---|
| `LSEC-CONF-v0.1-APR-POS-001` | POS | Distinct, valid, policy-authorized public approvals exceed the required threshold | Threshold status met; validation and operator gates remain independently required |
| `LSEC-CONF-v0.1-APR-NEG-001` | NEG | Fewer distinct approvals than required | Reject `approval_threshold_not_met` |
| `LSEC-CONF-v0.1-APR-NEG-002` | NEG | Duplicate approver evidence is counted more than once | Reject `duplicate_approval`; threshold remains unmet |
| `LSEC-CONF-v0.1-APR-BND-001` | BND | Distinct approvals equal the threshold exactly | Threshold status met; no signing or settlement authority follows automatically |
| `LSEC-CONF-v0.1-APR-FCL-001` | FCL | Threshold policy or approver authority is missing/contradictory | Reject `approval_policy_unavailable`; do not invent a threshold |

Family invariant: approval evidence cannot originate from Harness/Evals scores,
Bitcoin confirmations, adapters, or unrecognized identities.

### 5.7 Replay protection (`RPL`)

| Case ID | Class | Scenario | Expected outcome / invariant |
|---|---|---|---|
| `LSEC-CONF-v0.1-RPL-POS-001` | POS | Canonical intent/request identifier is absent from caller-supplied replay view | Report fresh; do not mutate replay storage |
| `LSEC-CONF-v0.1-RPL-NEG-001` | NEG | Intent/request identifier is already present within retention | Reject `replay_detected` |
| `LSEC-CONF-v0.1-RPL-BND-001` | BND | Identifier is evaluated at the exact documented retention boundary | Apply the specified inclusive/exclusive boundary deterministically; no implicit time |
| `LSEC-CONF-v0.1-RPL-FCL-001` | FCL | Replay view is unavailable, malformed, stale, or inconsistent | Reject `replay_state_unavailable`; never treat unknown as fresh |

Family invariant: this plan is read-only. Persistent replay recording and its
atomic transition remain future implementation decisions.

### 5.8 Expiration controls (`EXP`)

| Case ID | Class | Scenario | Expected outcome / invariant |
|---|---|---|---|
| `LSEC-CONF-v0.1-EXP-POS-001` | POS | Caller-supplied evaluation time is within all intent, quote, payment, approval, and operator-evidence lifetimes | Expiration checks pass; no runtime clock read |
| `LSEC-CONF-v0.1-EXP-NEG-001` | NEG | Any required artifact is expired | Reject the artifact-specific expiration code |
| `LSEC-CONF-v0.1-EXP-NEG-002` | NEG | An artifact is not yet valid | Reject `not_yet_valid` |
| `LSEC-CONF-v0.1-EXP-BND-001` | BND | Evaluation time equals the documented expiry boundary | Apply the inherited canonical boundary exactly and deterministically |
| `LSEC-CONF-v0.1-EXP-FCL-001` | FCL | Evaluation time is missing or would require system/network time | Reject `evaluation_time_unavailable`; no implicit clock authority |

Family invariant: expiration policy cannot supply canonical height, finality, or
consensus time.

### 5.9 Receipts and audit evidence (`AUD`)

| Case ID | Class | Scenario | Expected outcome / invariant |
|---|---|---|---|
| `LSEC-CONF-v0.1-AUD-POS-001` | POS | Deterministic audit result binds intent, policy, approvals, replay, expiry, and Protocol-validation outcomes | Emit public evidence only; no settlement or history claim |
| `LSEC-CONF-v0.1-AUD-NEG-001` | NEG | Receipt claims settlement without independent L28 settlement evidence | Reject `settlement_claim_unverified` |
| `LSEC-CONF-v0.1-AUD-NEG-002` | NEG | Audit object claims ledger mutation, broadcast, signing, or consensus change | Reject `audit_authority_forbidden` |
| `LSEC-CONF-v0.1-AUD-BND-001` | BND | Identical canonical inputs are evaluated repeatedly | Public audit body and identifier are byte-stable/idempotent |
| `LSEC-CONF-v0.1-AUD-FCL-001` | FCL | Required lineage identifier or evidence binding is missing/conflicting | Reject `audit_lineage_invalid`; do not repair or invent lineage |

Family invariant: receipts and audit records are evidence, not L28 history,
validation, settlement, custody, or authorization by themselves.

### 5.10 Operator authorization gates (`OPR`)

| Case ID | Class | Scenario | Expected outcome / invariant |
|---|---|---|---|
| `LSEC-CONF-v0.1-OPR-POS-001` | POS | Explicit, current, scope-matching operator evidence is supplied after other local gates | Report operator gate satisfied; still no signer invocation in conformance |
| `LSEC-CONF-v0.1-OPR-NEG-001` | NEG | Operator denies the request | Reject `operator_authorization_denied` |
| `LSEC-CONF-v0.1-OPR-NEG-002` | NEG | Operator evidence applies to a different intent, amount, identity, or policy | Reject `operator_authorization_mismatch` |
| `LSEC-CONF-v0.1-OPR-BND-001` | BND | Evidence scope exactly matches the maximum locally approved amount and lifetime | Gate may pass exactly; validation remains mandatory and signer remains inactive |
| `LSEC-CONF-v0.1-OPR-FCL-001` | FCL | Operator authorization or independent security review evidence is missing/stale/unverifiable | Reject `operator_gate_unavailable`; absence is never consent |

Family invariant: operator authorization is necessary for future signer runtime
but is not Protocol validation or settlement authorization.

### 5.11 External subsystem non-authority (`EXT`)

| Case ID | Class | Scenario | Expected outcome / invariant |
|---|---|---|---|
| `LSEC-CONF-v0.1-EXT-POS-001` | POS | Harness/Evals report is attached as labeled advisory evidence | Preserve it as advisory metadata only; outcome is unchanged if removed |
| `LSEC-CONF-v0.1-EXT-NEG-001` | NEG | Harness/Evals score attempts to unlock signing, raise limits, or authorize settlement | Reject `advisory_authority_forbidden` |
| `LSEC-CONF-v0.1-EXT-NEG-002` | NEG | Bitcoin observation/height/confirmation claims L28 signing or validation authority | Reject `external_evidence_authority_forbidden` |
| `LSEC-CONF-v0.1-EXT-BND-001` | BND | Advisory or Bitcoin evidence is absent | Core authorization/validation semantics remain identical; no dependency |
| `LSEC-CONF-v0.1-EXT-FCL-001` | FCL | Input attempts to select production proof architecture, Bitcoin confirmation count, or observer quorum | Reject `future_security_decision_required` |

Family invariant: Harness/Evals remains advisory only. Bitcoin remains external
evidence only. Neither can sign, control custody, validate L28 transactions,
authorize settlement, or affect consensus.

### 5.12 Protocol and economic non-interference (`ECO`)

| Case ID | Class | Scenario | Expected outcome / invariant |
|---|---|---|---|
| `LSEC-CONF-v0.1-ECO-POS-001` | POS | Public status echoes all protected Protocol/economic facts exactly | Values match Section 2.2; no override permitted |
| `LSEC-CONF-v0.1-ECO-NEG-001` | NEG | Signer/policy input attempts to change issuance, supply, reward, height, history, or consensus | Reject `protocol_override_forbidden` |
| `LSEC-CONF-v0.1-ECO-NEG-002` | NEG | Proposed service payment uses coinbase or reserved sender identity | Reject through mandatory Protocol validation; no issuance path |
| `LSEC-CONF-v0.1-ECO-BND-001` | BND | Local spending maximum equals a protected economic value | Treat it only as a local cap; it does not redefine the protected fact |
| `LSEC-CONF-v0.1-ECO-FCL-001` | FCL | Canonical height, issued supply, ledger state, or historical binding is unavailable where required | Fail closed under Protocol rules; do not infer or synthesize state |

Family invariant: L28 remains the sole settlement and consensus authority. A
signer cannot override issuance, supply, height, history, validation, or
consensus.

---

## 6. Coverage and acceptance matrix

| Required coverage | Planned family or families | Acceptance invariant |
|---|---|---|
| Isolated future signer boundary | `ISO`, `KEY` | No signer invocation or secret crossing |
| Authorization != validation | `AUT` | Separate statuses; validation rejection always wins |
| Mandatory `validate_transaction` | `VAL`, `ECO` | No alternate or missing delegate accepted |
| Key custody separation | `KEY` | Public material only; secret input rejected without echo |
| Spending limits | `LIM` | Exact per-transaction/cumulative boundaries; unknown fails closed |
| Approval thresholds | `APR` | Distinct approvals only; threshold never invented |
| Replay protection | `RPL` | Known replay rejected; unavailable state fails closed |
| Expiration controls | `EXP` | Caller-supplied time only; exact boundaries deterministic |
| Receipts/audit evidence | `AUD` | Evidence cannot claim settlement or rewrite history |
| Operator authorization | `OPR` | Explicit scoped gate required; absence is not consent |
| Harness/Evals | `EXT` | Advisory only and removable without changing core semantics |
| Bitcoin | `EXT` | External evidence only; no L28 authority |
| Protocol/economic preservation | `ECO` | All protected facts unchanged; no override path |

A later conformance implementation is acceptable only when every listed case:

1. has one deterministic fictional fixture;
2. produces its exact expected outcome and stable code;
3. proves the common non-execution flags;
4. contains no private, wallet, credential, RPC, or production material;
5. performs no file, network, clock, signer, wallet, broadcast, or ledger write;
6. preserves `validate_transaction` as mandatory authority; and
7. leaves Protocol v1.0.0 and every protected fact unchanged.

---

## 7. Blocked future security decisions

The following remain exactly:

`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

- production proof architecture;
- Bitcoin confirmation count; and
- observer quorum.

Foundation 112 does not choose defaults, ranges, thresholds, fallback values,
or production meanings for these items. A fixture that attempts to supply or
infer them as current policy must fail closed under `EXT-FCL-001`.

Production key custody, signer implementation, atomic replay persistence,
operator approval issuance, broadcast, settlement submission, and production
audit retention also require later separately governed specifications,
independent security review, explicit implementation authorization, and
explicit operator authorization.

---

## 8. Deferred implementation sequence

This plan does not authorize the sequence below; it records dependencies for
future operator decisions:

1. lock exact public fixture and result schemas;
2. materialize offline fictional fixtures for the planned cases;
3. implement a non-signing, read-only conformance runner;
4. independently review custody, policy, replay atomicity, and audit retention;
5. resolve all required future security decisions through governed review;
6. specify a signer interface in a separate milestone; and
7. only after explicit authorization, consider an isolated implementation.

MCP, REST/OpenAPI, SDK, wallet, network, RPC, signing, broadcast, and settlement
work must not precede completion of the canonical offline conformance surface.

---

## 9. Explicit non-activation statement

Foundation 112:

- generates or imports no keys;
- creates or imports no wallets;
- creates no signatures;
- signs and broadcasts nothing;
- connects to no RPC, peer, or network;
- implements no signer runtime;
- activates no settlement;
- submits no transaction;
- mutates no ledger or replay store;
- adds no tests, fixtures, schemas, dependencies, or runtime code;
- changes no consensus or Protocol rule;
- changes no economic or historical fact; and
- grants no operator, signer, adapter, Harness/Evals, or Bitcoin authority.

---

## 10. Document control

| Field | Value |
|---|---|
| Foundation | 112 |
| Parent | `084945d348f9e76ded7bc7d87691e0b582a239b8` |
| Path | `docs/local_signing_economic_control_conformance_plan_v0.1.md` |
| Status | documentation/conformance planning only; non-activating |
| Source architecture review | `docs/local_signing_economic_control_architecture_review_v0.1.md` |
| Runtime implementation | none |
| Tests / fixtures added | none |
| Key or wallet activity | none |
| Signing / broadcast / network activity | none |
| Settlement activation | none |
| Protocol v1.0.0 | unchanged |
| `validate_transaction` | unchanged and mandatory |
| Protected economic facts | unchanged |
| Harness/Evals authority | advisory only |
| Bitcoin authority | external evidence only |
| Production proof / confirmation / quorum | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
