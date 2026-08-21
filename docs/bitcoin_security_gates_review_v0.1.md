# Bitcoin Security Gates Review v0.1

**Foundation:** 106

**Status:** security-gates review / non-activating

**Document version:** `bitcoin-security-gates-review/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Parent:** `84630c4f47aef9435aaa05b568d559040caaa76e`

**Branch:** `foundation106-bitcoin-security-gates-review`

**Implementation:** none

**Runtime activation:** none

**Network activity:** none

**Wallet / signing activity:** none

**Existing files modified:** none

**Normative subordination:** This document is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md). On conflict, Protocol v1.0.0 prevails.
It is also subordinate to Foundation 93 (adapter boundary), Foundation 94
(implementation gate catalog), and Foundation 105 (threat-model review).
It MUST NOT redefine settlement, issuance, supply, consensus height
authority, historical evidence, or `validate_transaction`.

---

## 1. Status

Foundation 106 documents the **remaining security gates** that MUST be
satisfied before any future Bitcoin interoperability activation.

This document is **documentation only**. It is **non-activating**. It does
not implement an adapter, select a production proof architecture, choose a
confirmation count, choose an observer quorum, authorize custody or
signing, or permit Bitcoin or L28 runtime activity.

| Statement | Status |
|---|---|
| Foundation | 106 |
| Activation | none |
| Protocol v1.0.0 | FROZEN |
| Bitcoin relationship to L28 consensus | **External.** Bitcoin is not L28 consensus. |

Bitcoin interoperability, if ever authorized later, remains **external
evidence at most**. Observation is not settlement. Passing prior fixtures
or this review is **not** permission to spend L28, mint L28, mine BTC,
open listeners, or treat Bitcoin state as L28 state.

Absence of any remaining gate is a **block**, not a default-allow.
Missing required security decisions fail closed.

---

## 2. Current completed security foundation

The following prior work is **consumed, not altered**. Completion of these
items does **not** satisfy the remaining gates in §3 and does **not**
activate Bitcoin runtime.

| Foundation | Artifact | What it completed | What it did not do |
|---|---|---|---|
| F93 | `docs/bitcoin_interoperability_spec.md` | Design-only adapter boundary, identity firewall, proof/trust catalog, non-activation | No implementation; no proof-architecture selection |
| F94 | `docs/bitcoin_interoperability_conformance_plan_v0.1.md` | Conformance plan and implementation-gate catalog | Plan only; no fixtures in that foundation |
| F95 NID | `fx-btc-v01-0001`–`0005` + network-identity tests | Explicit Bitcoin network labels; unknown/missing/conflict fail closed | No live network identity; no default network |
| F96 PRF | `fx-btc-v01-0006`–`0011` + proof-validation tests | Structural public-proof accept/reject under caller-supplied **test** policy | Not cryptographic production verification |
| F97 WRN | `fx-btc-v01-0012`–`0016` + wrong-network tests | No cross-network repair or coercion | No P2P/RPC wrong-network delivery |
| F98 REO | `fx-btc-v01-0017`–`0021` + reorg/stale tests | Stale reuse and unavailable-tip fail closed | No production confirmation or reorg policy |
| F99 RPL | `fx-btc-v01-0022`–`0025` + replay/duplicate tests | Evidence-id and txid/outpoint uniqueness in fixtures | No production evidence store |
| F100 AGR | `fx-btc-v01-0026`–`0029` + observer-agreement tests | Disagreement and missing test-local quorum state fail closed | No production observer N |
| F101 SEC | `fx-btc-v01-0030`–`0037` + secret/signing/broadcast tests | Forbidden fields and unsupported sign/broadcast operations | No wallet, keys, or signer |
| F102 ECO | `fx-btc-v01-0038`–`0045` + economic-authority tests | `adapter_override_forbidden` for economics, height, validation, history | No production adapter isolation beyond tests |
| F103 IDN | `fx-btc-v01-0046`–`0051` + native/wrapped identity tests | BTC / wrap / bridge ≠ native L28 | No wrap product; no bridge execution |
| F104 DET | `fx-btc-v01-0052`–`0057` + deterministic-serialization tests | Duplicate keys, unknown fields, uppercase hex, and inference fail closed | Not a production serializer |
| F104A | NID shared fixture-discovery compatibility | Compatibility fix so NID discovery remains isolated and deterministic | No Bitcoin activation; no family expansion |
| F105 | `docs/bitcoin_interoperability_threat_model_v0.1.md` | Threat-model review (Foundation 94 gate item 4) | Did not select proof, confirmation, quorum, custody, or operator authorization |

These 57 fixtures and 10 isolated test modules remain **conformance
artifacts**. They exercise documented fail-closed behavior against fictional
public inputs. They do not demonstrate live Bitcoin network security and
they do not satisfy remaining gates A–F below.

Every completed Bitcoin fixture retains `not_production_policy = true` and:

- `production_proof_architecture = BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`
- `production_confirmation_count = BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`
- `production_quorum = BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

---

## 3. Remaining security gates

Foundation 94 requires Bitcoin adapter implementation to remain blocked
until each remaining item is **separately** completed. Foundation 105
satisfied threat-model review only. Foundation 106 records the still-open
gates. **None of the following is satisfied by this document.**

### A. Proof-model decision

A later foundation MUST choose among (or compose) candidate observation
models. This review **analyzes** them and **does not select** an
architecture.

| Candidate | Trust / threat summary | Why it is not selected here |
|---|---|---|
| Bitcoin Core / RPC observer | Operator trusts one node’s view, configuration, network, and RPC authentication. Failure modes include wrong network, stale tip, credential leak, operator-controlled lie, and connectivity loss. | A single RPC view is operator-trusted. RPC credentials are custody-adjacent secrets and MUST NEVER enter adapters, prompts, logs, or hosted models. |
| SPV / header-chain verification | Assumes honest-majority hashpower, correct network magic/genesis, and a complete enough header set. Failure modes include eclipse/fake-header attacks, reorgs, and wrong genesis. | Stronger than blind RPC **if** headers are independently checked; still probabilistic. No SPV/P2P code is authorized. |
| Merkle inclusion proof | Proves inclusion **in a referenced block**, not that the block remains canonical. Failure modes include a valid path to a stale, orphaned, or wrong-network block. | Insufficient alone; must bind network identity, tip policy, and reorg rules in a later composition. |
| Multiple independent observers | Reduces a single-operator lie **if** independence is real. Failure modes include collusion, common-provider dependence, quorum split, and invented majority. | Does not create Bitcoin consensus. Test-local observer counts are not a production N. |

F96 `PRF` tests structural public-proof shape under a **caller-supplied
test policy**. That is not a production proof stack.

**Production proof architecture:**

`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

No architecture is selected. No RPC, SPV, P2P, or explorer client is
authorized by this document.

### B. Reorg / finality decision

Bitcoin confirmations are **probabilistic**, not absolute finality. L28
canonical height is consensus-derived and fail-closed when missing.
Bitcoin height MUST remain Bitcoin-domain height.

| Requirement | Analysis |
|---|---|
| Stale evidence | Previously accepted observations that no longer descend from a declared Bitcoin tip MUST be marked stale and MUST NOT be reused as fresh evidence. |
| Conflicting tips | Incompatible tips for the same declared network MUST fail closed. They are not a majority puzzle to solve by convenience. |
| Reorg handling | A later observation specification MUST define how reorged evidence is invalidated. This Foundation does not write that policy. |
| Confirmation policy | A later specification MUST declare a network-specific minimum confirmation policy. Convenience MUST NOT set the number. |
| Missing required state | Missing headers, unsynced observers, or unavailable tip state are `required_state_unavailable`, not “zero confirmations.” |

F98 `REO` already asserts these fail-closed **conformance** outcomes
against fictional tips. Caller-supplied `test_min_confirmations` values
are test-only. They are **not** a production confirmation count.

Even a later, deeply confirmed Bitcoin transaction MUST NOT be treated as
L28 settlement, coinbase, refund, mint, or ledger mutation.

**Production confirmation count:**

`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

No confirmation number is chosen. No production reorg/finality policy is
chosen.

### C. Observer quorum decision

| Topic | Analysis |
|---|---|
| Independence | Distinct observer names that share one RPC host, explorer, image, or operator are not independent. |
| Disagreement | Incompatible public facts MUST yield `observer_disagreement` or equivalent. An adapter MUST NOT invent a majority. |
| Correlated failures | Common-provider dependence, eclipse/isolation, and stale synchronization can make N observers behave as one. |
| Missing quorum state | Required but unavailable observer state MUST fail closed (`required_state_unavailable`). It MUST NOT degrade to a single observer. |

F100 `AGR` already fails closed on disagreement and missing **test-local**
quorum state. Fixture `test_observer_count` is not a production quorum.

**Production observer quorum:**

`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

No quorum number is chosen. Independence criteria and timeout remain unset.

### D. Custody / signing architecture

Observation and signing are **separate authorities**.

Observers and adapters MUST NOT receive or control:

- private keys
- seed phrases
- mnemonics
- xprv
- wallet secrets
- RPC credentials
- signing authority
- broadcast authority

F101 `SEC` already rejects documented secret field names and unsupported
sign/broadcast operations in isolated fixtures. Those fixtures use
disposable forbidden-field markers, not real secrets.

An observation adapter that can sign or broadcast is a custody and
activation failure.

An isolated signer architecture, if ever authorized, MUST be a **later
governed milestone**. It MUST NOT be reachable from the observation path.
This Foundation does **not** implement signing, wallets, or key creation.

### E. Independent security review

A later independent security review is **required** before any Bitcoin
runtime activation. This Foundation 106 document is **not** that review.

| Item | Required content |
|---|---|
| Review scope | Adapter boundary; observer/proof path; parser/serialization; secret/custody separation; L28 economic and identity firewall; non-activation of UAII v0.1 Bitcoin operations |
| Threat coverage | Foundation 105 threat matrix families `NID`, `PRF`, `WRN`, `REO`, `RPL`, `AGR`, `SEC`, `ECO`, `IDN`, `DET`, plus live eclipse, operator-control, correlated observers, and production parser divergence |
| Acceptance criteria | Protocol v1.0.0 unchanged; Bitcoin remains external; observation ≠ settlement; no secrets in adapters/prompts/logs; all grant/mutation flags remain false for observation; missing gates still fail closed; no silent selection of proof architecture, confirmation count, or quorum |

Passing isolated fixtures is **not** acceptance. The review MUST be
independent of the implementing operator’s convenience.

### F. Operator authorization gate

Explicit operator authorization is **required** before any of the
following:

- runtime activation of a Bitcoin observer or adapter
- networking (Bitcoin RPC, SPV, P2P, or equivalent)
- wallets
- signing
- broadcast
- settlement that cites Bitcoin evidence (which still cannot itself be L28
  settlement)

Documentation, merged fixtures, threat-model review, and this gates review
are **not** operator authorization.

Authorization MUST be specific. A general “Bitcoin interoperability exists
as documents” statement MUST NOT be treated as permission to open
listeners, import keys, or mutate ledgers.

---

## 4. Explicit non-goals

Foundation 106 MUST NOT and does not:

- create or run a Bitcoin runtime
- connect Bitcoin Core or use Bitcoin RPC
- start SPV or Bitcoin P2P
- create, import, or use wallets
- generate or handle keys
- sign Bitcoin or L28 transactions as a Bitcoin adapter
- broadcast Bitcoin transactions
- mine BTC
- deploy `contracts/L28Bridge.sol` or execute `contracts/deploy_bridge.py`
- activate settlement
- select a production proof architecture
- choose a production confirmation count
- choose a production observer quorum
- modify Protocol v1.0.0
- add Bitcoin operations to UAII v0.1

---

## 5. L28 firewall

Bitcoin cannot control:

- issuance
- supply
- canonical height
- validation
- consensus
- history
- settlement authority

Protected Protocol facts remain exact and MUST NOT be recalculated:

| Fact | Value |
|---|---|
| Hard cap | 28,000,000 L28 |
| Emission ceiling | 11,130,000 L28 |
| Historically mined | 2,824,584 L28 |
| Treasury locked | 500,000 L28 |
| Circulating snapshot | 2,324,584 L28 |
| Halving interval | 210,000 |
| Reward sequence | 28 → 14 → 7 → 3 → 1 → 0 |
| Historical mined-through entry | 100,877 |
| Next canonical height after bootstrap | 100,878 |
| Issuance | coinbase only |
| Height authority | consensus-derived |
| Historical evidence | immutable |
| Adapter override allowed | false |

Sole L28 transfer/coinbase validator remains `validate_transaction`.
Attempted adapter overrides remain `adapter_override_forbidden`.
Bitcoin height MUST NEVER become L28 canonical height.

### 5.1 Harness / Evals

Any **Harness/Evals** capability is an **optional isolated commerce
subsystem**.

| Rule | Status |
|---|---|
| Role | Advisory only |
| Protocol authority | **None** |
| Issuance / supply / height / validation / consensus / history / settlement | MUST NOT be controlled by Harness/Evals |
| Bitcoin activation | MUST NOT be implied by the existence of Harness/Evals |

Harness/Evals MUST NOT be treated as a Bitcoin observer, a proof
architecture, a confirmation policy, a quorum, a wallet, or an L28
authority. Advisory output is not settlement and is not Protocol v1.0.0.

---

## 6. Final gate status table

| Gate | Status |
|---|---|
| Proof architecture | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Confirmation policy | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Observer quorum | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Custody / signing | Future governed milestone |
| Security review | Required |
| Operator authorization | Required |

Bitcoin adapter implementation remains **blocked**. Foundation 106
satisfies **security-gates review documentation only**. It does not satisfy
proof-model decision, reorg/finality decision, custody/signing
architecture, independent security review, or operator authorization.

---

## 7. Document control

| Field | Value |
|---|---|
| Foundation | 106 |
| Parent | `84630c4f47aef9435aaa05b568d559040caaa76e` |
| Path | `docs/bitcoin_security_gates_review_v0.1.md` |
| Status | security-gates review / non-activating |
| Implementation | none |
| Runtime activation | none |
| Network activity | none |
| Wallet / signing activity | none |
| Existing files modified | none |
| Bitcoin operations added to UAII v0.1 | none |
| Production proof architecture | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production confirmation count | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production observer quorum | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Custody / signing architecture | future governed milestone |
| Independent security review | required; not this document |
| Operator authorization | required; not this document |
| Payment model authorized | none |
| Harness/Evals protocol authority | none |
