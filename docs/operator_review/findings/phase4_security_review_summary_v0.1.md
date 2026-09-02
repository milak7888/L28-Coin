# Phase 4 — Independent Security Review Round 1 Summary v0.1

Status: `ROUND_1_REPOSITORY_REVIEW_COMPLETE_FINDINGS_OPEN`

Review series: `R0001`

Reviewed repository parent: `c46a06462b4f20ed4b043c8ada2f96b876ed39f5`

## 1. Reviewer role and limitations

Codex acted in this phase as an evidence-bound repository reviewer and made no implementation changes or policy choices. The review is independent from authoring/implementation activity in Phase 4, but it is not a substitute for a named qualified human security expert. No human reviewer identity, credentials, organizational/financial independence, conflict disclosure, or signoff exists in the reviewed repository.

Accordingly:

- every finding remains open;
- no finding satisfies the published closure criteria;
- no LSOD decision is approved;
- no security maturity gate advances; and
- no implementation, signer invocation, deployment, or activation is authorized.

## 2. Evidence reviewed

The review covered:

- `PROTOCOL.md`;
- Foundation122 `docs/local_signer_interface_security_review_v0.1.md`;
- all four Foundation123 signer-security architecture documents;
- all four Foundation124 profiles/contracts and `docs/local_signer_implementation_gate_matrix_v0.1.md`;
- all four Foundation125 conformance plans and `docs/local_signer_operator_decision_register_v0.1.md`;
- all four Foundation126 decision-proposal documents and `docs/local_signer_operator_resolution_packet_v0.1.md`;
- all seven Phase 1 records under `docs/operator_decisions/`;
- all three Phase 2 review-preparation documents;
- Phase 3.1 `docs/security/l28_high_assurance_security_target_v0.1.md`;
- all three Phase 3.2 finding/remediation/closure framework documents;
- the 100 F120 local-signer-interface fixtures and four Foundation121 test-local files;
- relevant boundaries in `coin/tx_validation.py`, `coin/uaii_reference_core.py`, `coin/uaii_signed_receipt.py`, `coin/isolated_agent_purchase_demo.py`, `coin/m2m_replay_registry.py`, and `coin/m2m_registry_backup.py`; and
- directly relevant Foundation121 deterministic offline tests, observed `45 passed` during this review.

The pytest run emitted one cache warning because the sandbox could not write `.pytest_cache`; all 45 selected tests passed, and the working tree remained free of test-created changes.

## 3. Disposition rules applied

- `PASS` was available only if current repository evidence met every published closure requirement, including approved decisions, production-relevant evidence, complete testing, and qualified independent signoff. No item met that standard.
- `GAP` was assigned where reviewable design/candidate material exists but an approved production choice, implementation-grade evidence, required test/recovery evidence, or qualified independent signoff is absent.
- `REQUIRED_CHANGE` was reserved for a demonstrated nonconforming selected policy or implementation. None exists in scope, so no defect was invented.
- `BLOCKED` was reserved for a condition that prevents substantive review from proceeding. The 29 items have documented requirements and candidates that can proceed to qualified review, so their present missing evidence was classified `GAP`. The out-of-scope GAT decisions remain blocked separately.

Design/specification alone was not treated as implementation evidence. Offline fixture fields and hashes were not treated as authentication, custody, atomicity, durable audit, or production-runtime evidence. Existing isolated receipt signing, disposable demo, and older M2M replay/backup code were not treated as the future local-signer security implementation by inference.

## 4. Exact 29-ID disposition inventory

| Finding ID | LSOD decision ID | Domain | Disposition | Closure state |
|---|---|---|---|---|
| `L28-SRF-R0001-0001` | `LSOD-EVD-001` | Authenticated evidence | `GAP` | `OPEN` |
| `L28-SRF-R0001-0002` | `LSOD-EVD-002` | Authenticated evidence | `GAP` | `OPEN` |
| `L28-SRF-R0001-0003` | `LSOD-EVD-003` | Authenticated evidence | `GAP` | `OPEN` |
| `L28-SRF-R0001-0004` | `LSOD-EVD-005` | Authenticated evidence | `GAP` | `OPEN` |
| `L28-SRF-R0001-0005` | `LSOD-EVD-006` | Authenticated evidence | `GAP` | `OPEN` |
| `L28-SRF-R0001-0006` | `LSOD-EVD-007` | Authenticated evidence | `GAP` | `OPEN` |
| `L28-SRF-R0001-0007` | `LSOD-EVD-008` | Authenticated evidence | `GAP` | `OPEN` |
| `L28-SRF-R0001-0008` | `LSOD-EVD-009` | Authenticated evidence | `GAP` | `OPEN` |
| `L28-SRF-R0001-0009` | `LSOD-CUS-001` | Custody | `GAP` | `OPEN` |
| `L28-SRF-R0001-0010` | `LSOD-CUS-003` | Custody | `GAP` | `OPEN` |
| `L28-SRF-R0001-0011` | `LSOD-CUS-004` | Custody | `GAP` | `OPEN` |
| `L28-SRF-R0001-0012` | `LSOD-CUS-005` | Custody | `GAP` | `OPEN` |
| `L28-SRF-R0001-0013` | `LSOD-CUS-006` | Custody | `GAP` | `OPEN` |
| `L28-SRF-R0001-0014` | `LSOD-CUS-007` | Custody | `GAP` | `OPEN` |
| `L28-SRF-R0001-0015` | `LSOD-CUS-010` | Custody | `GAP` | `OPEN` |
| `L28-SRF-R0001-0016` | `LSOD-CUS-011` | Custody | `GAP` | `OPEN` |
| `L28-SRF-R0001-0017` | `LSOD-STA-001` | Atomic state | `GAP` | `OPEN` |
| `L28-SRF-R0001-0018` | `LSOD-STA-002` | Atomic state | `GAP` | `OPEN` |
| `L28-SRF-R0001-0019` | `LSOD-STA-003` | Atomic state | `GAP` | `OPEN` |
| `L28-SRF-R0001-0020` | `LSOD-STA-004` | Atomic state | `GAP` | `OPEN` |
| `L28-SRF-R0001-0021` | `LSOD-STA-006` | Atomic state | `GAP` | `OPEN` |
| `L28-SRF-R0001-0022` | `LSOD-STA-008` | Atomic state | `GAP` | `OPEN` |
| `L28-SRF-R0001-0023` | `LSOD-STA-009` | Atomic state | `GAP` | `OPEN` |
| `L28-SRF-R0001-0024` | `LSOD-STA-010` | Atomic state | `GAP` | `OPEN` |
| `L28-SRF-R0001-0025` | `LSOD-OPS-001` | Operations/runtime | `GAP` | `OPEN` |
| `L28-SRF-R0001-0026` | `LSOD-OPS-002` | Operations/runtime | `GAP` | `OPEN` |
| `L28-SRF-R0001-0027` | `LSOD-OPS-005` | Operations/runtime | `GAP` | `OPEN` |
| `L28-SRF-R0001-0028` | `LSOD-OPS-006` | Operations/runtime | `GAP` | `OPEN` |
| `L28-SRF-R0001-0029` | `LSOD-OPS-007` | Operations/runtime | `GAP` | `OPEN` |

Each LSOD ID appears exactly once in this disposition inventory and exactly once as the primary ID of its domain finding.

## 5. Counts

| Disposition | Count |
|---|---:|
| `PASS` | `0` |
| `GAP` | `29` |
| `REQUIRED_CHANGE` | `0` |
| `BLOCKED` | `0` |
| **Total** | **`29`** |

All 29 findings have `HUMAN_SIGNOFF_UNASSIGNED` and remain open.

## 6. Highest-risk findings

No numeric risk score or production ranking is invented. The following findings have the broadest potential impact because failure could create false authority, expose future signing material, duplicate authorization, corrupt recovery, or create prohibited capabilities:

| Finding / LSOD | Material risk |
|---|---|
| `L28-SRF-R0001-0001` / `LSOD-EVD-001` | Unapproved proof/canonicalization could make forged evidence appear authentic |
| `L28-SRF-R0001-0002` / `LSOD-EVD-002` | Undefined trust-root/issuer governance could manufacture or preserve rogue authority |
| `L28-SRF-R0001-0006` / `LSOD-EVD-007` | Undefined roles/thresholds and absent atomic consumption could enable collusion or double authorization |
| `L28-SRF-R0001-0007` / `LSOD-EVD-008` | Absent replay enforcement could permit cross-request or repeated authority use |
| `L28-SRF-R0001-0010` / `LSOD-CUS-003` | Missing isolation/non-exportability could expose future signer authority |
| `L28-SRF-R0001-0011` / `LSOD-CUS-004` | Undefined role separation could permit unilateral or collusive custody control |
| `L28-SRF-R0001-0013` and `0014` / `LSOD-CUS-006` and `007` | Non-atomic lifecycle/revocation could preserve stale or compromised material authority |
| `L28-SRF-R0001-0018` and `0019` / `LSOD-STA-002` and `003` | Missing isolation/durability/fencing could create lost, duplicate, or split authoritative outcomes |
| `L28-SRF-R0001-0022` / `LSOD-STA-008` | Missing atomic approval/operator consumption could permit repeated authority |
| `L28-SRF-R0001-0023` / `LSOD-STA-009` | Unsafe recovery could reopen replay/spend/approval state or roll authority backward |
| `L28-SRF-R0001-0025` / `LSOD-OPS-001` | Untrusted time could accept expired or revoked authority |
| `L28-SRF-R0001-0026` / `LSOD-OPS-002` | Non-durable or mutable audit could erase accountability or falsely attest outcomes |
| `L28-SRF-R0001-0029` / `LSOD-OPS-007` | Missing runtime isolation could expose secrets or create signer/network/settlement capability paths |

## 7. Dependencies preventing approval

Approval is prevented by:

1. no selected and approved production candidate for any of the 29 decisions;
2. no named accountable approver for the applicable decision records;
3. no qualified human independent-review identity, qualifications, conflict disclosure, findings signoff, or remediation signoff;
4. no production authenticated issuer/verifier/revocation evidence;
5. no approved custody technology, roles, lifecycle, incident, or evidence system;
6. no integrated authoritative atomic state for replay, spending, approval/operator consumption, policy transitions, and audit intent;
7. no approved trusted-time or durable tamper-evident audit mechanism;
8. no approved runtime error, monitoring, identity, capability, isolation, or penetration evidence;
9. no implementation-specific adversarial, concurrency, fault, crash/recovery, abuse, privacy, service, or end-to-end evidence;
10. Phase 1 records remain `REQUIRES_SECURITY_EXPERT_REVIEW` with no selected values;
11. the following remain outside this review and `IMPLEMENTATION_EVIDENCE_REQUIRED_FIRST`: `LSOD-EVD-004`, `LSOD-CUS-009`, `LSOD-STA-005`, `LSOD-STA-011`, `LSOD-OPS-003`, `LSOD-OPS-004`, and `LSOD-OPS-008`; and
12. `LSOD-GAT-001`, `LSOD-GAT-002`, `LSOD-GAT-003`, and `LSOD-GAT-004` remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

## 8. Maturity and eligibility conclusions

### `DECISIONS_APPROVED`

**Not eligible.** All 29 reviewed decision items have open `GAP` findings, all human signoffs are unassigned, Phase 1 records remain unresolved, and evidence-first/GAT dependencies remain outstanding. Round 1 cannot update a decision record or advance this gate.

### Implementation authorization

**Not eligible.** The Foundation124 implementation gate matrix requires approved decisions, implementation evidence, tests, independent review, and separate authorization. Those conditions are not met. `LSOD-GAT-004` independently preserves signer implementation/runtime/deployment/activation as blocked.

Neither conclusion is a permanent prohibition; each is the evidence-grounded state at the reviewed parent. Any later consideration must follow the Phase 3.2 remediation and closure workflow and preserve exact artifact/version lineage.

## 9. Protocol, economics, and authority preservation

L28 Protocol v1.0.0 remains authoritative. `coin.tx_validation.validate_transaction` remains canonical and mandatory and must bind to the exact transaction. Authorization is not validation. Eligibility is not signer invocation.

Protected facts remain exactly:

- hard cap `28000000`;
- emission ceiling `11130000`;
- historically mined `2824584`;
- treasury locked `500000`;
- circulating snapshot `2324584`;
- halving interval `210000`;
- reward schedule `[28,14,7,3,1,0]`;
- historical mined-through entry `100877`;
- next canonical height `100878`;
- coinbase-only issuance;
- consensus-derived canonical height; and
- immutable historical evidence.

Bitcoin remains external evidence only and has zero authority over L28 issuance, supply, canonical height, validation, consensus, history, or settlement. Production Bitcoin proof architecture, Bitcoin confirmation/reorganization policy and count, and observer quorum/independence remain blocked and unselected. Observation is not settlement.

## 10. Non-activation and signoff conclusion

This review creates findings only. It approves no operator decision and grants no signer, wallet, key, signature, HSM/KMS, RPC, network, submission, broadcast, mining, bridge, ledger/state mutation, settlement, database, migration, server, deployment, testnet, production process, or activation authority.

Round 1 reviewer conclusion: `NOT_READY_FOR_OPERATOR_CONSIDERATION` for every reviewed LSOD ID.

Independent human signoff status: `UNASSIGNED`. This summary must not be represented as qualified human security certification or closure evidence.
