# Authenticated Signer Evidence Architecture v0.1

**Foundation:** 123

**Workstream:** 1 of 4 — F122-G01

**Status:** ARCHITECTURE DEFINED; DOCUMENTATION ONLY; NON-ACTIVATING

**Document version:** `authenticated-signer-evidence-architecture/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Required parent:** `a66f02f224577dca090ac99f4182dade2a2160f1`

**Runtime authorization:** none

---

## 1. Purpose and scope

This document addresses Foundation122 finding F122-G01 at the architecture
level. It defines the future trust boundary for authenticating the public
caller, operator, policy, authorization, and approval evidence consumed by
`l28-local-signer-interface/v0.1`.

It does not implement an evidence verifier, credential format, issuer registry,
revocation service, key, wallet, signer, signature, RPC client, network client,
state store, audit service, or runtime. It grants no signing, spending,
submission, broadcast, settlement, deployment, or production authority.

This architecture is subordinate to [L28 Protocol v1.0.0](../PROTOCOL.md),
Foundation117, and Foundation122. On conflict, Protocol v1.0.0 prevails.

## 2. Fixed authority model

1. L28 remains the sole issuance, supply, canonical-height, validation,
   consensus, historical-ledger, and native-settlement authority.
2. `coin.tx_validation.validate_transaction` remains the canonical and
   mandatory Protocol validation path. No evidence issuer or verifier may
   replace, bypass, repair, or override it.
3. Authentication establishes only whether a public evidence claim is accepted
   under an approved future local security profile.
4. Authorization is not Protocol validation. An authenticated authorization
   claim may restrict a transaction but cannot make an invalid transaction
   valid.
5. Signer eligibility is not signer invocation. Authenticated evidence may
   contribute to `eligible_public_projection`; it cannot request or perform
   signing.
6. Evidence issuers, verifiers, Harness/Evals, Bitcoin observations, and
   adapters have zero L28 consensus or settlement authority.

Missing, malformed, stale, revoked, unverifiable, ambiguously bound, or
contradictory required evidence fails closed.

## 3. Architectural components

The future boundary requires five logically separate components. Their
implementation and deployment remain future work.

| Component | Responsibility | Explicitly prohibited authority |
|---|---|---|
| Evidence issuer registry | Identify approved issuer roles, public verification references, status, scope, and policy version | Cannot authorize Protocol validity, issuance, height, consensus, history, or settlement |
| Evidence verifier | Verify schema, provenance, authenticity, scope, freshness, revocation, and bindings under one exact security profile | Cannot sign, load signer keys, mutate ledger state, or substitute for `validate_transaction` |
| Revocation/freshness view | Supply authenticated, current issuer/evidence status | Cannot default missing state to valid or fresh |
| Policy-version resolver | Bind evidence to one exact approved policy version and digest | Cannot upgrade, downgrade, merge, or infer a policy version |
| Public audit projector | Emit a minimal public verification result and lineage references | Cannot expose proof secrets or claim signature, broadcast, or settlement |

The components may be deployed separately, but their authority remains exactly
the table above. Transport separation does not create a new trust authority.

## 4. Evidence classes and issuer authority

### 4.1 Caller identity evidence

Caller evidence proves only that an approved identity authority authenticated a
public caller identity for the exact request and validity interval. It must bind
the F117 `caller_id`, `caller_public_identity`, public verification-key
identifier if used, `scope_request_id`, issuance time, expiry time, issuer,
security profile, and evidence identifier.

Caller authentication does not establish operator consent, policy authority,
approval authority, transaction validity, balance, or settlement.

### 4.2 Operator authorization evidence

Operator evidence proves only that an approved operator authority made an
authenticated decision for the exact request, intent, policy, payer, payee,
asset, maximum amount, validity interval, and required independent-review
reference.

The operator issuer must be distinct in authority from the caller and from any
future signer custody operator. An operator approval is necessary where policy
requires it, but it cannot validate a transaction or invoke a signer.

### 4.3 Policy and local authorization evidence

Policy evidence must originate from an issuer authorized for the exact policy
namespace and version. It binds the policy identifier and digest, asset,
limits, window, approval rules, operator-gate requirement, effective interval,
and issuer status.

Local authorization evidence must bind the exact request, intent, policy
version, payer, payee, asset, amount, evaluator identity, and validity interval.
It cannot grant unlimited spend, Protocol override, runtime authority, or
settlement authority.

### 4.4 Approval evidence

Each approval must bind one authenticated approver identity to the exact
request, intent, policy version, approved amount, decision, issuance time, and
expiry. The issuer must be authorized to authenticate that approver under the
bound policy.

Approval identity is evaluated by exact public identity, not display name,
case folding, alias inference, or set normalization. Duplicate approvers add no
authority and fail under the existing F117/F118 semantics. An approval cannot
be transferred across a request, intent, policy version, amount, payer, or
payee.

## 5. Required authenticated evidence envelope

The production authentication profile remains a future versioned specification,
but every authenticated evidence object must be able to bind at least:

1. exact evidence type and version;
2. globally unambiguous public evidence identifier;
3. issuer identifier and exact issuer-authority role;
4. public verification-material identifier, never private material;
5. subject identity and subject role;
6. request, intent, policy-version, party, asset, and amount bindings applicable
   to that evidence class;
7. issuance, not-before, expiry, and revocation-check times;
8. security-profile identifier and policy digest;
9. anti-replay identifier and intended verifier/audience binding;
10. provenance chain references required by the approved profile;
11. authentication result and stable public failure category; and
12. a public-only audit projection reference.

F117 request and response schemas remain unchanged. A later authorized profile
must specify how authenticated artifacts are referenced without silently adding
fields to `l28-local-signer-interface/v0.1`.

## 6. Verification sequence

A future verifier must evaluate evidence in this order and stop at the first
applicable failure consistent with F117 precedence:

1. enforce exact encoding, profile, schema, type, size, and canonical-order
   rules before semantic processing;
2. reject secret material, secret locators, credentials, or unsupported proof
   material;
3. resolve the exact approved security profile and issuer role; no negotiation,
   downgrade, or default profile is allowed;
4. verify provenance and the evidence authenticity mechanism selected by that
   approved future profile;
5. verify issuer status and authority for the exact evidence class and scope;
6. verify current revocation status for issuer, verification material,
   credential, subject, and policy version as required;
7. verify not-before, expiry, freshness, and policy-effective intervals using
   the trusted-time architecture in
   `local_signer_time_audit_runtime_hardening_architecture_v0.1.md`;
8. verify exact request, intent, policy, party, asset, amount, audience, and
   transaction bindings;
9. verify replay and single-use requirements using the atomic-state architecture
   in `local_signer_atomic_state_semantics_v0.1.md`;
10. produce only an authenticated-evidence decision and public audit projection;
    and
11. continue through independent local authorization and mandatory
    `coin.tx_validation.validate_transaction` binding before eligibility can be
    reported.

Verification failure cannot be repaired by another issuer, adapter, caller,
operator, Harness/Evals result, Bitcoin observation, or signer.

## 7. Provenance, revocation, and freshness

### 7.1 Provenance

Every accepted claim must have a complete, authenticated provenance path from
the evidence object to an approved issuer authority and exact security profile.
Unknown, circular, ambiguous, cross-profile, or incomplete provenance fails
closed. A transport source or possession of an evidence object is not
provenance.

### 7.2 Revocation

Revocation is authoritative for local evidence acceptance only. The future
revocation design must cover issuer authority, verification material, subject,
credential/evidence identifier, policy version, and delegated authority.

Unavailable, stale, rollback-detected, or contradictory revocation state fails
closed. Cached status may be used only under an explicitly approved future
freshness policy; this document selects no cache duration or grace period.

### 7.3 Freshness and policy-version binding

Freshness requires authenticated time and exact policy-version state. Evidence
issued under a superseded, unavailable, revoked, or ambiguously active policy
version cannot be silently migrated. An approval and authorization must bind
the same exact policy version evaluated for limits and operator requirements.

This document selects no clock source, skew allowance, evidence lifetime,
revocation interval, or policy grace window.

## 8. Anti-replay and approval identity

Evidence verification must bind replay identity to the evidence identifier,
issuer, subject, request, intent, policy version, audience, and applicable
amount/party tuple. The atomic state boundary must distinguish:

- a byte-identical idempotent retry of an already committed public eligibility
  result;
- reuse of single-use evidence;
- a duplicate approval identity;
- an identifier reused with conflicting content; and
- an unknown or unavailable replay state.

Only the first may return a prior public result, and it must never re-invoke a
signer or consume approval/spending state again. All other cases fail closed
under the existing F117 taxonomy. Exact runtime mappings require a later
conformance milestone and are not invented here.

## 9. Public audit projection

The public projection may disclose only the minimum evidence needed to audit
the decision:

- evidence profile and public evidence identifier;
- issuer and subject public identifiers;
- request, intent, policy-version, and decision bindings;
- verification status and stable public failure category;
- issuance/evaluation/expiry times from trusted time;
- revocation-state reference and freshness status;
- canonical public digest and lineage references; and
- explicit `public_evidence_only=true` and non-execution assertions.

It must not disclose proof secrets, private verification inputs, credentials,
wallet or key locators, infrastructure details, raw internal policy data, or
security-sensitive error detail. The projection is not a signature, signed
receipt, transaction receipt, Protocol validation result, settlement proof,
ledger record, or Protocol history.

## 10. Failure and recovery rules

Required evidence or state that is missing, malformed, unsupported, expired,
not yet valid, revoked, stale, unauthenticated, unavailable, contradictory, or
not exactly bound blocks eligibility. The verifier must not:

- infer identity or issuer authority;
- select a fallback issuer or policy version;
- treat a network or revocation outage as valid evidence;
- normalize mismatched identities or bindings;
- aggregate partial approvals into authority;
- reuse evidence across scopes;
- expose sensitive verification errors; or
- invoke signing or runtime behavior as recovery.

Recovery means obtaining new, complete, authenticated evidence and beginning a
new deterministic evaluation. It never means repairing an evidence object in
place.

## 11. Dependencies and remaining gates

This architecture does not resolve:

1. the approved authentication/proof mechanism and algorithm profile;
2. issuer governance, enrollment, delegation, revocation, and compromise
   procedures;
3. production verification-material custody and rotation;
4. trusted production time;
5. atomic replay, spending, and approval state;
6. durable audit storage and service/runtime hardening;
7. implementation, conformance fixtures/tests, adversarial testing, deployment,
   operations, and independent security review; or
8. separate operator authorization for any later milestone.

Production proof architecture, Bitcoin confirmation/reorg policy and count,
and observer quorum/independence remain
`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`. Bitcoin remains external evidence
only and has zero L28 authority.

## 12. Protected Protocol and economic facts

This architecture preserves exactly:

| Invariant | Exact value |
|---|---:|
| Hard cap | `28000000` L28 |
| Emission ceiling | `11130000` L28 |
| Historically mined | `2824584` L28 |
| Treasury locked | `500000` L28 |
| Circulating snapshot | `2324584` L28 |
| Halving interval | `210000` |
| Reward schedule | `[28,14,7,3,1,0]` |
| Historical mined-through entry | `100877` |
| Next canonical height | `100878` |
| Issuance | coinbase only |
| Canonical height | consensus derived |
| Historical evidence | immutable |

No evidence issuer or verifier may alter or reinterpret these facts.

## 13. Non-activation conclusion

Foundation123 defines architecture only. This document creates no evidence
issuer/verifier runtime, credential, key, wallet, signer, signature, RPC or
network connection, transaction submission, broadcast, state mutation,
settlement, deployment, testnet, or production service.

Signer implementation, runtime, deployment, and activation remain blocked
until every applicable Foundation122 gate is satisfied by later authorized
work, verified, independently reviewed, and separately operator-authorized.
