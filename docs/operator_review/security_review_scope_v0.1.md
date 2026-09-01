# Local Signer Security Review Scope v0.1

Status: `SECURITY_REVIEW_PREPARATION_ONLY`

Decision effect: none. This document selects no production value, approves no decision, and grants no implementation, deployment, signer-invocation, or activation authority.

## 1. Purpose and source boundary

This document defines the independent-review scope for the 29 Foundation126 decisions classified `SECURITY_EXPERT_DECISION_REQUIRED`. The authoritative sources are:

- `docs/local_signer_implementation_gate_matrix_v0.1.md` (Foundation124);
- `docs/local_signer_operator_decision_register_v0.1.md` (Foundation125);
- `docs/local_signer_operator_resolution_packet_v0.1.md` (Foundation126); and
- the seven Phase 1 records under `docs/operator_decisions/`, which remain unresolved and provide dependency context only.

Every listed decision remains `CANDIDATE_NOT_APPROVED` and `OPERATOR_DECISION_REQUIRED`. Independent review produces advice and evidence for a later accountable operator decision; it is not itself approval.

## 2. Exact review inventory

### 2.1 Authenticated evidence — 8

1. `LSOD-EVD-001` — proof format, algorithms, parameters, canonical proof input, and deprecation.
2. `LSOD-EVD-002` — issuer registry, trust roots, enrollment, delegation, revocation authority, and compromise governance.
3. `LSOD-EVD-003` — verifier identity, authentication, authorization, isolation, and verification-material lifecycle.
4. `LSOD-EVD-005` — revocation-source authenticity, freshness, caching, conflicts, outage, and recovery.
5. `LSOD-EVD-006` — policy activation, exact-version binding, supersession, transition, and rollback prohibition.
6. `LSOD-EVD-007` — approval roles, independence, threshold governance, scope, and consumption.
7. `LSOD-EVD-008` — replay domain, nonce provenance, request binding, single-use policy, and retention.
8. `LSOD-EVD-009` — public audit projection, authenticity, privacy, disclosure, retention, and recovery.

### 2.2 Custody — 8

1. `LSOD-CUS-001` — algorithm/material allowlist, parameters, derivations, identifiers, use, and deprecation.
2. `LSOD-CUS-003` — isolation class, process/storage/export boundaries, attestation, health, and failure behavior.
3. `LSOD-CUS-004` — roles, authentication, scopes, forbidden combinations, thresholds, and separation of duties.
4. `LSOD-CUS-005` — lifecycle ceremonies, observers, ordering, evidence, abort/recovery, and review.
5. `LSOD-CUS-006` — activation, expiry, rotation, overlap, in-flight treatment, and predecessor disablement.
6. `LSOD-CUS-007` — revocation authority, triggers, publication, freshness, incident deadlines, and recovery.
7. `LSOD-CUS-010` — compromise detection, containment, forensics/privacy, notification, successor, and return criteria.
8. `LSOD-CUS-011` — custody-evidence proof, verification cadence, durability, lifecycle lineage, and privacy.

### 2.3 Atomic state — 8

1. `LSOD-STA-001` — authoritative storage boundary, administrative domain, partition, trust, and failure model.
2. `LSOD-STA-002` — consistency, isolation, concurrency, authoritative ordering, conflicts, and partition keys.
3. `LSOD-STA-003` — durability, replication, split-brain prevention, acknowledgement, and fail-closed availability.
4. `LSOD-STA-004` — canonical identifiers, integrity domains, lineage, collision handling, and versioning.
5. `LSOD-STA-006` — replay/idempotency/evidence-consumption retention, tombstones, audit, disputes, and privacy.
6. `LSOD-STA-008` — approval/operator scope, uniqueness, reuse, threshold, and atomic consumption.
7. `LSOD-STA-009` — backup/restore, recovery authority, reconciliation, rollback prohibition, and ceremony.
8. `LSOD-STA-010` — storage confidentiality/integrity, access, telemetry, audit, and non-signer key separation.

### 2.4 Operations and runtime security — 5

1. `LSOD-OPS-001` — trusted-time sources, authentication, selection, monotonicity, rollback/jump, outage, and cache semantics.
2. `LSOD-OPS-002` — audit authenticity, integrity chain, checkpoints, durability, retention, recovery, access, and redaction.
3. `LSOD-OPS-005` — secure-error disclosure, correlation, timing, deterministic precedence, and retry guidance.
4. `LSOD-OPS-006` — monitoring allowlist, authenticated health, alerts, incidents, access, privacy, retention, and outages.
5. `LSOD-OPS-007` — process/service trust zones, privileges, capabilities, filesystem/network/secret isolation, and attestation.

Inventory total: authenticated evidence `8` + custody `8` + atomic state `8` + operations/runtime `5` = `29`.

## 3. Review boundaries

The independent reviewers shall:

- review the decision question and allowed decision shape without selecting an undocumented default;
- state reviewer identity, qualifications, independence, conflicts, artifacts and versions reviewed, methods, assumptions, limitations, and residual risk;
- assess threat actors, trust boundaries, attack surfaces, failure modes, recovery, authority separation, auditability, and privacy for each ID;
- identify dependencies that must be approved, measured, implemented, or reviewed before a later operator decision can be defensible;
- evaluate whether proposed evidence and tests would be sufficient, reproducible, adversarial, and fail closed;
- classify findings by severity and require traceable remediation and independent verification;
- preserve exact separation between security-expert recommendation and accountable operator approval; and
- treat missing, partial, contradictory, stale, unauthenticated, unavailable, or superseded evidence as fail closed.

This is an architecture, policy-shape, and assurance review. It may analyze hypothetical designs and fictional/disposable offline evidence. It may not exercise real custody or runtime capabilities.

## 4. Explicitly not in scope

The review does not:

- approve any of the 29 decisions or any Phase 1 record;
- select a proof algorithm, provider, technology, trust root, identity, role, threshold, quorum, lifetime, retention duration, time source, numeric bound, topology, or production value;
- implement a signer, wallet, key, signature, HSM/KMS integration, database, migration, service, or production control;
- access keys, seeds, mnemonics, xprv, wallets, credentials, environment variables, `.env`, keychains, browser data, SSH material, or Bitcoin configuration;
- invoke signing, submit transactions, connect RPC/network services, broadcast, mine, bridge, settle, mutate ledger/state, deploy, start services, create a testnet, or activate runtime behavior;
- resolve the seven `IMPLEMENTATION_EVIDENCE_REQUIRED_FIRST` items: `LSOD-EVD-004`, `LSOD-CUS-009`, `LSOD-STA-005`, `LSOD-STA-011`, `LSOD-OPS-003`, `LSOD-OPS-004`, or `LSOD-OPS-008`;
- change the seven Phase 1 records: `LSOD-EVD-010`, `LSOD-CUS-002`, `LSOD-CUS-008`, `LSOD-CUS-012`, `LSOD-STA-007`, `LSOD-STA-012`, or `LSOD-OPS-009`; or
- decide `LSOD-GAT-001` production Bitcoin proof architecture, `LSOD-GAT-002` Bitcoin confirmation/reorg policy/count, `LSOD-GAT-003` observer quorum/independence, or `LSOD-GAT-004` signer implementation/runtime/deployment/activation.

All four GAT decisions remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

## 5. Authority and non-activation constraints

- L28 Protocol v1.0.0 remains authoritative.
- `coin.tx_validation.validate_transaction` remains the canonical mandatory validation boundary and must bind to the exact transaction.
- Authorization is not validation. Eligibility is not signer invocation.
- No evidence, reviewer, policy, custody mechanism, state component, clock, audit system, operator, adapter, Harness/Evals output, or Bitcoin observation can override L28 issuance, supply, canonical height, validation, consensus, history, or settlement.
- Bitcoin remains external evidence only and has zero L28 authority.
- Review completion, favorable findings, or passing offline tests do not authorize implementation, deployment, signing, wallet/key access, RPC/networking, broadcast, ledger mutation, settlement, testnet, or activation.

## 6. Protected protocol and economics

This scope preserves exactly:

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

## 7. Review output boundary

For each ID, the reviewer may issue findings, required remediation, residual risks, and a recommendation of `READY_FOR_OPERATOR_CONSIDERATION` or `NOT_READY_FOR_OPERATOR_CONSIDERATION`. Neither recommendation is approval. A later, separately authorized operator decision record must still satisfy Foundation125 and Foundation126 approval-record requirements. Until then, every item remains unresolved and all affected paths fail closed.
