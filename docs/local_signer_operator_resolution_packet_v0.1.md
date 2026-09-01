# Local Signer Operator Resolution Packet v0.1

Status: `RESOLUTION_READINESS_ONLY_NON_APPROVING`

Foundation: 126, workstream 5

Coverage: all 47 Foundation125 `LSOD` decisions

## 1. Purpose and classification rules

This is the authoritative resolution-readiness summary for the canonical 47-decision register. It does not approve a candidate, select production policy, authorize implementation, or activate any signer/runtime behavior.

Each stable ID is classified exactly once:

- `OPERATOR_CAN_DECIDE_NEXT`: the operator can open the actual resolution record now using repository evidence and required review; classification does not pre-approve an outcome.
- `SECURITY_EXPERT_DECISION_REQUIRED`: the decision requires named independent security expertise before operator approval.
- `IMPLEMENTATION_EVIDENCE_REQUIRED_FIRST`: a concrete, separately authorized non-production evidence exercise or measurement is required before a defensible decision; no such exercise is authorized here.
- `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`: the decision cannot proceed under Foundation126 and remains blocked.

Every ID also remains `CANDIDATE_NOT_APPROVED`. Missing required decisions/evidence fails closed. L28 Protocol v1.0.0, canonical `coin.tx_validation.validate_transaction`, authorization/validation separation, and eligibility/invocation separation remain controlling.

## 2. Exact 47-ID readiness classification

| Stable ID | Readiness classification | Resolution dependency/order and next evidence |
|---|---|---|
| `LSOD-EVD-001` | `SECURITY_EXPERT_DECISION_REQUIRED` | Cryptographic/protocol reviewer first; coordinate with EVD-002/003 and OPS-001; canonical vectors and threat model required |
| `LSOD-EVD-002` | `SECURITY_EXPERT_DECISION_REQUIRED` | Identity/PKI governance review after proof requirements are framed; revocation/policy/audit dependencies documented |
| `LSOD-EVD-003` | `SECURITY_EXPERT_DECISION_REQUIRED` | Verifier/isolation/material-lifecycle review coordinated with EVD-001/002, CUS-003, OPS-007 |
| `LSOD-EVD-004` | `IMPLEMENTATION_EVIDENCE_REQUIRED_FIRST` | Security architecture first, then measured issuance/verification/revocation/outage evidence; `PARAMETER_REQUIRES_MEASUREMENT` |
| `LSOD-EVD-005` | `SECURITY_EXPERT_DECISION_REQUIRED` | Revocation/availability threat model coordinated with EVD-002/004 and OPS-001/002 |
| `LSOD-EVD-006` | `SECURITY_EXPERT_DECISION_REQUIRED` | Policy-governance and atomic transition review coordinated with EVD-002/004 and STA-002 |
| `LSOD-EVD-007` | `SECURITY_EXPERT_DECISION_REQUIRED` | Authorization/collusion review coordinated with EVD-002/006, CUS-004, STA-008 |
| `LSOD-EVD-008` | `SECURITY_EXPERT_DECISION_REQUIRED` | Replay/nonce/retention review coordinated with STA-001/006 and EVD-007 |
| `LSOD-EVD-009` | `SECURITY_EXPERT_DECISION_REQUIRED` | Audit/privacy review coordinated with OPS-002/006 and proof design |
| `LSOD-EVD-010` | `OPERATOR_CAN_DECIDE_NEXT` | Operator may decide only bounded non-activating scope, reviewers, evidence, and prohibited capabilities; EVD-001..009 remain prerequisites to substantive implementation |
| `LSOD-CUS-001` | `SECURITY_EXPERT_DECISION_REQUIRED` | Independent cryptographic/custody review before any material profile; coordinate with EVD-001 and CUS-002/003 |
| `LSOD-CUS-002` | `OPERATOR_CAN_DECIDE_NEXT` | Operator may decide whether generation/import scope is none, generation, import, or both; enabling paths still require CUS-001/003/005 security review |
| `LSOD-CUS-003` | `SECURITY_EXPERT_DECISION_REQUIRED` | Isolation/attestation threat model and independent penetration architecture review; coordinate with OPS-007 |
| `LSOD-CUS-004` | `SECURITY_EXPERT_DECISION_REQUIRED` | Organizational/access-control/collusion review before roles or thresholds are approved |
| `LSOD-CUS-005` | `SECURITY_EXPERT_DECISION_REQUIRED` | Ceremony security/state-machine review after CUS-002/004 and audit requirements are framed |
| `LSOD-CUS-006` | `SECURITY_EXPERT_DECISION_REQUIRED` | Lifecycle/concurrency/time review coordinated with CUS-005/007, STA-002, OPS-001 |
| `LSOD-CUS-007` | `SECURITY_EXPERT_DECISION_REQUIRED` | Incident/revocation authority and freshness review coordinated with CUS-004/006/010 |
| `LSOD-CUS-008` | `OPERATOR_CAN_DECIDE_NEXT` | Operator may decide whether backup is prohibited or in scope; any enabled mechanism waits for CUS-003/004/006/007 and OPS-002 |
| `LSOD-CUS-009` | `IMPLEMENTATION_EVIDENCE_REQUIRED_FIRST` | Selected material/isolation/backup technology and copy inventory required before destruction method; no real material operation authorized |
| `LSOD-CUS-010` | `SECURITY_EXPERT_DECISION_REQUIRED` | Incident-response, forensics/privacy, containment and recovery review after roles/lifecycle/revocation are framed |
| `LSOD-CUS-011` | `SECURITY_EXPERT_DECISION_REQUIRED` | Custody-evidence proof/privacy/audit review coordinated with EVD-001/003 and OPS-002 |
| `LSOD-CUS-012` | `OPERATOR_CAN_DECIDE_NEXT` | Operator may define a non-key, non-signing evidence milestone only; production custody waits for CUS-001..011 and GAT-004 |
| `LSOD-STA-001` | `SECURITY_EXPERT_DECISION_REQUIRED` | Distributed-state trust/failure model review first; coordinate with STA-002/003/009 and OPS-007 |
| `LSOD-STA-002` | `SECURITY_EXPERT_DECISION_REQUIRED` | Concurrency/isolation/formal-invariant review after state boundary is framed |
| `LSOD-STA-003` | `SECURITY_EXPERT_DECISION_REQUIRED` | Durability/replication/split-brain review; no quorum/count selected; coordinate with STA-001/002/005/009 |
| `LSOD-STA-004` | `SECURITY_EXPERT_DECISION_REQUIRED` | Cryptographic/state-integrity and canonical-lineage review coordinated with EVD-001 and STA-001/010 |
| `LSOD-STA-005` | `IMPLEMENTATION_EVIDENCE_REQUIRED_FIRST` | Conflict/latency/crash prototype measurements required; `PARAMETER_REQUIRES_MEASUREMENT` |
| `LSOD-STA-006` | `SECURITY_EXPERT_DECISION_REQUIRED` | Replay/privacy/audit/legal retention review coordinated with EVD-008/009 and OPS-002 |
| `LSOD-STA-007` | `OPERATOR_CAN_DECIDE_NEXT` | Operator may decide local economic-control objectives/shape; exact values/windows require rationale, concurrency review, and no ledger interpretation |
| `LSOD-STA-008` | `SECURITY_EXPERT_DECISION_REQUIRED` | Authorization/reuse/threshold atomic-consumption review coordinated with EVD-007/008 and STA-002 |
| `LSOD-STA-009` | `SECURITY_EXPERT_DECISION_REQUIRED` | Disaster-recovery/state-integrity review after durability/integrity/retention models are framed |
| `LSOD-STA-010` | `SECURITY_EXPERT_DECISION_REQUIRED` | Storage security and non-signer key-separation review coordinated with OPS-002/006/007 |
| `LSOD-STA-011` | `IMPLEMENTATION_EVIDENCE_REQUIRED_FIRST` | Concrete schema and migration prototype required before transform/cutover choice; no migration authorized |
| `LSOD-STA-012` | `OPERATOR_CAN_DECIDE_NEXT` | Operator may define abstract/non-production state evidence scope; production state/runtime waits for STA-001..011 and GAT-004 |
| `LSOD-OPS-001` | `SECURITY_EXPERT_DECISION_REQUIRED` | Independent trusted-time/rollback review first; numeric skew/uncertainty/outage/cache values are `PARAMETER_REQUIRES_MEASUREMENT` |
| `LSOD-OPS-002` | `SECURITY_EXPERT_DECISION_REQUIRED` | Audit-security/privacy/resilience review coordinated with EVD-009, CUS-011, STA-003/006/009 |
| `LSOD-OPS-003` | `IMPLEMENTATION_EVIDENCE_REQUIRED_FIRST` | Representative canonical corpus and parser CPU/memory benchmarks required; every numeric bound `PARAMETER_REQUIRES_MEASUREMENT` |
| `LSOD-OPS-004` | `IMPLEMENTATION_EVIDENCE_REQUIRED_FIRST` | Load/capacity/dependency/fault measurements required; all limits/timeouts `PARAMETER_REQUIRES_MEASUREMENT` |
| `LSOD-OPS-005` | `SECURITY_EXPERT_DECISION_REQUIRED` | Application-security/privacy review of exact F117 mapping, disclosure, timing, and retries |
| `LSOD-OPS-006` | `SECURITY_EXPERT_DECISION_REQUIRED` | Observability/privacy/incident review; thresholds/retention later require measurement |
| `LSOD-OPS-007` | `SECURITY_EXPERT_DECISION_REQUIRED` | Platform/isolation/capability and penetration architecture review before topology selection |
| `LSOD-OPS-008` | `IMPLEMENTATION_EVIDENCE_REQUIRED_FIRST` | Concrete component/trust-zone architecture, failure evidence, and runbook exercises required; production deployment remains blocked |
| `LSOD-OPS-009` | `OPERATOR_CAN_DECIDE_NEXT` | Operator may approve assurance structure, non-waivable minimum, reviewer independence, and evidence format; passing evidence is not pre-approved |
| `LSOD-GAT-001` | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` | Production Bitcoin proof architecture remains unselected and blocked; Bitcoin external evidence only |
| `LSOD-GAT-002` | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` | Bitcoin confirmation/reorg policy and count remain unselected and blocked; no value/range/fallback |
| `LSOD-GAT-003` | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` | Observer quorum/independence remain unselected and blocked; no count/model/fallback |
| `LSOD-GAT-004` | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` | Signer implementation/runtime/deployment/activation remains blocked until every applicable prerequisite is satisfied and separately authorized |

### 2.1 Classification counts

| Classification | Count |
|---|---:|
| `OPERATOR_CAN_DECIDE_NEXT` | 7 |
| `SECURITY_EXPERT_DECISION_REQUIRED` | 29 |
| `IMPLEMENTATION_EVIDENCE_REQUIRED_FIRST` | 7 |
| `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` | 4 |
| **Total** | **47** |

## 3. Dependency order

Resolution must proceed in this order without treating earlier discussion as approval:

1. **Operator scope and assurance framing:** review `LSOD-EVD-010`, `CUS-002`, `CUS-008`, `CUS-012`, `STA-007`, `STA-012`, and `OPS-009`. Record only the decisions actually supported; unresolved portions remain candidates.
2. **Name independent experts and accountable approvers:** assign cryptographic/identity, custody, distributed-state, trusted-time, audit/privacy, application/platform security, and assurance reviewers with conflict disclosures.
3. **Resolve foundational security shapes:** evidence trust (`EVD-001`–`003`, `005`–`009`), custody controls (`CUS-001`, `003`–`007`, `010`, `011`), state semantics (`STA-001`–`004`, `006`, `008`–`010`), and operations controls (`OPS-001`, `002`, `005`–`007`). Cross-domain decisions must use the same versions and authority assumptions.
4. **Authorize evidence exercises separately if needed:** only after exact scope/prohibitions are approved, gather evidence for `EVD-004`, `CUS-009`, `STA-005`, `STA-011`, `OPS-003`, `OPS-004`, and `OPS-008`. Such work must remain non-signing, non-networked unless separately authorized, non-production, and non-activating.
5. **Close implementation prerequisites:** re-review every applicable decision, conformance evidence, independent finding, remediation, rollback/change control, and authority firewall.
6. **Keep GAT gates closed:** `GAT-001`–`004` remain blocked until separately governed future security decisions. No preceding resolution implicitly opens them.

## 4. Minimum decisions before any implementation authorization

Foundation126 authorizes no implementation. A future operator may consider only a bounded evidence-producing implementation authorization after, at minimum:

1. `LSOD-EVD-010`, `LSOD-CUS-012`, `LSOD-STA-012`, and `LSOD-OPS-009` have approved, mutually consistent scope, prohibited capabilities, test evidence, reviewer, and stop conditions;
2. every foundational security decision applicable to the proposed component is approved with independent review—there is no blanket approval by domain;
3. `LSOD-OPS-007` defines the applicable least-privilege boundary and component identities;
4. dependencies are version-bound, missing decisions explicitly block affected paths, and no unresolved value is supplied by a default;
5. the authorization states that it grants no signing, wallet/key access, transaction submission, broadcast, settlement, deployment, or activation; and
6. `LSOD-GAT-004` remains blocked.

Any actual signer implementation, signer runtime, deployment, or activation cannot be authorized until all applicable 43 non-GAT decisions are resolved, all F122 gates are satisfied with implementation/conformance/independent-review evidence, and `LSOD-GAT-004` is separately decided. That condition is not met.

## 5. Decisions that may be reviewed together

Joint review is permitted only for consistency; each ID still receives its own approval record:

- **Scope/assurance bundle:** `EVD-010`, `CUS-012`, `STA-012`, `OPS-009`.
- **Custody operational-scope bundle:** `CUS-002`, `CUS-008`; any enabled capability then waits for its security dependencies.
- **Local economic-control framing:** `STA-007` may be reviewed with `EVD-006`, `EVD-007`, and `STA-008`, but the latter three require security expertise.
- **Evidence trust bundle:** `EVD-001`–`003`, `EVD-005`, `EVD-006`, and `EVD-009` with `OPS-001/002/007` representatives.
- **Custody security bundle:** `CUS-001`, `CUS-003`–`007`, `CUS-010`, `CUS-011`.
- **Atomic-state bundle:** `STA-001`–`004`, `STA-006`, `STA-008`–`010`.
- **Operations security bundle:** `OPS-001`, `OPS-002`, `OPS-005`–`007`.

Joint review does not permit one decision to stand in for another or to broaden authority.

## 6. Decisions that must wait

- `EVD-004`, `CUS-009`, `STA-005`, `STA-011`, `OPS-003`, `OPS-004`, and `OPS-008` wait for the specified implementation/measurement evidence and prior security decisions.
- Every `SECURITY_EXPERT_DECISION_REQUIRED` ID waits for a named qualified independent reviewer and required threat/evidence record.
- `GAT-001`, `GAT-002`, `GAT-003`, and `GAT-004` remain blocked.
- Deployment, activation, real custody, signing, wallet/key access, networking, RPC, broadcast, settlement, mining, bridge, and testnet work must wait for separate authorization even after planning decisions are resolved.

## 7. Required approval-record fields

Each future resolution record must contain:

1. exact LSOD stable ID and decision-record version;
2. selected candidate/parameter profile and explicit rejected candidates;
3. status and effective scope, environment, interval, predecessor, and successor;
4. accountable operator name/role and approval authority evidence;
5. decision question, rationale, threat model, risks addressed, residual risks, and assumptions;
6. exact dependencies and their approved versions;
7. implementation/measurement evidence references and provenance;
8. conformance, adversarial, fault, recovery, and regression evidence references;
9. independent reviewer identity, qualifications, independence/conflict statement, findings, and disposition;
10. Protocol/authority/non-execution assertions, including canonical validation binding;
11. rollback prohibition, change control, compromise response, supersession, and deactivation rules;
12. explicit statement that approval does not imply signer invocation, deployment, activation, broadcast, or settlement; and
13. immutable public audit reference containing no secret material.

Missing any required field leaves the decision unapproved and fail closed.

## 8. Required independent-review evidence

Independent review must identify the exact artifacts/versions reviewed, reviewer qualifications and conflicts, threat model, methods, tests independently reproduced, findings by severity, required remediation, remediation verification, residual risk, and explicit scope limitations. A reviewer recommendation is evidence for the accountable operator; it is not itself operator approval or runtime authorization.

Security expertise must cover the relevant domain: cryptography/identity, custody, distributed-state correctness, trusted time, audit/privacy, application/platform isolation, denial-of-service, incident/recovery, and end-to-end authority separation. One reviewer need not cover every domain, and Harness/Evals cannot serve as approval authority.

## 9. Exact next operator action

After Foundation126, the operator should open a separately authorized **operator decision-resolution session**, not another planning-only Foundation milestone. In that session the operator should:

1. assign accountable approvers and independent security experts;
2. present the seven `OPERATOR_CAN_DECIDE_NEXT` packets for actual disposition in dependency order;
3. commission expert decision records for the 29 security-expert IDs;
4. define separately authorized, non-activating evidence charters for the seven implementation-evidence IDs only after their prerequisite security/scope decisions; and
5. leave all four GAT decisions blocked.

No further planning-only Foundation milestone is required before beginning actual decision resolution. This statement does not mean any decision is approved or that implementation may begin.

## 10. Protocol, economics, and non-activation

Preserved exactly: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.

Bitcoin remains external evidence only and has zero authority over L28 issuance, supply, height, validation, consensus, history, or settlement. Production Bitcoin proof architecture, Bitcoin confirmation/reorg policy and count, and observer quorum/independence remain blocked and unselected.

Foundation126 grants no implementation, signer invocation, signature generation, wallet/key/HSM/KMS access, RPC/network connection, submission, broadcast, mining, bridge, ledger mutation, settlement, database, migration, server, deployment, testnet, or activation authorization.
