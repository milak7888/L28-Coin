# Phase 4 Round 1 — Atomic-State Security Findings v0.1

Status: `INDEPENDENT_REPOSITORY_REVIEW_ROUND_1`

Review series: `R0001`

Scope: exactly eight Foundation126 atomic-state decisions classified `SECURITY_EXPERT_DECISION_REQUIRED`.

Reviewer capacity: Codex performed an evidence-bound repository review independently from implementation activity in this phase. This is not qualified human distributed-systems or cryptographic signoff.

## Common evidence boundary

Evidence reviewed across all eight findings:

- `PROTOCOL.md` and `docs/local_signer_interface_security_review_v0.1.md`;
- `docs/local_signer_atomic_state_semantics_v0.1.md`;
- `docs/local_signer_atomic_state_storage_contract_v0.1.md`;
- `docs/local_signer_implementation_gate_matrix_v0.1.md`;
- the atomic-state rows in `docs/local_signer_operator_decision_register_v0.1.md`;
- `docs/local_signer_atomic_state_conformance_plan_v0.1.md`;
- `docs/local_signer_atomic_state_decision_proposals_v0.1.md` and the Foundation126 resolution packet;
- Phase 1–3.2 operator-review and assurance artifacts;
- F120 local-signer-interface fixtures and Foundation121 tests; and
- relevant pre-existing boundaries in `coin/m2m_replay_registry.py`, `coin/m2m_registry_backup.py`, and `coin/uaii_reference_core.py`.

The older M2M SQLite replay/backup components and UAII read-only replay lookup are separate bounded facilities. Repository evidence does not bind them to the future local-signer request, cumulative spending, approval/operator consumption, policy transition, or audit-intent atomic unit defined by F123/F124. They cannot be treated as the future signer state implementation by inference.

## L28-SRF-R0001-0017

- **LSOD decision ID:** `LSOD-STA-001`
- **Disposition:** `GAP`
- **Threat/risk:** Split authority, untrusted or silently empty state, wrong administrative domain, stale replicas, unauthorized fallback stores, or ambiguous failure could permit duplicate authority.
- **Repository evidence actually reviewed:** F123/F124 define one authoritative state boundary, explicit initialization, domain partitioning, health/integrity, and fail-closed unavailable state. F126 compares embedded, isolated-service, and append-only/event candidates without choosing a product or boundary. F120 explicitly reports atomic transition not implemented.
- **Evidence missing:** Approved storage/trust boundary and administrative domain; fault model; initialization/bootstrap authority; health/integrity evidence; forbidden fallback analysis; implementation provenance; outage/partition tests; and independent distributed-state review.
- **Required remediation:** Select an exact authoritative-boundary candidate and define ownership, partition keys, fault assumptions, initialization, health, isolation, unavailable-state behavior, and prohibited authority. Any prototype or implementation requires separate authorization.
- **Residual risk:** Multiple or default-empty stores could create contradictory replay/spend/approval outcomes.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; the authoritative state boundary is not selected or evidenced.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; distributed-state architecture signoff is absent.

## L28-SRF-R0001-0018

- **LSOD decision ID:** `LSOD-STA-002`
- **Disposition:** `GAP`
- **Threat/risk:** TOCTOU, lost updates, double consumption, stale snapshots, nondeterministic ordering, deadlock, or weak isolation could violate replay and economic controls.
- **Repository evidence actually reviewed:** F123/F124 specify serializable-equivalent invariants, conditional atomic snapshots/commits, monotonic versions, partition/order rules, and deterministic conflict rejection. F126 lists transactional, compare-and-swap, and event/command candidates without selection. F121 performs no state mutation or concurrency test.
- **Evidence missing:** Approved consistency/isolation/order model; formal invariants; linearization points; partition keys; liveness/failure limits; implementation; controlled race schedules; deadlock/partition/crash evidence; and independent concurrency review.
- **Required remediation:** Define the exact consistency and ordering candidate, state its formal safety/liveness invariants, and provide separately authorized deterministic concurrency/fault evidence with independent verification.
- **Residual risk:** Concurrent requests could each observe eligibility and consume the same authority or spending capacity.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; abstract atomicity has no implementation-grade proof.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; formal/concurrency reviewer signoff is absent.

## L28-SRF-R0001-0019

- **LSOD decision ID:** `LSOD-STA-003`
- **Disposition:** `GAP`
- **Threat/risk:** Lost or ambiguous commits, stale success, replica lag, split brain, unsafe quorum downgrade, or recovery divergence could create multiple authoritative outcomes.
- **Repository evidence actually reviewed:** F123/F124 require all-or-none durable acknowledgement, replica/version integrity, split-brain fencing, and fail-closed availability. F126 compares single durable store, replicated transactional state, and log-derived state without selecting durability or quorum. The offline M2M SQLite registry is not integrated with the local-signer atomic unit.
- **Evidence missing:** Approved durability/replication model; failure domains; acknowledgement and recovery-point semantics; fencing; replica health; implementation and crash-point evidence; no-downgrade tests; and independent resilience review.
- **Required remediation:** Select a durability/fault candidate with exact acknowledgement, fencing, replica health, uncertainty, and recovery rules; produce fault/crash/partition evidence before operator consideration.
- **Residual risk:** A reported success may be lost or duplicated after failure, reopening consumed authority.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; no durable unique-outcome evidence exists for the future signer boundary.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; resilience/distributed-systems signoff is absent.

## L28-SRF-R0001-0020

- **LSOD decision ID:** `LSOD-STA-004`
- **Disposition:** `GAP`
- **Threat/risk:** Identifier collision, record reassociation, lineage forgery, digest downgrade, malformed versions, or canonicalization drift could corrupt authority state.
- **Repository evidence actually reviewed:** F123/F124 define canonical record/version/commit identifiers, domain separation, uniqueness, monotonic lineage, integrity verification, and collision failure. F126 compares digest-derived, monotonic-sequence, and combined identifiers without selecting an integrity mechanism. F120/F121 verify fixture digests only.
- **Evidence missing:** Approved identifier and integrity profile; canonical record encoding; authentication/digest lifecycle; collision/reassociation analysis; independent verification implementation; migration lineage; adversarial vectors; and cryptographic/state-integrity review.
- **Required remediation:** Define exact domains, encodings, identifiers, integrity mechanism, collision behavior, version lineage, migration rules, and canonical vectors for qualified independent review.
- **Residual risk:** Deterministic fixture hashes can be mistaken for authenticated durable state integrity.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; current digests do not establish production state authenticity or lineage.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; cryptographic/state-integrity signoff is absent.

## L28-SRF-R0001-0021

- **LSOD decision ID:** `LSOD-STA-006`
- **Disposition:** `GAP`
- **Threat/risk:** Replay after deletion, premature reuse, erased audit/dispute lineage, stale restore, or excessive privacy retention could undermine authority and accountability.
- **Repository evidence actually reviewed:** F123/F124 require per-record retention, tombstones, monotonic proof, compaction/deletion audit, recovery, and privacy. F126 compares horizon-based, permanent-tombstone, and event-history candidates without selecting duration. F120 uses fixed fictional retention values but mutates no state.
- **Evidence missing:** Approved retention model and justified horizons; privacy/legal analysis; tombstone/compaction semantics; backup/restore interaction; integrity-preserving expiry; implementation; boundary/replay/recovery tests; and independent review.
- **Required remediation:** Define per-record retention and tombstone candidates tied to threat/evidence/dispute lifetimes, specify privacy and recovery behavior, and obtain measured/legal evidence where required before selecting durations.
- **Residual risk:** Deleted or restored state may permit reuse, while over-retention may create unnecessary privacy exposure.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; no production retention policy or enforcement evidence exists.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; retention/privacy/replay signoff is absent.

## L28-SRF-R0001-0022

- **LSOD decision ID:** `LSOD-STA-008`
- **Disposition:** `GAP`
- **Threat/risk:** Approval transfer, duplicate identity, threshold races, concurrent reuse, wrong operator/scope, or restoration of consumed records could produce double authorization.
- **Repository evidence actually reviewed:** F123/F124 define exact identity/scope/threshold/reuse binding and atomic irreversible approval/operator consumption. F126 compares single-use, bounded reuse, and operator-session candidates without selection. F120/F121 model approval outcomes without consuming state.
- **Evidence missing:** Approved reuse/consumption profile; authenticated identity/operator linkage; threshold semantics; atomic integration with replay/spend/audit; expiry/revocation; concurrency implementation; race/recovery tests; and independent authorization/state review.
- **Required remediation:** Select exact approval/operator consumption semantics and prove atomic unique consumption across duplicates, races, expiry, revocation, crash, and recovery under separate authorization.
- **Residual risk:** The same approval or operator grant could authorize multiple requests in a future runtime.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; fictional threshold checks are not atomic consumption evidence.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; authorization/atomic-consumption signoff is absent.

## L28-SRF-R0001-0023

- **LSOD decision ID:** `LSOD-STA-009`
- **Disposition:** `GAP`
- **Threat/risk:** Stale/corrupt restore, lost commits, forked lineage, unauthorized recovery, partial restoration, counter rollback, or replay reopening could invalidate security state.
- **Repository evidence actually reviewed:** F123/F124 require authenticated backup provenance, exact latest-version proof, recovery roles/ceremony, reconciliation, blocked ambiguity, and no rollback. F126 compares snapshots/log replay, replicated checkpoints, and rebuild-only candidates without selection. `coin/m2m_registry_backup.py` implements a separate offline registry backup/recovery boundary, not the future combined signer state.
- **Evidence missing:** Approved recovery architecture and authority; complete-state backup provenance; recovery point semantics; reconciliation across replay/spend/approval/operator/audit intent; implementation; fork/loss/crash tests; and independent disaster-recovery review.
- **Required remediation:** Define and independently review the future signer-state recovery model, authoritative-version proof, roles, ceremony, reconciliation, fail-closed uncertainty, and no-rollback evidence. Do not reuse the older registry backup by assumption.
- **Residual risk:** Recovery could reopen consumed authority or conceal lost state while reporting success.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; no integrated signer-state recovery evidence exists.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; disaster-recovery/state-integrity signoff is absent.

## L28-SRF-R0001-0024

- **LSOD decision ID:** `LSOD-STA-010`
- **Disposition:** `GAP`
- **Threat/risk:** Unauthorized state read/write, tampering, privacy leakage, privilege escalation, telemetry exposure, or reuse of signer material for storage protection could compromise controls.
- **Repository evidence actually reviewed:** F123/F124 require data classification, least privilege, confidentiality/integrity separation, non-signer key/material lifecycle, access audit, monitoring, and recovery. F126 compares application, storage-layer, and layered protection without selecting technology. F121 contains no production store or material.
- **Evidence missing:** Approved storage-security profile; access roles; protection/integrity mechanisms; separate non-signer material lifecycle; data/telemetry classification; monitoring/audit/recovery; implementation/penetration evidence; and independent storage review.
- **Required remediation:** Define the storage trust and access candidate, prove signer-material separation, specify confidentiality/integrity/lifecycle/telemetry/recovery controls, and submit adversarial access/tamper evidence for independent review.
- **Residual risk:** Compromised storage could alter authorization state or expose sensitive evidence without detection.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; no production storage-security enforcement evidence exists.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; storage/key-management signoff is absent.

## Domain conclusion

Atomic-state dispositions: `PASS 0`, `GAP 8`, `REQUIRED_CHANGE 0`, `BLOCKED 0`.

No database, state store, migration, replay/spend/approval mutation, recovery operation, or runtime was created or invoked. No finding is closed and no atomic-state decision is approved.

L28 Protocol v1.0.0 and canonical `coin.tx_validation.validate_transaction` remain authoritative. Authorization is not validation. Eligibility is not signer invocation. Bitcoin remains external evidence only.

Protected facts remain exactly: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.

Production Bitcoin proof architecture, Bitcoin confirmation/reorganization policy and count, observer quorum/independence, and signer implementation/runtime/deployment/activation remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`. This artifact authorizes no implementation or runtime behavior.
