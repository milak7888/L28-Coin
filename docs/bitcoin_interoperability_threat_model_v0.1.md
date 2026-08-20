# Bitcoin Interoperability — Threat-Model Review v0.1

**Foundation:** 105

**Status:** threat-model review / non-activating

**Document version:** `bitcoin-interoperability-threat-model/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Parent:** `c9585b08a302c1122e46693efc8cb8a2a6f43b34`

**Branch:** `foundation105-bitcoin-interoperability-threat-model-review`

**Implementation:** none

**Runtime activation:** none

**Network activity:** none

**Wallet / signing activity:** none

**Existing fixtures modified:** none

**Existing tests modified:** none

**Authoritative inputs (consumed, not altered):**

- `docs/bitcoin_interoperability_spec.md` (Foundation 93)
- `docs/bitcoin_interoperability_conformance_plan_v0.1.md` (Foundation 94)
- `conformance/bitcoin_interoperability/v0.1/fixtures/fx-btc-v01-0001.json` through `fx-btc-v01-0057.json`
- `tests/test_bitcoin_interoperability_*fixtures.py` (10 isolated modules)

**Normative subordination:** This document is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md). On conflict, Protocol v1.0.0 prevails.
This review is also subordinate to Foundation 93 for adapter-boundary rules
and to Foundation 94 for conformance family mapping. It MUST NOT redefine
settlement, issuance, supply, consensus height authority, historical
evidence, or `validate_transaction`.

---

## 1. Title, status, and scope

Foundation 105 is the **Bitcoin interoperability threat-model review**
required as item 4 of the Foundation 94 implementation gate.

This document is **documentation and security analysis only**. It is
**non-activating**. It does not implement an adapter, select a production
proof architecture, choose a confirmation count, choose an observer quorum,
authorize custody or signing, or permit Bitcoin or L28 runtime activity.

### 1.1 Explicit statements

- Bitcoin interoperability is **external** to L28 consensus.
- Bitcoin has **zero authority** over L28 issuance, supply, canonical
  height, validation, consensus, history, or settlement authorization.
- **Observation is not settlement.** An observation-accept in a fixture is
  not Bitcoin finality and is not L28 ledger mutation.
- **Passing fixtures does not activate** Bitcoin RPC, SPV, P2P, wallet,
  signing, broadcast, mining, bridging, or settlement.
- **Missing required security decisions fail closed.** Absence of a later
  gate is a block, not a default-allow.

### 1.2 What this review is not

This review is not a production security certification, not a Bitcoin
finality proof, not an independent third-party audit, and not operator
authorization. Completed Foundation 95–104 fixtures and isolated tests are
**conformance artifacts**. They exercise documented fail-closed behavior
against fictional public inputs. They do not demonstrate live Bitcoin
network security.

---

## 2. Security objective

If Bitcoin evidence is introduced later, the following MUST remain true
regardless of observer honesty, proof quality, confirmation depth, or
adapter result:

1. L28 Protocol v1.0.0 remains the sole native settlement and issuance
   authority.
2. L28 issuance remains coinbase-only. Bitcoin evidence MUST NOT mint,
   burn, or otherwise create L28.
3. L28 canonical height remains consensus-derived. Bitcoin height MUST
   remain Bitcoin-domain height.
4. Sole L28 transfer/coinbase validator remains `validate_transaction` in
   `coin/tx_validation.py`.
5. Historical evidence remains immutable. Bitcoin adapters MUST NOT rewrite
   L28 history, supply records, or genesis/hash/snapshot evidence.
6. BTC, wrapped BTC, wrapped L28, and native L28 remain distinct identities.
   A bridge contract MUST NOT define native L28 identity.
7. Private-key and wallet-custody material, signing authority, and
   broadcast authority MUST remain outside observers, adapters, UAII
   payloads, logs, and hosted models. RPC credentials MUST NEVER enter UAII
   payloads, prompts, logs, hosted models, or public adapters; any credential
   use by a future separately authorized local RPC observer remains part of
   the later proof/observer security architecture.
8. Observation success MUST NOT grant execution, spend, signing, broadcast,
   ledger mutation, settlement finality, or L28 issuance.
9. Where required Bitcoin or public state cannot be established without
   forbidden inference (clock, network, environment, or hidden state),
   evaluation MUST fail closed.

The security objective is **containment**: Bitcoin may later be cited as
labeled external evidence at most. It MUST NEVER become an L28 authority.

---

## 3. Protected assets

The following assets remain protected if any future Bitcoin observation
path is considered. Values are restated exactly; they MUST NOT be
recalculated, rounded, derived, or replaced by caller input.

### 3.1 Protocol v1.0.0 economic and height invariants

| Protected fact | Exact value |
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
| Issuance mechanism | coinbase only |
| Height authority | consensus-derived |
| Historical evidence | immutable |
| Adapter override allowed | false |
| Protocol version | 1.0.0 |

### 3.2 Authority surfaces

| Asset | Protection |
|---|---|
| Issuance authority | Coinbase-only; no adapter mint, burn, or non-coinbase issuance path |
| Canonical height | Consensus-derived; Bitcoin height is never L28 height |
| Validation authority | Solely `validate_transaction`; adapters cannot force accept/reject |
| Historical evidence | Immutable; no replace/mutate/repair of historical records |
| Supply records | Exact protected totals above; no caller-provided substitutes |
| Asset identity | BTC ≠ wrapped BTC ≠ wrapped L28 ≠ native L28; no symbol/name inference |
| Secret material | Private keys, seeds, mnemonics, xprv, RPC credentials, and wallet secrets never enter adapters |
| Deterministic conformance behavior | Identical canonical public inputs produce equivalent public outcomes; no clock/env/network inference |
| Future signing / custody boundaries | Observation and signing remain separate authorities; neither is implemented here |

---

## 4. Trust boundaries

Each boundary below is a one-way evidence path. Lower layers MUST NOT
become authorities for layers above them. The conceptual direction remains:

```
Bitcoin network
    → observer / proof verifier
    → Bitcoin interoperability adapter
    → Universal Access boundary
    → L28 protocol validation
```

A future isolated signer, if ever authorized, is a **separate** authority
and MUST NOT be embedded in or directly controlled by the observation path.
Any future interface between observation and signing remains part of the
later custody/signing architecture and is not selected here. Bridge and
wrapped representations are identity-confusion surfaces, not native L28.

| Boundary | MAY (future, after later gates) | MUST NOT |
|---|---|---|
| External Bitcoin network | Produce public chain data (headers, txids, amounts in satoshis, heights labeled as Bitcoin) | Define L28 identity, issuance, supply, canonical height, validation, consensus, history, or settlement |
| Observer / proof verifier | Check public Bitcoin facts against a declared network and a later-approved proof policy | Sign, broadcast, custody, mint L28, choose L28 height, or silently repair wrong-network/stale evidence |
| Adapter boundary | Normalize public observation results into a labeled Bitcoin-domain evidence object | Become a validation authority; override economics; accept secrets; grant execution/spend |
| Universal Access boundary | Accept or reject adapter-mapped **public** objects under a later authorized interface profile | Embed Bitcoin private material; silently extend UAII v0.1; override Protocol v1.0.0 |
| L28 validation | Validate **L28** transactions via `validate_transaction` | Accept Bitcoin proofs as L28 coinbase, height, supply, or settlement |
| Future isolated signer | Hold signing material in an isolated local boundary, if a later custody foundation authorizes it | Be implemented, networked, or reachable from observers/adapters by this Foundation |
| Bridge / wrapped representations | Exist as non-native, non-Bitcoin-native identity objects | Define native L28; be treated as native BTC; confer issuance or settlement authority |

A future Bitcoin observer is not `CoreL28Node` and not `L28P2PNode`. It
cannot authorize ledger mutation and cannot supply canonical L28 height.

---

## 5. Adversary capabilities

This review assumes an adversary who can interact with the **public
evidence path** and with any future observer or adapter process. The
adversary is not assumed to break Protocol v1.0.0 by itself; the threat is
that Bitcoin-facing code, parsers, or operators might be induced to treat
external evidence as L28 authority.

Adversaries of concern can:

- provide malformed, incomplete, or spoofed Bitcoin evidence
- lie about Bitcoin network identity (mainnet vs testnet vs signet vs
  regtest vs unknown)
- provide stale, orphaned, or reorged evidence as if it were current
- replay previously accepted evidence-ids or txid/outpoint tuples
- cause observers to disagree, or present a single captured observer as
  consensus
- isolate or eclipse observers so that a false tip appears locally canonical
- inject secret-like fields (`private_key`, `mnemonic`, `xprv`, RPC
  credentials) as disposable markers or as attempted custody material
- attempt signing or broadcast escalation (`sign_bitcoin_transaction`,
  `broadcast_bitcoin_transaction`, `signing_authorized=true`)
- attempt L28 economic, height, validation, or history overrides
  (hard cap, emission ceiling, historically mined, treasury, circulating
  snapshot, non-coinbase issuance, Bitcoin height as L28 height,
  `validate_transaction` force-accept, historical-record mutation)
- confuse BTC, wrapped BTC, wrapped L28, and native L28 identities,
  including via bridge-contract metadata
- exploit nondeterministic clock, environment, or network inference when
  required public state is missing
- exploit parser and serialization ambiguity (duplicate JSON keys, unknown
  strict-schema fields, uppercase hex silent-normalization)
- cause oversized or malformed-input denial of service against a future
  parser or evaluator

These capabilities are **documented threats**. They are not permission to
implement runtime defenses beyond the already isolated conformance suite.

---

## 6. Threat matrix

Legend for columns:

- **Existing conformance defense** — what Foundation 95–104 fixtures/tests
  already assert in a test-local, non-networked evaluator. This is
  **enforced conformance behavior**, not a live Bitcoin network control.
- **Required fail-closed behavior** — the documented closed outcome if the
  threat is realized.
- **Residual risk** — what remains after conformance coverage.
- **Future decision required** — a later governed foundation or operator
  decision; not made here.

| Threat | Attacked boundary | Possible consequence | Existing conformance defense | Required fail-closed behavior | Residual risk | Future decision required |
|---|---|---|---|---|---|---|
| Unknown, missing, or conflicting Bitcoin network identity | Observer / adapter | Wrong-chain evidence treated as intended Bitcoin network | `NID` (`fx-btc-v01-0001`–`0005`); `network_identity_invalid`; no default network | Reject; no inferred network | Test labels are fictional; live network-magic/genesis binding is unimplemented | Production network-identity registry remains later-gated |
| Malformed, incomplete, or mutated public proof | Observer / proof verifier | False inclusion or unverifiable “proof” accepted | `PRF` (`0006`–`0011`); `proof_invalid` / `proof_insufficient` / `required_state_unavailable` | Reject; no repair; no invented proof | Structural checks ≠ cryptographic verification of a live header chain | Production proof architecture: `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Wrong-network proof (e.g. mainnet material on testnet identity) | Observer / adapter | Cross-network coercion; stolen or replayed evidence from another Bitcoin network | `WRN` (`0012`–`0016`); `network_mismatch` | Reject; no coercion or relabel | Live P2P/RPC wrong-network delivery is not exercised | Bind later proof model to declared network identity |
| Stale / reorged evidence reused as fresh | Observer / adapter | Spend or observation against an orphaned Bitcoin block | `REO` (`0017`–`0021`); `proof_stale` / `reorg_detected` / `required_state_unavailable` | Reject reuse; missing tip is not “zero confirmations” | No production confirmation depth or reorg policy exists | Production confirmation count and reorg/finality: `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Replay of evidence-id or duplicate txid/outpoint | Adapter | Same Bitcoin outpoint cited as new independent evidence | `RPL` (`0022`–`0025`); `replay_detected` / `duplicate_evidence` / `required_state_unavailable` | Fail closed; no implied first-seen accept | Test-local prior-accept state is not a production evidence store | Later evidence-id persistence design, if observation is ever authorized |
| Observer disagreement / invented majority | Observer quorum | One captured or split view treated as Bitcoin truth | `AGR` (`0026`–`0029`); `observer_disagreement` / `required_state_unavailable` | Reject; no majority invention | Test observer count is fixture-local only | Production observer quorum: `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Secret-field injection | Adapter / UAII / logs | Custody material in prompts, payloads, or logs; later key use | `SEC` (`0030`–`0037`); `secret_material_forbidden` | Reject; do not parse, log, or echo secrets | Conformance uses disposable markers, not real secrets; production logging paths are unimplemented | Custody / signing architecture remains later-gated |
| Signing or broadcast escalation | Adapter / future signer | Observation path becomes a wallet | `SEC`; `operation_unsupported` / `authority_denied` | Reject; `signing_authorized` and `broadcast_authorized` remain false | No signer exists; residual is future implementation error | Isolated signer, if any, must be a later separate authority |
| L28 economic, height, validation, or history override | Adapter → L28 validation | Changed hard cap, mint path, Bitcoin height as L28 height, forced validation, rewritten history | `ECO` (`0038`–`0045`); `adapter_override_forbidden` | Reject; invariants unchanged; no mint; no `validate_transaction` call | Conformance cannot substitute for production code-path isolation | Keep production adapter from importing validation/mint/ledger surfaces |
| BTC / wrap / bridge identity confusion | Adapter / bridge metadata | Wrapped or bridged asset treated as native L28 or native BTC | `IDN` (`0046`–`0051`); `asset_identity_invalid` | Reject; no native/wrapped guess; `native_asset=false` for BTC-domain accept | EVM `L28Bridge.sol` remains classified non-native and unexecuted | No bridge-defined identity even if a later wrap product exists |
| Clock / environment / network inference | Adapter evaluator | Hidden time or env fills missing public state | `DET` (`0052`–`0057`); `required_state_unavailable` / `schema_invalid` | Reject; no `time`, `os.environ`, or network fallback | Future runtime could reintroduce inference if implemented carelessly | Runtime must preserve fail-closed missing-state rules |
| Duplicate JSON keys or unknown strict fields | Parser / serializer | First/last-key ambiguity; silent schema extension | `DET`; `schema_invalid`; no first/last keep; no unknown-field ignore | Reject; no repair | Production parsers could differ from the test-local strict loader | Canonical public-input parser rules in a later implementation spec |
| Uppercase / noncanonical hex silent-normalization | Parser | Distinct identifiers collapsed by `.lower()` | `DET` boundary `0056`; uppercase MUST NOT be repaired | Reject as `schema_invalid`; original bytes unchanged | Other encodings (stripped whitespace, `0x` prefix) are not fully enumerated | Canonical identifier encoding in a later implementation spec |
| Oversized / malformed input DoS | Parser / process | Evaluator hang, memory exhaustion, or crash-open | Conceptual only; fixtures are small and bounded | Fail closed on malformed input; no crash-open accept | No production size/time limits are set here | Later bounded-parsing decision; no numbers chosen in this review |

All grant and mutation flags remain false across these families:
`execution_authorized`, `spend_authorized`, `signing_authorized`,
`broadcast_authorized`, `ledger_mutated`, `settlement_finalized`,
`transaction_submitted`, `l28_issuance_authorized`, and
`adapter_override_allowed`.

---

## 7. Proof / trust-model threat analysis

Foundation 93 compared candidate observation models **without selecting a
production architecture**. This review analyzes the same candidates as
threats and trust assumptions only. **No production proof architecture is
selected or recommended.**

The production proof architecture remains:

`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

### 7.1 Bitcoin Core / RPC observer

| Aspect | Analysis |
|---|---|
| Mechanism | Query a Bitcoin Core (or equivalent) node over RPC for headers, transactions, and confirmations |
| Trust | Operator trusts that node’s view, configuration, network, and RPC authentication |
| Threats | Wrong network; stale tip; RPC credential leak; operator-controlled lie; connectivity loss; RPC result treated as L28 state |
| Conformance coverage | `NID`, `WRN`, `REO`, `SEC` (RPC credential field names), `ECO` |
| Residual | A single RPC view is operator-trusted. Conformance does not talk to bitcoind. Credentials MUST NEVER enter UAII payloads, prompts, logs, hosted models, or public adapters |
| Decision | Unselected. `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |

### 7.2 Header / SPV-style verification

| Aspect | Analysis |
|---|---|
| Mechanism | Verify a proof-of-work header chain and use headers to check inclusion |
| Trust | Honest-majority hashpower; correct network magic/genesis; sufficiently complete header set |
| Threats | Eclipse or fake-header attacks if peers are captured; reorgs; wrong genesis/network; treating SPV success as L28 finality |
| Conformance coverage | `PRF`, `WRN`, `REO` structural cases only |
| Residual | Better than blind RPC **if** headers are independently checked, still probabilistic. No SPV or P2P code exists in this Foundation |
| Decision | Unselected. `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |

### 7.3 Merkle inclusion proof

| Aspect | Analysis |
|---|---|
| Mechanism | Merkle path from transaction to a block hash that is itself justified |
| Trust | The referenced block hash is on the intended canonical Bitcoin chain |
| Threats | Valid Merkle path to a stale, orphaned, or wrong-network block; incomplete path; mutated txid; inclusion mistaken for remaining-canonical status |
| Conformance coverage | `PRF` structural accept/reject; `REO` stale reuse; `WRN` network bind |
| Residual | Proves inclusion **in that block**, not that the block remains canonical. Insufficient alone for later settlement evidence |
| Decision | Unselected. Composition with header/tip policy remains `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |

### 7.4 Multiple independent observers

| Aspect | Analysis |
|---|---|
| Mechanism | Require agreement among independently operated observers |
| Trust | Observer independence; non-collusion; shared network identity |
| Threats | Correlated infrastructure; quorum split; ambiguous disagreement; inventing a majority without an approved rule |
| Conformance coverage | `AGR` test-local agreement/disagreement; disagreement and missing quorum state fail closed |
| Residual | Reduces a single-operator lie **if** independence is real. Does not create Bitcoin consensus. Test `test_observer_count` is not a production N |
| Decision | Production observer quorum remains `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |

### 7.5 Third-party / public explorer style evidence

| Aspect | Analysis |
|---|---|
| Mechanism | A third party or public explorer attests Bitcoin facts |
| Trust | Oracle or explorer honesty, availability, and non-equivocation |
| Threats | Capture, downtime, ambiguous attestation, key compromise, scraped HTML/JSON treated as proof |
| Conformance coverage | No explorer client exists. Identity and override families still reject native-L28 claims regardless of attestation source |
| Residual | Weakest listed model for adversarial settings. Default posture for later settlement evidence remains reject unless a future foundation explicitly authorizes a labeled, non-settlement metadata role |
| Decision | Unselected. `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` — default posture is reject-for-settlement |

This Foundation does **not** rank these models as an implementation order.

---

## 8. Reorg / finality threats

Bitcoin confirmations are **probabilistic**, not absolute finality.

L28 canonical height is consensus-derived and fail-closed when missing.
Bitcoin height is a different domain and MUST remain labeled as Bitcoin
height.

### 8.1 Threats

| Threat | Description |
|---|---|
| Shallow confirmation | Evidence that is valid at low depth can be displaced by a later competing chain |
| Stale / orphaned block | A Merkle-valid transaction in a block that is no longer on the declared tip |
| Conflicting tips | Two observers report incompatible chain tips for the same declared network |
| Missing required Bitcoin state | Headers, tip, or confirmation state unavailable; adversary or operator may prefer a default of “zero confirmations” or “trust last seen” |
| Conversion into L28 finality | Treating a deeply confirmed Bitcoin transaction as L28 settlement, coinbase, refund, mint, or ledger mutation |

### 8.2 Existing conformance behavior

Family `REO` (`fx-btc-v01-0017`–`0021`) already requires:

- previously accepted observations that no longer descend from a declared
  fictional tip to be treated as stale and not reused
- insufficient or unavailable confirmation state to fail closed
- conflicting or unusable canonical Bitcoin state to yield
  `required_state_unavailable`, not an invented zero-confirmation accept

Caller-supplied **test-local** `test_min_confirmations` values in fixtures
are conformance parameters only. They are **not** a production confirmation
count.

### 8.3 Explicit non-decisions

This review does **not** choose a production confirmation count.

This review does **not** choose a production reorg/finality policy.

Both remain:

`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

Even a later, deeply confirmed Bitcoin transaction MUST NOT be treated as
L28 settlement finality, L28 coinbase, L28 ledger mutation, or an L28
refund or mint.

---

## 9. Observer disagreement / isolation

### 9.1 Threats

| Threat | Description |
|---|---|
| Collusion | Independently labeled observers share control and present a consistent lie |
| Common-provider dependence | Distinct observer names that actually share one RPC host, one explorer, or one cloud image |
| Eclipse / isolation | A victim observer sees only attacker-fed peers or a captured bitcoind |
| Stale synchronization | One observer lags and reports an old tip as current |
| Disagreement | Honest observers diverge; an adapter invents a majority or picks a favorite |

### 9.2 Existing conformance behavior

Family `AGR` (`fx-btc-v01-0026`–`0029`) already requires:

- incompatible public facts from observers to yield `observer_disagreement`
- missing required test-local quorum state to yield
  `required_state_unavailable`
- no invented majority and no default observer

Fixture `test_observer_count` is a **test-only** parameter. It is not a
production quorum.

### 9.3 Explicit non-decision

This review does **not** choose a production observer quorum number.

Production observer quorum remains:

`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

Independence criteria, timeout, and anti-correlation rules are also unset.
Missing those decisions MUST fail closed, not degrade to a single observer.

---

## 10. Secret / custody / signing boundary

Observers and adapters MUST NOT receive or control:

- private keys
- seed phrases
- mnemonics
- xprv
- wallet secrets
- signing authority
- broadcast authority

RPC credentials are distinct from wallet/signing custody material. They
MUST NEVER enter UAII payloads, prompts, logs, hosted models, or public
adapters. A future separately authorized local Bitcoin Core / RPC observer
may require RPC authentication inside its isolated observer boundary; this
review does not select that model or define credential handling.

This review uses **no real secrets** and no realistic secret material.
Foundation 101 conformance fixtures use only documented disposable field
markers. Those markers are forbidden-field names, not keys.

### 10.1 Existing conformance behavior

Family `SEC` (`fx-btc-v01-0030`–`0037`) already requires:

- presence of documented secret field names → `secret_material_forbidden`
- signing operation attempts → `operation_unsupported`
- broadcast operation attempts → `operation_unsupported`
- unauthorized `signing_authorized=true` claims → `authority_denied`
- nested secret fields fail closed
- evaluator results MUST NOT echo marker values
- `signing_authorized`, `broadcast_authorized`, and
  `transaction_submitted` remain false

### 10.2 Residual and later work

No wallet is created or imported here. No signer is implemented. Observation
and signing MUST remain **separate authorities**. An observation adapter
that can sign or broadcast is a custody and activation failure.

Production custody/signing architecture is **not** chosen in this review and
remains a later governed foundation.

RPC credentials are custody-adjacent secrets. They MUST NEVER enter UAII
payloads, prompts, logs, hosted models, or public adapters.

---

## 11. L28 economic-authority firewall

Bitcoin evidence MUST NEVER:

- change the hard cap 28,000,000 L28
- change the emission ceiling 11,130,000 L28
- change historically mined 2,824,584 L28
- change treasury locked 500,000 L28
- change circulating snapshot 2,324,584 L28
- bypass coinbase-only issuance
- supply canonical height
- override `validate_transaction`
- rewrite historical evidence
- mint or burn L28

Attempted overrides MUST fail closed with `adapter_override_forbidden`.

Bitcoin height MUST NEVER become L28 canonical height. Height authority
MUST remain consensus-derived. The historical mined-through entry remains
100,877. The next canonical height after bootstrap remains 100,878. Bitcoin
height 840000, or any other Bitcoin height, is external Bitcoin evidence
only.

Bitcoin satoshi amounts MUST remain satoshi amounts. They MUST NOT be
coerced into L28 units.

### 11.1 Existing conformance behavior

Family `ECO` (`fx-btc-v01-0038`–`0045`) already rejects:

- hard-cap override
- emission-ceiling override
- historically-mined override
- treasury locked and circulating snapshot override
- non-coinbase issuance claims (`adapter_mint` remains forbidden;
  issuance remains `coinbase_only`; `l28_issuance_authorized` remains false)
- Bitcoin height claimed as L28 canonical height
- `validate_transaction` override / `force_accept`
- historical evidence mutation (`historical_evidence` remains `immutable`;
  `ledger_mutated` remains false)

The proposed value does not matter. Equality with a canonical constant is
still an authority override and remains forbidden. Conformance evaluators
MUST NOT import or call production `validate_transaction`, mint, coinbase
ingestion, or ledger-write surfaces.

---

## 12. Native / wrapped / bridge identity risks

BTC, wrapped BTC, wrapped L28, and native L28 MUST remain distinct.

| Forbidden claim | Required outcome |
|---|---|
| Bitcoin is native L28 | `asset_identity_invalid` |
| BTC is L28 | `asset_identity_invalid` |
| Wrapped BTC is native BTC | `asset_identity_invalid`; `native_asset` remains false |
| Wrapped L28 is native L28 | `asset_identity_invalid` |
| A bridge contract defines native L28 identity | `asset_identity_invalid` |
| Asset identity cannot be established | `asset_identity_invalid`; no native/wrapped guess |

A bridge contract has **zero authority** to define native L28.
`contracts/L28Bridge.sol` is classified as EVM lock/release code. It is not
Bitcoin support and not native L28. `contracts/deploy_bridge.py` is an EVM
deploy helper. This Foundation MUST NOT execute or deploy either.

Identity MUST NOT be inferred from symbol or name alone (`BTC`, `L28`).
Identity MUST NOT be inferred from bridge metadata.

### 12.1 Existing conformance behavior

Family `IDN` (`fx-btc-v01-0046`–`0051`):

- `0046` accepts Bitcoin-domain evidence only, with `native_asset=false`,
  and grants no execution, spend, signing, broadcast, ledger, settlement,
  or issuance authority
- `0047`–`0051` reject with `asset_identity_invalid`

Observation-accept of labeled Bitcoin evidence is still not native L28 and
still not settlement.

---

## 13. Determinism / parser / serialization threats

A future public adapter MUST be deterministic on canonical public inputs.
Hidden evaluator state, system clock, process environment, and network
fallbacks are forbidden inference sources.

| Threat | Required fail-closed behavior | Existing conformance |
|---|---|---|
| Duplicate JSON keys in public adapter input | `schema_invalid`; do not keep first value; do not keep last value; do not repair | `DET` `0054`; raw public input parsed with duplicate-key detection |
| Unknown field where strict request schema applies | `schema_invalid`; no ignore; no best-effort parse; no schema extension | `DET` `0055` |
| Case mutation / silent hex normalization | Uppercase or noncanonical identifiers are not accepted via `.lower()` or equivalent repair; original input remains unchanged | `DET` `0056` accepts canonical lowercase 64-character hex; derived uppercase mutation is test-local and must reject |
| System clock inference | `required_state_unavailable`; do not read system time | `DET` `0057`; fixture `fixed_clock` MUST NOT fill missing request state |
| Environment inference | `required_state_unavailable`; do not read `os.environ` / `getenv` | `DET` `0057` |
| Network fallback | `required_state_unavailable`; do not query RPC/DNS/P2P to invent state | `DET` `0057`; no network imports in isolated tests |
| Hidden mutable evaluator state | Repeated evaluation of identical input yields identical public outcomes | `DET` `0052`–`0053` |
| Unstable error behavior | Same malformed input yields the same conceptual code | `DET` plus family-wide expected-result equality |
| Canonical serialization | UTF-8 JSON; documented field order; stable separators; no `repr()` as canonical output | `DET` `0052`–`0053` byte-stable public outcome |

Identical canonical public inputs MUST produce equivalent public outputs.
Equivalent repeated canonical evaluation MUST produce byte-identical
serialized public outcomes. Caller input, fixtures, and `l28_invariants`
MUST NOT be mutated.

---

## 14. Denial-of-service considerations

A future parser or adapter process can be stressed by oversized payloads,
deeply nested JSON, huge Merkle arrays, duplicate-key storms, or
pathological hex strings.

This review documents those risks **conceptually**:

- Malformed input MUST fail closed. It MUST NOT crash-open into an
  observation-accept, grant, or L28 mutation.
- Parsing SHOULD be bounded in a later implementation specification.
- Resource exhaustion of an observer MUST be treated as
  `required_state_unavailable` or equivalent, not as a default success.

This Foundation does **not** introduce runtime limits, byte caps, timeouts,
or production policy numbers. Choosing those numbers would be a later
implementation decision and is out of scope.

Existing fixtures are small, fictional, and locally evaluated. Their
passage does not prove denial-of-service resistance.

---

## 15. Existing mitigations

Foundations 95–104 implemented the Foundation 94 catalog as **57**
isolated fixtures (`fx-btc-v01-0001` through `fx-btc-v01-0057`) and **10**
test modules. Coverage:

| Family | Fixtures | Isolated test module |
|---|---|---|
| `NID` network identity | `0001`–`0005` | `tests/test_bitcoin_interoperability_network_identity_fixtures.py` |
| `PRF` proof validation | `0006`–`0011` | `tests/test_bitcoin_interoperability_proof_validation_fixtures.py` |
| `WRN` wrong-network evidence | `0012`–`0016` | `tests/test_bitcoin_interoperability_wrong_network_fixtures.py` |
| `REO` reorg / stale | `0017`–`0021` | `tests/test_bitcoin_interoperability_reorg_stale_fixtures.py` |
| `RPL` replay / duplicate | `0022`–`0025` | `tests/test_bitcoin_interoperability_replay_duplicate_fixtures.py` |
| `AGR` observer agreement | `0026`–`0029` | `tests/test_bitcoin_interoperability_observer_agreement_fixtures.py` |
| `SEC` secret / signing / broadcast | `0030`–`0037` | `tests/test_bitcoin_interoperability_secret_signing_broadcast_security_fixtures.py` |
| `ECO` L28 economic firewall | `0038`–`0045` | `tests/test_bitcoin_interoperability_economic_authority_firewall_fixtures.py` |
| `IDN` native / wrapped identity | `0046`–`0051` | `tests/test_bitcoin_interoperability_native_wrapped_identity_fixtures.py` |
| `DET` deterministic serialization | `0052`–`0057` | `tests/test_bitcoin_interoperability_deterministic_serialization_fixtures.py` |

These artifacts already test, in a **test-local evaluator**:

- explicit Bitcoin network labels and fail-closed missing/unknown/conflict
- structural public-proof accept/reject under caller-supplied test policy
- no cross-network repair
- stale/reorg reuse rejection and unavailable-tip fail-closed
- replay and duplicate outpoint rejection
- observer disagreement without invented majority
- forbidden secret fields and unsupported sign/broadcast operations
- exact L28 invariant firewall (`adapter_override_forbidden`)
- native/wrapped/bridge identity separation
- duplicate-key, unknown-field, uppercase-hex, and inference fail-closed

They do **not** prove production security. They do **not** prove Bitcoin
finality. They do **not** activate RPC, SPV, P2P, wallets, signing,
broadcast, mining, bridges, or settlement. Observation-accept remains
flags-false external evidence only.

Every fixture retains `not_production_policy = true` and:

- `production_proof_architecture = BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`
- `production_confirmation_count = BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`
- `production_quorum = BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`

---

## 16. Residual risks / unresolved decisions

The following MUST remain exactly unresolved in this Foundation:

| Decision | Status |
|---|---|
| Production proof architecture | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production confirmation count | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production observer quorum | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |

Also left for later governed foundations:

- production reorg / finality policy
- custody / signing architecture
- independent security review
- explicit operator authorization
- any UAII profile that would expose Bitcoin observation as a public
  operation (UAII v0.1 remains unchanged)

Additional residual risks that conformance cannot close:

- live eclipse, hashpower, or operator-control attacks against a real
  Bitcoin view
- correlated “independent” observers
- production parser divergence from the test-local strict loader
- future implementation accidentally importing `validate_transaction`,
  mint, wallet, RPC, or bridge surfaces
- denial-of-service against an unimplemented runtime
- treating passing CI as permission to spend, mint, mine, or settle

Missing any later gate MUST fail closed. Documentation of a threat is not
mitigation of that threat in production.

---

## 17. Foundation 105 conclusion / gate status

Foundation 94’s implementation gate for Bitcoin adapter implementation is:

1. Foundation 94 conformance plan — plan document (prior)
2. Machine-readable fixtures — `fx-btc-v01-0001` through `0057` (prior
   Foundations 95–104)
3. Deterministic isolated test runner — 10 `test_bitcoin_interoperability_*`
   modules (prior Foundations 95–104)
4. **Threat-model review — this document (Foundation 105)**
5. Proof-model decision — **not satisfied**
6. Reorg / finality decision — **not satisfied**
7. Custody / signing architecture — **not satisfied**
8. Independent security review — **not satisfied**
9. Explicit operator authorization — **not satisfied**

Foundation 105 satisfies **THREAT-MODEL REVIEW only** (item 4).

It MUST NOT be read as satisfying items 5–9. It MUST NOT be read as
re-opening Protocol v1.0.0. It MUST NOT be read as activating Bitcoin
interoperability.

Bitcoin adapter implementation remains **blocked** pending later gates.
Absence of those gates is a block, not a default-allow.

---

## 18. Document control

| Field | Value |
|---|---|
| Foundation | 105 |
| Parent | `c9585b08a302c1122e46693efc8cb8a2a6f43b34` |
| Path | `docs/bitcoin_interoperability_threat_model_v0.1.md` |
| Status | threat-model review / non-activating |
| Implementation | none |
| Runtime activation | none |
| Network activity | none |
| Wallet / signing activity | none |
| Existing fixtures modified | none |
| Existing tests modified | none |
| Bitcoin operations added to UAII v0.1 | none |
| Production proof architecture | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production confirmation count | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production observer quorum | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production reorg / finality policy | unset (later governed foundation) |
| Custody / signing architecture | unset (later governed foundation) |
| Payment model authorized | none |

Protected economic facts restated for firewall continuity (unchanged,
never recalculated):

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
