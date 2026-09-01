# Local Signer Custody Control Profile v0.1

Status: `DEFINED_DESIGN_ONLY`

Foundation: 124, workstream 2

Addresses: Foundation122 `F122-G02`

Subordinate authority: L28 Protocol v1.0.0

## 1. Scope and boundary

This profile defines controls that a future isolated signer-custody subsystem would have to satisfy. It is a public design contract, not a custody implementation. It creates, imports, reads, derives, rotates, revokes, backs up, recovers, destroys, or uses no key material. It accesses no wallet, HSM, KMS, keychain, secret, signing service, RPC endpoint, network, or runtime.

Custody is subordinate to the L28 authority boundary:

- authorization is not Protocol validation;
- signer eligibility is not signer invocation;
- `coin.tx_validation.validate_transaction` remains mandatory and canonical;
- custody possession conveys no issuance, supply, height, validation, history, consensus, or settlement authority;
- every missing, unknown, contradictory, unavailable, degraded, quarantined, or unverifiable required custody state fails closed.

The public profile identifier is `l28-local-signer-custody-control/v0.1`. Compatibility requires exact profile and major-version equality.

## 2. Control-profile envelope

The exact top-level property order for a future public custody-control profile is:

1. `custody_profile`
2. `custody_version`
3. `custody_profile_id`
4. `material_policy`
5. `generation_import_policy`
6. `isolation_policy`
7. `role_policy`
8. `ceremony_policy`
9. `lifecycle_policy`
10. `rotation_policy`
11. `revocation_policy`
12. `backup_recovery_policy`
13. `destruction_policy`
14. `compromise_policy`
15. `custody_evidence_policy`
16. `authority_assertions`
17. `non_execution`
18. `profile_digest`

Unknown fields, implicit defaults, null control values, caller-selected policy values, or incompatible versions are rejected. A production profile cannot be active while any required value is `OPERATOR_DECISION_REQUIRED`.

## 3. Material policy

`material_policy` property order is:

1. `algorithm_profile`
2. `algorithm_parameters`
3. `material_origin_policy`
4. `material_exportability`
5. `material_usage_scope`
6. `public_identifier_derivation`
7. `policy_state`

Only a versioned operator-approved allowlist may identify future algorithms, parameters, material forms, origins, and usage scopes. Unknown, deprecated, mismatched, unapproved, or caller-selected material fails closed. Foundation124 selects no algorithm, curve, key size, derivation scheme, device class, or provider.

Private key material, seeds, mnemonics, xprvs, recovery secrets, and credentials must never appear in public evidence, logs, receipts, interface envelopes, fixtures, tests, error details, or audit projections.

## 4. Generation and import boundary

`generation_import_policy` property order is:

1. `generation_allowed`
2. `import_allowed`
3. `approved_origin_classes`
4. `ceremony_profile_id`
5. `operator_authorization_profile_id`
6. `provenance_required`
7. `activation_separate`

Generation and import are distinct future privileges. Neither is implied by signer-interface eligibility, invocation authority, custody administration, or possession of public evidence. Each requires a separately authorized ceremony, authenticated operators, provenance, audit evidence, and post-ceremony verification. Provisioning never activates use; activation is a separate later gate.

Any attempted generation/import outside the approved boundary, missing provenance, unapproved origin, incomplete ceremony, or authorization mismatch fails closed and places the lifecycle in `QUARANTINED`.

## 5. Isolation and access controls

`isolation_policy` property order is:

1. `isolation_class`
2. `process_boundary`
3. `network_boundary`
4. `storage_boundary`
5. `export_boundary`
6. `attestation_profile_id`
7. `health_evidence_required`

Future custody must minimize exposed interfaces, prevent raw-secret export, separate public verification data from private material, and deny direct access by callers, adapters, Harness/Evals, Bitcoin observers, and ordinary application processes. Failure or uncertainty in isolation or attestation fails closed.

`role_policy` property order is:

1. `custody_administrator_roles`
2. `provisioning_roles`
3. `invocation_controller_roles`
4. `recovery_roles`
5. `destruction_roles`
6. `audit_roles`
7. `forbidden_role_combinations`
8. `threshold_profile_id`

Custody administration, operator authorization, invocation control, recovery, destruction, and audit are distinct roles. No single role gains end-to-end authority by default. Least privilege, authenticated sessions, scope, expiry, revocation, and separation of duties are mandatory. Exact role mappings and thresholds remain operator decisions.

## 6. Ceremonies and lifecycle

`ceremony_policy` property order is:

1. `ceremony_type`
2. `ceremony_id`
3. `required_roles`
4. `required_threshold`
5. `policy_version`
6. `public_record_required`
7. `independent_observation_required`

A future ceremony must bind its type, participants, threshold, policy version, scope, outputs, and public record. Partial, abandoned, duplicated, reordered, unverifiable, or mismatched ceremonies fail closed.

`lifecycle_policy` property order is:

1. `custody_identity`
2. `material_version`
3. `lifecycle_state`
4. `state_version`
5. `activated_at`
6. `expires_at`
7. `predecessor_material_version`
8. `successor_material_version`

The allowed normal transition sequence is:

`UNINITIALIZED -> PROVISIONED_INACTIVE -> ACTIVE -> ROTATING -> REVOKED -> DESTROYED`

`QUARANTINED` and `COMPROMISED` are fail-closed states reachable from any non-destroyed state. Only `ACTIVE`, within its approved scope and lifetime and with current verified custody evidence, may be considered by a future invocation controller. Lifecycle state alone never invokes signing.

Unrecognized transitions, version rollback, skipped activation, use of inactive/revoked/destroyed material, or uncertain state fail closed.

## 7. Rotation and revocation

`rotation_policy` property order is:

1. `rotation_trigger_profile`
2. `overlap_allowed`
3. `predecessor_disable_rule`
4. `successor_activation_rule`
5. `verification_material_publication_rule`
6. `rotation_audit_required`

Rotation must preserve stable public identity only where the approved policy explicitly permits it. Old and new material cannot both be usable outside an approved, bounded overlap. A successor cannot activate before its custody evidence is verified; a predecessor must fail closed at the defined disable point.

`revocation_policy` property order is:

1. `revocation_authority_profile`
2. `revocation_trigger_profile`
3. `revocation_publication_rule`
4. `revocation_effective_rule`
5. `revocation_freshness_rule`
6. `recovery_after_revocation_rule`

Revocation is monotonic. Revoked material cannot return to `ACTIVE`; recovery requires separately provisioned successor material. Missing, stale, unavailable, or unauthenticated revocation state fails closed.

## 8. Backup, recovery, and destruction

`backup_recovery_policy` property order is:

1. `backup_allowed`
2. `backup_isolation_class`
3. `backup_export_policy`
4. `backup_threshold_profile`
5. `recovery_ceremony_profile`
6. `recovery_test_profile`
7. `backup_retention_rule`

Whether backup exists at all is an operator security decision. If allowed, backup must preserve or strengthen isolation, access thresholds, provenance, inventory, retention, and audit controls. Recovery must produce a new verified lifecycle event and cannot silently restore revoked or compromised material.

`destruction_policy` property order is:

1. `destruction_trigger_profile`
2. `destruction_method_profile`
3. `required_roles`
4. `required_threshold`
5. `verification_method_profile`
6. `public_record_required`

Destruction must be irreversible under the selected custody architecture, independently evidenced, and reflected in monotonic lifecycle state. Failed or unverifiable destruction leaves material `QUARANTINED`; it never permits assumed destruction.

## 9. Compromise response

`compromise_policy` property order is:

1. `detection_sources`
2. `quarantine_rule`
3. `revocation_rule`
4. `notification_rule`
5. `containment_roles`
6. `forensic_evidence_rule`
7. `successor_provisioning_rule`
8. `return_to_service_rule`

Suspected compromise immediately blocks eligibility and invocation, preserves evidence, initiates authenticated revocation, and requires separately authorized successor provisioning. No automatic return to service is allowed. Incident response cannot rewrite historical evidence or L28 state.

## 10. Public custody evidence

`custody_evidence_policy` property order is:

1. `evidence_profile_id`
2. `custody_identity`
3. `public_key_identifier`
4. `material_version`
5. `algorithm_profile`
6. `lifecycle_state`
7. `policy_version`
8. `isolation_class`
9. `ceremony_record_ids`
10. `revocation_record_id`
11. `verified_at`
12. `expires_at`
13. `verification_state`
14. `evidence_digest`

Custody evidence is public-only, minimally identifying, authenticated, time-bounded, revocation-aware, and bound to the signer request and active policy. It proves only that custody controls were evaluated. It does not expose secret material, prove transaction validity, or authorize invocation, broadcast, or settlement.

## 11. Fail-closed control states

The future custody verifier must classify controls as `verified`, `rejected`, `revoked`, `expired`, `quarantined`, `compromised`, `unavailable`, or `operator_decision_required`. Only complete `verified` evidence for an `ACTIVE` material version can contribute to eligibility. All other states fail closed with an existing Foundation117 status/code; this profile invents no replacement code.

Authority assertions must set every issuance, supply, height, history, validation, consensus, and settlement override false. Non-execution assertions must prove no key operation, wallet access, signature creation, transaction submission, broadcast, RPC/network connection, ledger mutation, settlement, service start, deployment, or testnet activation occurred.

## 12. Operator decisions and remaining gates

Each item below is `OPERATOR_DECISION_REQUIRED` before implementation evidence can satisfy `F122-G02`:

- approved algorithm, parameter, material, derivation, and public-identifier policies;
- whether generation, import, or both are permitted and the approved origin classes;
- custody isolation technology/class, process/storage/export boundary, and attestation;
- named role mapping, authentication, access scopes, forbidden combinations, and thresholds;
- ceremony procedures, observers, evidence, and independent review requirements;
- activation, expiry, rotation triggers, bounded overlap, and predecessor disable rules;
- revocation authority, trigger, publication, freshness, and incident deadlines;
- whether backup is permitted and, if so, isolation, quorum, retention, and recovery controls;
- destruction method, verification method, required roles, and evidence retention;
- compromise detection, containment, forensics, notification, and successor policy;
- custody-evidence proof, verification cadence, audit durability, and privacy policy;
- implementation architecture, service boundary, testing, independent review, deployment, and activation authorization.

Until all applicable decisions and later evidence exist, custody remains `GAP_REQUIRES_FUTURE_WORK` and signer implementation remains blocked.

## 13. Protocol and economic invariants

This profile preserves: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; and immutable historical evidence.

Bitcoin remains external evidence only. Production Bitcoin proof architecture, Bitcoin confirmation/reorg policy and count, and observer quorum/independence remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

Foundation124 grants no signer, custody runtime, wallet, key, signature, HSM/KMS, network, RPC, broadcast, settlement, deployment, or activation authorization.
