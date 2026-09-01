# Authenticated Signer Evidence Conformance Plan v0.1

Status: `DEFINED_PLAN_ONLY`

Foundation: 125, workstream 2

Source profile: `l28-authenticated-signer-evidence/v0.1`

Addresses: F122-G01 and decisions `LSOD-EVD-001` through `LSOD-EVD-010`

## 1. Scope

This document plans deterministic future conformance for authenticated caller, operator, economic-policy, local-authorization, and approval evidence. It creates no fixture, schema file, test, proof, credential, issuer, verifier, key, wallet, signer, signature, runtime, network, RPC, broadcast, or settlement behavior.

The plan is subordinate to L28 Protocol v1.0.0 and the Foundation124 authenticated-evidence profile. `coin.tx_validation.validate_transaction` remains canonical and mandatory. Authorization is not Protocol validation. Evidence eligibility is not signer invocation. Every test outcome must preserve zero execution and every L28 authority override false.

All production mechanisms and values named by `LSOD-EVD-001` through `010` remain `OPERATOR_DECISION_REQUIRED`. Parameterized tests may use documented fictional values but cannot promote those values into production policy.

## 2. Deterministic test model

Future cases use public/disposable, fictional identities and fixed integer time. They read no environment, clock, credential, wallet, keychain, HSM/KMS, service, RPC, or network state. Canonical input is immutable UTF-8 JSON with exact property order, no duplicate/unknown fields, exact ordered arrays, integer-only times/amounts, and domain-separated digests as later specified consistently with Foundation117.

Case-family IDs are immutable:

- `ASE-POS-NN`: complete accepted evidence-profile inputs;
- `ASE-NEG-NN`: one explicit invalid condition with otherwise coherent input;
- `ASE-BND-NN`: exact semantic or size/time/threshold boundary;
- `ASE-FCL-NN`: missing, unavailable, undecided, corrupt, or contradictory required authority/state.

These are planned family IDs, not fixture IDs or runtime codes. A later fixture specification may expand each family into stable cases only after its required operator decisions are approved. Expansion must retain the family ID and exact expected invariant.

Expected outcomes are:

- POS: `PROFILE_CONFORMANT_INPUT`; contributes evidence to eligibility evaluation only and performs no invocation.
- NEG: deterministic rejection at the earliest applicable Foundation117/profile gate.
- BND: the exact specified side of the boundary passes or rejects; equality rules remain explicit.
- FCL: fail closed with the applicable existing Foundation117 unavailable/security-decision status and no fallback.

No outcome means authenticated production evidence, transaction validity, signing authorization, signature creation, receipt, or settlement.

## 3. Planned family inventory

### 3.1 Positive families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `ASE-POS-01` | Exact profile/version, top-level and nested order, public-only fields | Profile-conformant input | No unknown/default/secret data; digest input is canonical |
| `ASE-POS-02` | Caller identity evidence bound to caller/request/audience | Profile-conformant input | Identity proves only the exact caller and scope |
| `ASE-POS-03` | Operator authorization bound to request/intent/policy/parties/amount | Profile-conformant input | Operator authority is scoped and does not validate or invoke |
| `ASE-POS-04` | Economic-policy and local-authorization evidence share exact active policy version/digest | Profile-conformant input | No version inference, merge, or downgrade |
| `ASE-POS-05` | Approval identities, roles, ordered sequence, threshold set, scope | Profile-conformant input | Each distinct approver counts at most once; authorization only |
| `ASE-POS-06` | Complete authenticated issuer provenance/delegation chain | Profile-conformant input | Authority never exceeds the narrowest authenticated link |
| `ASE-POS-07` | Current authenticated revocation state and verification-material lifecycle | Profile-conformant input | Every required subject is explicitly not revoked under fresh state |
| `ASE-POS-08` | Not-before, expiry, evidence lifetime, trusted-time uncertainty | Profile-conformant input | `now >= not_before` and `now < expires_at` under approved parameters |
| `ASE-POS-09` | Nonce/idempotency/evidence/request/intent/policy binding and fresh replay state | Profile-conformant input | Exact single-use state is available and unconsumed |
| `ASE-POS-10` | Minimal deterministic public audit projection | Profile-conformant input | Projection reveals no proof/credential/secret and claims no settlement |
| `ASE-POS-11` | Authorization passes and canonical validation binding is accepted | Eligible evidence sequence only | Authorization and validation are separately represented and both required |
| `ASE-POS-12` | Exact idempotent duplicate of previously committed public result | Return exact prior public result | No state re-consumption and no signer invocation |

### 3.2 Negative families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `ASE-NEG-01` | Unknown profile/version/evidence type/property | Reject at schema/profile gate | No compatibility inference or ignored field |
| `ASE-NEG-02` | Duplicate property, reordered property, malformed UTF-8, float/null | Reject at canonicalization gate | No repair or coercion |
| `ASE-NEG-03` | Secret, credential, private-key locator, wallet locator, or raw proof secret | Reject at public-only gate | Sensitive input is never projected or logged |
| `ASE-NEG-04` | Invalid/forged/mismatched proof or canonical proof input | Reject at proof-authentication gate | No alternate proof or downgrade |
| `ASE-NEG-05` | Unknown, unauthorized, wrong-scope, or compromised issuer | Reject at issuer-authority gate | Possession or transport source is not authority |
| `ASE-NEG-06` | Circular, incomplete, overbroad, cross-profile, or reassociated delegation | Reject at provenance gate | Delegation cannot expand authority |
| `ASE-NEG-07` | Revoked issuer/material/subject/evidence/policy | Reject at revocation gate | Revoked status is monotonic and cannot be repaired |
| `ASE-NEG-08` | Not yet valid, expired, stale, or excessive time uncertainty | Reject at freshness gate | Time failure cannot be bypassed by other evidence |
| `ASE-NEG-09` | Wrong verifier, audience, request, intent, identity, party, asset, amount, or transaction digest | Reject at exact-binding gate | No partial match, normalization, or reassociation |
| `ASE-NEG-10` | Inactive/superseded/unknown policy version or digest mismatch | Reject at policy gate | Caller cannot select or revive a policy |
| `ASE-NEG-11` | Duplicate approval/approver, invalid role, wrong scope/order, or insufficient threshold | Reject at approval gate | Duplicate identities add no authority |
| `ASE-NEG-12` | Consumed nonce/evidence, conflicting idempotency binding, or cross-domain replay | Reject at replay gate | Validation/authorization history does not excuse replay |
| `ASE-NEG-13` | Local authorization rejected while Protocol validation accepted | Ineligible at authorization gate | Validation acceptance grants no spending authority |
| `ASE-NEG-14` | Local authorization accepted while Protocol validation rejected | Ineligible at validation gate | Authorization cannot make an invalid transaction valid |
| `ASE-NEG-15` | Evidence or response claims signer invocation/signature/broadcast/settlement | Reject at authority/non-execution gate | Eligibility never implies execution |
| `ASE-NEG-16` | Audit projection contains extra private/internal field or false authority claim | Reject audit projection | Public projection remains minimal and advisory |

### 3.3 Boundary families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `ASE-BND-01` | Exact supported profile/version versus adjacent unsupported version | Exact version passes; adjacent rejects | Compatibility is explicit, not negotiated |
| `ASE-BND-02` | Proof/canonical input at approved maximum and one unit beyond | Maximum follows policy; beyond rejects | Parameter comes from `LSOD-EVD-001`, never a fixture default |
| `ASE-BND-03` | Delegation depth at approved maximum and one beyond | Maximum follows policy; beyond rejects | No inferred unlimited chain |
| `ASE-BND-04` | `now == not_before` and immediately before | Equality passes; before rejects | Integer trusted-time semantics exact |
| `ASE-BND-05` | `now == expires_at` and immediately before | Equality rejects; immediately before may pass | Expiry is strict |
| `ASE-BND-06` | Freshness/revocation-cache age at approved maximum and one beyond | Exact rule follows approved decision; beyond rejects | No hidden grace interval |
| `ASE-BND-07` | Approval count immediately below, exactly at, and above approved threshold | Below rejects; exact/above follow policy without duplicate counting | Threshold value remains parameterized by `LSOD-EVD-007` |
| `ASE-BND-08` | Policy activation/supersession transition instant | Exactly one policy state is authoritative | No overlap ambiguity or rollback |
| `ASE-BND-09` | Replay/retention expiration boundary | Consumed identity never becomes silently fresh | Retention remains parameterized by `LSOD-EVD-008` |
| `ASE-BND-10` | Public projection at allowed disclosure boundary | Allowlisted fields only | No extra field or secret leakage |

### 3.4 Fail-closed families

| Family ID | Input focus | Expected outcome | Required invariant |
|---|---|---|---|
| `ASE-FCL-01` | Required proof decision `LSOD-EVD-001` unresolved | Security-decision-required rejection | No placeholder proof becomes production valid |
| `ASE-FCL-02` | Issuer registry/trust root unavailable or contradictory | Unavailable rejection | No fallback issuer or trust-on-first-use |
| `ASE-FCL-03` | Verifier identity/material state unavailable | Unavailable rejection | No alternate verifier |
| `ASE-FCL-04` | Revocation source unavailable/stale/conflicting | Unavailable rejection | Outage never means not revoked |
| `ASE-FCL-05` | Trusted time unavailable/rollback affected | Unavailable rejection | Caller/system timestamps are not fallback authority |
| `ASE-FCL-06` | Policy resolver unavailable or multiple active versions | Unavailable/contradictory rejection | No version selection by caller |
| `ASE-FCL-07` | Replay/approval-consumption state unavailable or uncertain | Unavailable rejection | No assumption of freshness or non-consumption |
| `ASE-FCL-08` | Durable audit requirement unavailable | Unavailable rejection | No eligibility result before required audit intent/evidence |
| `ASE-FCL-09` | Canonical validation binding missing/rejected/pending/unavailable | Validation rejection | Evidence verifier never invokes or substitutes validation |
| `ASE-FCL-10` | Multiple simultaneous failures | First applicable Foundation117 failure only | Later failure never masks or repairs earlier failure |

## 4. Precedence and deterministic mutation requirements

Each NEG/BND/FCL case starts from one coherent POS baseline and applies one test-local disposable mutation. The expected earliest gate follows the Foundation124 sequence: schema/public-only; proof/provenance; issuer; revocation; trusted time; exact bindings; replay; audit; authorization; canonical validation; eligibility. Multi-failure cases intentionally mutate a later and an earlier gate to prove the earlier result wins.

Tests must independently derive canonical bytes and digests. They may not call a production verifier, signer, wallet, network, RPC, broadcast, settlement, environment, or clock. Static/AST-aware checks must distinguish prohibited executable behavior from literal negative-fixture data.

## 5. Acceptance and traceability

A future materialization is incomplete unless every family maps to one or more immutable case IDs, each applicable `LSOD-EVD-*` decision maps to positive, negative, boundary, and fail-closed evidence, stable Foundation117 status/code precedence is preserved, and all authority/non-execution assertions are exact.

Passing this plan would prove only deterministic evidence-profile conformance. It would not authenticate a production actor, invoke `coin.tx_validation.validate_transaction`, authorize signing, create a signature, or activate a runtime.

## 6. Protocol and economic invariants

Preserved exactly: hard cap `28000000`; emission ceiling `11130000`; historically mined `2824584`; treasury locked `500000`; circulating snapshot `2324584`; halving interval `210000`; reward schedule `[28,14,7,3,1,0]`; historical mined-through entry `100877`; next canonical height `100878`; coinbase-only issuance; consensus-derived canonical height; immutable historical evidence.

Bitcoin remains external evidence only. Production Bitcoin proof architecture, Bitcoin confirmation/reorg policy and count, observer quorum/independence, and signer implementation/runtime/deployment/activation remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

Foundation125 authorizes no implementation or activation.
