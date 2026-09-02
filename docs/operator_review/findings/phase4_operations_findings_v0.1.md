# Phase 4 Round 1 — Operations and Runtime-Security Findings v0.1

Status: `INDEPENDENT_REPOSITORY_REVIEW_ROUND_1`

Review series: `R0001`

Scope: exactly five Foundation126 operations/runtime decisions classified `SECURITY_EXPERT_DECISION_REQUIRED`.

Reviewer capacity: Codex performed an evidence-bound repository review independently from implementation activity in this phase. This is not qualified human time, audit, application, privacy, platform, or penetration-test signoff.

## Common evidence boundary

Evidence reviewed across all five findings:

- `PROTOCOL.md` and `docs/local_signer_interface_security_review_v0.1.md`;
- `docs/local_signer_time_audit_runtime_hardening_architecture_v0.1.md`;
- `docs/local_signer_time_audit_resource_policy_v0.1.md`;
- `docs/local_signer_implementation_gate_matrix_v0.1.md`;
- the operations rows in `docs/local_signer_operator_decision_register_v0.1.md`;
- `docs/local_signer_time_audit_resource_conformance_plan_v0.1.md`;
- `docs/local_signer_ops_decision_proposals_v0.1.md` and the Foundation126 resolution packet;
- Phase 1–3.2 operator-review and assurance artifacts; and
- F120 local-signer-interface fixtures plus Foundation121 profile/schema/security tests, observed `45 passed` in Round 1.

Foundation121 intentionally avoids system time, environment, network, production validation, signer, state mutation, and runtime behavior. That is useful non-execution evidence, not proof of production time, audit, errors, monitoring, isolation, or service hardening.

## L28-SRF-R0001-0025

- **LSOD decision ID:** `LSOD-OPS-001`
- **Disposition:** `GAP`
- **Threat/risk:** Forged/manipulated time, rollback or forward jumps, correlated source failure, excess uncertainty, stale cache, or indefinite outage fallback could accept expired/revoked evidence or corrupt policy/lifecycle windows.
- **Repository evidence actually reviewed:** F123/F124 define authenticated sources, selection, monotonic reference, uncertainty/skew/jump/rollback/outage/cache semantics, and fail-closed time state. F126 compares single-source, multiple-source, and primary-plus-cache candidates without selecting sources, quorum, or numbers. F120 uses fixed caller-supplied integer time; F121 proves no system clock read.
- **Evidence missing:** Approved source/selection/independence model; authentication; monotonic durable state; measured skew/uncertainty/outage/cache bounds; rollback/recovery behavior; implementation/fault evidence; and independent time-security review.
- **Required remediation:** Define one trusted-time candidate and threat model, authorize measurements separately for numeric values, demonstrate authenticated time binding and rollback/outage failure behavior, and obtain qualified independent review.
- **Residual risk:** Caller-controlled or untrusted time could make stale authority appear valid.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; fixed offline timestamps provide no production time assurance.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; qualified trusted-time/rollback signoff is absent.

## L28-SRF-R0001-0026

- **LSOD decision ID:** `LSOD-OPS-002`
- **Disposition:** `GAP`
- **Threat/risk:** Audit evidence may be forged, deleted, inserted, reordered, truncated, rolled back, leaked, inaccessible, or unrecoverable, destroying accountability or exposing sensitive data.
- **Repository evidence actually reviewed:** F123/F124 require authenticated append-only lineage, checkpoints, durable acknowledgement, access/redaction/publication, retention, and recovery. F126 compares append-only log, transactionally coupled audit, and externally anchored integrity candidates without selection. F120/F121 verify deterministic audit/report digests only.
- **Evidence missing:** Approved authenticity/integrity mechanism; durable storage/commit semantics; checkpoint and verification model; access/privacy/redaction; retention/recovery; implementation and tamper/failure evidence; and independent audit/privacy/resilience review.
- **Required remediation:** Select an exact audit candidate and specify atomic commit relationship, authenticity, ordering, checkpoints, durability, access, public projection, retention, redaction, loss/recovery, and independent verification. Any store implementation requires separate authorization.
- **Residual risk:** A deterministic digest can identify fixture content but cannot prove durable, authentic, non-repudiable operational history.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; no production tamper-evident audit system exists.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; audit/privacy/resilience signoff is absent.

## L28-SRF-R0001-0027

- **LSOD decision ID:** `LSOD-OPS-005`
- **Disposition:** `GAP`
- **Threat/risk:** Error details, correlations, timing, precedence, or retry guidance could leak secrets/topology, enable enumeration, create timing oracles, or cause unsafe retries.
- **Repository evidence actually reviewed:** F117/F118 define stable fail-closed statuses/codes and precedence; F120/F121 verify deterministic expected codes offline. F123/F124 require public-safe errors and protected internal diagnostics. F126 compares minimal, split public/internal, and constant-shape candidates without selecting a mapping or timing policy.
- **Evidence missing:** Approved mapping to existing F117 statuses/codes; disclosure and privacy threat model; internal diagnostic access/audit; timing/correlation/retry policy; implementation behavior; multi-failure/leakage tests; and independent application-security review.
- **Required remediation:** Define a versioned allowlisted error policy preserving F117 compatibility and precedence, with public/internal separation, correlation/retry constraints, timing analysis, unknown-error failure behavior, adversarial tests, and independent review.
- **Residual risk:** An unreviewed runtime could expose protected state or vary failure behavior even while fixtures remain deterministic.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; offline expected codes do not prove secure runtime error handling.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; application-security/privacy signoff is absent.

## L28-SRF-R0001-0028

- **LSOD decision ID:** `LSOD-OPS-006`
- **Disposition:** `GAP`
- **Threat/risk:** Undetected attacks/failures, false health, alert loss/lag, unauthorized telemetry access, privacy leakage, or monitoring authority creep could prevent safe response or reveal sensitive state.
- **Repository evidence actually reviewed:** F123/F124 define public-safe monitoring allowlists, authenticated health, incident alerts, access/retention, outage handling, and non-authority. F126 compares minimal, layered, and attestational monitoring candidates without selecting platform, fields, thresholds, or retention. No production monitor or incident evidence is present.
- **Evidence missing:** Approved telemetry/health/incident profile; data classification; authenticated health; detection coverage; access and retention; measured thresholds; alert-loss/false-signal evidence; runbook exercises; and independent observability/privacy review.
- **Required remediation:** Define a versioned monitoring candidate with minimum necessary signals, authenticated health, access/retention/privacy, outage/escalation, non-authority, measurement plan, incident exercises, and independent review.
- **Residual risk:** Failures or attacks may remain invisible, while excessive telemetry may leak evidence, topology, or identities.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; monitoring requirements are design-only and unmeasured.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; observability/privacy/incident signoff is absent.

## L28-SRF-R0001-0029

- **LSOD decision ID:** `LSOD-OPS-007`
- **Disposition:** `GAP`
- **Threat/risk:** Privilege escape, component impersonation, arbitrary filesystem/network access, secret exposure, shared-host compromise, boundary bypass, or degraded isolation could expose authority and enable forbidden actions.
- **Repository evidence actually reviewed:** F123/F124 require least-privilege trust zones, component identities, capability allowlists, process/filesystem/network/secret isolation, attestation/health, and fail-closed degradation. F126 compares process, service/host, and capability-sandbox candidates without selecting platform/topology. F121 AST checks prove only that the four fixture-test files avoid forbidden imports/calls.
- **Evidence missing:** Approved trust-zone/topology and capability profile; authenticated component identities; platform/host threat model; enforced process/filesystem/network/secret boundaries; attestation/health; update/failure behavior; implementation/penetration evidence; and independent platform review.
- **Required remediation:** Define exact component identities, trust zones, least privileges, prohibited capabilities, isolation/attestation, update, failure, quarantine, and recovery rules, then provide separately authorized penetration/fault evidence.
- **Residual risk:** A future runtime without enforced isolation could turn a validation or eligibility component into a signing, network, or settlement authority path.
- **Reviewer conclusion:** `NOT_READY_FOR_OPERATOR_CONSIDERATION`; test-source isolation is not production service isolation.
- **Independence/signoff status:** `HUMAN_SIGNOFF_UNASSIGNED`; platform/isolation penetration signoff is absent.

## Domain conclusion

Operations/runtime dispositions: `PASS 0`, `GAP 5`, `REQUIRED_CHANGE 0`, `BLOCKED 0`.

No time source, audit store, monitor, server, network, RPC, runtime, deployment, or testnet was accessed or started. No finding is closed and no operations decision is approved.

L28 Protocol v1.0.0 and canonical `coin.tx_validation.validate_transaction` remain authoritative. Authorization is not validation. Eligibility is not signer invocation. Bitcoin remains external evidence only.

Protected facts remain exactly: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.

Production Bitcoin proof architecture, Bitcoin confirmation/reorganization policy and count, observer quorum/independence, and signer implementation/runtime/deployment/activation remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`. This artifact authorizes no implementation or runtime behavior.
