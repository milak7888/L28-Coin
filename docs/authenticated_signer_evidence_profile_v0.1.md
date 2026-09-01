# Authenticated Signer Evidence Profile v0.1

Status: `DEFINED_DESIGN_ONLY`

Foundation: 124, workstream 1

Addresses: Foundation122 `F122-G01`

Subordinate authority: L28 Protocol v1.0.0

## 1. Scope

This profile converts the Foundation123 authenticated-evidence architecture into a concrete future public contract. It defines evidence that a future signer-interface implementation would have to verify before it could determine signer eligibility. It does not implement evidence verification, authorization, signing, wallet access, submission, broadcast, settlement, networking, RPC, or ledger mutation.

The profile has these immutable separations:

- authorization is not Protocol validation;
- signer eligibility is not signer invocation;
- `coin.tx_validation.validate_transaction` remains the canonical and mandatory L28 transaction validator;
- authenticated evidence grants no authority over L28 issuance, supply, height, validation, consensus, history, or settlement;
- missing, unknown, stale, revoked, contradictory, malformed, unverifiable, or unavailable required evidence fails closed.

The public profile identifier is `l28-authenticated-signer-evidence/v0.1`. Compatibility requires exact profile and major-version equality. Unknown fields, versions, evidence types, verification states, or codes are rejected rather than ignored.

## 2. Evidence envelope

A future evidence artifact is a separate public object referenced by the Foundation117 request envelope. It does not add fields to or silently revise that envelope. Its exact top-level property order is:

1. `evidence_profile`
2. `evidence_version`
3. `evidence_id`
4. `evidence_type`
5. `issuer`
6. `subject`
7. `verifier_binding`
8. `scope_binding`
9. `policy_binding`
10. `approval_binding`
11. `proof_binding`
12. `issued_at`
13. `not_before`
14. `expires_at`
15. `revocation`
16. `replay`
17. `provenance`
18. `verification_state`
19. `verification_code`
20. `verified_at`
21. `audit_projection`
22. `authority_assertions`
23. `non_execution`
24. `envelope_digest`

Required scalar fields use UTF-8 strings except integer time fields. Null, floating-point, environment-derived, or implicit values are forbidden. Object properties retain the order defined below; arrays retain supplied order and may not be set-normalized.

### 2.1 Identity and type

- `evidence_profile`: exactly `l28-authenticated-signer-evidence/v0.1`.
- `evidence_version`: exactly `0.1`.
- `evidence_id`: immutable public identifier, unique within its issuer domain.
- `evidence_type`: exactly one of `caller_identity`, `operator_authorization`, `economic_policy`, `local_authorization`, or `approval`.

An evidence set must contain every type required by the active security profile. Extra evidence does not repair missing evidence and cannot broaden scope.

### 2.2 Issuer and subject

`issuer` property order is:

1. `issuer_id`
2. `issuer_role`
3. `issuer_registry_id`
4. `issuer_authority_version`
5. `verification_material_ref`

The issuer must be enrolled for the exact evidence type, scope, and issuance time. Delegation must be explicit and bounded; provenance chains may not confer broader authority than their narrowest link.

`subject` property order is:

1. `subject_id`
2. `subject_role`
3. `public_identity_ref`

The subject must exactly match the relevant caller, operator, policy authority, or approver binding in the signer-interface request.

### 2.3 Verifier and request scope

`verifier_binding` property order is:

1. `verifier_id`
2. `verifier_profile`
3. `audience`

The future verifier must prove that it is evaluating the evidence for the named audience under the named profile. Caller-controlled verifier identifiers are not trusted.

`scope_binding` property order is:

1. `request_id`
2. `intent_id`
3. `caller_id`
4. `operator_id`
5. `payer_id`
6. `payee_id`
7. `asset`
8. `amount`
9. `transaction_digest`

Every value must equal the corresponding canonical request value. A mismatch fails closed; no normalization, repair, reassociation, or partial match is allowed.

### 2.4 Policy and approvals

`policy_binding` property order is:

1. `policy_id`
2. `policy_version`
3. `policy_digest`
4. `activation_epoch`

The exact active policy version and digest must be resolved independently of caller input. A missing, inactive, superseded, unknown, or digest-mismatched policy fails closed.

`approval_binding` property order is:

1. `approval_id`
2. `approver_id`
3. `approver_role`
4. `approval_scope`
5. `approval_threshold_set_id`
6. `approval_sequence`

For non-approval evidence, these fields use the profile-defined empty public values. For approval evidence, identity, role, scope, threshold set, and sequence are mandatory. Duplicate approval or approver identities, reused approvals, invalid roles, insufficient thresholds, unordered sequences, or approvals outside scope fail closed. Approval evidence conveys authorization input only; it neither validates a transaction nor invokes a signer.

### 2.5 Proof, provenance, and authenticated verification

`proof_binding` property order is:

1. `proof_profile`
2. `proof_algorithm`
3. `proof_material_ref`
4. `proof_digest`

`provenance` property order is:

1. `source_system_id`
2. `source_record_id`
3. `issuance_event_id`
4. `delegation_chain_ids`
5. `provenance_digest`

The proof must authenticate the complete canonical envelope excluding `verification_state`, `verification_code`, `verified_at`, `audit_projection`, and `envelope_digest`. Verification must also authenticate issuer authority, provenance, delegation, and verification-material status. The proof material reference must be public-only and must never expose a private key, seed, mnemonic, xprv, credential, wallet, or secret.

No production proof mechanism, algorithm, issuer registry, trust root, or verification-material system is selected by Foundation124. Those choices are `OPERATOR_DECISION_REQUIRED` and block production verification.

## 3. Freshness, expiration, and revocation

`issued_at`, `not_before`, `expires_at`, and `verified_at` are integer seconds in the trusted-time domain selected by a future approved policy. The following must all hold:

- `issued_at <= not_before < expires_at`;
- verification time is not before `not_before` and is strictly before `expires_at`;
- evidence age and remaining lifetime satisfy the active evidence-type policy;
- the trusted time source and its uncertainty satisfy the Foundation124 time policy;
- issuer authority and verification material were valid at issuance and verification;
- revocation state is fresh enough for the active profile.

`revocation` property order is:

1. `revocation_registry_id`
2. `revocation_record_id`
3. `revocation_epoch`
4. `revocation_state`
5. `revocation_checked_at`

Allowed `revocation_state` values are `not_revoked`, `revoked`, and `unknown`. `revoked`, `unknown`, unavailable registry state, stale revocation state, or untrusted time fails closed. No grace interval exists unless a later operator-approved profile defines and reviews one.

## 4. Replay binding

`replay` property order is:

1. `nonce`
2. `idempotency_key`
3. `replay_domain`
4. `single_use`
5. `consumption_ref`

The nonce, idempotency key, evidence identifier, request identifier, intent identifier, evidence type, and policy version must be bound together. `single_use` must be true for operator authorization, local authorization, and approval evidence unless a later operator decision expressly defines narrower safe reuse. Replay state must be checked and consumed through the future atomic-state contract. Missing, unavailable, inconsistent, already-consumed, or conflicting state fails closed.

## 5. Verification states and precedence

Allowed `verification_state` values are:

- `unverified`
- `verified`
- `rejected`
- `revoked`
- `expired`
- `not_yet_valid`
- `unavailable`
- `operator_decision_required`

The `verification_code` must be an existing Foundation117 stable response code applicable to the observed failure. This profile does not create replacement interface codes. Before a production implementation exists, artifacts remain `unverified` or `operator_decision_required`; fixtures and tests cannot promote them to production `verified`.

Verification order is immutable:

1. envelope schema, order, profile, version, and public-only checks;
2. provenance and proof authentication;
3. issuer enrollment, delegation, and authority scope;
4. revocation and verification-material status;
5. trusted-time freshness and expiration;
6. verifier, request, identity, transaction, policy, and approval bindings;
7. replay-state availability and status;
8. audit-projection derivation;
9. authorization evaluation;
10. mandatory `coin.tx_validation.validate_transaction` binding;
11. eligibility decision.

An earlier failure is never masked by a later one. The Foundation117 response precedence remains authoritative. Eligibility cannot be emitted unless every required evidence object is `verified`, authorization passes, canonical validation passes, and all other gates pass. Eligibility still does not invoke signing.

## 6. Public audit projection

`audit_projection` property order is:

1. `audit_event_id`
2. `evidence_id`
3. `evidence_type`
4. `issuer_id`
5. `subject_id`
6. `policy_id`
7. `policy_version`
8. `verification_state`
9. `verification_code`
10. `verified_at`
11. `request_id`
12. `intent_id`
13. `transaction_digest`
14. `revocation_record_id`
15. `replay_consumption_ref`
16. `evidence_digest`

The projection is public, minimal, deterministic, and contains no proof material, secrets, private credentials, raw private evidence, or unnecessary personal data. It is audit evidence only and has no settlement or consensus authority. Authenticity, tamper evidence, retention, access, and recovery remain governed by the Foundation124 time/audit/resource policy.

## 7. Authority and non-execution assertions

`authority_assertions` must state false for every attempted override of issuance, supply, height, history, validation, consensus, or settlement. `non_execution` must state false for signing attempted, signature created, wallet accessed, key accessed, transaction submitted, broadcast attempted, RPC connected, network connected, ledger mutated, settlement attempted, settlement activated, miner started, node started, service started, deployment attempted, and testnet activated.

The `envelope_digest` is a future domain-separated digest of the canonical public envelope. Its algorithm, domain label, and deployment use must remain consistent with Foundation117 and require an approved implementation specification and tests; this document performs no digest computation.

## 8. Operator decisions and remaining gates

Each item below is `OPERATOR_DECISION_REQUIRED` before implementation evidence can satisfy `F122-G01`:

- authenticated proof format, algorithm, parameters, and canonical proof input;
- issuer-registry governance, trust roots, enrollment, delegation, and revocation authority;
- verifier identity, authentication, authorization, and verification-material lifecycle;
- evidence-type lifetimes, freshness windows, and any permitted clock uncertainty;
- revocation source, authenticity, update cadence, cache policy, and outage behavior;
- policy activation, supersession, rollback prohibition, and version-transition rules;
- approval issuer roles, threshold-set governance, scope, and consumption policy;
- replay domain, nonce source, single-use policy, and retention;
- public audit disclosure, privacy, authenticity, retention, and recovery policy;
- implementation boundary, independent security review, and production deployment authorization.

Until all applicable decisions are explicit and supported by implementation evidence and adversarial tests, authenticated evidence remains `GAP_REQUIRES_FUTURE_WORK`. Missing a required decision fails closed with the applicable Foundation117 security-decision status/code.

## 9. Protocol and economic invariants

This profile preserves: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; and immutable historical evidence.

Bitcoin remains external evidence only. Production Bitcoin proof architecture, Bitcoin confirmation/reorg policy and count, and observer quorum/independence remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

Foundation124 grants no signer, runtime, wallet, key, signature, network, RPC, broadcast, settlement, deployment, or activation authorization.
