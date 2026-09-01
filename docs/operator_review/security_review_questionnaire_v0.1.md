# Local Signer Independent Security Review Questionnaire v0.1

Status: `SECURITY_REVIEW_PREPARATION_ONLY`

This questionnaire supports independent review of the 29 Foundation126 `SECURITY_EXPERT_DECISION_REQUIRED` items. Answers are review evidence, not operator decisions. Reviewers must not select production values, approve runtime behavior, or resolve Bitcoin or activation gates.

## 1. Reviewer declaration

For each reviewed LSOD ID, provide:

1. reviewer identity, relevant qualifications, organizational relationship, funding relationship, and conflicts;
2. exact artifact names, versions, digests where applicable, and review dates;
3. methods used, evidence independently reproduced, assumptions accepted or rejected, and scope limitations;
4. findings by severity, required remediation, residual risks, and verification status; and
5. one disposition: `READY_FOR_OPERATOR_CONSIDERATION` or `NOT_READY_FOR_OPERATOR_CONSIDERATION`.

Neither disposition is approval. Missing answers, unsupported assumptions, unresolved dependencies, or contradictory evidence must produce `NOT_READY_FOR_OPERATOR_CONSIDERATION`.

## 2. Security assumptions

- `Q-ASS-01`: Which actors, components, stores, clocks, issuers, verifiers, operators, and reviewers are trusted, for what exact purpose, and by which authority?
- `Q-ASS-02`: Which parties may be malicious, compromised, colluding, unavailable, stale, or equivocating?
- `Q-ASS-03`: Which independence assumptions exist, and what evidence makes them credible rather than nominal?
- `Q-ASS-04`: Which assumptions depend on unapproved technology, provider, algorithm, threshold, duration, topology, or production value?
- `Q-ASS-05`: Does any assumption permit caller-controlled evidence, implicit defaults, trust-on-first-use, stale state, rollback, or fail-open behavior?
- `Q-ASS-06`: How are assumptions version-bound, authenticated, monitored, invalidated, and re-reviewed after change or compromise?
- `Q-ASS-07`: Which assumptions remain untestable until separately authorized implementation or measurement evidence exists?
- `Q-ASS-08`: Does the design remain safe when Harness/Evals, adapters, or Bitcoin evidence is absent or adversarial?

## 3. Attack surfaces

- `Q-ATK-01`: Enumerate every input, parser, identity, evidence, policy, approval, state, time, audit, custody, administrative, recovery, and monitoring boundary.
- `Q-ATK-02`: Where can evidence be forged, replayed, substituted, reassociated, downgraded, reordered, truncated, or made stale?
- `Q-ATK-03`: Where can identity, role, scope, delegation, threshold, or separation-of-duty checks be bypassed?
- `Q-ATK-04`: Where can concurrency, partial failure, caching, replication, retry, or recovery create multiple authoritative outcomes?
- `Q-ATK-05`: Where can sensitive or personal data leak through public evidence, errors, timing, telemetry, audit, backup, or recovery?
- `Q-ATK-06`: Which capability boundaries could permit wallet/key access, signing, RPC/networking, submission, broadcast, ledger mutation, or settlement?
- `Q-ATK-07`: Can external Bitcoin evidence or an advisory subsystem acquire authority over L28 protocol state by direct or indirect dependency?

## 4. Failure modes and fail-closed behavior

- `Q-FAL-01`: What happens when required evidence, identity, policy, approval, state, time, audit, health, or reviewer evidence is missing?
- `Q-FAL-02`: What happens when evidence is malformed, contradictory, expired, revoked, superseded, corrupt, unavailable, or from the wrong domain/version?
- `Q-FAL-03`: What happens during timeout, lost acknowledgement, deadlock, split brain, partial commit, process crash, dependency outage, or restart?
- `Q-FAL-04`: Is there exactly one deterministic outcome and error precedence for simultaneous failures?
- `Q-FAL-05`: Can retry, cache, fallback, degraded mode, emergency procedure, or operator action weaken a control or guess success?
- `Q-FAL-06`: How is ambiguous authority/state quarantined, and what evidence is required before it can leave quarantine?
- `Q-FAL-07`: Do all failures preserve mandatory `coin.tx_validation.validate_transaction` binding and the separation of authorization from validation?

## 5. Recovery behavior

- `Q-REC-01`: What authority may initiate, approve, execute, verify, and terminate recovery, and which role combinations are forbidden?
- `Q-REC-02`: How does recovery prove the last authoritative version, complete lineage, integrity, and absence of rollback or replay reopening?
- `Q-REC-03`: How are stale, corrupt, incomplete, forked, revoked, or unverifiable recovery artifacts handled?
- `Q-REC-04`: How are in-flight requests, approvals, evidence consumption, counters, revocations, and lifecycle transitions reconciled?
- `Q-REC-05`: What recovery tests cover every crash/commit point, unavailable dependency, operator error, and failed recovery attempt?
- `Q-REC-06`: What deactivation, quarantine, compromise, and post-incident review steps apply before any return to consideration?

## 6. Authority boundaries

- `Q-AUT-01`: Which component authorizes, which validates, which determines eligibility, and which—if separately authorized in the future—could invoke a signer?
- `Q-AUT-02`: How is `coin.tx_validation.validate_transaction` bound to the exact transaction as the canonical mandatory validator without being replaced or bypassed?
- `Q-AUT-03`: What proves authorization is not Protocol validation and eligibility is not signer invocation?
- `Q-AUT-04`: What proves no evidence, custody, state, time, audit, reviewer, operator, adapter, Harness/Evals output, or Bitcoin observation can override issuance, supply, canonical height, validation, consensus, history, or settlement?
- `Q-AUT-05`: Are administrative, emergency, recovery, or monitoring capabilities strictly scoped and unable to create implicit runtime authority?
- `Q-AUT-06`: Does a favorable review remain advisory to the accountable operator and incapable of approving implementation, deployment, or activation?

## 7. Auditability

- `Q-AUD-01`: Which decision inputs, versions, verification outcomes, state transitions, failures, approvals, reviewer findings, and recoveries must be durably recorded?
- `Q-AUD-02`: How are authenticity, append-only lineage, ordering, checkpoints, durable acknowledgement, access, and independent verification established?
- `Q-AUD-03`: Can deletion, insertion, mutation, reorder, truncation, rollback, redaction, or restoration be detected without exposing secrets?
- `Q-AUD-04`: How are evidence provenance, test reproducibility, finding remediation, and independent re-verification linked?
- `Q-AUD-05`: What remains visible in a public projection, what is withheld, why, and how is omission of required binding detected?
- `Q-AUD-06`: How does audit outage or uncertain durability prevent a success/eligibility outcome?

## 8. Privacy concerns

- `Q-PRV-01`: What personal, organizational, operational, custody, or linkable data exists at every boundary?
- `Q-PRV-02`: Is each collected, retained, disclosed, or correlated field necessary for a named security purpose?
- `Q-PRV-03`: Can identifiers, nonces, approvals, timing, errors, audit entries, telemetry, or recovery evidence enable cross-request or cross-domain correlation?
- `Q-PRV-04`: Do minimization, access, redaction, retention, deletion, dispute, and recovery requirements conflict, and how is the conflict resolved without rewriting history?
- `Q-PRV-05`: Can secrets or sensitive topology appear in public evidence, diagnostics, logs, test artifacts, backups, or reviewer reports?
- `Q-PRV-06`: How are privacy failures detected, contained, audited, remediated, and independently verified?

## 9. Implementation risks

- `Q-IMP-01`: Which security property relies on a future implementation detail not established by the reviewed architecture?
- `Q-IMP-02`: Which candidate controls require implementation or measurement evidence before numeric values or operational acceptance could be considered?
- `Q-IMP-03`: How could canonical serialization, verification, state ordering, time, or error precedence diverge across implementations?
- `Q-IMP-04`: What static, dynamic, adversarial, fault, concurrency, crash/recovery, privacy, and penetration evidence would be required?
- `Q-IMP-05`: What build/configuration provenance, dependency, isolation, update, rollback-prohibition, and remediation controls would be required?
- `Q-IMP-06`: Which unimplemented controls make a proposed decision unsafe or premature today?
- `Q-IMP-07`: What exact facts would trigger re-review, supersession, quarantine, or withdrawal of a later approval?
- `Q-IMP-08`: Does any document, test, prototype, or reviewer statement imply runtime authorization? If so, identify it as a blocking finding.

## 10. Decision-specific reviewer questions

### 10.1 Authenticated evidence

- `Q-EVD-001` (`LSOD-EVD-001`): Are proof domains, canonical inputs, algorithm identifiers, encodings, parameters, downgrade rules, and deprecation states unambiguous and independently verifiable?
- `Q-EVD-002` (`LSOD-EVD-002`): Can issuer enrollment, delegation, revocation, trust-root change, and compromise recovery occur without rogue or stale authority?
- `Q-EVD-003` (`LSOD-EVD-003`): Are verifier identity, audience, roles, material lifecycle, isolation, revocation, and health independently authenticated and separated from custody?
- `Q-EVD-005` (`LSOD-EVD-005`): Can forged, stale, conflicting, cached, rolled-back, or unavailable revocation state ever yield acceptance?
- `Q-EVD-006` (`LSOD-EVD-006`): Are policy activation, exact digest/version binding, overlap, in-flight treatment, supersession, and rollback prohibition atomic and auditable?
- `Q-EVD-007` (`LSOD-EVD-007`): Do approval roles, identity uniqueness, scope, thresholds, independence, expiry/revocation, and consumption resist collusion and concurrent reuse?
- `Q-EVD-008` (`LSOD-EVD-008`): Are nonce provenance, administrative replay domain, exact request/intent/policy binding, collision handling, consumption, and retention sufficient?
- `Q-EVD-009` (`LSOD-EVD-009`): Is the public projection authentic, minimal, privacy-preserving, durable, recoverable, and complete enough to verify required bindings?

### 10.2 Custody

- `Q-CUS-001` (`LSOD-CUS-001`): Can a versioned material profile prevent weak, ambiguous, downgraded, cross-purpose, or mismatched material without selecting an algorithm here?
- `Q-CUS-003` (`LSOD-CUS-003`): Are non-exportability, least privilege, trust zones, attestation, health, containment, quarantine, and failure behavior credible against the stated attacker model?
- `Q-CUS-004` (`LSOD-CUS-004`): Are roles, scopes, authentication, forbidden combinations, thresholds, emergency authority, and separation of duties resistant to collusion and escalation?
- `Q-CUS-005` (`LSOD-CUS-005`): Is every ceremony a deterministic, authenticated, durable state machine that cannot be forged, reordered, partially resumed, or recovered by assumption?
- `Q-CUS-006` (`LSOD-CUS-006`): Are activation, expiry, rotation, overlap, in-flight treatment, predecessor disablement, and non-reactivation monotonic under concurrency?
- `Q-CUS-007` (`LSOD-CUS-007`): Are revocation authority, triggers, publication, freshness, atomic visibility, incident handling, and irreversibility sufficient under outage and compromise?
- `Q-CUS-010` (`LSOD-CUS-010`): Do detection, containment, forensics/privacy, notification, successor separation, recovery, and return criteria prevent continued or repeated compromise?
- `Q-CUS-011` (`LSOD-CUS-011`): Can public custody evidence prove only supportable claims with adequate freshness, revocation, verifier independence, privacy, durable lineage, and outage behavior?

### 10.3 Atomic state

- `Q-STA-001` (`LSOD-STA-001`): Is there exactly one authoritative state boundary with explicit initialization, domain isolation, health, fault assumptions, and no fallback store?
- `Q-STA-002` (`LSOD-STA-002`): Do consistency, isolation, ordering, partitioning, version conflicts, and atomic commit enforce all replay/spend/approval invariants under concurrency?
- `Q-STA-003` (`LSOD-STA-003`): Can acknowledgement, durability, replication, fencing, availability, and recovery prevent lost or multiple authoritative outcomes without selecting a quorum here?
- `Q-STA-004` (`LSOD-STA-004`): Are identifiers, versions, commits, integrity domains, collision handling, lineage, downgrade resistance, and privacy canonical and independently verifiable?
- `Q-STA-006` (`LSOD-STA-006`): Do retention, tombstones, compaction, deletion audit, dispute requirements, privacy, backup, and recovery prevent replay reopening or erased lineage?
- `Q-STA-008` (`LSOD-STA-008`): Are approval/operator identity, scope, thresholds, reuse, expiry/revocation, and consumption bound atomically and irreversibly?
- `Q-STA-009` (`LSOD-STA-009`): Can backup/restore and recovery prove authoritative lineage, reconcile every committed outcome, prohibit rollback, and block ambiguous domains?
- `Q-STA-010` (`LSOD-STA-010`): Are storage access, confidentiality, integrity, telemetry, lifecycle, and non-signer material separated from signer custody and least-privileged?

### 10.4 Operations and runtime security

- `Q-OPS-001` (`LSOD-OPS-001`): Can authenticated sources, selection, monotonic reference, uncertainty, rollback/jump detection, outage, cache expiry, and recovery be reviewed without inventing numeric values?
- `Q-OPS-002` (`LSOD-OPS-002`): Are audit authenticity, ordering, checkpoints, durable acknowledgement, access, redaction, retention, publication, loss, and recovery tamper-evident and privacy-safe?
- `Q-OPS-005` (`LSOD-OPS-005`): Does the error design preserve existing F117 statuses/codes, deterministic precedence, safe correlation/retry, and resistance to disclosure, enumeration, and timing oracles?
- `Q-OPS-006` (`LSOD-OPS-006`): Are telemetry, health, alerting, incident response, access, retention, outage, and recovery public-safe, authenticated, and incapable of granting authority?
- `Q-OPS-007` (`LSOD-OPS-007`): Do process, privilege, capability, filesystem, network, secret, identity, attestation, update, and failure boundaries enforce least privilege and containment?

## 11. Exact 29-ID questionnaire coverage

| Domain | IDs covered | Decision-specific questions |
|---|---|---|
| Authenticated evidence | `LSOD-EVD-001`, `LSOD-EVD-002`, `LSOD-EVD-003`, `LSOD-EVD-005`, `LSOD-EVD-006`, `LSOD-EVD-007`, `LSOD-EVD-008`, `LSOD-EVD-009` | `Q-EVD-001`, `002`, `003`, `005`, `006`, `007`, `008`, `009` |
| Custody | `LSOD-CUS-001`, `LSOD-CUS-003`, `LSOD-CUS-004`, `LSOD-CUS-005`, `LSOD-CUS-006`, `LSOD-CUS-007`, `LSOD-CUS-010`, `LSOD-CUS-011` | `Q-CUS-001`, `003`, `004`, `005`, `006`, `007`, `010`, `011` |
| Atomic state | `LSOD-STA-001`, `LSOD-STA-002`, `LSOD-STA-003`, `LSOD-STA-004`, `LSOD-STA-006`, `LSOD-STA-008`, `LSOD-STA-009`, `LSOD-STA-010` | `Q-STA-001`, `002`, `003`, `004`, `006`, `008`, `009`, `010` |
| Operations/runtime | `LSOD-OPS-001`, `LSOD-OPS-002`, `LSOD-OPS-005`, `LSOD-OPS-006`, `LSOD-OPS-007` | `Q-OPS-001`, `002`, `005`, `006`, `007` |

Coverage total: `8 + 8 + 8 + 5 = 29` unique LSOD IDs.

## 12. Non-decision and authority confirmation

The questionnaire cannot resolve `LSOD-GAT-001` production Bitcoin proof architecture, `LSOD-GAT-002` Bitcoin confirmation/reorg policy/count, `LSOD-GAT-003` observer quorum/independence, or `LSOD-GAT-004` signer activation. All remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`. Bitcoin remains external evidence only.

L28 Protocol v1.0.0 and `coin.tx_validation.validate_transaction` remain authoritative. Authorization is not validation. Eligibility is not signer invocation. No review response may change issuance, supply, canonical height, validation, consensus, history, or settlement.

Protected facts remain exactly: `28000000`, `11130000`, `2824584`, `500000`, `2324584`, `210000`, `[28,14,7,3,1,0]`, `100877`, `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.

This questionnaire authorizes no signer implementation, wallet/key/signature activity, HSM/KMS access, RPC/network connection, submission, broadcast, mining, bridge, ledger/state mutation, settlement, database, deployment, testnet, or activation.
