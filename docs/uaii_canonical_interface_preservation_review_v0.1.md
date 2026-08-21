# UAII Canonical Interface Preservation Review v0.1

**Foundation:** 108

**Status:** canonical interface preservation review / non-activating

**Document version:** `uaii-canonical-interface-preservation-review/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Interface profile preserved:** `l28-universal-ai-access-interface/v0.1`

**Parent:** `45e46cd4a4d706086247f38d5974b56b6549aeb8`

**Branch:** `foundation108-uaii-canonical-interface-preservation-review`

**Implementation:** none

**Runtime activation:** none

**Network activity:** none

**Wallet / signing activity:** none

**Existing files modified:** none

**Normative subordination:** This document is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md). On conflict, Protocol v1.0.0 prevails.
It is also subordinate to Universal Access Interface v0.1
(`docs/universal_access_interface_v0.1.md`) for schemas, operations, and
field meanings. Foundation 107 remains the adapter-boundary review. This
document MUST NOT redefine UAII schemas, settlement, issuance, supply,
consensus height authority, historical evidence, or `validate_transaction`.

**Related locked contracts (consumed, not replaced):**

- `PROTOCOL.md` — sole native settlement and issuance authority
- `docs/universal_access_interface_v0.1.md` — canonical UAII v0.1
- `docs/universal_access_conformance_plan_v0.1.md` — UAII conformance catalog
- `docs/universal_access_adapter_boundary_review_v0.1.md` — adapter / Bitcoin / Harness boundaries
- `coin/tx_validation.py` — sole transfer/coinbase validation authority

---

## 1. Status

Foundation 108 records that the L28 Universal Access Interface (UAII)
**canonical boundary is preserved**. It does not extend, fork, or activate
that interface.

This document is **documentation only**. It is an **interface preservation
review**. It is **non-activating**.

| Statement | Status |
|---|---|
| Foundation | 108 |
| Kind | Interface preservation review |
| Activation | none |
| Protocol v1.0.0 | FROZEN |
| L28 role | **Settlement authority remains L28.** UAII does not settle. |

Preserving UAII is not permission to implement adapters, SDKs,
Harness/Evals runtime, Bitcoin observation, wallets, signing, broadcast,
or settlement. Absence of a later implementation foundation is a **block**,
not a default-allow.

---

## 2. UAII authority boundary

UAII v0.1, profile `l28-universal-ai-access-interface/v0.1`, is the
**canonical public access interface** for agent-facing discovery, balance
inquiry, quotes, unsigned payment proposals, validation responses, and
receipts.

UAII does **not** replace Protocol v1.0.0. On conflict, Protocol prevails.

UAII exposes **access patterns only**. Successful interface evaluation is
evidence of a well-formed public request/response, not permission to spend,
settle, mint, mutate supply, or start a runtime.

`validate_transaction` in `coin/tx_validation.py` remains the **sole L28
transfer/coinbase validation authority**. UAII `validate_payment` is a
canonical public validation-response pattern. It MUST NOT become a second
validator and MUST NOT bypass `validate_transaction`.

Adapters, callers, hosted models, Bitcoin evidence, and Harness/Evals have
**no authority** to override validation, supply, issuance, height, history,
or consensus.

---

## 3. Canonical operations

The following public operations remain the preserved UAII v0.1 access
surface. Schemas are **canonical**. Field names, order, and meanings are
**stable**. Adapters MUST map 1:1 **without redefining semantics**.

| Access pattern | Canonical operation | Preserved meaning |
|---|---|---|
| Capability discovery | `discover_capabilities` | Public capability and deferred-adapter metadata. Not a grant. |
| Protocol status | `get_protocol_status` | Public protocol/profile snapshot. Not runtime activation. |
| Balances | `get_balance` | Public balance inquiry without private-material exposure. |
| Quotes | `create_quote` | Deterministic public quote object. Not settlement. |
| Unsigned payment requests | `create_unsigned_payment_request` | Unsigned payment proposal. Not a signed spend. |
| Validation | `validate_payment` | Deterministic public validation response. Not ledger mutation. |
| Receipts | `get_payment_receipt`, `verify_signed_receipt` | Receipt binding and public verification after independent L28 settlement. |

Deferred refund message shapes (`create_refund_request`,
`create_refund_receipt`) remain deferred. Signing, broadcast, and
autonomous spend remain **forbidden** as UAII operations. Unknown
operations MUST fail closed (`operation_unsupported`).

Canonical envelope and object field order specified by Foundation 79 remain
authoritative. Identical canonical public inputs MUST yield equivalent
public outcomes. Simulated or demo approvals MUST NOT be treated as
settlement.

This Foundation MUST NOT modify those schemas.

---

## 4. Version compatibility

| Rule | Preservation requirement |
|---|---|
| Versioned interfaces | The profile string `l28-universal-ai-access-interface/v0.1` identifies this surface. Breaking changes require a **new** interface profile string. |
| Reported protocol version | Remains `"1.0.0"`. UAII MUST NOT report a different Protocol version. |
| Backward compatibility | Existing v0.1 field meanings MUST NOT be silently reused for a different purpose. Callers that emit canonical v0.1 bytes MUST receive equivalent public outcomes. |
| Unknown fields | This profile **rejects** unknown fields (`schema_invalid`). Unknown fields MUST NOT be ignored, repaired, or treated as extensions. |
| No silent semantic changes | Additive deferred operations MUST NOT silently become executable. Status `deferred` remains non-executing until a later authorized implementation foundation. |
| No adapter-specific protocol extensions | MCP, REST/OpenAPI, and SDK transports MUST NOT introduce private operations, renamed fields, extra grant flags, or Bitcoin-native fields inside UAII v0.1. |

A later public Bitcoin observation capability, if ever authorized, MUST
publish a **new** interface profile or plan version. It MUST NOT silently
extend UAII v0.1.

Deprecated identifiers, if any, remain listed as superseded. They MUST NOT
be recycled with new meanings.

---

## 5. Adapter boundary

Deferred adapter identifiers remain **metadata only** in capability
discovery. This Foundation does not implement them.

| Adapter | Preserved role |
|---|---|
| MCP | **Future transport only.** Maps 1:1 to canonical UAII bytes. Cannot create authority. |
| REST / OpenAPI | **Future transport only.** Same canonical schemas. HTTP success is not settlement. |
| Python / TypeScript SDK | **Client access only.** Convenience wrappers MUST NOT bypass Protocol or UAII fail-closed rules. |

Adapters MUST NOT:

- bypass `validate_transaction`
- mint L28 or open a non-coinbase issuance path
- modify supply (hard cap, emission ceiling, historically mined, treasury
  locked, circulating snapshot, or reward schedule)
- modify history
- override consensus or supply canonical L28 height
- authorize settlement
- embed private keys, seeds, mnemonics, xprv, or credentials in prompts,
  params, logs, or hosted models

Attempted validation or economic override remains
`adapter_override_forbidden`.

---

## 6. Bitcoin boundary

Bitcoin evidence remains **external**. It is not native L28.

No Bitcoin fields become native L28 fields. Bitcoin network identifiers,
txids, block hashes, Bitcoin heights, satoshi amounts, and Bitcoin
confirmation counts MUST stay labeled Bitcoin-domain data.

Bitcoin cannot define:

- L28 identity
- L28 canonical height
- L28 supply
- L28 validation
- L28 settlement

A Bitcoin observer is not `adapter.mcp`, `adapter.rest_openapi`,
`adapter.python_sdk`, or `adapter.typescript_sdk`. It MUST NOT be smuggled
into `discover_capabilities` as a supported native UAII v0.1 operation.

UAII v0.1 Bitcoin operations remain **none**. This preservation review does
not activate Bitcoin RPC, SPV, P2P, wallets, signing, broadcast, mining,
or bridging.

---

## 7. Harness / Evals boundary

Harness/Evals remains an **optional commerce subsystem**. It is
**evidence / advisory only**.

| Rule | Status |
|---|---|
| Consensus | **Cannot affect consensus** |
| Settlement authority | **Cannot affect settlement authority** |
| Issuance / validation | None |
| UAII replacement | Forbidden. Advisory reports MUST NOT redefine canonical quote, payment, or receipt schemas. |

An agent MAY read an evidence report and later submit an independent L28
transaction. L28 core MUST NOT depend on Harness/Evals scoring to validate
or settle. This Foundation does not implement Harness/Evals runtime.

---

## 8. Security preservation

UAII preservation includes the existing secret and activation firewall:

| Control | Status in this Foundation |
|---|---|
| Private keys | **No keys.** MUST NEVER enter prompts, UAII params, adapters, logs, or hosted services. |
| Wallets | **No wallet** creation, import, or use. |
| Signing | **No signing** as a UAII operation. Isolated local signing remains a later/local boundary (Foundation 64+), not activated here. |
| Broadcast | **No broadcast.** |
| Runtime activation | **None.** |

`execution_authorized`, `signing_authorized`, and `spend_authorized` remain
false on UAII v0.1 paths defined by Foundation 79. System clock, timezone
defaults, environment variables, and network time MUST NOT become hidden
authority for expiration or idempotency.

---

## 9. Remaining future work

The following remain **future work**. Foundation 108 does **not** implement
them:

| Item | Note |
|---|---|
| MCP exposure | Transport mapping only, if later authorized |
| REST / OpenAPI exposure | Transport mapping only, if later authorized |
| Python / TypeScript SDK exposure | Client access only, if later authorized |
| Secure local signing | Isolated signer boundary; not an adapter; not Bitcoin custody |
| Economic controls | Informational UAII limit fields remain subordinate to Protocol validation |
| Isolated two-agent testnet | Later governed test activity; not implied by this review |

Bitcoin production proof architecture, confirmation count, and observer
quorum remain `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` (Foundations
105–106). Those decisions are not made here.

---

## 10. Document control

| Field | Value |
|---|---|
| Foundation | 108 |
| Parent | `45e46cd4a4d706086247f38d5974b56b6549aeb8` |
| Path | `docs/uaii_canonical_interface_preservation_review_v0.1.md` |
| Status | canonical interface preservation review / non-activating |
| Implementation | none |
| Runtime activation | none |
| Network activity | none |
| Wallet / signing activity | none |
| Existing files modified | none |
| UAII v0.1 schemas modified | none |
| UAII v0.1 operations added | none |
| Adapter / SDK implementation | none |
| Harness/Evals runtime | none |
| Protocol v1.0.0 | unchanged |
| `validate_transaction` | unchanged |
| Issuance / supply / history | unchanged |
| Bitcoin runtime activation | none |
