# Local Signer Time, Audit, and Resource Policy v0.1

Status: `DEFINED_DESIGN_ONLY`

Foundation: 124, workstream 4

Addresses: Foundation122 `F122-G05`, `F122-G06`, `F122-G07`, and `F122-G08`

Subordinate authority: L28 Protocol v1.0.0

## 1. Scope and authority

This policy defines future trusted-time, durable-audit, bounded-parser, resource-control, monitoring, process-isolation, and security-testing requirements for the local signer boundary. It implements no clock service, audit store, parser, rate limiter, process, signer, wallet, key, server, network, RPC, broadcast, settlement, deployment, or testnet.

The policy preserves these separations:

- authorization is not Protocol validation;
- signer eligibility is not signer invocation;
- `coin.tx_validation.validate_transaction` remains canonical and mandatory;
- time, audit, monitoring, and service evidence cannot override L28 issuance, supply, height, history, validation, consensus, or settlement;
- missing, stale, unauthenticated, rolled-back, unavailable, contradictory, corrupt, or over-limit required evidence fails closed.

The public policy identifier is `l28-local-signer-time-audit-resource/v0.1`. Compatibility requires exact policy and major-version equality.

## 2. Policy envelope

The exact top-level property order for a future public policy is:

1. `policy_profile`
2. `policy_version`
3. `policy_id`
4. `time_policy`
5. `audit_policy`
6. `parser_policy`
7. `resource_policy`
8. `error_policy`
9. `monitoring_policy`
10. `isolation_policy`
11. `test_policy`
12. `authority_assertions`
13. `non_execution`
14. `policy_digest`

Unknown fields, versions, implicit defaults, null required values, caller-selected limits, or undecided required production values fail closed. A production profile cannot be active while any required value is `OPERATOR_DECISION_REQUIRED`.

## 3. Trusted production-time policy

`time_policy` property order is:

1. `time_profile_id`
2. `source_ids`
3. `source_authentication_profile`
4. `authoritative_selection_rule`
5. `monotonic_reference_profile`
6. `maximum_skew_seconds`
7. `maximum_uncertainty_seconds`
8. `rollback_detection_rule`
9. `forward_jump_rule`
10. `outage_rule`
11. `cached_time_rule`
12. `time_evidence_lifetime_seconds`

All time values are integers in a single named time domain. A future implementation must authenticate its approved source set, bind source identity and measurement evidence, compare wall time with an approved monotonic reference, detect rollback and unreasonable forward movement, expose uncertainty, and preserve the evidence used for every decision.

Eligibility fails closed when:

- no approved authenticated source is available;
- source identity, proof, measurement, or policy binding fails;
- sources disagree beyond the approved bound;
- uncertainty exceeds the approved bound;
- monotonic rollback, epoch rollback, or an unapproved forward jump is detected;
- cached evidence is absent, expired, untrusted, or outside its allowed outage use;
- an integer time is malformed, overflows, or crosses a policy boundary ambiguously;
- any required numeric bound remains `OPERATOR_DECISION_REQUIRED`.

At expiration boundaries, `now < expires_at` is required; equality is expired. At not-before boundaries, `now >= not_before` is required. Time success cannot repair revoked, invalid, or unauthorized evidence.

No time source, authentication mechanism, source quorum, skew value, uncertainty value, outage duration, or cache duration is chosen here.

## 4. Durable and tamper-evident audit policy

`audit_policy` property order is:

1. `audit_profile_id`
2. `event_schema_version`
3. `authenticity_profile`
4. `integrity_chain_profile`
5. `checkpoint_profile`
6. `durability_profile`
7. `retention_profile`
8. `recovery_profile`
9. `access_control_profile`
10. `redaction_profile`
11. `publication_profile`
12. `audit_health_evidence_profile`

Every decision attempt must create a deterministic public-safe audit event binding request, intent, policy, evidence, validator result, replay/economic state, eligibility outcome, error code, trusted-time evidence, and prior audit lineage. Audit evidence is advisory/public accountability evidence only; it is not an L28 receipt of settlement unless Protocol-governed settlement evidence later proves that fact.

A conforming future audit system must:

- authenticate event origin and the service/process identity that emitted it;
- preserve canonical payload digests and append-only monotonic lineage;
- detect deletion, insertion, reordering, truncation, duplication, rollback, and mutation;
- create independently verifiable checkpoints under an approved policy;
- durably retain events, access decisions, recovery actions, and policy changes;
- restrict write, read, export, redact, retain, and recover roles separately;
- expose only public/disposable evidence in public projections;
- never log private keys, seeds, mnemonics, xprvs, credentials, wallet contents, raw authenticated proofs, or secret configuration;
- verify recovery against pre-failure checkpoints before service eligibility resumes.

Missing audit publication capacity, broken lineage, unauthenticated records, failed durability acknowledgement, unavailable required checkpoint state, unauthorized access, or uncertain recovery fails closed before eligibility is returned. A durable local eligibility audit still does not sign, broadcast, or settle.

No authenticity algorithm, integrity-chain mechanism, checkpoint authority, audit storage, retention duration, recovery objective, access platform, or redaction technology is chosen here.

## 5. Bounded parsing policy

`parser_policy` property order is:

1. `maximum_request_bytes`
2. `maximum_response_bytes`
3. `maximum_json_depth`
4. `maximum_object_properties`
5. `maximum_array_elements`
6. `maximum_string_bytes`
7. `maximum_integer_digits`
8. `maximum_evidence_objects`
9. `maximum_provenance_depth`
10. `maximum_approvals`
11. `duplicate_property_rule`
12. `unknown_property_rule`
13. `normalization_rule`
14. `parse_work_budget`

All maximums must be positive integers selected by an operator-approved production profile and tested at below, exact, and above boundaries. Duplicate properties, unknown properties, invalid UTF-8, forbidden normalization, floating point, noncanonical integers, excessive nesting, excessive collections, oversized strings, excessive evidence chains, and exhausted work budgets fail closed before evidence or authorization evaluation.

The canonical rules from Foundation117-F121 remain authoritative: deterministic UTF-8 JSON, exact property order, exact arrays, no duplicate keys, no unknown keys, no whitespace-dependent semantics, and no lossy or caller-directed normalization.

Foundation124 selects no numeric parser maximum or work budget. Every such value is `OPERATOR_DECISION_REQUIRED`.

## 6. Rate and resource policy

`resource_policy` property order is:

1. `rate_identity_dimensions`
2. `rate_window_seconds`
3. `sustained_request_limit`
4. `burst_request_limit`
5. `concurrent_request_limit`
6. `queue_depth_limit`
7. `request_timeout_milliseconds`
8. `cpu_budget`
9. `memory_budget_bytes`
10. `storage_budget_bytes`
11. `file_descriptor_budget`
12. `audit_backpressure_rule`
13. `dependency_circuit_breaker_rule`
14. `overload_recovery_rule`

Rate identity must use authenticated caller, operator, policy, and service dimensions; caller-controlled network metadata alone is insufficient. Limits must apply before expensive proof work where safe, remain consistent across the selected deployment boundary, and prevent one identity or partition from starving others.

Queue saturation, timeout, resource exhaustion, audit backpressure, dependency failure, circuit-breaker activation, or unavailable rate state fails closed with a secure error. Degraded operation may not bypass authenticated evidence, validation, replay, spending, approvals, trusted time, audit durability, or custody gates.

Foundation124 selects no rate, burst, concurrency, queue, timeout, CPU, memory, storage, descriptor, or recovery value. Every such value is `OPERATOR_DECISION_REQUIRED`.

## 7. Secure error policy

`error_policy` property order is:

1. `public_status_taxonomy`
2. `public_code_taxonomy`
3. `precedence_profile`
4. `correlation_id_profile`
5. `internal_detail_policy`
6. `timing_disclosure_policy`
7. `retry_disclosure_policy`

Public responses must use the Foundation117 stable status/code taxonomy and precedence. This policy invents no replacement codes. Errors reveal no secrets, private evidence, key/custody state beyond safe public status, internal topology, dependency identifiers, configuration, raw exceptions, stack traces, timing oracle, rate-limit bypass, or recovery method.

Correlation identifiers are public, deterministic where required by the interface, and non-secret. Retry guidance cannot imply that an authorization, validation, replay, custody, or security-decision failure will become eligible without corrected and newly verified evidence.

## 8. Monitoring and alerting policy

`monitoring_policy` property order is:

1. `health_evidence_profile`
2. `security_event_profile`
3. `metric_allowlist`
4. `log_allowlist`
5. `alert_profile`
6. `incident_profile`
7. `monitoring_access_profile`
8. `monitoring_retention_profile`

Monitoring must detect authentication failures, revocation failures, replay conflicts, spending-limit conflicts, approval misuse, clock anomalies, audit-integrity failures, parser abuse, overload, custody-health failures, validation-binding mismatches, and prohibited invocation attempts. Alerts are advisory and cannot change eligibility, invoke signing, or override fail-closed behavior.

Metrics and logs must be explicitly allowlisted and public-safe. Monitoring outage, excessive lag, unauthorized access, or missing required security health evidence blocks production eligibility under the approved policy.

## 9. Process and key isolation requirements

`isolation_policy` property order is:

1. `public_interface_process_boundary`
2. `evidence_verifier_process_boundary`
3. `state_process_boundary`
4. `custody_process_boundary`
5. `audit_process_boundary`
6. `privilege_profile`
7. `filesystem_access_profile`
8. `network_access_profile`
9. `secret_access_profile`
10. `sandbox_profile`

The future public interface, evidence verification, atomic state, custody, and audit functions must have explicit least-privilege boundaries. The public interface must never receive raw private key material. Harness/Evals and adapters remain advisory and have no custody, validation, consensus, or settlement authority. Bitcoin observers remain external-evidence inputs only.

Failure of required isolation, unexpected privilege, prohibited filesystem/network/secret access, or boundary attestation mismatch fails closed. Foundation124 chooses no process manager, container, host, cloud, sandbox, deployment topology, or secret system.

## 10. Fault, recovery, and adversarial test policy

`test_policy` property order is:

1. `conformance_profile`
2. `malformed_input_profile`
3. `adversarial_evidence_profile`
4. `boundary_test_profile`
5. `rate_resource_test_profile`
6. `concurrency_test_profile`
7. `crash_recovery_test_profile`
8. `clock_fault_test_profile`
9. `audit_recovery_test_profile`
10. `custody_isolation_test_profile`
11. `independent_review_profile`

Later implementation evidence must include deterministic positive, negative, boundary, and fail-closed cases; malformed and adversarial evidence; duplicate and conflicting requests; concurrent spending/approval/replay races; crash before/during/after atomic commit; audit loss/recovery/tamper attempts; time rollback, forward jump, skew, disagreement, and outage; parser and resource exhaustion; privilege and isolation violations; safe-error review; and independent security assessment.

The Foundation120 fixtures and Foundation121 tests are offline conformance evidence only. They do not exercise production authentication, custody, atomic storage, trusted time, audit durability, resource enforcement, service hardening, or runtime isolation. Passing them activates nothing.

## 11. Operator decisions and remaining gates

Each item below is `OPERATOR_DECISION_REQUIRED` before implementation evidence can satisfy `F122-G05` through `F122-G08`:

- trusted-time sources, source authentication, selection/quorum rule, monotonic reference, skew, uncertainty, rollback/forward-jump, outage, and cache values;
- audit authenticity, integrity chain, checkpoints, storage, durability, retention, recovery, access, redaction, and publication policies;
- every parser byte, depth, property, array, string, integer, evidence, provenance, approval, and work-budget limit;
- rate identity, window, sustained/burst/concurrency/queue limits, timeouts, CPU, memory, storage, descriptor, backpressure, and recovery rules;
- secure-error detail, correlation, timing, and retry policies consistent with Foundation117;
- required security metrics, logs, health evidence, alerts, incident response, access, and retention;
- process/service boundaries, privilege, filesystem, network, secret, and sandbox policies;
- deployment topology, operator runbooks, rollback prohibition, recovery authorization, and independent review;
- complete implementation-focused adversarial, fault, concurrency, crash, recovery, DoS, and isolation test acceptance criteria.

Until these decisions and later evidence exist, the four addressed findings remain `GAP_REQUIRES_FUTURE_WORK`. No documentation or offline test can substitute for production evidence.

## 12. Protocol and economic invariants

This policy preserves: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; and immutable historical evidence.

Bitcoin remains external evidence only. Production Bitcoin proof architecture, Bitcoin confirmation/reorg policy and count, and observer quorum/independence remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

Foundation124 grants no signer, time service, audit service, runtime, wallet, key, signature, network, RPC, broadcast, settlement, deployment, testnet, or activation authorization.
