# Local Signer Custody Conformance Plan v0.1

Status: `DEFINED_PLAN_ONLY`

Foundation: 125, workstream 3

Source profile: `l28-local-signer-custody-control/v0.1`

Addresses: F122-G02 and decisions `LSOD-CUS-001` through `LSOD-CUS-012`

## 1. Scope

This document plans deterministic and future security conformance for the custody-control profile. It performs no generation, import, derivation, storage, access, rotation, revocation, backup, recovery, destruction, HSM/KMS operation, signing, wallet operation, or secret inspection. It creates no executable fixture, test, runtime, service, or deployment.

Custody remains isolated and subordinate to L28 Protocol v1.0.0. `coin.tx_validation.validate_transaction` is canonical and mandatory. Authorization is not validation. Custody status and signer eligibility are not signer invocation. Possession or custody evidence has zero authority over issuance, supply, height, history, validation, consensus, or settlement.

All values and mechanisms in `LSOD-CUS-001` through `012` remain `OPERATOR_DECISION_REQUIRED`. Test data must use fictional public identifiers and simulated state labels only—never real material, locators, credentials, devices, wallets, HSMs, KMSs, or services.

## 2. Deterministic family model

Immutable planned family IDs are:

- `CUS-POS-NN`: coherent public custody-control evidence;
- `CUS-NEG-NN`: one invalid control, transition, role, or evidence condition;
- `CUS-BND-NN`: exact lifecycle, threshold, time, overlap, or retention boundary;
- `CUS-FCL-NN`: missing, corrupt, unavailable, compromised, quarantined, or undecided custody state.

Expected outcomes are profile-level only:

- POS: `CONTROL_PROFILE_CONFORMANT`; may contribute to eligibility but never invokes a signer.
- NEG: deterministic rejection at the earliest custody-control gate.
- BND: exact approved boundary behavior, with production values supplied only by approved decision profiles.
- FCL: ineligible/unavailable/security-decision-required with no fallback, key operation, or recovery by assumption.

These labels are not runtime codes. Any future materialization must use the existing Foundation117 taxonomy.

## 3. Planned family inventory

### 3.1 Positive families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `CUS-POS-01` | Exact custody profile/version/schema/order and public-only values | Control-profile conformant | No unknown/default/secret fields |
| `CUS-POS-02` | Approved material profile and public identifier binding | Control-profile conformant | No algorithm negotiation or cross-purpose use |
| `CUS-POS-03` | Separately authorized fictional generation ceremony evidence | Control-profile conformant simulation | Generation permission does not imply import, activation, or signing |
| `CUS-POS-04` | Separately authorized fictional import ceremony evidence | Control-profile conformant simulation | Import origin/provenance/quarantine controls exact |
| `CUS-POS-05` | Isolation, non-exportability, attestation, and health evidence | Control-profile conformant | Public evidence contains no material or secret locator |
| `CUS-POS-06` | Distinct authenticated roles and satisfied approved ceremony threshold | Control-profile conformant | Separation of duties remains intact |
| `CUS-POS-07` | Valid monotonic lifecycle transition | Control-profile conformant | Only approved predecessor/successor states accepted |
| `CUS-POS-08` | Bound rotation with verified successor and disabled predecessor | Control-profile conformant | No uncontrolled dual authority |
| `CUS-POS-09` | Current monotonic revocation evidence | Control-profile conformant | Revoked material cannot reactivate |
| `CUS-POS-10` | Approved fictional backup/recovery evidence, if policy permits backup | Control-profile conformant simulation | Restored material remains inactive pending verification |
| `CUS-POS-11` | Verified destruction public evidence and reconciled inventory | Control-profile conformant simulation | Destruction is monotonic and reveals no secret |
| `CUS-POS-12` | Public custody evidence bound to request/policy/material/lifecycle | Control-profile conformant | Evidence proves controls only, not validity or invocation |

### 3.2 Negative families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `CUS-NEG-01` | Unknown/deprecated/mismatched material profile or caller-selected algorithm | Reject material policy | No negotiation, downgrade, or conversion |
| `CUS-NEG-02` | Private key/seed/mnemonic/xprv/wallet/credential/locator field | Reject public-only gate | Secret is never read, projected, or logged |
| `CUS-NEG-03` | Generation attempted under import-only/no-generation policy | Reject generation boundary | Permission classes are independent |
| `CUS-NEG-04` | Import attempted under generation-only/no-import policy | Reject import boundary | No implied import authority |
| `CUS-NEG-05` | Unverifiable origin, duplicate identity, malformed encoding, incomplete ceremony | Reject provisioning | Failed material remains quarantined |
| `CUS-NEG-06` | Isolation/attestation mismatch, exportable claim, unexpected access path | Reject isolation gate | Degraded boundary cannot contribute to eligibility |
| `CUS-NEG-07` | Unauthorized role, expired session, forbidden role combination, insufficient threshold | Reject access/ceremony gate | No single role gains end-to-end control |
| `CUS-NEG-08` | Skipped, reversed, unknown, or stale lifecycle transition | Reject lifecycle gate | State rollback/reactivation forbidden |
| `CUS-NEG-09` | Use of PROVISIONED_INACTIVE/ROTATING-outside-policy/REVOKED/DESTROYED material | Reject eligibility | Lifecycle status never repaired by request evidence |
| `CUS-NEG-10` | Rotation activates successor early or leaves predecessor enabled too long | Reject rotation | Exact transition boundary enforced |
| `CUS-NEG-11` | Revocation missing authentication, wrong authority, stale publication, or recovery reactivation | Reject revocation | Revocation monotonic |
| `CUS-NEG-12` | Backup disallowed, wrong isolation, insufficient recovery roles, stale/revoked backup | Reject backup/recovery | Recovery never silently restores authority |
| `CUS-NEG-13` | Incomplete/unverifiable destruction or missing inventory copy | Reject destruction claim; quarantine | Assumed destruction forbidden |
| `CUS-NEG-14` | Compromise alert ignored, queued use continues, predecessor reused | Reject and quarantine | Suspected compromise immediately blocks use |
| `CUS-NEG-15` | Custody evidence forged/stale/mismatched/over-disclosing | Reject custody evidence | Public evidence is authenticated, minimal, current, exact |
| `CUS-NEG-16` | Custody evidence claims validation, signature, broadcast, or settlement | Reject authority assertion | Custody has no Protocol or execution authority |

### 3.3 Boundary families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `CUS-BND-01` | Exact supported profile version versus adjacent unsupported version | Exact passes; adjacent rejects | No compatibility inference |
| `CUS-BND-02` | Ceremony roles immediately below, exactly at, and above approved threshold | Below rejects; exact/above follow policy | Threshold remains parameterized by `LSOD-CUS-004/005` |
| `CUS-BND-03` | Activation instant immediately before/at/after | Only policy-authorized interval can be ACTIVE | No early activation |
| `CUS-BND-04` | Material expiry immediately before/at/after | Equality is expired unless approved profile explicitly says otherwise | Trusted integer time exact; no hidden grace |
| `CUS-BND-05` | Rotation overlap at maximum and one unit beyond | Maximum follows approved policy; beyond rejects | No uncontrolled dual use |
| `CUS-BND-06` | Revocation publication/freshness at approved maximum and beyond | Boundary follows policy; stale rejects | No outage-as-valid behavior |
| `CUS-BND-07` | Backup/recovery threshold and retention boundary | Exact policy applies; missing/expired evidence rejects | No threshold or duration selected here |
| `CUS-BND-08` | Destruction coverage last inventory copy | All scoped copies required | Partial destruction never becomes DESTROYED |
| `CUS-BND-09` | Custody-evidence verification cadence/expiry boundary | Exact approved freshness semantics | Stale evidence cannot contribute to eligibility |
| `CUS-BND-10` | Lifecycle state version concurrent with request binding | Only exact current version accepted | Stale lifecycle snapshot fails closed |

### 3.4 Fail-closed families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `CUS-FCL-01` | Material/algorithm decision unresolved | Security-decision-required | No placeholder algorithm or material |
| `CUS-FCL-02` | Generation/import permission or origin class unresolved | Security-decision-required | Default is no operation |
| `CUS-FCL-03` | Isolation or attestation unavailable/contradictory | Ineligible/unavailable | No software/process fallback |
| `CUS-FCL-04` | Role/threshold/ceremony policy missing | Security-decision-required | No single-operator default |
| `CUS-FCL-05` | Lifecycle/revocation state missing, stale, corrupt, or forked | Ineligible/unavailable | Unknown is never ACTIVE |
| `CUS-FCL-06` | Backup/recovery outcome uncertain | Quarantined/ineligible | No restore by assumption |
| `CUS-FCL-07` | Destruction verification unavailable | Quarantined, not DESTROYED | Unverified destruction remains unsafe |
| `CUS-FCL-08` | Suspected compromise with incomplete containment/review | COMPROMISED/QUARANTINED | No automatic return to service |
| `CUS-FCL-09` | Custody evidence verifier or trusted time unavailable | Ineligible/unavailable | No stale evidence fallback |
| `CUS-FCL-10` | Audit durability/recovery unavailable | Ineligible/unavailable | Lifecycle action is not treated as durably proven |
| `CUS-FCL-11` | Canonical validation binding missing/rejected | Ineligible | Custody never substitutes validation |
| `CUS-FCL-12` | Implementation/deployment/activation decision unresolved | Security-decision-required | Profile conformance grants zero runtime authorization |

## 4. Security-test method

Future deterministic cases operate only on public fictional custody-state objects. Negative and boundary probes use test-local mutations. Security/fault plans may specify mocked unavailable/corrupt/compromised states but may not contact or emulate a real wallet, signer, HSM, KMS, keychain, secret store, RPC service, or network.

Static/AST-aware checks must verify that test material imports no custody runtime and calls no key, wallet, signing, network, submission, broadcast, or settlement API. Literal negative-case vocabulary is not itself executable behavior and must not be checked with naive forbidden-string matching.

## 5. Acceptance and traceability

Future materialization must trace every `LSOD-CUS-*` decision to POS, NEG, BND, and FCL evidence where applicable; preserve exact profile property order; cover every lifecycle state and authorized transition; prove separation of duties; and verify that all authority overrides and non-execution assertions remain false.

Passing future custody conformance proves neither production custody safety nor the existence or use of a key. It authorizes no implementation, ceremony, device access, signing, deployment, or activation.

## 6. Protocol and economic invariants

Preserved exactly: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.

Bitcoin remains external evidence only. Production Bitcoin proof architecture, Bitcoin confirmation/reorg policy and count, observer quorum/independence, and signer implementation/runtime/deployment/activation remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

Foundation125 authorizes no implementation or activation.
