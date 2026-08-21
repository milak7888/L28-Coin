# Universal Access / Adapter Boundary Review v0.1

**Foundation:** 107

**Status:** interface-boundary review / non-activating

**Document version:** `universal-access-adapter-boundary-review/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Parent:** `ca77cd63e022d6176ae17399ed3eae3041da5f4a`

**Branch:** `foundation107-universal-access-adapter-boundary-review`

**Implementation:** none

**Runtime activation:** none

**Network activity:** none

**Wallet / signing activity:** none

**Existing files modified:** none

**Normative subordination:** This document is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md). On conflict, Protocol v1.0.0 prevails.
It is also subordinate to Universal Access Interface v0.1
(`docs/universal_access_interface_v0.1.md`) for public interface field names
and operations, to Foundation 93 for Bitcoin adapter identity, and to
Foundations 105–106 for remaining Bitcoin security gates. It MUST NOT
redefine settlement, issuance, supply, consensus height authority,
historical evidence, or `validate_transaction`.

**Related locked contracts (consumed, not replaced):**

- `PROTOCOL.md` — sole native settlement and issuance authority
- `docs/universal_access_interface_v0.1.md` — canonical public access interface
- `docs/universal_access_conformance_plan_v0.1.md` — UAII conformance catalog
- `docs/bitcoin_interoperability_spec.md` — Bitcoin evidence is external
- `docs/bitcoin_interoperability_threat_model_v0.1.md` — threat-model review
- `docs/bitcoin_security_gates_review_v0.1.md` — remaining Bitcoin gates
- `coin/tx_validation.py` — sole transfer/coinbase validation authority

---

## 1. Status

Foundation 107 documents the **interface boundaries** between:

- canonical L28 Universal Access
- future transport adapters
- Bitcoin-domain evidence
- optional Harness/Evals advisory output

This document is **documentation only**. It is **non-activating**. It does
not implement UAII processors, adapters, SDKs, Bitcoin observers, wallets,
signers, Harness/Evals runtime, or settlement.

| Statement | Status |
|---|---|
| Foundation | 107 |
| Activation | none |
| Protocol v1.0.0 | FROZEN |
| L28 role | **Settlement authority remains L28.** No adapter, Bitcoin object, or Harness/Evals report substitutes for Protocol validation or ledger settlement. |

Absence of a later implementation foundation is a **block**, not a
default-allow. Documenting a boundary does not expose that boundary as a
live operation.

---

## 2. Universal Access canonical boundary

The Universal Access Interface (UAII) v0.1,
`l28-universal-ai-access-interface/v0.1`, is the **canonical public access
interface** for agent-facing L28 operations.

Balances, quotes, unsigned payment requests, validation, receipts, and
capability discovery MUST use the **canonical UAII schemas** defined in
`docs/universal_access_interface_v0.1.md` and the Foundation 94-era UAII
conformance catalog. Alternate JSON shapes, renamed operations, or
transport-specific fields MUST NOT become a second protocol.

### 2.1 Canonical operations (profile status unchanged)

| Operation | Role at this boundary |
|---|---|
| `discover_capabilities` | Capability and deferred-adapter metadata discovery |
| `get_protocol_status` | Public protocol/profile snapshot |
| `get_balance` | Public balance inquiry |
| `create_quote` | Deterministic quote object |
| `create_unsigned_payment_request` | Unsigned payment proposal |
| `validate_payment` | Deterministic validation response; does not settle |
| `get_payment_receipt` | Receipt binding after independent L28 settlement |
| `verify_signed_receipt` | Public verification of a signed receipt |
| `create_refund_request` / `create_refund_receipt` | Deferred message shapes only |
| Signing / broadcast / autonomous spend | Forbidden as UAII operations |

Unknown operations MUST fail closed (`operation_unsupported`).

### 2.2 Adapters expose UAII; they do not redefine it

Future adapters MUST map 1:1 to the canonical JSON envelope and operation
contracts. They MUST preserve canonical field order and public digests.
They MUST keep `execution_authorized`, `signing_authorized`, and
`spend_authorized` false unless a later Protocol-authorized path exists
(none in UAII v0.1).

Adapters MUST NOT:

- invent operations absent from the profile
- silently extend UAII v0.1
- smuggle Bitcoin observation into `discover_capabilities` as a supported
  native v0.1 operation
- present simulated or demo approvals as settlement

On conflict: Protocol v1.0.0 prevails over UAII; UAII prevails over adapter
or Bitcoin design documents for public interface field names.

---

## 3. Bitcoin evidence boundary

Bitcoin data remains **external evidence**. It is not native L28.

If a later, separately versioned interface profile ever cites Bitcoin
facts, those objects MUST remain clearly labeled **Bitcoin-domain data**
(for example: Bitcoin network identifier, Bitcoin txid, Bitcoin block
hash, Bitcoin height, satoshi amounts, confirmation information labeled as
Bitcoin confirmations).

Bitcoin evidence cannot become:

- L28 canonical height
- L28 supply
- L28 issuance
- L28 validation
- L28 consensus
- L28 history
- L28 settlement authority

Bitcoin satoshi amounts MUST remain satoshi amounts. Bitcoin height MUST
remain Bitcoin height. Observation-accept in a Bitcoin conformance fixture
is not L28 settlement and grants no execution, spend, signing, broadcast,
ledger mutation, or issuance.

A Bitcoin observer is **not** `adapter.mcp`, `adapter.rest_openapi`,
`adapter.python_sdk`, or `adapter.typescript_sdk`. It MUST NOT be declared
as a supported native UAII v0.1 operation.

UAII v0.1 is **unchanged** by this review. No Bitcoin operations are added.

---

## 4. Adapter boundaries

Deferred UAII adapter identifiers remain **metadata only**:

- `adapter.mcp`
- `adapter.rest_openapi`
- `adapter.python_sdk`
- `adapter.typescript_sdk`

This Foundation does not implement any of them.

### 4.1 MCP adapter

| Rule | Requirement |
|---|---|
| Role | Transport / interface only |
| Mapping | 1:1 to canonical UAII envelope and operations |
| Authority | **Cannot create authority** |

An MCP binding MAY later carry public UAII request/response bytes. It MUST
NOT become a validator, minter, height authority, or settlement engine. It
MUST NOT accept private keys, seeds, mnemonics, xprv, or credentials into
tool arguments, prompts, or logs.

### 4.2 REST / OpenAPI

| Rule | Requirement |
|---|---|
| Role | Transport / interface only |
| Schemas | **Same canonical UAII schemas** |
| Authority | Cannot create authority |

HTTP paths, content types, and status-code mapping are transport concerns.
They MUST NOT fork field names, invent grant flags, or relax
`validate_transaction`. REST success is not L28 settlement.

### 4.3 Python / TypeScript SDK

| Rule | Requirement |
|---|---|
| Role | Client access only |
| Protocol bypass | **Forbidden** |
| Authority | Cannot create authority |

An SDK MAY later wrap canonical public calls for convenience. Convenience
MUST NOT hide fail-closed rules, MUST NOT embed keys, and MUST NOT call
production mutation surfaces (`mint`, ledger writes, Bitcoin RPC, bridge
deploy) as a substitute for UAII validation.

### 4.4 All adapters

Every adapter, including a future Bitcoin interoperability adapter if
later gated and separately versioned, MUST NOT:

- bypass `validate_transaction`
- modify Protocol economics (hard cap, emission ceiling, historically
  mined, treasury locked, circulating snapshot, reward schedule)
- mint L28 or open a non-coinbase issuance path
- authorize settlement
- override consensus or supply canonical L28 height
- rewrite historical evidence
- convert Bitcoin-domain facts into L28 identity, units, or height

Attempted overrides remain `adapter_override_forbidden` at the Bitcoin
conformance boundary and remain Protocol-forbidden at the L28 core.

---

## 5. Harness / Evals boundary

Harness/Evals is an **optional isolated commerce subsystem**. It is
**advisory only**.

Documented flow (conceptual; not implemented here):

```
Agent A
    → Harness/Evals
    → Evidence Report
    → Agent decision
    → L28 settlement
    → Receipt
```

| Step | Authority |
|---|---|
| Agent A | May request an advisory evidence report |
| Harness/Evals | MAY produce an evidence report. MUST NOT settle. |
| Evidence Report | Advisory public artifact. Not a quote substitute that redefines UAII. Not Bitcoin finality. Not L28 consensus. |
| Agent decision | Off-protocol commercial judgment. Not Protocol authorization. |
| L28 settlement | Sole settlement path: Protocol v1.0.0 + `validate_transaction` + consensus-derived height |
| Receipt | UAII receipt/verification objects only after independent L28 settlement |

### 5.1 Rules

| Rule | Status |
|---|---|
| Optional commerce subsystem | Yes |
| Advisory only | Yes |
| Consensus authority | **None** |
| Issuance authority | **None** |
| Validation authority | **None** |
| Settlement authorization | **None** |

Harness/Evals MUST NOT:

- control settlement
- mint or burn L28
- supply canonical height
- replace `validate_transaction`
- define native L28 identity
- act as a Bitcoin observer, proof architecture, confirmation policy,
  quorum, wallet, or signer
- be smuggled into UAII v0.1 as a supported native settlement operation

An evidence report MAY inform an agent. L28 core MUST NOT depend on
external scoring, ranking, or Harness/Evals output to validate or settle.

---

## 6. Security dependencies

Interface mapping does not satisfy Bitcoin production gates. The following
remain exactly unresolved and **block** Bitcoin adapter implementation:

| Dependency | Status |
|---|---|
| Production proof architecture | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production confirmation count | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production observer quorum | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Custody / signing | Future governed milestone |

Also still required before any Bitcoin runtime: independent security
review and explicit operator authorization (Foundation 106). This
interface-boundary review does **not** satisfy those items.

UAII isolated signing remains the Foundation 64+ local signer boundary for
**L28** signatures. That boundary is not a Bitcoin wallet and is not
activated by this document.

---

## 7. Authority firewall table

| Component | May do | Must not do |
|---|---|---|
| UAII | Expose the canonical public interface for discovery, balance, quote, unsigned payment, validation, and receipts | Redefine Protocol v1.0.0; offer signing/broadcast/spend as interface operations; silently add Bitcoin operations in v0.1 |
| Adapter | Transport canonical UAII data (and, if later authorized under a new profile, labeled external evidence) | Create authority; bypass `validate_transaction`; mint; authorize settlement; override consensus or economics |
| Harness/Evals | Provide advisory evidence reports | Control settlement; issue L28; validate L28 transactions; supply canonical height |
| Bitcoin evidence | Describe labeled Bitcoin-domain facts | Control L28 height, supply, issuance, validation, consensus, history, or settlement |
| L28 core | Validate via `validate_transaction` and settle under Protocol v1.0.0 | Depend on external scoring, Harness/Evals, Bitcoin tips, or adapter grants |

---

## 8. Non-goals

Foundation 107 MUST NOT and does not:

- implement MCP
- implement REST / OpenAPI
- implement Python or TypeScript SDKs
- implement a Bitcoin adapter
- connect Bitcoin RPC, SPV, or P2P
- create or import wallets
- create or handle keys
- sign
- broadcast
- deploy or execute a bridge
- activate settlement
- choose a production Bitcoin proof architecture, confirmation count, or
  observer quorum
- implement Harness/Evals runtime
- modify Protocol v1.0.0
- modify UAII v0.1 schemas or operations

---

## 9. Document control

| Field | Value |
|---|---|
| Foundation | 107 |
| Parent | `ca77cd63e022d6176ae17399ed3eae3041da5f4a` |
| Path | `docs/universal_access_adapter_boundary_review_v0.1.md` |
| Status | interface-boundary review / non-activating |
| Implementation | none |
| Runtime activation | none |
| Network activity | none |
| Wallet / signing activity | none |
| Existing files modified | none |
| UAII v0.1 operations added | none |
| Bitcoin operations added to UAII v0.1 | none |
| MCP / REST / SDK implementation | none |
| Harness/Evals protocol authority | none |
| Production proof architecture | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production confirmation count | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production observer quorum | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Custody / signing architecture | future governed milestone |
