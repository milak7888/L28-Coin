# Local Signer Key Custody and Lifecycle Architecture v0.1

**Foundation:** 123

**Workstream:** 2 of 4 — F122-G02

**Status:** ARCHITECTURE DEFINED; DESIGN ONLY; NON-ACTIVATING

**Document version:** `local-signer-key-custody-lifecycle-architecture/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Required parent:** `a66f02f224577dca090ac99f4182dade2a2160f1`

**Key material or key operation performed:** none

**Runtime authorization:** none

---

## 1. Purpose and scope

This document addresses Foundation122 finding F122-G02 at the architecture
level. It defines requirements for a possible future isolated local signer key
custody and lifecycle boundary.

This is design only. It generates, imports, reads, derives, stores, backs up,
recovers, rotates, revokes, destroys, or uses no key. It creates no wallet,
signature, signer runtime, RPC/network connection, submission, broadcast,
settlement, deployment, or production service.

This architecture is subordinate to [L28 Protocol v1.0.0](../PROTOCOL.md),
Foundation117, Foundation122, and
`authenticated_signer_evidence_architecture_v0.1.md`. On conflict, Protocol
v1.0.0 prevails.

## 2. Fixed authority separation

1. L28 remains the sole issuance, supply, canonical-height, validation,
   consensus, historical-ledger, and native-settlement authority.
2. `coin.tx_validation.validate_transaction` remains mandatory before signer
   eligibility. Possession or use of a key cannot validate a transaction.
3. Authorization is not Protocol validation.
4. Signer eligibility is not signer invocation.
5. A signature, if a future separately authorized system ever creates one,
   cannot create issuance, change supply/height/history, establish consensus,
   submit or broadcast itself, or prove settlement.
6. Custody operators cannot approve spending policy, validate transactions, or
   unilaterally authorize invocation. Policy/operator decision authority and
   custody authority must remain separated.

Missing, unavailable, stale, revoked, compromised, ambiguous, or contradictory
custody evidence fails closed.

## 3. Future custody boundary

The future boundary must isolate four roles:

| Role | Permitted responsibility | Prohibited responsibility |
|---|---|---|
| Custody security administrator | Govern approved security profiles and lifecycle procedures | Cannot approve individual spend or invoke signing |
| Custody operator | Perform separately authorized lifecycle ceremonies under required separation and audit | Cannot alter policy, Protocol validation, economics, or settlement |
| Signer invocation controller | Present an already eligible, exactly bound request to the isolated signer edge | Cannot access/export key material or bypass custody state |
| Independent reviewer/auditor | Verify public custody-control evidence and lifecycle records | Cannot operate keys, approve spend, or become L28 authority |

No single role may combine policy approval, operator authorization, custody
administration, and signer invocation authority. Any future role combination
or emergency exception requires an explicit security decision, constrained
scope, independent review, and separate operator authorization.

## 4. Approved algorithm and material policy

A future versioned custody security profile must define an explicit allowlist
for permitted algorithms, parameters, public-key encodings, key origins,
hardware/software isolation classes, usage constraints, and deprecation state.

The profile must:

1. reject unknown, deprecated, weak, ambiguous, or unapproved algorithms and
   material;
2. prohibit algorithm negotiation, downgrade, caller-selected parameters, and
   silent conversion;
3. bind every public key identifier to one exact profile, origin, lifecycle
   state, and permitted use;
4. distinguish transaction-signing material from audit/authentication material;
5. prohibit private material in interface requests, responses, logs, fixtures,
   prompts, adapters, environment variables, or public audit output; and
6. require independent approval and migration planning before profile changes.

This document selects no algorithm, curve, key size, hardware product, wallet
format, derivation method, key origin, or migration schedule.

## 5. Generation and import policy

Future production policy must explicitly choose whether generation, import, or
both are permitted for each custody profile. There is no default.

### 5.1 Generation requirements

If future generation is authorized, it must occur entirely inside the approved
isolated custody boundary using an approved entropy source and ceremony. Raw
private material must not leave the boundary. Generation must produce only the
minimum public identifiers and attestation/audit references permitted by the
profile.

### 5.2 Import requirements

If future import is authorized, its source, transport, authorization,
attestation, duplicate detection, quarantine, validation, and destruction of
transient material must be explicitly specified and independently reviewed.
Unverifiable origin, ambiguous encoding, duplicate identity, unapproved
material, or incomplete ceremony evidence fails closed.

### 5.3 No implied permission

Approval of generation does not approve import, and approval of import does not
approve generation. Neither approves signer invocation. Foundation123 performs
neither operation.

## 6. Isolation and access control

The future custody boundary must enforce:

- private material non-exportability under normal and recovery operation;
- process and privilege separation from API, policy, validation, adapter,
  network, broadcast, ledger, and audit-query components;
- authenticated, least-privilege, purpose-bound access;
- separation of lifecycle administration from transaction authorization;
- an approved threshold or multi-party control for sensitive ceremonies,
  without a threshold value being selected here;
- explicit operation, key identifier, policy version, request digest, and
  validity-window binding;
- denial of interactive or general-purpose access paths not required by the
  approved profile;
- complete, tamper-evident lifecycle audit evidence; and
- fail-closed behavior on identity, authorization, state, time, isolation, or
  audit dependency failure.

The isolated boundary must receive no caller-controlled key path, wallet path,
provider locator, algorithm choice, command, plugin, or arbitrary payload.

## 7. Lifecycle state model

The architecture defines these logical states without implementing them:

`UNINITIALIZED` -> `PROVISIONED_INACTIVE` -> `ACTIVE` -> `ROTATING` ->
`REVOKED` -> `DESTROYED`

`QUARANTINED` and `COMPROMISED` are fail-closed states reachable from any
state where integrity, provenance, isolation, authorization, or audit evidence
is uncertain.

Rules:

1. only an exact, authorized, audited transition is valid;
2. absent or contradictory state is not `ACTIVE`;
3. `PROVISIONED_INACTIVE` material cannot sign;
4. `ROTATING` must define which generation is eligible for new requests and
   how in-flight requests fail or bind, without dual uncontrolled authority;
5. `REVOKED`, `QUARANTINED`, `COMPROMISED`, and `DESTROYED` cannot sign;
6. rollback to an earlier active state is forbidden;
7. lifecycle state and policy version must be atomically visible to invocation
   control; and
8. recovery creates an explicitly authorized state transition, never silent
   reactivation.

Exact transition protocols and runtime codes require later specifications and
conformance work.

## 8. Rotation and revocation

### 8.1 Rotation

Rotation must bind old and new public key identifiers, approved profiles,
activation/deactivation boundaries, pending-request treatment, audit lineage,
and operator approvals. New material remains inactive until all required
evidence is complete. Old material must not remain eligible beyond its approved
transition boundary.

No caller, policy object, adapter, or network event may trigger unreviewed
rotation. Rotation cannot repair an otherwise invalid or unauthorized
transaction.

### 8.2 Revocation

Revocation must be monotonic, promptly visible to eligibility and invocation
control, and durable across restart/recovery. Revoked material cannot be
reactivated. A replacement requires a new lifecycle identity and ceremony.

Unavailable or stale revocation state blocks signer eligibility/invocation. A
future emergency-revocation path must be separately authorized, independently
reviewed, and unable to create spending or validation authority.

## 9. Backup and recovery

Backup is permitted only if an approved future profile explicitly requires it.
That profile must define non-exportability or protected export, authorization,
separation of duties, inventory, geographic/administrative separation,
confidentiality, integrity, availability, version binding, retention,
destruction, and recovery testing.

Recovery must:

1. occur inside an approved isolated boundary;
2. require authenticated and independently authorized ceremony evidence;
3. verify exact backup identity, profile, integrity, provenance, lifecycle
   state, and revocation status;
4. prevent restoration of revoked, superseded, compromised, or destroyed
   material;
5. create durable, tamper-evident audit evidence; and
6. leave the key inactive until post-recovery verification completes.

Missing or contradictory backup/recovery evidence fails closed. This document
selects no backup mechanism, escrow design, recovery quorum, or storage system.

## 10. Destruction

Future destruction policy must define the approved sanitization method for each
material/isolation class, all copies and backups in scope, verification,
inventory reconciliation, audit evidence, and treatment of failed or
unverifiable destruction.

Destruction is a monotonic lifecycle transition. Unverified destruction leaves
the material `QUARANTINED` or `COMPROMISED`, not safely destroyed. Public audit
output may state verified status and public identifiers only; it must not
expose material or sensitive infrastructure detail.

## 11. Compromise response

Suspected compromise must immediately fail closed for new eligibility and
invocation decisions. The future response plan must cover:

- quarantine and revocation;
- prevention of in-flight and queued use;
- independent incident authority and custody-operator separation;
- inventory and affected public-key identification;
- evidence preservation and tamper-evident incident audit;
- notification and operational containment;
- replacement under a new lifecycle identity;
- recovery without reactivating compromised material; and
- post-incident independent review before any later activation.

Compromise response cannot rewrite L28 history, reverse consensus, modify
supply, declare settlement, or bypass normal Protocol validation.

## 12. Custody verification and public evidence

A future verifier may consume public custody-control evidence proving only:

- public key identifier and approved profile;
- current lifecycle state and state version;
- public origin/attestation reference;
- isolation/control profile identifier;
- rotation/revocation status and freshness;
- last approved verification and independent-review references; and
- exact request/key/profile binding at the signer edge.

The authenticity mechanism for custody evidence remains future security work.
Custody evidence must contain no private material, seed, mnemonic, xprv,
keystore, wallet secret, credential, recovery material, host path, or locator.

Custody verification is not transaction validation, authorization, a signature,
submission, broadcast, settlement, or proof that signing occurred.

## 13. Dependencies and remaining gates

This architecture leaves unresolved:

1. algorithm/material and isolation profile selection;
2. generation/import permission and ceremony details;
3. custody technology and deployment architecture;
4. access-control and multi-party mechanism, including any threshold;
5. backup/recovery and destruction mechanisms;
6. authenticated custody evidence and issuer governance;
7. atomic lifecycle/revocation state and trusted time;
8. durable audit implementation and runtime/service hardening;
9. implementation, conformance, adversarial/fault/recovery tests, operations,
   and independent security review; and
10. separate operator authorization for every later lifecycle or runtime
    milestone.

Production proof architecture, Bitcoin confirmation/reorg policy and count,
and observer quorum/independence remain
`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`. No value or design is selected.

## 14. Protected Protocol and economic facts

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

Custody and any future signature have zero authority to change these facts.

## 15. Non-activation conclusion

Foundation123 performs no key or wallet operation. This document implements no
custody boundary, signer, signature, RPC/network connection, submission,
broadcast, state mutation, settlement, deployment, testnet, or production
service.

Signer implementation and every lifecycle/runtime operation remain blocked
until later authorized specifications, implementation, verification,
independent review, and separate operator authorization satisfy all applicable
Foundation122 gates.
