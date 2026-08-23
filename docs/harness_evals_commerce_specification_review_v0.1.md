# Harness/Evals Commerce Specification Review v0.1

**Foundation:** 110

**Status:** Harness/Evals commerce specification review / non-activating

**Document version:** `harness-evals-commerce-specification-review/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Parent:** `e28e44adf3a47f4b46dced8ddc13c86894018f4f`

**Branch:** `foundation110-harness-evals-commerce-specification-review`

**Implementation:** none

**Runtime activation:** none

**Network activity:** none

**Wallet / signing activity:** none

**Existing files modified:** none

**Normative subordination:** This document is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md). On conflict, Protocol v1.0.0 prevails.
It is also subordinate to Universal Access Interface v0.1
(`docs/universal_access_interface_v0.1.md`) for public access patterns,
Foundations 107–109 for adapter and UAII preservation boundaries, and
Foundations 93/105–106 for Bitcoin external-evidence rules. This document
MUST NOT implement Harness runtime, an evaluation or scoring engine, a
marketplace, or change issuance, supply, history, height, consensus, or
`validate_transaction`.

**Related locked contracts (consumed, not replaced):**

- `PROTOCOL.md` — sole native settlement and issuance authority
- `docs/universal_access_interface_v0.1.md` — canonical public access interface
- `docs/universal_access_adapter_boundary_review_v0.1.md` — Harness/Evals as advisory only
- `docs/uaii_canonical_interface_preservation_review_v0.1.md` — UAII preservation
- `docs/adapter_exposure_specification_review_v0.1.md` — adapters are transport only
- `docs/bitcoin_security_gates_review_v0.1.md` — remaining Bitcoin gates
- `coin/tx_validation.py` — sole transfer/coinbase validation authority

---

## 1. Status

Foundation 110 documents the **optional Harness/Evals commerce subsystem
boundary** for machine-to-machine (M2M) agent commerce.

This document is **documentation only**. It is a **commerce subsystem
specification review**. It is **non-activating**. It contains no runtime
and no implementation.

| Statement | Status |
|---|---|
| Foundation | 110 |
| Kind | Commerce subsystem specification review |
| Activation | none |
| Protocol v1.0.0 | FROZEN |
| L28 role | **Settlement authority remains L28.** Harness/Evals does not settle. |

Documenting a future evidence layer is not permission to run evaluations,
score agents, open a marketplace, or treat a report as payment. Absence of
a later authorized milestone is a **block**, not a default-allow.

---

## 2. Harness/Evals role

Harness/Evals is an **optional trust/evidence layer** for M2M commerce.

If later authorized, it MAY:

- evaluate models, agents, and tools
- produce **evidence reports**

It does **not** control L28.

| Claim | Status |
|---|---|
| Harness/Evals is Protocol v1.0.0 | Forbidden |
| Harness/Evals is a validator | Forbidden |
| Harness/Evals is a minter | Forbidden |
| Harness/Evals is settlement authorization | Forbidden |
| A high score is L28 consensus | Forbidden |

Advisory output is commercial judgment support. It is not coinbase, not
canonical height, and not `validate_transaction`.

---

## 3. Architecture flow

Documented flow (conceptual; not implemented here):

```
Agent A
    → Service request
    → Harness/Evals
    → Evaluation + Evidence Report
    → Agent decision
    → L28 settlement
    → Receipt / history
```

| Step | Meaning | Authority |
|---|---|---|
| Agent A | Requests a service or counterpart evaluation | No Protocol grant |
| Service request | Public, non-secret description of needed work | Not a UAII settlement operation |
| Harness/Evals | Optional evaluation of model, agent, or tool | **None** over L28 |
| Evaluation + Evidence Report | Advisory artifact | Informs; does **not** authorize settlement |
| Agent decision | Off-protocol choice to proceed, decline, or renegotiate | Not Protocol authorization |
| L28 settlement | Independent L28 transaction | Protocol v1.0.0 + `validate_transaction` + consensus-derived height |
| Receipt / history | UAII receipt/verification after independent settlement; L28 historical evidence remains immutable | L28 history MUST NOT be rewritten by scores |

**Evidence informs decisions. Evidence does not authorize settlement.**

L28 core MUST NOT wait on, require, or incorporate Harness/Evals scores to
validate or settle.

---

## 4. Agent identity model

Future identity concepts, if later authorized, are **public commerce
labels**. They do not create protocol authority.

| Concept | Future meaning (non-activating) | Must not imply |
|---|---|---|
| Agent identifier | Stable public id for an agent or service principal | Spend authority, mint authority, reserved Protocol identities (`COINBASE`, `__MINT__`) |
| Version lineage | Declared software/model version chain | Automatic trust or validation bypass |
| Capability profile | Declared skills/tools the agent claims | UAII operation grants or Bitcoin observation rights |
| Evaluation history | Prior evidence-report references | Reputation-based settlement rights |
| Evidence reports | Linked advisory artifacts | Consensus votes or coinbase |

Identity does **not** create protocol authority. A well-known agent id MUST
NOT become canonical height, issuance, or `validate_transaction` success.

Private keys, seeds, and wallet descriptors MUST NOT be used as agent
identifiers.

---

## 5. Capability and evaluation model

If later authorized, evaluation MAY cover:

| Target | Advisory question |
|---|---|
| Model evaluation | Does a declared model version behave as claimed under a stated test context? |
| Agent evaluation | Does an agent complete declared tasks within stated limits? |
| Tool evaluation | Does a tool return public results matching its declared interface? |

Possible **advisory** evidence fields (illustrative, not a schema
implementation):

- accuracy
- reliability
- latency
- cost
- limitations

| Rule | Status |
|---|---|
| Evidence is advisory | Required |
| Scores cannot affect consensus | Required |
| Missing evaluation | Fail closed for **commerce choice** only; MUST NOT fail or pass L28 validation |

Numeric scores MUST NOT be coerced into L28 amounts, Bitcoin confirmations,
or grant flags (`execution_authorized`, `spend_authorized`,
`l28_issuance_authorized`).

---

## 6. Evidence report boundary

A future evidence report, if authorized, is an **evaluation artifact**.
Conceptual public contents MAY include:

| Field concept | Role |
|---|---|
| Evaluation artifact | What was tested (model / agent / tool) |
| Metrics | Advisory measurements (accuracy, reliability, latency, cost) |
| Test context | Declared, caller-supplied conditions; no hidden system clock or network inference as authority |
| Version | Subject version lineage |
| Limitations | Explicit non-claims |
| Evidence hash | Public digest of the report body for later citation |

| Claim | Status |
|---|---|
| Report is settlement authorization | **Forbidden** |
| Report is L28 consensus | **Forbidden** |
| Report is a UAII quote or receipt | **Forbidden** (MUST NOT redefine canonical UAII schemas) |
| Report is Bitcoin finality | **Forbidden** |

An evidence hash is a citation aid. It is not a Merkle Bitcoin proof, not
an L28 receipt id with spend meaning, and not historical-ledger mutation.

---

## 7. Reputation / history boundary

Optional **future** reputation or evaluation-history tracking MAY cite
prior evidence reports.

Rules:

- **No reputation-based minting.** High scores MUST NOT create L28.
- **No reputation-based validation bypass.** Reputation MUST NOT skip
  `validate_transaction`.
- **No special settlement rights.** Reputation MUST NOT set
  `settlement_finalized`, `execution_authorized`, or
  `spend_authorized`.

L28 historical evidence (including historically mined 2,824,584 L28,
mined-through entry 100,877, and next canonical height 100,878) remains
**immutable** and is a different domain from evaluation history.
Evaluation history MUST NOT rewrite Protocol history, supply records, or
genesis/hash/snapshot evidence.

---

## 8. L28 interface boundary

Harness/Evals MAY:

- provide evidence references
- provide capability information

Harness/Evals MUST NOT:

- mint L28
- validate transactions
- alter supply (hard cap 28,000,000 L28; emission ceiling 11,130,000 L28;
  historically mined 2,824,584 L28; treasury locked 500,000 L28;
  circulating snapshot 2,324,584 L28; reward sequence 28 → 14 → 7 → 3 → 1 → 0;
  halving interval 210,000)
- alter canonical height
- alter history
- authorize settlement
- bypass `validate_transaction`

Issuance remains coinbase-only. Height authority remains
consensus-derived. Adapter override remains forbidden.

---

## 9. Security boundary

| Control | Status in this Foundation |
|---|---|
| Private keys | **No private keys** in reports, prompts, evaluation inputs, or logs |
| Wallets | **No wallets** |
| Signing | **No signing** as a Harness/Evals operation |
| Broadcast | **No broadcast** |
| Production credentials | **No production credentials** (including Bitcoin RPC credentials) |

Only public identifiers, public digests, and public metrics MAY appear in
an evidence report. Hosted models MUST NOT receive seeds, xprv, or
keystore material as evaluation subjects.

---

## 10. UAII boundary

Harness/Evals, if later composed, MUST use **bounded public interfaces**.

UAII v0.1, profile `l28-universal-ai-access-interface/v0.1`, remains the
**canonical public access interface** for discovery, balances, quotes,
unsigned payment requests, validation responses, and receipts.

| Rule | Status |
|---|---|
| Hidden protocol extensions | **Forbidden** |
| New UAII operations in v0.1 | **None** in this Foundation |
| Evidence report as `create_quote` / `validate_payment` / receipt | **Forbidden** semantic overload |
| `discover_capabilities` smuggling Harness as native settlement | **Forbidden** |

A later public “cite evidence report” field, if ever wanted, requires a
**new** interface profile or plan version. It MUST NOT silently extend
UAII v0.1.

Adapters (MCP / REST / SDK) remain transport only (Foundation 109).
Harness/Evals MUST NOT control those adapters.

---

## 11. Bitcoin boundary

Bitcoin evidence remains **external**. It is not native L28.

Harness/Evals **cannot** convert Bitcoin evidence into L28 authority.

| Forbidden conversion | Status |
|---|---|
| Bitcoin height → L28 canonical height | Forbidden |
| Satoshis → L28 units | Forbidden |
| Bitcoin confirmation score → L28 settlement | Forbidden |
| Explorer or RPC quote → issuance | Forbidden |
| Evidence-report “BTC reliability” → `validate_transaction` success | Forbidden |

A Bitcoin observer is not Harness/Evals. Harness/Evals is not a proof
architecture, confirmation policy, or observer quorum. Those production
decisions remain:

- `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` (proof architecture)
- `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` (confirmation count)
- `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` (observer quorum)

This Foundation does not activate Bitcoin RPC, SPV, P2P, wallets, signing,
broadcast, mining, or bridging.

---

## 12. Future implementation gates

The following remain **separate authorized milestones**. Foundation 110
does **not** open them:

| Milestone | Gate |
|---|---|
| Harness runtime | Later authorized foundation; still advisory; still no L28 control |
| Agent evaluation engine | Later authorized foundation; scores cannot affect consensus |
| Reputation system | Later authorized foundation; no mint, no validation bypass, no special settlement rights |
| Marketplace features | Later authorized foundation; listings are not Protocol operations |

Each milestone MUST remain subordinate to Protocol v1.0.0, UAII v0.1 (or a
new explicit profile), and `validate_transaction`. Bitcoin runtime and
settlement activation remain separately gated and are not implied here.

---

## 13. Document control

| Field | Value |
|---|---|
| Foundation | 110 |
| Parent | `e28e44adf3a47f4b46dced8ddc13c86894018f4f` |
| Path | `docs/harness_evals_commerce_specification_review_v0.1.md` |
| Status | Harness/Evals commerce specification review / non-activating |
| Implementation | none |
| Runtime activation | none |
| Network activity | none |
| Wallet / signing activity | none |
| Existing files modified | none |
| Harness runtime | none |
| Evaluation / scoring engine | none |
| Marketplace | none |
| Protocol v1.0.0 | unchanged |
| Issuance / supply / history / height | unchanged |
| `validate_transaction` | unchanged |
| Settlement authorization | none |
| UAII v0.1 operations added | none |
| Bitcoin runtime activation | none |
