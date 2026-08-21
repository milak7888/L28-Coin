# Adapter Exposure Specification Review v0.1

**Foundation:** 109

**Status:** adapter exposure specification review / non-activating

**Document version:** `adapter-exposure-specification-review/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Canonical interface:** `l28-universal-ai-access-interface/v0.1`

**Parent:** `d22717801475ffc392326b7b3f9908e430b06f27`

**Branch:** `foundation109-adapter-exposure-specification-review`

**Implementation:** none

**Runtime activation:** none

**Network activity:** none

**Wallet / signing activity:** none

**Existing files modified:** none

**Normative subordination:** This document is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md). On conflict, Protocol v1.0.0 prevails.
It is also subordinate to Universal Access Interface v0.1
(`docs/universal_access_interface_v0.1.md`) for schemas and operations,
Foundation 107 for adapter boundaries, and Foundation 108 for UAII
preservation. This document MUST NOT implement adapters, create APIs or
SDKs, change UAII, change Protocol v1.0.0, or change `validate_transaction`.

**Related locked contracts (consumed, not replaced):**

- `PROTOCOL.md` — sole native settlement and issuance authority
- `docs/universal_access_interface_v0.1.md` — canonical UAII v0.1
- `docs/universal_access_conformance_plan_v0.1.md` — UAII conformance catalog
- `docs/universal_access_adapter_boundary_review_v0.1.md` — adapter / Bitcoin / Harness boundaries
- `docs/uaii_canonical_interface_preservation_review_v0.1.md` — UAII preservation
- `coin/tx_validation.py` — sole transfer/coinbase validation authority

---

## 1. Status

Foundation 109 documents **future adapter exposure boundaries** for UAII
without implementing adapters.

This document is **documentation only**. It is an **adapter exposure
specification review**. It is **non-activating**. It contains **no code**
and **no runtime**.

| Statement | Status |
|---|---|
| Foundation | 109 |
| Kind | Adapter exposure specification review |
| Activation | none |
| Protocol v1.0.0 | FROZEN |
| L28 role | **Settlement authority remains L28.** Adapters do not settle. |

Documenting how a future MCP, REST, or SDK binding **would** map to UAII
is not permission to create that binding. Absence of a later authorized
implementation milestone is a **block**, not a default-allow.

---

## 2. Adapter authority model

UAII v0.1 remains the **canonical public access interface**.

Adapters **expose UAII**. They do not replace it, fork it, or redefine
field meanings.

Adapters are **transport layers only**. They carry canonical public
request/response bytes (or an equivalent 1:1 mapping of those bytes).

Adapters **cannot create protocol authority**. Transport success is not
Protocol validation, not issuance, not consensus, and not settlement.

| Layer | Authority |
|---|---|
| Protocol v1.0.0 | Settlement, issuance, supply, height, history |
| `validate_transaction` | Sole L28 transfer/coinbase validation |
| UAII v0.1 | Canonical public access patterns |
| Adapter (MCP / REST / SDK) | Transport / client access only |
| Isolated local signer (F64+) | L28 signing material, if later composed; not an adapter |

`execution_authorized`, `signing_authorized`, and `spend_authorized` remain
false on UAII v0.1 paths unless a later Protocol-authorized path exists
(none in this profile).

---

## 3. MCP exposure specification

A future MCP adapter, if separately authorized, is **future transport
only**. This Foundation does not implement MCP, register tools, or open
listeners.

### 3.1 Future request mapping

- Each MCP tool invocation MUST map 1:1 to one UAII operation
  (`discover_capabilities`, `get_balance`, `create_quote`,
  `create_unsigned_payment_request`, `validate_payment`,
  `get_payment_receipt`, `verify_signed_receipt`, or a later authorized
  profile operation).
- Tool arguments MUST be the canonical UAII request envelope fields, in
  canonical order and types.
- Unknown operations MUST fail closed (`operation_unsupported`).
- Private keys, seeds, mnemonics, xprv, RPC credentials, and credential
  headers MUST NOT be accepted as tool arguments.

### 3.2 Future response mapping

- MCP content MUST return the canonical UAII response object (or a
  lossless wrapping that still exposes that object).
- Grant flags MUST NOT be added or flipped by the transport.
- Equivalent canonical request bytes MUST yield equivalent public results.

### 3.3 Versioning

- MCP exposure MUST declare `interface_profile` =
  `l28-universal-ai-access-interface/v0.1` (or a later **new** profile
  string).
- A new MCP protocol version MUST NOT silently change UAII v0.1 semantics.

### 3.4 Error handling

- Canonical UAII error objects (`code`, `message`, optional `detail`) MUST
  be preserved.
- MCP transport failures (disconnect, timeout, malformed MCP framing) are
  **transport errors**. They MUST NOT be rewritten as Protocol success or
  as `validate_transaction` success.

### 3.5 Rules

- MCP does **not** validate transactions.
- MCP does **not** settle.
- MCP does **not** modify consensus.

---

## 4. REST / OpenAPI exposure specification

A future REST/OpenAPI adapter, if separately authorized, is **future
transport only**. This Foundation does not create HTTP APIs, OpenAPI
documents, or servers.

### 4.1 Future API resource mapping

- Resources MUST correspond to UAII operations, not to a parallel resource
  model (for example, a “payments” collection MUST NOT imply ledger
  writes).
- Methods MAY be conventional HTTP verbs wrapping canonical UAII envelopes.
  HTTP `200` is not L28 settlement.

### 4.2 Schemas

- Request and response bodies MUST use the **same canonical UAII schemas**.
- OpenAPI type aliases MUST NOT rename fields, drop required keys, or
  introduce adapter-only grant flags.

### 4.3 Compatibility

- Clients that speak UAII v0.1 canonical JSON MUST remain representable
  over REST without semantic change.
- Breaking HTTP layouts require a new interface profile, not a silent
  v0.1 reinterpretation.

### 4.4 Authentication boundaries

- Transport authentication (TLS, API tokens, mTLS), if ever authorized
  later, authenticates the **channel**, not L28 spend authority.
- RPC credentials, wallet secrets, and private keys MUST NOT appear in
  headers, query strings, bodies, or logs.
- Presence of a valid transport credential MUST NOT set
  `spend_authorized` or `execution_authorized`.

### 4.5 Rules

- REST does **not** redefine UAII.
- REST **cannot** bypass `validate_transaction`.

---

## 5. Python / TypeScript SDK exposure

Future SDKs, if separately authorized, are **client libraries only**. This
Foundation does not publish packages, generate clients, or add runtime
helpers.

| Requirement | Rule |
|---|---|
| Role | Client access only |
| Schemas | Canonical UAII schema usage only |
| Version compatibility | Bind to `l28-universal-ai-access-interface/v0.1` until a new profile exists |
| Hidden authority | **None.** Convenience MUST NOT hide fail-closed rules. |

SDKs MUST NOT:

- mint L28
- write ledger state
- bypass validation (`validate_transaction` or UAII `validate_payment`
  semantics)
- control settlement
- embed keys, call Bitcoin RPC, deploy bridges, or invoke
  `contracts/deploy_bridge.py` / `coin/multi_coin_miner.py`

An SDK MAY serialize canonical envelopes and display public results. It
MUST NOT construct an alternate validator.

---

## 6. Versioning and compatibility

| Rule | Requirement |
|---|---|
| Interface versioning | Profile string `l28-universal-ai-access-interface/v0.1` identifies this surface. Breaking changes require a new profile string. |
| Backward compatibility | Canonical v0.1 field meanings remain stable. Equivalent canonical request bytes MUST yield equivalent public outcomes across adapters. |
| Deprecation rules | Deprecated identifiers remain listed as superseded. They MUST NOT be recycled with new meanings. Deferred operations MUST NOT silently become executable. |
| Unknown-field handling | UAII v0.1 **rejects** unknown fields (`schema_invalid`). Adapters MUST NOT strip, ignore, or “best-effort” unknown keys. |
| No silent semantic changes | Transport-only revisions (MCP session framing, HTTP path cosmetics, SDK method names) MUST NOT change Protocol or UAII semantics. |

Adapter-specific protocol extensions are forbidden inside v0.1.

---

## 7. Error boundary model

Adapters MUST preserve **canonical error meanings**. They MAY add a
transport envelope around an error; they MUST NOT replace `code` with a
generic “500” that hides `schema_invalid`, `secret_material_forbidden`, or
`adapter_override_forbidden`.

| Class | Origin | Adapter duty |
|---|---|---|
| Transport errors | Disconnect, timeout, HTTP framing, MCP session loss | Report as transport failure. MUST NOT imply Protocol validation success or settlement. |
| Validation errors | UAII schema / `validate_payment` public response / `validate_transaction` | Preserve canonical codes and fail-closed outcomes. MUST NOT coerce or repair. |
| Protocol errors | Profile mismatch, frozen economic invariants, missing canonical height | Preserve Protocol/UAII codes. MUST NOT invent height, supply, or network defaults. |
| Authorization errors | Forbidden secrets, claimed grants, adapter override attempts | `secret_material_forbidden`, `adapter_override_forbidden`, `operation_unsupported`, or `authority_denied` as already specified. MUST NOT grant spend/sign/broadcast. |

Error `message` and `detail` MUST remain public and secret-free. Paths,
stack traces, and credentials MUST NOT leak.

---

## 8. Security boundary

| Control | Status in this Foundation |
|---|---|
| Private keys | **No keys** in adapters, prompts, params, headers, logs, or hosted models |
| Wallets | **No wallets** |
| Signing | **No signing** as an adapter operation |
| Broadcast | **No broadcast** |
| RPC credentials | **No RPC credentials** (Bitcoin or otherwise) |
| Private infrastructure | **No private infrastructure** implied (no hosted adapter service, no listener, no bridge deploy) |

Only public keys, public key ids, signatures, digests, and public
identities MAY cross process boundaries. Simulated approvals are not
settlement.

---

## 9. Bitcoin boundary

Bitcoin remains **external evidence**. It is not native L28.

A future Bitcoin interoperability adapter, if later gated and separately
versioned, would still be **transport only** for labeled Bitcoin-domain
objects. It is not `adapter.mcp` / REST / SDK by default and MUST NOT be
smuggled into UAII v0.1 `discover_capabilities` as a supported native
operation.

It cannot control:

- issuance
- supply
- canonical height
- validation
- consensus
- history
- settlement

Bitcoin satoshi amounts remain satoshis. Bitcoin height remains Bitcoin
height. Observation is not settlement. Production proof architecture,
confirmation count, and observer quorum remain
`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

This Foundation does not activate Bitcoin RPC, SPV, P2P, wallets, signing,
broadcast, mining, or bridging.

---

## 10. Harness / Evals boundary

Harness/Evals remains an **optional advisory subsystem**.

It **can** provide evidence reports to an agent.

It **cannot** control:

- adapters (MCP / REST / SDK exposure)
- validation (`validate_transaction` or UAII validation semantics)
- settlement

L28 core MUST NOT depend on Harness/Evals scoring. This Foundation does
not implement Harness/Evals runtime.

---

## 11. Future implementation gates

The following remain **separate authorized milestones**. Foundation 109
does **not** open them:

| Milestone | Gate |
|---|---|
| MCP implementation | Later authorized foundation or operator decision; transport mapping only |
| REST / OpenAPI implementation | Later authorized foundation or operator decision; same canonical schemas |
| Python SDK | Later authorized foundation; client library only |
| TypeScript SDK | Later authorized foundation; client library only |

Each milestone MUST remain subordinate to Protocol v1.0.0, UAII v0.1 (or a
new explicit profile), and `validate_transaction`. Bitcoin runtime and
settlement activation remain separately gated (Foundations 105–106) and
are not implied here.

---

## 12. Document control

| Field | Value |
|---|---|
| Foundation | 109 |
| Parent | `d22717801475ffc392326b7b3f9908e430b06f27` |
| Path | `docs/adapter_exposure_specification_review_v0.1.md` |
| Status | adapter exposure specification review / non-activating |
| Implementation | none |
| Runtime activation | none |
| Network activity | none |
| Wallet / signing activity | none |
| Existing files modified | none |
| MCP / REST / SDK implementation | none |
| UAII v0.1 schemas modified | none |
| Protocol v1.0.0 | unchanged |
| `validate_transaction` | unchanged |
| Bitcoin runtime activation | none |
| Settlement activation | none |
| Harness/Evals runtime | none |
| Production proof architecture | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production confirmation count | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production observer quorum | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
