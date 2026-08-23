# Local Signing / Economic Control Architecture Review v0.1

**Foundation:** 111

**Status:** local signing/economic control architecture review / non-activating

**Document version:** `local-signing-economic-control-architecture-review/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Parent:** `6c5e6d6c9dec73ee8864698b165394dda4141d33`

**Branch:** `foundation111-local-signing-economic-control-architecture-review`

**Implementation:** none

**Runtime activation:** none

**Network activity:** none

**Wallet / signing activity:** none

**Existing files modified:** none

**Normative subordination:** This document is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md). On conflict, Protocol v1.0.0 prevails.
It is also subordinate to Universal Access Interface v0.1
(`docs/universal_access_interface_v0.1.md`) for public operations,
Foundations 64+ for the isolated local-signer **design** boundary (not
activated here), Foundations 107–110 for adapter / UAII / Harness
boundaries, and Foundations 93/105–106 for Bitcoin external-evidence and
remaining security gates. This document MUST NOT generate keys, create or
import wallets, sign or broadcast transactions, implement signer runtime,
or change Protocol v1.0.0, `validate_transaction`, issuance, supply,
history, or height.

**Related locked contracts (consumed, not replaced):**

- `PROTOCOL.md` — sole native settlement and issuance authority
- `docs/universal_access_interface_v0.1.md` — canonical public access interface
- `docs/universal_access_adapter_boundary_review_v0.1.md` — adapters cannot create authority
- `docs/uaii_canonical_interface_preservation_review_v0.1.md` — UAII preservation
- `docs/adapter_exposure_specification_review_v0.1.md` — transport-only adapters
- `docs/harness_evals_commerce_specification_review_v0.1.md` — advisory evidence only
- `docs/bitcoin_security_gates_review_v0.1.md` — custody/signing remains a future governed milestone
- `coin/tx_validation.py` — sole transfer/coinbase validation authority

---

## 1. Status

Foundation 111 documents **future local signing and economic-control
architecture boundaries** without implementing signing.

This document is **documentation only**. It is a **local signing / economic
control architecture review**. It is **non-activating**. It uses **no
keys**, **no wallets**, and **no runtime**.

| Statement | Status |
|---|---|
| Foundation | 111 |
| Kind | Local signing / economic control architecture review |
| Activation | none |
| Protocol v1.0.0 | FROZEN |
| L28 role | **Settlement authority remains L28.** A signer does not settle. |

Documenting a future isolated signer is not permission to generate keys,
import wallets, sign, broadcast, or treat policy approval as
`validate_transaction` success. Absence of a later authorized milestone is
a **block**, not a default-allow.

---

## 2. Signing authority boundary

Signing is **separate** from observation and evaluation.

| Authority | Role | This Foundation |
|---|---|---|
| Bitcoin / external observation | Labeled external evidence at most | Not a signer |
| Harness/Evals | Advisory evidence reports | Not a signer |
| Isolated local signer | Future home of L28 signing material, if authorized | Specified only; **not implemented** |
| `validate_transaction` | Sole L28 transfer/coinbase validator | Unchanged |
| Protocol v1.0.0 | Settlement, issuance, height, history | Unchanged |

A signer **cannot** become consensus authority. A signature is not
canonical height and not a coinbase.

A signer **cannot** bypass `validate_transaction`. A locally signed
payload that fails Protocol validation MUST fail closed.

Signer architecture **requires future authorization**. Foundation 64+
records an isolated local-signer **design** boundary. Foundations 105–106
leave production custody/signing as a **future governed milestone**. This
review does not open that milestone.

An observation adapter or evaluation engine that can sign or broadcast is
a custody and activation failure.

---

## 3. Key custody boundary

The following MUST remain isolated from public interfaces, if a later
signer is ever authorized:

| Material | Isolation rule |
|---|---|
| Private keys | Local signer boundary only |
| Seeds | Local signer boundary only |
| Mnemonics | Local signer boundary only |
| Wallet secrets | Local signer boundary only |
| Credentials (including Bitcoin RPC credentials) | Never public; never adapter-held |

Rules:

- Secrets **never** enter adapters (MCP, REST/OpenAPI, Python/TypeScript
  SDK).
- Secrets **never** enter Harness/Evals (reports, evaluation inputs, or
  scores).
- Secrets **never** enter logs, prompts, UAII params, APIs, receipts, or
  hosted models.
- Secrets **never** enter Bitcoin evidence paths (observers, proof
  objects, explorer-style attestations).

Only public keys, public key ids, signatures, digests, and public
identities MAY cross process boundaries. This Foundation does not create,
import, store, or display any of those secret classes. Conformance markers
from Bitcoin `SEC` fixtures remain disposable field names, not keys.

---

## 4. Transaction authorization model

Future controls, if later authorized, MAY include the following **public
policy** concepts. They are not implemented here.

| Control | Future meaning | Must not imply |
|---|---|---|
| Transaction intent | Declared public intent to propose an L28 transfer | Settlement, mint, or broadcast |
| Authorization checks | Local policy gates before a **later** isolated sign step | `validate_transaction` success |
| Policy evaluation | Limits, expiry, replay, and operator rules applied to public intent | Consensus override |
| Approval requirements | Required public approvals or thresholds | Implicit spend grant |
| Audit records | Public evidence that a policy check ran | L28 historical rewrite |

**Authorization is not validation.**

Local authorization answers: “Does this isolated signer’s operator policy
allow *attempting* a later signature on this public intent?”

`validate_transaction` remains **L28 authority** for transfer and
coinbase correctness. A policy allow MUST still fail closed if Protocol
validation fails. Simulated or demo approvals are not payment, settlement,
or spend authorization.

`execution_authorized`, `spend_authorized`, and `signing_authorized`
remain false on UAII v0.1 paths unless a later Protocol-authorized
interface exists (none in this Foundation).

---

## 5. Economic controls

Future **safety** controls, if later authorized, MAY include:

| Control | Role |
|---|---|
| Spending limits | Informational or local-policy caps (`max_amount`, per-transaction, cumulative) |
| Rate limits | Local attempt throttling |
| Expiration | Caller-supplied `expires_at` / quote / payment expiry only; no system-clock authority |
| Replay protection | Fail closed on reused public receipt/request ids |
| Operator approvals | Extra local human/operator gates |
| Emergency controls | Local halt of **signing attempts** only |

Rules:

- Controls **cannot** change consensus.
- Controls **cannot** mint L28 or open a non-coinbase issuance path.
- Controls **cannot** alter supply (hard cap 28,000,000 L28; emission
  ceiling 11,130,000 L28; historically mined 2,824,584 L28; treasury
  locked 500,000 L28; circulating snapshot 2,324,584 L28; halving
  interval 210,000; reward sequence 28 → 14 → 7 → 3 → 1 → 0).

Emergency stop of a signer is not a Protocol hard-fork, not a supply
rewrite, and not a substitute for missing canonical height. Height
authority remains consensus-derived. Historical mined-through entry
remains 100,877. Next canonical height after bootstrap remains 100,878.

---

## 6. Receipt and audit boundary

| Artifact | Future role | Must not do |
|---|---|---|
| Authorization records | Public evidence that local policy ran | Authorize ledger mutation by themselves |
| Transaction receipts | UAII receipt / verification objects after **independent** L28 settlement | Replace `validate_transaction` |
| Audit history | Operator-visible trail of intents and policy outcomes | Rewrite L28 history |

**Audit records are evidence.** They are not L28 consensus and not
historical-ledger mutation.

Audit records **cannot rewrite L28 history**. Protocol historical
evidence remains immutable. Evaluation history and signer audit logs are
different domains from historically mined supply and genesis/hash/snapshot
evidence.

---

## 7. UAII boundary

UAII v0.1, profile `l28-universal-ai-access-interface/v0.1`, exposes
**canonical public operations**: capability discovery, balances, quotes,
unsigned payment requests, validation responses, and receipts.

Signing is **not** a default UAII authority. Signing, broadcast, and
autonomous spend remain **forbidden** as UAII v0.1 operations.

Signing requires **separately governed interfaces** (a later profile or
implementation foundation). It MUST NOT be smuggled into
`discover_capabilities` as a supported native v0.1 sign operation.

Adapters remain transport only. They MUST NOT become signers.

---

## 8. Harness / Evals boundary

Harness/Evals MAY provide advisory evidence reports.

Harness/Evals **cannot** sign.

Harness/Evals **cannot** authorize settlement.

Harness/Evals **cannot** control keys.

A high evaluation score MUST NOT unlock signing, raise spending limits as
Protocol truth, or set `l28_issuance_authorized`. Scores cannot affect
consensus (Foundation 110).

---

## 9. Bitcoin boundary

Bitcoin evidence remains **external**. It is not native L28.

Bitcoin interoperability does **not** provide signing authority.

| Forbidden implication | Status |
|---|---|
| Bitcoin observation adapter signs L28 or BTC | Forbidden |
| Bitcoin height authorizes an L28 signature | Forbidden |
| Confirmations replace `validate_transaction` | Forbidden |
| RPC credentials held by a UAII adapter | Forbidden |
| Production proof / confirmation / quorum chosen here | Forbidden; remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |

A future Bitcoin isolated signer, if ever considered, is a **separate**
custody decision from L28 local signing and from observation. This
Foundation implements neither.

---

## 10. Security gates

| Gate | Status |
|---|---|
| Future signer architecture | **Not implemented.** Later governed milestone. |
| Operator authorization | **Required** before any signer runtime; not this document. |
| Independent security review | **Required** before any signer runtime; not this document. |

Foundation 106 already records custody/signing as a future governed
milestone and independent security review plus operator authorization as
required. This review **does not satisfy** those gates.

Missing any gate fails closed. Documentation of architecture is not a
signer.

---

## 11. Non-goals

Foundation 111 MUST NOT and does not:

- generate keys
- create wallets
- import wallets
- sign
- broadcast
- use Bitcoin or other RPC
- activate runtime
- implement signer runtime
- change Protocol v1.0.0
- change `validate_transaction`
- change issuance, supply, history, or height

---

## 12. Document control

| Field | Value |
|---|---|
| Foundation | 111 |
| Parent | `6c5e6d6c9dec73ee8864698b165394dda4141d33` |
| Path | `docs/local_signing_economic_control_architecture_review_v0.1.md` |
| Status | local signing/economic control architecture review / non-activating |
| Implementation | none |
| Runtime activation | none |
| Network activity | none |
| Key generation | none |
| Wallet creation / import | none |
| Signing activity | none |
| Broadcast activity | none |
| Existing files modified | none |
| Protocol v1.0.0 | unchanged |
| `validate_transaction` | unchanged |
| Issuance / supply / history / height | unchanged |
| UAII v0.1 sign operations added | none |
| Bitcoin runtime activation | none |
| Custody / signing architecture | future governed milestone; not implemented |
