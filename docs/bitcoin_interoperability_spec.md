# Bitcoin Interoperability Specification v0.1

**Foundation:** 93

**Status:** specification / non-activating

**Document version:** `bitcoin-interoperability-spec/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Parent:** `6ae914709d84f90371b2b44841e6c344da9b694f`

**Branch:** `foundation93-bitcoin-interoperability-spec`

**Implementation:** none

**Normative subordination:** This document is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md). On conflict, Protocol v1.0.0 prevails.
This document is also subordinate to the Universal Access Interface v0.1
(`docs/universal_access_interface_v0.1.md`) for any future public interface
mapping. It MUST NOT redefine settlement, issuance, supply, consensus height
authority, historical evidence, or `validate_transaction`.

**Related locked contracts (consumed, not replaced):**

- `PROTOCOL.md` — sole native settlement and issuance authority
- `coin/tx_validation.py` — sole transfer/coinbase validation authority
- `docs/universal_access_interface_v0.1.md` — canonical agent-facing interface
- `docs/universal_access_conformance_plan_v0.1.md` — UAII conformance catalog
- `docs/l28_future_capability_registry_v0.1.md` — bridge/wrapped ≠ native L28
- `docs/l28_core_p2p_architecture_v0.1.md` — CoreL28Node vs transport roles
- Historical evidence and protected economic constants — immutable

---

## 0. Purpose and non-activation

### 0.1 Purpose

Foundation 93 defines how **future Bitcoin interoperability MAY connect to
L28** while remaining **strictly external** to native L28 Protocol v1.0.0.

This is a **design-only** specification. It classifies existing repository
artifacts, defines an external adapter boundary, records proof/trust and
reorg/finality requirements, and states activation gates. It does **not**
authorize, implement, deploy, or operate Bitcoin connectivity.

### 0.2 Explicit non-activation

Foundation 93 MUST NOT:

- make Bitcoin network calls
- connect Bitcoin Core
- use Bitcoin RPC
- start a Bitcoin node
- mine BTC
- create or import Bitcoin wallets
- generate Bitcoin keys
- sign Bitcoin transactions
- broadcast Bitcoin transactions
- deploy contracts
- start L28 networking
- modify ledger state
- modify consensus
- modify Protocol v1.0.0
- execute `contracts/deploy_bridge.py`
- add Bitcoin operations to UAII v0.1

Passing, merging, or publishing this document is **not** permission to spend
L28, mint L28, mine BTC, open listeners, or treat Bitcoin state as L28 state.

---

## 1. Native identity boundary

Bitcoin is **not** native L28.

| Claim | Status |
|---|---|
| Bitcoin is native L28 | Forbidden |
| BTC is L28 | Forbidden |
| A wrapped BTC representation is native L28 | Forbidden |
| A bridge contract defines L28 identity | Forbidden |
| Bitcoin height is L28 canonical height | Forbidden |
| Bitcoin validity is L28 transaction validity | Forbidden |
| Bitcoin supply facts redefine L28 supply | Forbidden |

Native L28 identity remains the public, machine-to-machine protocol defined by
Protocol v1.0.0: coinbase-only issuance, consensus-derived height, and
`validate_transaction` as the sole transfer/coinbase validator.

Bitcoin state MUST NEVER redefine:

- L28 consensus
- L28 supply
- L28 issuance
- L28 canonical height
- L28 transaction validity
- L28 historical evidence

A future Bitcoin observation, proof, receipt citation, or adapter result is
**external evidence at most**. It is never a native L28 asset, never a mint
authority, and never a substitute for Protocol validation.

This restates the Future Capability Registry rule: a bridge contract or
wrapped representation does not define native L28, and treating a bridge
contract as native L28 identity is rejected.

---

## 2. Existing repository artifact classification

This Foundation **classifies** the following artifacts. It does **not** delete,
modify, execute, or promote them.

### 2.1 `coin/multi_coin_miner.py`

| Field | Classification |
|---|---|
| Path | `coin/multi_coin_miner.py` |
| Observed behavior | Local SHA-256 hash-prefix loops labeled `BTC`, `ETH`, `SOL`, and `L28` |
| Bitcoin Core / P2P / RPC | Not present in the file |
| Bitcoin difficulty / headers / blocks | Not present |
| Consensus mining | Not demonstrated |

`coin/multi_coin_miner.py` is **not** evidence of Bitcoin consensus or Bitcoin
network mining unless later repository evidence proves otherwise. Present
evidence shows only a local string-prefixed hash search. The bounded testnet
readiness audit already treats `mine_l28` in this file as a dormant helper and
records that `difficulty_18_is_consensus` is false.

This Foundation MUST NOT execute the file and MUST NOT treat a successful
local hash prefix as a Bitcoin block, Bitcoin proof-of-work, or L28 coinbase.

### 2.2 `contracts/L28Bridge.sol`

| Field | Classification |
|---|---|
| Path | `contracts/L28Bridge.sol` |
| Language / target | Solidity `^0.8.20` EVM contract |
| Pattern | Lock/release of native EVM value (`msg.value`) across named EVM destinations |
| Bitcoin script / UTXO / headers | Not present |
| Native L28 ledger / coinbase | Not present |

`L28Bridge.sol` is **EVM interoperability code**. It is **not** Bitcoin
support and **not** native L28. Destination examples in the contract comments
are EVM chain identifiers (`polygon`, `bsc`). Owner/validator/fee controls do
not confer L28 issuance, height, or validation authority.

The Future Capability Registry and the bounded testnet audit already record
that wrapped/bridge artifacts are not native L28. This Foundation preserves
that classification.

### 2.3 `contracts/deploy_bridge.py`

| Field | Classification |
|---|---|
| Path | `contracts/deploy_bridge.py` |
| Observed purpose | EVM bridge deployment helper / cost estimator |
| Networks referenced | Ethereum, BNB Smart Chain, Polygon, Avalanche, Arbitrum, Optimism, Base |
| Bitcoin | Not present |

`deploy_bridge.py` MUST NOT be executed by this Foundation. It is an EVM
deployment utility, not a Bitcoin adapter, not a Bitcoin wallet, and not an
L28 consensus component. Execution would be a separate, later-authorized
operator action outside Foundation 93.

### 2.4 Classification summary

| Artifact | Native L28 | Bitcoin support | Authority over L28 economics | This Foundation |
|---|---|---|---|---|
| `coin/multi_coin_miner.py` | No | No (local hash helper only) | None | Classify only; do not run |
| `contracts/L28Bridge.sol` | No | No (EVM lock/release) | None | Classify only; do not deploy |
| `contracts/deploy_bridge.py` | No | No (EVM deploy helper) | None | Classify only; do not execute |

---

## 3. Bitcoin adapter model

### 3.1 Conceptual direction

```
Bitcoin network
    ↓
Bitcoin observer / proof verifier
    ↓
Bitcoin interoperability adapter
    ↓
Canonical L28 Universal Access boundary
    ↓
L28 protocol validation
```

Each arrow is a **one-way evidence path**. Lower layers MUST NOT become
authorities for layers above them.

### 3.2 Layer duties

| Layer | May do (future) | Must not do |
|---|---|---|
| Bitcoin network | Produce public chain data | Define L28 identity |
| Observer / proof verifier | Check public Bitcoin facts against a declared network and proof | Sign, broadcast, custody, or mint L28 |
| Bitcoin interoperability adapter | Normalize public observation results into a future L28-facing evidence object | Become a validation authority |
| Canonical L28 Universal Access boundary | Accept or reject adapter-mapped public objects under UAII rules | Embed Bitcoin private material or override Protocol |
| L28 protocol validation | Validate **L28** transactions via `validate_transaction` | Accept Bitcoin proofs as L28 coinbase, height, or supply |

### 3.3 Adapter is not a validator

The adapter MUST NOT become a validation authority.

- Sole L28 transfer/coinbase validator remains `validate_transaction` in
  `coin/tx_validation.py`.
- Sole L28 issuance mechanism remains coinbase.
- Sole L28 height authority remains consensus-derived canonical height.
- Adapters MUST map 1:1 to a future authorized public interface. They MUST
  NOT override economics, historical evidence, or validation.

An adapter disagreement, missing observer, or unverifiable proof MUST fail
closed. Silence, defaults, or “best effort” MUST NOT invent Bitcoin or L28
state.

### 3.4 Relationship to CoreL28Node / L28P2PNode

Foundation 19 separates native policy (`CoreL28Node`) from untrusted
transport (`L28P2PNode`). A future Bitcoin observer is closer to an
**external evidence source** than to either role:

- it is not CoreL28Node;
- it is not L28P2PNode;
- it cannot authorize ledger mutation;
- it cannot supply canonical L28 height.

---

## 4. Initial capability mode

The safest first Bitcoin capability MUST be **read-only observation /
verification**.

No future Bitcoin adapter implementation may begin with signing, broadcast,
custody, wrapping, lock/release, or L28 mint/burn.

### 4.1 Possible future public facts

A later authorized observation object MAY expose only public facts, for
example:

- Bitcoin network identifier
- block hash
- block height
- transaction id
- output index
- amount in satoshis
- confirmations
- script/address representation where safe
- Merkle inclusion evidence
- proof-verification result

All such fields are **Bitcoin-domain public evidence**. They MUST be labeled
as Bitcoin facts. They MUST NOT be silently copied into L28 amount, height,
`IssuedSupply`, or identity fields.

### 4.2 Forbidden in observation mode

- Bitcoin private keys, seeds, xprvs, wallet descriptors containing secrets
- RPC credentials
- signing-device material
- broadcast authorization
- spend authorization
- L28 `execution_authorized=true`
- any field implying L28 mint, burn, or settlement finality from Bitcoin data

### 4.3 Observation result flags

Any future public observation success object MUST keep, at minimum:

- `execution_authorized` = false
- `spend_authorized` = false
- `signing_authorized` = false
- `ledger_mutated` = false
- `transaction_submitted` = false
- `l28_issuance_authorized` = false
- `native_asset` = false for BTC and wrapped-BTC representations

---

## 5. Proof and trust models

This section compares candidate observation models **without implementing
them** and **without selecting a production architecture**. Repository
evidence is not sufficient to choose a production Bitcoin proof stack.
Unresolved selections are marked
`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

### 5.1 Bitcoin Core RPC observer

| Field | Assessment |
|---|---|
| Mechanism | Query a Bitcoin Core (or equivalent) node over RPC for headers, transactions, and confirmations |
| Trust assumptions | Operator trusts that node’s view, configuration, network, and RPC authentication |
| Security properties | Full-node verification is strong **if** the node is honest, synced, and on the intended network |
| Failure modes | Wrong network, stale tip, RPC credential leak, operator-controlled lie, connectivity loss |
| Observation only | Acceptable as a **candidate** local observer after a later security decision |
| Later settlement evidence | Not sufficient by itself; a single RPC view is operator-trusted |
| Decision | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |

RPC credentials are custody-adjacent secrets. They MUST NEVER enter UAII
payloads, prompts, logs, hosted models, or public adapters.

### 5.2 SPV / header-chain verification

| Field | Assessment |
|---|---|
| Mechanism | Verify proof-of-work header chain and use headers to check inclusion |
| Trust assumptions | Honest-majority hashpower; correct network magic/genesis; complete enough header set |
| Security properties | Better than blind RPC if headers are independently checked; still probabilistic |
| Failure modes | Eclipse/fake-header attacks if peers are captured; reorgs; wrong genesis/network |
| Observation only | Acceptable as a **candidate** after a later security decision |
| Later settlement evidence | Stronger than a single RPC quote, still not absolute finality |
| Decision | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |

### 5.3 Merkle transaction inclusion proof

| Field | Assessment |
|---|---|
| Mechanism | Merkle path from transaction to a block hash that is itself justified |
| Trust assumptions | The referenced block hash is on the intended canonical Bitcoin chain |
| Security properties | Proves inclusion **in that block**, not that the block remains canonical |
| Failure modes | Valid Merkle path to a stale/orphaned/wrong-network block; incomplete path; mutated txid |
| Observation only | Useful **composed with** a header/tip policy |
| Later settlement evidence | Insufficient alone; must bind network identity, tip policy, and reorg rules |
| Decision | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` (composition required) |

### 5.4 Multiple independent observer quorum

| Field | Assessment |
|---|---|
| Mechanism | Require agreement among N independently operated observers |
| Trust assumptions | Observer independence; non-collusion; shared network identity |
| Security properties | Reduces single-operator lie; does not create Bitcoin consensus |
| Failure modes | Correlated infrastructure; quorum split; ambiguous disagreement |
| Observation only | Acceptable as a **candidate** fail-closed composition |
| Later settlement evidence | May strengthen evidence; disagreement MUST fail closed |
| Decision | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` (N, independence, timeout unset) |

### 5.5 External oracle model

| Field | Assessment |
|---|---|
| Mechanism | A third party attests Bitcoin facts |
| Trust assumptions | Oracle honesty and availability |
| Security properties | Weakest of the listed models for adversarial settings |
| Failure modes | Oracle capture, downtime, ambiguous attestation, key compromise |
| Observation only | Not preferred; only conceivable as explicitly labeled untrusted metadata |
| Later settlement evidence | Not sufficient |
| Decision | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` — default posture is reject-for-settlement |

### 5.6 Production selection

This Foundation does **not** select a production proof architecture.
A later foundation MUST publish a threat model and choose among (or compose)
the models above. Until then, no Bitcoin adapter implementation is authorized.

---

## 6. Reorg / finality model

Bitcoin confirmations are **probabilistic**, not absolute finality.

L28 canonical height is consensus-derived and fail-closed when missing.
Bitcoin height is a different domain and MUST remain labeled as Bitcoin
height.

### 6.1 Future requirements (not implemented here)

A later Bitcoin observation specification MUST define:

1. **Minimum confirmation policy** — a declared, network-specific policy
   object. This Foundation does **not** hard-code a production confirmation
   count.
2. **Reorg handling** — previously accepted observations that no longer
   descend from the declared canonical Bitcoin tip MUST be marked stale and
   MUST NOT be reused as fresh evidence.
3. **Stale proof rejection** — proofs bound to orphaned or insufficiently
   confirmed blocks MUST fail closed.
4. **Conflicting chain-tip evidence** — two observers reporting incompatible
   tips for the same declared network MUST fail closed.
5. **Explicit network identity** — mainnet, testnet, signet, regtest, and
   unknown networks are distinct. Unknown or omitted network identity MUST
   fail closed.
6. **Fail closed when canonical Bitcoin state cannot be established** —
   missing headers, unsynced observers, or quorum disagreement are not
   “zero confirmations”; they are unavailable state.

### 6.2 Confirmation count

A production confirmation count is
`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

Any later number MUST be justified by a threat model for the intended
Bitcoin network and use case (observation vs later settlement evidence).
Convenience MUST NOT set the number.

### 6.3 No conversion of Bitcoin finality into L28 finality

Even a deeply confirmed Bitcoin transaction MUST NOT be treated as:

- L28 settlement finality
- L28 coinbase
- L28 ledger mutation
- an L28 refund or mint

---

## 7. Custody boundary

Foundation 93 MUST NOT implement custody.

### 7.1 Forbidden material

The following MUST NEVER enter prompts, UAII payloads, logs, hosted models,
or public adapters:

- Bitcoin private keys
- seed phrases
- xprvs
- wallet credentials
- descriptors containing secrets
- signing devices / device PINs
- RPC credentials
- L28 private keys or seeds (unchanged UAII rule)

### 7.2 Authority separation

| Authority | Future home | This Foundation |
|---|---|---|
| Bitcoin observation | External observer / proof verifier | Specified only |
| Bitcoin signing | Isolated local signer/wallet boundary | Not implemented |
| L28 signing | Isolated local signer (Foundations 64+) | Unchanged; not Bitcoin |
| L28 validation | `validate_transaction` | Unchanged |

Observation and signing MUST remain **separate authorities**. An observation
adapter that can sign or broadcast is a custody and activation failure.

### 7.3 Existing EVM deploy helper

`contracts/deploy_bridge.py` can reach public EVM RPCs if executed. That is
an EVM operational risk, not a Bitcoin custody design. This Foundation MUST
NOT run it and MUST NOT treat its chain list as a Bitcoin network registry.

---

## 8. Future payment models

The following models are **described only**. None is authorized,
implemented, or ranked as selected.

### 8.1 Model catalog

| ID | Model | Summary |
|---|---|---|
| A | Bitcoin as external payment evidence | A verified Bitcoin payment is cited as public evidence that an off-L28 transfer occurred. L28 state does not change unless a later, separately authorized L28 transaction is independently valid. |
| B | Atomic-swap-compatible future model | Hash- or adaptor-signature-locked complementary transactions across Bitcoin and L28. Requires future isolated signers on both sides and a later protocol for timeouts. |
| C | Wrapped representation | An EVM or other-chain token claims to represent BTC or L28. The token is not native L28 and not BTC. |
| D | Lock/release bridge | Lock value on one chain and release on another under validators/oracles. `L28Bridge.sol` is an EVM example of this *pattern*, not a Bitcoin or native-L28 implementation. |
| E | Custodial gateway | An operator takes BTC or L28 and credits an internal balance. Highest custody concentration. |

### 8.2 Trust / security complexity (increasing)

1. **A — External payment evidence** (lowest additional L28 authority; still
   needs a proof/reorg policy)
2. **B — Atomic-swap-compatible** (high protocol and signer complexity; no
   wrap/mint if correctly isolated)
3. **C — Wrapped representation** (identity confusion risk; registry already
   rejects wrap-as-native)
4. **D — Lock/release bridge** (validator/oracle and liquidity risk; EVM
   artifact already present and non-native)
5. **E — Custodial gateway** (highest trust; incompatible with
   “no secrets in adapters/hosted models”)

This ranking is a **complexity/trust comparison**, not an authorization
order and not a product roadmap.

### 8.3 Authorization status

All five models are **unauthorized**. Model A is the only class that can
later be considered as an extension of read-only observation, and only after
the activation gates in §13.

---

## 9. Supply firewall

Bitcoin interoperability MUST NOT:

- mint L28
- burn L28 outside frozen Protocol rules
- change the hard cap **28,000,000 L28**
- change the emission ceiling **11,130,000 L28**
- change historically mined **2,824,584 L28**
- change treasury locked **500,000 L28**
- change circulating snapshot **2,324,584 L28**
- bypass coinbase-only issuance
- supply canonical height
- override `validate_transaction`
- rewrite historical evidence

These facts are Protocol v1.0.0 invariants and Foundation 91 conformance
constants. A Bitcoin adapter that presents different numbers, a non-coinbase
issuance mechanism, or a Bitcoin height as L28 height MUST fail closed with
an override-forbidden or equivalent fail-closed code.

Bitcoin satoshi amounts MUST remain satoshi amounts. They MUST NOT be
coerced into L28 units.

---

## 10. Failure policy

Future Bitcoin interoperability MUST fail closed for:

| Condition | Required behavior |
|---|---|
| Unknown Bitcoin network | Reject; no default network |
| Malformed proof | Reject; no repair |
| Insufficient proof | Reject; no “unconfirmed accept” |
| Chain-tip conflict | Reject both conflicting tips |
| Stale / reorged evidence | Reject; do not reuse |
| Adapter disagreement | Reject; no majority invention without a later-approved quorum rule |
| Missing required state | Reject; no implicit clock, tip, or RPC fallback |
| Identity confusion (BTC as L28) | Reject |
| Wrapped/native asset confusion | Reject |
| Attempted L28 economic override | Reject (`adapter_override_forbidden` or equivalent) |
| Secret material presented to the adapter | Reject (`secret_material_forbidden` or equivalent); do not log secrets |

Fail closed means: no L28 ledger mutation, no implied grant, no guessed
network, and no conversion of missing Bitcoin state into a zero or default
success.

---

## 11. Universal Access relationship

Bitcoin interoperability is an **external adapter/capability layer**.

It MUST map into canonical L28 interfaces if and when a later interface
profile is authorized. It MUST NOT require changing native L28 Protocol
v1.0.0.

### 11.1 UAII v0.1 is unchanged

Foundation 93 does **not** add Bitcoin operations to
`l28-universal-ai-access-interface/v0.1`.

Deferred UAII adapters remain metadata only:

- `adapter.mcp`
- `adapter.rest_openapi`
- `adapter.python_sdk`
- `adapter.typescript_sdk`

A Bitcoin observer is **not** one of those adapters and MUST NOT be smuggled
into `discover_capabilities` as a supported native operation in v0.1.

### 11.2 Future extension / versioning requirements

A later foundation that wants a public Bitcoin observation operation MUST:

1. Publish a new interface profile or plan version (not silently extend v0.1).
2. Keep Bitcoin fields in a Bitcoin-labeled object (network id, txid,
   satoshis, confirmations, proof).
3. Keep all grant/mutation flags false for observation.
4. Reject secret fields at the envelope.
5. Remain subordinate to Protocol v1.0.0 and `validate_transaction`.
6. Add conformance cases before implementation (see §12).

On conflict, Protocol v1.0.0 prevails over UAII; UAII prevails over this
Bitcoin design document for interface field names.

---

## 12. Future conformance requirements

No Bitcoin adapter implementation may begin until a later conformance plan
includes at least these isolated, deterministic cases:

| Area | Required cases |
|---|---|
| Network identity | Known network accepted as labeled; unknown/omitted rejected |
| Valid proof | Schema-valid public proof + declared policy → observation accept, flags false |
| Invalid proof | Malformed / incomplete Merkle or header material → reject |
| Wrong-network proof | Mainnet proof on testnet identity (and reverse) → reject |
| Reorg | Evidence that was valid under tip T0 becomes stale under tip T1 → reject reuse |
| Replay | Same evidence id presented after accept → fail-closed replay |
| Duplicate evidence | Duplicate txid/outpoint under the same network → fail closed |
| Stale confirmation | Confirmations below the later-declared policy → reject |
| Adapter disagreement | Two observers, incompatible tips → reject |
| Secret injection | Private key, seed, xprv, RPC password in payload → `secret_material_forbidden` |
| Attempted signing | Bitcoin sign operation → `operation_unsupported` |
| Attempted broadcast | Bitcoin broadcast operation → `operation_unsupported` |
| L28 mint/supply/height override | Bitcoin adapter sets hard cap, mined supply, or L28 height → `adapter_override_forbidden` |
| Wrapped/native substitution | `asset_id=L28` for BTC or wrap → reject |
| Deterministic serialization | Identical canonical public inputs → identical public outcomes |

Tests MUST be disposable and MUST NOT call Bitcoin networks, RPC, or wallets.

---

## 13. Activation gates

No Bitcoin implementation may proceed until **each** of the following is
separately approved by a later authorized foundation or operator decision:

1. Threat model
2. Proof model
3. Custody model
4. Reorg / confirmation policy
5. Conformance plan
6. Isolated tests
7. Security review
8. Operator authorization

Absence of any gate is a block, not a default-allow. Documentation in this
file does not satisfy any gate.

---

## 14. Non-activation checklist

Foundation 93 created exactly this specification file. It MUST NOT:

| Action | Status |
|---|---|
| Bitcoin network calls | Forbidden |
| Bitcoin Core / RPC | Forbidden |
| Start a node | Forbidden |
| Mine BTC | Forbidden |
| Create/import Bitcoin wallets | Forbidden |
| Generate keys | Forbidden |
| Sign Bitcoin transactions | Forbidden |
| Broadcast Bitcoin transactions | Forbidden |
| Deploy `L28Bridge.sol` | Forbidden |
| Execute `deploy_bridge.py` | Forbidden |
| Run `multi_coin_miner.py` as Bitcoin mining | Forbidden |
| Start L28 networking | Forbidden |
| Modify ledger or consensus | Forbidden |
| Modify Protocol v1.0.0 | Forbidden |
| Add UAII v0.1 Bitcoin operations | Forbidden |

---

## 15. Document control

| Field | Value |
|---|---|
| Foundation | 93 |
| Status | specification / non-activating |
| Parent | `6ae914709d84f90371b2b44841e6c344da9b694f` |
| Implementation | none |
| Bitcoin operations added to UAII v0.1 | none |
| Production confirmation count | unset (`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`) |
| Production proof architecture | unset (`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`) |
| Payment model authorized | none |

Protected economic facts restated for firewall continuity (unchanged):

| Fact | Value |
|---|---:|
| Hard cap | 28,000,000 L28 |
| Emission ceiling | 11,130,000 L28 |
| Historically mined | 2,824,584 L28 |
| Treasury locked | 500,000 L28 |
| Circulating snapshot | 2,324,584 L28 |
| Issuance | coinbase only |
| Height authority | consensus-derived |
| Historical evidence | immutable |
