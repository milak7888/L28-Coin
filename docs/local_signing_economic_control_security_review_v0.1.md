# Local Signing / Economic Control Security Gate Review v0.1

**Foundation:** 116
**Status:** SECURITY GATE REVIEW; DOCUMENTATION ONLY; NON-ACTIVATING
**Document version:** 0.1
**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)
**Review branch:** `foundation116-local-signing-economic-control-security-review`
**Required parent / reviewed HEAD:** `69a68d669994d7e3bbe37dd2e6b20403aedf2bd9`
**Runtime authority introduced:** none
**Signing, broadcast, settlement, wallet, key, RPC, or network behavior introduced:** none

---

## 1. Purpose and authority

This document reviews Foundations 111 through 115 as one local-signing and
economic-control conformance boundary. It is a repository security-gate review,
not a production security certification and not approval to implement or
activate a signer.

This review is subordinate to [L28 Protocol v1.0.0](../PROTOCOL.md). On conflict,
Protocol v1.0.0 prevails. L28 remains the sole settlement, consensus, issuance,
supply, canonical-height, validation, and historical-ledger authority.

The review makes no production-proof, Bitcoin-confirmation, observer-quorum,
key-custody, signer-runtime, or production-policy decision. It creates no
authority path and changes no protocol, economics, consensus, validation,
height, or history.

## 2. Reviewed evidence and commit lineage

### 2.1 Foundation lineage

The reviewed artifacts form this current-branch ancestry:

| Foundation | Commit | Reviewed artifact |
|---|---|---|
| F111 | `d1a472fb53b3546d5f0922b8a9e170a9375563fb` | `docs/local_signing_economic_control_architecture_review_v0.1.md` |
| F112 | `06ceb9a6654b674136828402444978e3c6099d39` | `docs/local_signing_economic_control_conformance_plan_v0.1.md` |
| F113 | `480ca852e0397bd6eb0cb82f95c837a7ac44993a` | `docs/local_signing_economic_control_fixture_spec_v0.1.md` |
| F114 | `009f34b7006f1a15afadc82888b4b0a737659631` | 56 JSON fixtures under `conformance/local_signing_economic_control/v0.1/fixtures/` |
| F115 | `69a68d669994d7e3bbe37dd2e6b20403aedf2bd9` | Four test files listed below |

F115's four reviewed test files are:

- `tests/local_signing_fixture_test_support.py`
- `tests/test_local_signing_economic_control_fixture_schema.py`
- `tests/test_local_signing_economic_control_fixture_profiles.py`
- `tests/test_local_signing_economic_control_fixture_security.py`

The F114 set contains exactly 56 fixtures in 12 families, classified POS 12,
NEG 19, BND 13, and FCL 12. Each fixture is evidence-only, deterministic,
offline, public/disposable, and non-executing.

### 2.2 Structural references only

The following Bitcoin documents were consulted for review structure, status
taxonomy, threat/gate presentation, and explicit non-activation boundaries:

- `docs/bitcoin_interoperability_threat_model_v0.1.md`
- `docs/bitcoin_security_gates_review_v0.1.md`

They do not grant L28 authority. Bitcoin remains external evidence only.

## 3. Security boundary under review

The F111-F115 boundary consists of:

1. an architecture review for a future isolated signer boundary;
2. a deterministic offline conformance plan;
3. a canonical fixture specification;
4. 56 public/disposable non-executing JSON fixtures; and
5. test-only schema, profile, digest, invariant, malformed-input, and static
   security checks.

There is no signer interface, signer implementation, wallet, key store, key
material, signing operation, broadcast operation, RPC connection, network
connection, settlement runtime, production policy engine, or production state
store in this boundary.

The intended future sequence remains:

`operator authorization` -> `economic authorization` -> mandatory
`coin.tx_validation.validate_transaction` -> isolated signing boundary

Authorization and validation are independent gates. Authorization cannot make
an invalid transaction valid. Validation cannot confer spending authority.
Passing both gates would still not authorize broadcast or settlement.

## 4. Finding taxonomy

Every formal finding in this review is listed in Section 5 and has exactly one
classification:

- `PASS`: the reviewed F111-F115 evidence preserves the stated boundary.
- `GAP_REQUIRES_FUTURE_WORK`: the boundary is correct but a separately
  authorized design, implementation, or verification artifact is absent.
- `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`: proceeding into the affected
  runtime or production scope requires an explicit future security decision.

These classifications describe repository evidence at the reviewed parent.
They do not claim live or production enforcement.

## 5. Consolidated findings

### 5.1 Preserved boundary findings

| ID | Security area | Evidence and determination | Classification |
|---|---|---|---|
| F116-P01 | Authority separation integrity | F111-F113 assign consensus, settlement, issuance, height, history, and validation exclusively to L28. Every F114 `authority_assertions` object keeps all override flags false, and F115 checks them across all 56 fixtures. | `PASS` |
| F116-P02 | Authorization versus validation | F111-F113 explicitly define authorization as distinct from validation. The AUT and VAL fixture families exercise their independent outcomes; F115 rejects profiles that collapse the two gates. | `PASS` |
| F116-P03 | Mandatory transaction validation | Every fixture requires delegation to `coin.tx_validation.validate_transaction`; accepted profiles require invoked/accepted evidence and rejected profiles fail closed. F115 verifies the assertion without importing or invoking production transaction validation. | `PASS` |
| F116-P04 | Key, wallet, and custody isolation | F111-F113 keep the future signer isolated and forbid keys or wallets in the conformance layer. F114 contains public/disposable placeholders only. F115 statically rejects secret, key, wallet, and signing behavior. This is isolation evidence, not a custody implementation. | `PASS` |
| F116-P05 | Signing, broadcast, and settlement non-activation | All 56 fixtures set `signing_attempted=false`, `signature_created=false`, and `broadcast_attempted=false`. The specifications and tests introduce no runtime or activation path. | `PASS` |
| F116-P06 | Spending limits and approval thresholds | LIM and APR POS/NEG/BND/FCL cases cover configured per-transaction and cumulative limits, boundary equality, missing/insufficient approvals, and fail-closed inputs with explicit expected codes and invariants. | `PASS` |
| F116-P07 | Replay, expiration, and operator-gate behavior | RPL, EXP, and OPR families cover first use, duplicate/replay, expiration boundaries, absent/malformed state, authorized operators, and missing/mismatched evidence. Their expected results fail closed deterministically. | `PASS` |
| F116-P08 | Receipt and audit evidence authority | AUD cases permit public audit/receipt evidence only and expressly deny consensus, settlement, validation, and issuance authority. Receipt/audit material cannot prove that live settlement occurred. | `PASS` |
| F116-P09 | Harness/Evals isolation | F111-F115 keep Harness/Evals advisory and removable. EXT fixtures reject advisory evidence used as authority; F115 verifies this separation. | `PASS` |
| F116-P10 | Bitcoin isolation | F111-F115 treat Bitcoin data as external evidence only. EXT fixtures reject Bitcoin evidence used as L28 authority; no Bitcoin proof creates L28 settlement or consensus authority. | `PASS` |
| F116-P11 | Protected economic facts | The specifications, fixtures, and tests preserve every protected fact listed in Section 6 exactly and keep every economic override flag false. | `PASS` |
| F116-P12 | Deterministic conformance coverage | The committed inventory is exactly 56 fixtures across 12 families with POS 12, NEG 19, BND 13, and FCL 12. F115 verifies IDs, mapping, property order, strict parsing, digests, malformed probes, family profiles, authority assertions, non-execution, and static security restrictions. | `PASS` |

### 5.2 Missing implementation and assurance findings

| ID | Security area | Missing evidence or capability | Classification |
|---|---|---|---|
| F116-G01 | Canonical signer-interface contract | No separately versioned signer request/response protocol, trust-boundary contract, authenticated caller model, or interface-level error contract has been designed. | `GAP_REQUIRES_FUTURE_WORK` |
| F116-G02 | Custody and key lifecycle | No approved custody architecture, key generation/import policy, storage boundary, rotation, revocation, backup/recovery, destruction, compromise response, or implementation verification exists. F111-F115 correctly avoid choosing one. | `GAP_REQUIRES_FUTURE_WORK` |
| F116-G03 | Policy, approval, and operator evidence authenticity | Fixtures model public evidence fields but do not define production identity, authentication, provenance, anti-forgery, revocation, or authorization-administration mechanisms for policies, approvals, or operator gates. | `GAP_REQUIRES_FUTURE_WORK` |
| F116-G04 | Atomic state enforcement | There is no production state model or atomic persistence/concurrency design for replay consumption, cumulative spending, approval use, idempotency, or crash recovery. | `GAP_REQUIRES_FUTURE_WORK` |
| F116-G05 | Expiration time authority | Fixtures use deterministic supplied time, but no trusted production clock source, clock-skew policy, rollback handling, or outage behavior is selected. | `GAP_REQUIRES_FUTURE_WORK` |
| F116-G06 | Receipt and audit durability | No production audit store, append/tamper evidence, retention, access control, redaction, recovery, receipt authenticity, or independent verification design exists. | `GAP_REQUIRES_FUTURE_WORK` |
| F116-G07 | Parser and service hardening | F115 covers deterministic malformed probes and forbidden imports/calls, but no production parser limits, resource bounds, denial-of-service controls, rate limits, process isolation, secure failure reporting, or observability design exists. | `GAP_REQUIRES_FUTURE_WORK` |
| F116-G08 | Runtime integration assurance | No production authorization evaluator, signer, validator adapter, end-to-end integration, adversarial runtime test, deployment boundary, operator runbook, or independent production security review exists. | `GAP_REQUIRES_FUTURE_WORK` |

### 5.3 Decisions that remain blocked

| ID | Affected scope | Required unresolved decision | Classification |
|---|---|---|---|
| F116-B01 | Any production Bitcoin-proof dependency | Select and approve the production proof architecture. F111-F115 do not choose or imply one. | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| F116-B02 | Any production Bitcoin-confirmation dependency | Select and approve the confirmation/reorg policy, including the confirmation count. F111-F115 do not choose or imply a count. | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| F116-B03 | Any production observer-dependent decision | Select and approve observer quorum, observer independence, disagreement handling, and fail-closed behavior. F111-F115 do not choose or imply a quorum. | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| F116-B04 | Signer implementation, runtime, or activation | No signer implementation or runtime may begin until the interface, custody, authenticated policy/operator evidence, atomic state, time authority, audit durability, service hardening, validation delegation, and independent review gates in Section 8 are explicitly decided, specified, verified, and separately authorized. | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |

### 5.4 Finding counts

| Classification | Count |
|---|---:|
| `PASS` | 12 |
| `GAP_REQUIRES_FUTURE_WORK` | 8 |
| `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` | 4 |
| **Total formal findings** | **24** |

## 6. Protected protocol and economic invariants

The reviewed boundary leaves the following facts exact and unchanged:

| Invariant | Preserved value |
|---|---:|
| Protocol | L28 Protocol v1.0.0 (FROZEN) |
| Hard cap | `28,000,000 L28` |
| Emission ceiling | `11,130,000 L28` |
| Historically mined | `2,824,584 L28` |
| Treasury locked | `500,000 L28` |
| Circulating snapshot | `2,324,584 L28` |
| Halving interval | `210,000` blocks |
| Reward schedule | `28 -> 14 -> 7 -> 3 -> 1 -> 0 L28` |
| Historical mined-through entry | `100,877` |
| Next canonical height after bootstrap | `100,878` |
| Issuance rule | coinbase only |
| Canonical height | consensus-derived only |
| Historical ledger/supply evidence | immutable and non-overridable |

No signer, policy, operator, Harness/Evals output, Bitcoin observation,
receipt, audit record, fixture, or test may override any value or rule in this
table.

## 7. Coverage interpretation and residual risk

F114-F115 establish deterministic conformance evidence for the specified
fixture contract. They do not establish that a production signer is secure,
that a key exists or is protected, that authorization state is durable, that a
clock is trustworthy, that an operator is authentic, that a receipt proves live
settlement, or that any transaction has been signed, broadcast, validated by a
live runtime, or settled.

The principal residual risks are the eight gaps in Section 5.2. In particular,
test-local recomputation and static checks cannot substitute for production
process isolation, authenticated evidence, atomic state, custody controls,
runtime adversarial testing, or an independent security assessment.

The three Bitcoin decisions in F116-B01 through F116-B03 remain exactly
`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`. This review does not resolve,
narrow, or provide defaults for them.

## 8. Explicit gates before future signer work

### 8.1 Gate for a signer-interface design milestone

A future signer-interface **design** milestone is eligible only when separately
authorized and bounded to documentation/specification. Its gate must require:

1. explicit operator authorization for that milestone and its exact file scope;
2. a versioned, deterministic interface contract with strict schemas, stable
   errors, canonical serialization, duplicate/unknown-field rejection, and
   fail-closed semantics;
3. preservation of authorization as distinct from validation;
4. mandatory delegation to `coin.tx_validation.validate_transaction`, with no
   bypass, replacement, or validation-authority transfer;
5. an interface that transports no private key, seed, credential, wallet file,
   or secret evidence;
6. explicit non-execution and non-activation constraints; and
7. no resolution-by-default of any blocked production security decision.

Passing this design gate would authorize design artifacts only. It would not
authorize keys, wallets, signing, RPC, networking, broadcast, settlement,
runtime code, dependencies, deployment, or activation.

### 8.2 Gates before signer implementation or runtime

Signer implementation, runtime integration, or activation remains blocked
until all of the following are separately decided, documented, reviewed,
tested, and operator-authorized:

1. the canonical signer-interface design and its versioning/compatibility
   policy;
2. custody and complete key-lifecycle architecture, including compromise and
   recovery handling;
3. authenticated, authorized, revocable policy, approval, and operator evidence;
4. atomic replay, spending-limit, approval-consumption, idempotency, concurrency,
   and crash-recovery state semantics;
5. trusted time, skew, rollback, and expiry-failure semantics;
6. durable, access-controlled, privacy-reviewed, tamper-evident audit/receipt
   evidence and retention semantics;
7. bounded parsing, resource and rate limits, process isolation, secure errors,
   monitoring, and operational failure handling;
8. executable proof that every sign-eligible transaction passed the canonical
   `coin.tx_validation.validate_transaction` path and that failure is closed;
9. runtime adversarial, fault-injection, recovery, and end-to-end conformance
   testing without weakening L28 authority;
10. independent security review of the production design and implementation;
11. explicit operator authorization for implementation and, separately, for
    any deployment or activation; and
12. for any Bitcoin-dependent production path, prior resolution of F116-B01,
    F116-B02, and F116-B03.

These are gates, not selected architectures or implementation instructions.

## 9. Eligibility conclusion

**Future signer-interface work is eligible for a later, separately authorized
design milestone only**, subject to Section 8.1. The F111-F115 boundary is
coherent enough to design that non-executing interface without changing L28
Protocol v1.0.0 or activating signing.

Future signer **implementation, runtime integration, deployment, or activation
is blocked** pending the named unresolved security decisions and completed gates
in Sections 5.2, 5.3, and 8.2. In particular, this review does not approve a
custody implementation, production proof architecture, Bitcoin confirmation
count, observer quorum, production policy, signer runtime, or settlement path.

## 10. Validation record

At reviewed parent `69a68d669994d7e3bbe37dd2e6b20403aedf2bd9`:

- Foundation lineage F111-F115 is present in order.
- All exact F111-F115 artifact paths listed in Section 2 are present.
- The F114 inventory is exactly 56 fixtures / 12 families / POS 12 / NEG 19 /
  BND 13 / FCL 12.
- Foundation115 isolated fixture conformance tests: `41 passed`.
- Existing isolated 10-module Bitcoin fixture suite: `224 passed`.
- Protected economics match Section 6 exactly.
- No implementation, runtime, activation, or live-settlement claim is made.
- No finding changes or contradicts L28 Protocol v1.0.0.

## 11. Document control

Foundation116 adds this review document only. It does not modify F111-F115,
fixtures, tests, code, dependencies, protocol, economics, consensus, validation,
height, history, keys, wallets, runtime, networking, RPC, broadcast, settlement,
deployment, or production state.

This document ends Foundation116. Foundation117 is not authorized or started.
