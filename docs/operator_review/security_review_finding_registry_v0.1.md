# L28 Security Review Finding Registry Framework v0.1

Status: `FRAMEWORK_ONLY_NO_FINDINGS`

Decision effect: none. This document defines the controlled format for future independent-review findings. It creates no finding, pre-approves no finding, resolves no LSOD item, and authorizes no implementation or runtime behavior.

## 1. Purpose and authority boundary

The registry provides immutable identity, LSOD traceability, evidence provenance, severity, remediation state, reviewer conclusion, and independent signoff for findings produced under a separately authorized security review.

A finding is security-review evidence only. It cannot:

- approve or amend an LSOD decision;
- select a production value or security mechanism;
- substitute for accountable operator approval;
- advance a security maturity gate by itself; or
- authorize implementation, deployment, signer invocation, or activation.

The Phase 2 review scope and evidence requirements govern the current 29 `SECURITY_EXPERT_DECISION_REQUIRED` items. This framework does not change that inventory.

## 2. Finding identity

### 2.1 Finding ID format

Every future finding ID shall use:

`L28-SRF-<REVIEW_SERIES>-<SEQUENCE>`

where:

- `L28-SRF` is the fixed namespace;
- `<REVIEW_SERIES>` is `R` followed by exactly four ASCII digits, allocated once to one versioned independent-review engagement; and
- `<SEQUENCE>` is exactly four ASCII digits, beginning at `0001` and increasing without reuse within that review series.

Grammar:

`^L28-SRF-R[0-9]{4}-[0-9]{4}$`

Finding IDs are immutable, never reassigned, and never deleted. A duplicate, malformed, missing, recycled, or ambiguously allocated ID fails closed and cannot enter the registry. Corrections supersede content through a new finding-record version while preserving the original ID and complete history.

### 2.2 Finding record version

Each finding record has an integer `record_version` beginning at `1`. Every material change increments it by exactly one and identifies its predecessor. Review history is append-only; prior versions remain immutable evidence.

## 3. LSOD mapping rules

Every finding must contain:

- exactly one `primary_lsod_decision_id` from the authorized review scope;
- zero or more unique, ordered `related_lsod_decision_ids`;
- the exact LSOD decision-record or register version reviewed;
- the requirement/control references affected; and
- a statement of whether the finding affects one or more security maturity gates.

An LSOD mapping does not resolve or update the mapped decision. Cross-domain findings retain one primary ID and list every affected related ID; they are not duplicated to manufacture independent closure. Unknown, malformed, out-of-scope, or version-unbound LSOD references fail closed.

The Bitcoin and activation gates—`LSOD-GAT-001`, `LSOD-GAT-002`, `LSOD-GAT-003`, and `LSOD-GAT-004`—remain blocked and cannot be resolved by a registry entry.

## 4. Required finding record

Every future record must contain all fields below. `NONE` is permitted only where the field definition explicitly allows it; omission is not permitted.

| Field | Requirement |
|---|---|
| `finding_id` | Immutable ID satisfying Section 2.1 |
| `record_version` | Positive integer with exact predecessor linkage |
| `review_series` | Exact review engagement identity matching the finding ID |
| `primary_lsod_decision_id` | Exactly one authorized LSOD ID |
| `related_lsod_decision_ids` | Ordered unique list; may be empty |
| `source_requirements` | Exact document, section, version, and digest where applicable |
| `severity` | Exactly one of `PASS`, `GAP`, `REQUIRED_CHANGE`, or `BLOCKED` |
| `title` | Concise, unique description within the review series |
| `description` | Reproducible statement of the reviewed condition; no unsupported conclusion |
| `threat_model` | Assets, actors, trust assumptions, attack path, preconditions, failure modes, and affected invariants |
| `evidence_reviewed` | Ordered evidence manifest with artifact identity, version/digest, provenance, review method, and limitations |
| `tests_reviewed` | Ordered test manifest and independently reproduced results; `NONE` only with justification and resulting non-PASS disposition |
| `risk_impact` | Confidentiality, integrity, availability, authority, protocol, economic, privacy, recovery, and operational impact |
| `reviewer_conclusion` | Evidence-grounded conclusion and residual risk; never an operator approval |
| `required_remediation` | Exact required change/evidence, or `NONE` only for a supported `PASS` |
| `remediation_state` | One value from Section 6 |
| `dependencies` | Unresolved decisions, evidence, findings, or gates that constrain disposition |
| `maturity_gate_effect` | Gates blocked, reopened, or unaffected, with rationale |
| `independent_reviewer_signoff` | Required identity, qualifications, independence/conflict statement, scope, date, and conclusion |
| `change_control_history` | Append-only record of every version, actor, reason, evidence change, and state transition |

## 5. Severity definitions

Severity is an evidence disposition for the scoped requirement, not a business priority and not an operator decision.

### `PASS`

The exact reviewed requirement is supported by complete, version-bound, independently reproducible evidence; applicable tests pass; authority and fail-closed invariants hold; no required remediation remains; and residual risk is explicitly documented. `PASS` does not approve the linked LSOD decision or authorize runtime behavior.

### `GAP`

Required evidence, specification detail, traceability, test coverage, reviewer access, or dependency is missing or insufficient. The reviewer cannot substantiate `PASS`. A `GAP` leaves the linked decision not ready for operator consideration until closed under the closure criteria.

### `REQUIRED_CHANGE`

Reviewed design, implementation evidence, control, test behavior, or process fails a security requirement or exposes material risk that must be corrected. The affected decision and maturity gates remain blocked until remediation is independently verified.

### `BLOCKED`

Review or safe disposition cannot proceed because a prerequisite security decision, authoritative evidence, reviewer independence, protected invariant, or permitted review boundary is absent or contradictory. No default, waiver, risk acceptance, or scope inference may convert `BLOCKED` to another severity.

Severity must not be silently downgraded. Any proposed severity change requires new evidence, written rationale, an incremented record version, and independent reviewer signoff. Original severity history remains visible.

## 6. Remediation states

Allowed values are:

- `NOT_APPLICABLE`: permitted only for a supported `PASS` with `required_remediation: NONE`;
- `OPEN`: remediation or missing evidence has not been accepted for review;
- `EVIDENCE_SUBMITTED`: a versioned remediation-evidence bundle awaits reviewer validation;
- `REMEDIATION_PROPOSED`: a bounded proposal is awaiting reviewer disposition;
- `UNDER_REVIEW`: accepted evidence/remediation is being independently re-reviewed;
- `REJECTED`: submitted remediation was rejected with reasons and remains unresolved;
- `VERIFIED`: the independent reviewer verified the exact remediation against the finding and regressions;
- `CLOSED`: closure criteria were satisfied and independently signed; and
- `REOPENED`: later evidence, change, regression, expiry, compromise, or contradiction invalidated prior closure.

`VERIFIED` is not `CLOSED`. `CLOSED` is not LSOD approval. A `GAP`, `REQUIRED_CHANGE`, or `BLOCKED` finding cannot use `NOT_APPLICABLE`.

## 7. Evidence reviewed

The `evidence_reviewed` manifest must identify:

- artifact name, version, digest where applicable, origin, custodian, and collection method;
- exact review method and independently reproduced portions;
- whether the artifact is design, decision, implementation, test, operational, or review evidence;
- freshness/effective interval and supersession status;
- confidentiality/public-disclosure classification without recording secrets; and
- limitations, unavailable evidence, contradictions, and unresolved provenance.

Evidence bundles must be canonical, ordered, version-bound, and immutable after reviewer signoff. New evidence creates a new finding-record version; it never rewrites the reviewed bundle. Missing, stale, contradictory, unverifiable, or mismatched evidence cannot support `PASS`.

## 8. Reviewer conclusion and signoff

The reviewer conclusion must state:

- the exact question answered and the evidence-supported answer;
- assumptions accepted and rejected;
- observed and residual risks;
- limitations and unresolved dependencies;
- severity and remediation-state rationale;
- maturity-gate effect; and
- whether the linked decision is `READY_FOR_OPERATOR_CONSIDERATION` or `NOT_READY_FOR_OPERATOR_CONSIDERATION`.

Independent signoff requires reviewer name/role, relevant qualifications, organizational and financial independence, conflicts, exact scope and versions reviewed, methods, date, and an attestation that no operator approval or runtime authorization is implied. Missing or conflicted signoff cannot support `PASS`, `VERIFIED`, or `CLOSED`.

## 9. Empty registry state

At creation of this framework, the finding registry contains zero findings:

| Finding ID | Primary LSOD ID | Severity | Remediation state | Reviewer conclusion | Independent signoff |
|---|---|---|---|---|---|
| _No findings created_ | — | — | — | — | — |

This sentinel row is not a finding, has no finding ID, and confers no status.

## 10. Protocol, economics, and non-activation

L28 Protocol v1.0.0 remains authoritative. `coin.tx_validation.validate_transaction` remains the canonical mandatory validator and must bind to the exact transaction. Authorization is not validation. Eligibility is not signer invocation.

Bitcoin remains external evidence only and has zero authority over L28 issuance, supply, canonical height, validation, consensus, history, or settlement. The following remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`: production Bitcoin proof architecture; Bitcoin confirmation/reorganization policy and count; observer quorum/independence; and signer implementation/runtime/deployment/activation.

Protected facts remain exactly: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.

This framework authorizes no decision approval, protocol or code change, signer, wallet, key, signature, HSM/KMS access, RPC, network, submission, broadcast, mining, bridge, ledger/state mutation, settlement, database, migration, server, deployment, testnet, production process, or activation.
