# L28 Bounded Testnet Readiness Gap Audit v0.1

**Foundation:** 37

**Status:** Offline readiness gap audit only; non-activation

**Audit parent:** `980dad78e82b167f4527b1b92cfdd5a9878fad1e`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

## Purpose

This audit records evidence-backed gaps between the current public L28
repository and a future **isolated, disposable testnet** milestone.

It does not authorize, construct, start, or operate a testnet. It does not
change Protocol v1.0.0, consensus rules, ledger state, mining, wallets,
networking, tests, dependencies, or configuration. It grants **no execution
authority**.

## Classification legend

| Class | Meaning |
|---|---|
| **READY** | Direct in-repo evidence shows the dependency exists and is usable for the stated bounded purpose without inventing missing runtime. |
| **PARTIAL** | Relevant boundaries, specs, helpers, or local validators exist, but a required testnet piece is incomplete or inert. |
| **BLOCKED** | Required capability for starting or safely operating an isolated disposable testnet is absent or non-functional. |
| **OUT_OF_SCOPE** | Explicitly outside this bounded milestone, or must remain non-authority / non-reuse (for example Leap28 internals, creator-wallet spend claims, public mainnet activation). |

Uncertain or incomplete evidence is classified **PARTIAL** or **BLOCKED**, never
**READY**.

## Protected economic facts (must be preserved)

These facts are frozen under L28 Protocol v1.0.0 and MUST NOT be altered by any
testnet readiness work:

| Fact | Value | Evidence |
|---|---:|---|
| Protocol | v1.0.0 FROZEN | `PROTOCOL.md` |
| Hard cap | 28,000,000 (`28_000_000`) | `coin/tx_validation.py` `L28_MAX_SUPPLY`; `PROTOCOL.md` |
| Emission ceiling | 11,130,000 (`11_130_000`) | `coin/tx_validation.py` `L28_EMISSION_CEILING`; `PROTOCOL.md` |
| Halving interval | 210,000 | `coin/tx_validation.py` `L28_HALVING_INTERVAL` |
| Max coinbase reward | 28 | `coin/tx_validation.py` `L28_MAX_COINBASE_REWARD` |
| Reward schedule | (28, 14, 7, 3, 1) | `coin/tx_validation.py` `L28_REWARD_SCHEDULE` |

Historical checkpoint constants remain **reference-only** and MUST NOT be
auto-loaded into runtime balances:

- `L28_HISTORICAL_MINED = 2_824_584`
- `L28_HISTORICAL_LAST_ENTRY = 100_877`
- `L28_NEXT_HEIGHT_AFTER_CHECKPOINT = 100_878`

Evidence: `coin/tx_validation.py` comments; `docs/l28_identity_historical_continuity_audit.md`.

## Non-activation and independence statements

- This audit is offline documentation only.
- Passing or publishing this audit is **not** permission to spend L28, mine,
  open listeners, deploy nodes, or activate runtime.
- L28 remains independently testable through local unittest, invariants, and
  offline CLIs without Leap28, Nova, or any external orchestration platform.
- Leap28 private orchestration, SovereignBrain logic, memory spine, and private
  historical activation paths are **prohibited from reuse** as L28 testnet
  runtime (`PROTOCOL.md`, `NON_GOALS.md`, `docs/l28_future_capability_registry_v0.1.md`).
- No in-repo “Nova” integration surface was found; nothing named Nova may be
  treated as an L28 testnet dependency.

---

## Findings

### F37-01 Canonical chain initialization and historical bootstrap boundary

**Classification:** PARTIAL

| Field | Content |
|---|---|
| Evidence | `PROTOCOL.md` (empty dir / clone ≠ trusted genesis); `coin/ledger.py` `initialize_disposable_test_issuance_state`, `load_from_disk`, `_canonical_issuance_ready`; `coin/tx_validation.py` historical constants; `coin/historical_continuity_verifier.py` `verify_manifest`; `docs/l28_identity_historical_continuity_audit.md`; `docs/l28_historical_continuity_manifest_v0.1.json`; `tests/test_protocol_conformance.py` `TestCanonicalIssuanceGate`, `test_empty_directory_is_not_canonical_genesis`; `tests/test_historical_continuity_verifier.py` |
| Current behavior | Empty disk load fail-closes issuance readiness (`_canonical_issuance_ready = False`). Disposable test issuance requires explicit `acknowledge_test_only=True`. Historical continuity is offline-verifiable only. |
| Missing requirement | Named disposable-testnet genesis/bootstrap artifact and writer that binds a distinct network identity without promoting historical main-network checkpoint as live genesis. |
| Safety risk | Treating empty directories, historical snapshots, or clone state as genesis could forge issuance authority. |
| Minimum bounded remediation | Specify and implement a test-only genesis binder that creates ephemeral chain identity under explicit acknowledgement, never auto-loading historical balances. |
| Required validation | Unit tests for empty-dir rejection, acknowledgement gate, and genesis hash binding; no silent issuance. |
| Prerequisite / dependency | Network identity / environment separation (F37-12). |
| Recommended milestone order | M1 |

---

### F37-02 Consensus height and fail-closed state authority

**Classification:** PARTIAL

| Field | Content |
|---|---|
| Evidence | `PROTOCOL.md` (canonical height fail-closed); `coin/tx_validation.py` `validate_transaction` (`missing_consensus_lookups`, `canonical_height_unavailable`, `coinbase_height_mismatch`); `coin/ledger.py` `mint_height`, `add_transaction`; `coin/invariants.py` `run_invariants`; `coin/node_role_model.py` reserved `CANONICAL_READY_RESERVED` / `RUNNING_RESERVED`; `tests/test_protocol_conformance.py` emission/height cases |
| Current behavior | Coinbase validation requires consensus lookups; local ledger height advances on accepted coinbase. Node-role models keep canonical/running states reserved and unreachable. |
| Missing requirement | Network-agreed tip / height authority for multi-process isolated testnet (not only a local counter). |
| Safety risk | Independent local heights would diverge and allow inconsistent coinbase acceptance across nodes. |
| Minimum bounded remediation | Define Core tip authority for disposable testnet and wire fail-closed height lookups to that tip only. |
| Required validation | Divergence tests: missing tip rejects coinbase; mismatched height rejects. |
| Prerequisite / dependency | Runtime Core node lifecycle (F37-06); sync policy (F37-07). |
| Recommended milestone order | M2–M3 |

---

### F37-03 Transaction and coinbase validation

**Classification:** READY

| Field | Content |
|---|---|
| Evidence | `coin/tx_validation.py` `validate_transaction`, `is_coinbase_tx`, `compute_tx_id`, `TxPolicy`, `RESERVED_SENDERS`; `coin/mining.py` `build_coinbase_tx`, `build_mint_tx` (disabled); `coin/transaction_builder.py` `TransactionBuilder`; `coin/ledger.py` `add_transaction`; `tests/test_protocol_conformance.py` |
| Current behavior | Offline/local validation enforces identity, signatures (policy), coinbase shape, reserved senders, and discretionary-mint denial. |
| Missing requirement | None for **local** validation reuse. Networked mempool admission remains separate (see F37-10). |
| Safety risk | Low for local reuse if network admission stays fail-closed until specified. |
| Minimum bounded remediation | Reuse existing validators unchanged for disposable testnet; do not weaken `require_signatures` defaults without a dedicated foundation. |
| Required validation | Existing `tests/test_protocol_conformance.py` plus any new admission-layer tests. |
| Prerequisite / dependency | None for local validation. |
| Recommended milestone order | Available now (reuse in M1+) |

---

### F37-04 Supply-cap and emission enforcement

**Classification:** READY

| Field | Content |
|---|---|
| Evidence | `coin/tx_validation.py` `L28_MAX_SUPPLY`, `L28_EMISSION_CEILING`, `l28_coinbase_reward`, coinbase reject codes; `PROTOCOL.md` schedule and caps; `coin/invariants.py`; `tests/test_protocol_conformance.py` `TestEmissionSchedule` |
| Current behavior | Reward(H) and supply/emission ceilings are enforced in validation; discretionary mint path is disabled. |
| Missing requirement | None for Protocol v1.0.0 economics. Testnet MUST preserve the same caps unless a separately authorized non-main identity later defines otherwise (out of this audit’s activation scope). |
| Safety risk | Any override of cap/schedule would break Protocol v1.0.0 identity. |
| Minimum bounded remediation | Keep constants and checks unchanged; bind disposable testnet to the same economic rules. |
| Required validation | Invariants + emission schedule tests must remain green. |
| Prerequisite / dependency | None. |
| Recommended milestone order | Available now |

---

### F37-05 Deterministic ledger replay and persistence boundaries

**Classification:** PARTIAL

| Field | Content |
|---|---|
| Evidence | `coin/ledger.py` `BlocklessLedger`, `_save_transaction`, `load_from_disk`, `_seen_tx_ids`, `stable_address_shard`; `tests/test_protocol_conformance.py` `TestLedgerIdentityAndReplay`; M2M offline replay is separate (`coin/m2m_replay_registry.py`) |
| Current behavior | Local JSONL shard persistence with deterministic tx-id replay protection; load errors fail closed and clear issuance readiness. |
| Missing requirement | Multi-node disposable checkpoint/reset contract and explicit testnet data-dir lifecycle. Replay after load does not restore issuance readiness. |
| Safety risk | Partial loads or shared directories could desynchronize nodes or re-enable unintended issuance assumptions. |
| Minimum bounded remediation | Document ephemeral data-dir layout, reset semantics, and whether issuance must be re-acknowledged after every load. |
| Required validation | Replay identity tests; reset/cleanup tests for disposable directories. |
| Prerequisite / dependency | Node process isolation (F37-06). |
| Recommended milestone order | M1–M2 |

---

### F37-06 Node lifecycle and process isolation

**Classification:** BLOCKED

| Field | Content |
|---|---|
| Evidence | Specs: `docs/l28_core_p2p_architecture_v0.1.md`, `docs/node_role_model_v0.1.md`; inert models: `coin/node_role_model.py` `CoreNodeRoleModel`, `P2PNodeRoleModel`; tests: `tests/test_node_role_model.py`, `tests/test_node_role_scenario_suite.py`; broken stub: `coin/l28_coin.py` (`from ..wallet...`, `from ..network...` — packages absent); future registry lists Core/P2P as candidates: `docs/l28_future_capability_registry_v0.1.md` |
| Current behavior | Lifecycle states including `DISPOSABLE_TEST_READY` are modeled offline only. Reserved running/listening states are unreachable by design. No runtime Core/P2P process exists. |
| Missing requirement | Runnable isolated Core (and later P2P) process with sandbox data dirs, start/stop, and no accidental canonical activation. |
| Safety risk | Using the broken `L28Coin` stub or Leap28 process models would invent false readiness or leak private platforms. |
| Minimum bounded remediation | Implement a disposable-test-only Core process entrypoint that reaches only acknowledged test states; keep `CANONICAL_READY_RESERVED` / `RUNNING_RESERVED` unreachable until separately authorized. |
| Required validation | Process lifecycle tests; assert no sockets until P2P foundation; assert no canonical path. |
| Prerequisite / dependency | F37-01 genesis/test issuance binder; F37-12 network identity. |
| Recommended milestone order | M2 |

---

### F37-07 Peer discovery, transport, message validation, and synchronization

**Classification:** BLOCKED

| Field | Content |
|---|---|
| Evidence | Architecture/security docs: `docs/l28_core_p2p_architecture_v0.1.md`, `docs/l28_core_p2p_security_profile_v0.1.json`; composition capabilities are declarative only; no `wallet/` or `network/` packages; node-role/P2P reserved `LISTENING_RESERVED`; future candidate “Authenticated peer-to-peer networking” in `docs/l28_future_capability_registry_v0.1.md` |
| Current behavior | P2P is specification and inert role modeling. Production `coin/` modules do not provide peer transport or sync. |
| Missing requirement | Authenticated transport, message schema validation, peer discovery policy, and tip/header/tx synchronization for isolated testnet peers. |
| Safety risk | Ad-hoc sockets without fail-closed validation enable eclipse, spoofing, or consensus bypass. |
| Minimum bounded remediation | Dedicated P2P foundation implementing only disposable-testnet-bound frames and sync, following Foundation 19/20 specs. |
| Required validation | Malformed-frame matrices; no-connect default; multi-peer sync determinism tests. |
| Prerequisite / dependency | F37-06 Core lifecycle; F37-12 identity binding. |
| Recommended milestone order | M3 |

---

### F37-08 Mining difficulty, canonical work validation, and reward rules

**Classification:** PARTIAL

| Field | Content |
|---|---|
| Evidence | Reward path READY via `coin/mining.py` `build_coinbase_tx` / `l28_coinbase_reward`; dormant helpers `mine_block(difficulty=18)` in `coin/mining.py`, `mine_l28` in `coin/multi_coin_miner.py`; continuity manifest `docs/l28_historical_continuity_manifest_v0.1.json` fields `canonical_pow_formula_defined_in_v1: false`, `difficulty_18_is_consensus: false`; `WORKLOAD.md` non-normative |
| Current behavior | Emission/reward rules are enforced. Difficulty-18 helpers are not consensus-bound and use wall-clock entropy (`time.time()` in `mine_block`). |
| Missing requirement | Canonical work validation policy for disposable testnet (or an explicit blockless testnet minting policy that does not pretend PoW consensus). |
| Safety risk | Treating dormant difficulty helpers as consensus would create non-deterministic, non-canonical “mining.” |
| Minimum bounded remediation | Either (a) specify disposable-testnet work rules with deterministic validation, or (b) keep mining OUT_OF_SCOPE for the first isolated ledger milestone and issue only via acknowledged test coinbase under local tip authority. |
| Required validation | If work is included: deterministic accept/reject vectors. If deferred: tests prove no PoW helper grants issuance. |
| Prerequisite / dependency | F37-02 tip authority; F37-04 economics unchanged. |
| Recommended milestone order | M2 (rewards only) → M4 (optional work policy) |

---

### F37-09 Disposable test wallets and key isolation

**Classification:** PARTIAL

| Field | Content |
|---|---|
| Evidence | Ephemeral keys in offline suites (e.g. `tests/test_creator_wallet_transfer_intent_authorization_chain_conformance.py` `SUITE_SEED` / `from_private_bytes`); ledger disposable issuance gate; `SECURITY.md` disposable ledger guidance; missing packages referenced by `coin/l28_coin.py`; no `wallet/` directory |
| Current behavior | Offline tests generate disposable Ed25519 material in memory. No general disposable test-wallet keystore/CLI/runtime exists. Fixed creator public identity constants are verify-only. |
| Missing requirement | Isolated disposable test-wallet keygen/store that cannot load production creator secrets or Leap28 credentials. |
| Safety risk | Accidental reuse of real creator keys or host wallet paths would create live-asset risk. |
| Minimum bounded remediation | Add test-only wallet helper with ephemeral keys, explicit test network tag, and refusal to read production wallet paths. |
| Required validation | Tests forbid real creator private material; filesystem isolation checks. |
| Prerequisite / dependency | F37-12 environment separation. |
| Recommended milestone order | M2 |

---

### F37-10 Transaction propagation and settlement confirmation

**Classification:** BLOCKED

| Field | Content |
|---|---|
| Evidence | Local accept: `coin/ledger.py` `add_transaction`; M2M cites tx ids only (no L28 finality); no gossip/broadcast implementation under `coin/`; `docs/l28_future_capability_registry_v0.1.md` lists DAG selection/finality as future |
| Current behavior | Transactions apply locally when validated and accepted. No peer propagation or confirmation-depth API exists. |
| Missing requirement | Bounded gossip/admission path and explicit disposable-testnet confirmation semantics (even if shallow). |
| Safety risk | Claiming “settled” without sync invents finality. |
| Minimum bounded remediation | After P2P sync exists, define confirmation as tip inclusion under disposable network id; never reuse M2M registry as L28 settlement. |
| Required validation | Multi-node include/reject tests; no confirmation without tip agreement. |
| Prerequisite / dependency | F37-07 sync; F37-03 validators. |
| Recommended milestone order | M3–M4 |

---

### F37-11 Fork handling, reorganization policy, and recovery

**Classification:** BLOCKED

| Field | Content |
|---|---|
| Evidence | Future candidate `dag_consensus_selection` requires fork/reorg policy (`docs/l28_future_capability_registry_v0.1.md`); M2M `exchange_fork` is transcript/registry coordination only (`coin/m2m_replay_registry.py`); ledger recovery clears state on load failure; node-role `FAILED`→`STOPPED` is model-only |
| Current behavior | No L28 parent-graph tip selection or reorganization runtime. |
| Missing requirement | Explicit disposable-testnet fork choice and reorg/recovery policy before multi-miner or multi-peer tips. |
| Safety risk | Divergent tips without policy produce split ledgers and unsafe balances. |
| Minimum bounded remediation | Specify single-writer tip policy for the first milestone; defer multi-writer reorg to a later foundation. |
| Required validation | Competing-tip rejection or deterministic selection tests; recovery reset tests. |
| Prerequisite / dependency | F37-02, F37-07. |
| Recommended milestone order | M3 (single-writer) → M5 (reorg if multi-writer) |

---

### F37-12 Network identity, genesis/config binding, and environment separation

**Classification:** BLOCKED

| Field | Content |
|---|---|
| Evidence | `validate_transaction(..., network: str = "MAIN")` and ledger balance lookup label in `coin/tx_validation.py` / `coin/ledger.py`; P2P architecture requires future frames to bind protocol version + network id; no `TESTNET`/`DEVNET`/`REGTEST` identity module; `contracts/deploy_bridge.py` EVM “mainnet” strings are unrelated; continuity activation flags remain inactive |
| Current behavior | `"MAIN"` is a local label, not a multi-environment config system. No genesis-hash ↔ network-id binder exists. |
| Missing requirement | Explicit disposable network identifier, genesis binding, and hard separation from any main-network or historical checkpoint identity. |
| Safety risk | Cross-environment message or state reuse could launder test issuance into main identity claims. |
| Minimum bounded remediation | Introduce a disposable-only network id and config schema that fails closed on main/historical identity mix. |
| Required validation | Cross-network reject tests; config binding hash tests. |
| Prerequisite / dependency | None (gate for almost all runtime work). |
| Recommended milestone order | M1 |

---

### F37-13 Observability, shutdown, reset, and cleanup

**Classification:** PARTIAL

| Field | Content |
|---|---|
| Evidence | Offline CLIs emit sanitized JSON reports; logging in ledger/smoke/invariants; CI `.github/workflows/ci.yml`; Foundation 19 pause/shutdown states in docs/models only |
| Current behavior | Strong offline report discipline. No runtime health endpoints, networked graceful shutdown, or one-command disposable-testnet reset tooling. |
| Missing requirement | Process-level shutdown hooks, ephemeral data-dir cleanup, and operator-visible status for isolated nodes. |
| Safety risk | Orphaned processes or leftover state dirs can accidentally reconnect or reuse keys. |
| Minimum bounded remediation | Define stop/reset/cleanup commands for disposable data dirs only; no remote admin surface required for M1–M2. |
| Required validation | Tests that stop leaves no listeners and reset wipes only the tagged disposable directory. |
| Prerequisite / dependency | F37-06. |
| Recommended milestone order | M2 |

---

### F37-14 Adversarial, integration, and end-to-end test coverage

**Classification:** PARTIAL

| Field | Content |
|---|---|
| Evidence | Strong offline coverage: `tests/test_protocol_conformance.py`, M2M adversarial suites, `tests/test_node_role_model.py`, `tests/test_node_role_scenario_suite.py`, Foundation 36 `tests/test_creator_wallet_transfer_intent_authorization_chain_conformance.py`; CI `.github/workflows/ci.yml`; no multi-node networked e2e |
| Current behavior | Offline adversarial and conformance matrices are extensive. Networked multi-peer e2e does not exist. |
| Missing requirement | Isolated multi-process tests for sync, malformed peer messages, partition, and disposable confirmation. |
| Safety risk | Shipping networked code without adversarial sync tests repeats known P2P failure modes. |
| Minimum bounded remediation | Gate any P2P merge on dedicated adversarial sync suite (already required by future-capability promotion gates). |
| Required validation | Multi-node unittest or subprocess harness with disposable ports/dirs. |
| Prerequisite / dependency | F37-07. |
| Recommended milestone order | M3–M4 |

---

### F37-15 Foundations 31–36 relevance and explicit non-authority

**Classification:** OUT_OF_SCOPE (for testnet spend / settlement authority)

| Field | Content |
|---|---|
| Evidence | F31–F35 modules under `coin/creator_wallet_*`; F36 suite `tests/test_creator_wallet_transfer_intent_authorization_chain_conformance.py`; specs under `docs/creator_wallet_*` and `docs/creator_wallet_transfer_intent_authorization_chain_conformance_v0.1.md`; `execution_authorized` must remain JSON `false` |
| Current behavior | Offline creator-wallet control → intent → authorization → evidence → receipt chain verifies synthetic fixtures only. |
| Missing requirement | None for testnet authority — these foundations MUST NOT be treated as spend permission, balance proof, or testnet activation. |
| Safety risk | Misreading receipts as settlement would falsely authorize transfers. |
| Minimum bounded remediation | Keep F31–F36 offline and non-activating; cite them only as unrelated conformance evidence. |
| Required validation | Existing F36 non-activation tests remain green. |
| Prerequisite / dependency | None. |
| Recommended milestone order | Parallel / non-blocking; never a testnet prerequisite for spend |

**Relevance summary**

| Foundation | Artifact role | Testnet authority |
|---|---|---|
| 31 Bundle | Offline F30 member aggregation | None |
| 32 Intent | Unsigned transfer intent object | None |
| 33 Authorization | Signature over intent | None |
| 34 Evidence | Authorization + report binding | None |
| 35 Receipt | Successful evidence receipt | None |
| 36 Conformance | End-to-end offline suite | None |

---

### F37-16 Cross-cutting: Leap28 / Nova / bridge non-reuse

**Classification:** OUT_OF_SCOPE (prohibited reuse)

| Field | Content |
|---|---|
| Evidence | `PROTOCOL.md` Leap28 boundary; `NON_GOALS.md` “No Leap28 Logic Leakage”; `README.md` independence statements; `docs/l28_future_capability_registry_v0.1.md`; `contracts/L28Bridge.sol` / `contracts/deploy_bridge.py` (wrapped/bridge ≠ native L28) |
| Current behavior | Docs forbid Leap28 private logic leakage. Bridge is not native L28. No Nova surface found. |
| Missing requirement | None — prohibition is already normative. |
| Safety risk | Importing private orchestration would destroy independent testability and governance. |
| Minimum bounded remediation | Continue excluding Leap28/Nova/private historical activation from all testnet foundations. |
| Required validation | Static/import hygiene in future runtime modules. |
| Prerequisite / dependency | None. |
| Recommended milestone order | Standing constraint |

---

## Classification totals

| Classification | Count | Findings |
|---|---:|---|
| READY | 2 | F37-03, F37-04 |
| PARTIAL | 7 | F37-01, F37-02, F37-05, F37-08, F37-09, F37-13, F37-14 |
| BLOCKED | 5 | F37-06, F37-07, F37-10, F37-11, F37-12 |
| OUT_OF_SCOPE | 2 | F37-15, F37-16 |
| **Total** | **16** | |

---

## Required conclusions

### Overall readiness verdict

**NOT READY to start any testnet.**

The repository is offline-protocol-strong (validation, economics, disposable
issuance gate, inert node-role models, historical continuity verification, and
Foundations 31–36 offline conformance), but it lacks runtime Core/P2P
processes, disposable network identity/genesis binding, peer sync,
propagation/confirmation, and fork policy required for an isolated disposable
testnet.

### Explicit blockers to starting any testnet

1. **No disposable network identity / genesis binding** (F37-12).
2. **No runnable Core process isolation** (F37-06); `coin/l28_coin.py` is a broken non-package stub.
3. **No peer transport, discovery, or synchronization** (F37-07).
4. **No transaction propagation or confirmation semantics** (F37-10).
5. **No L28 fork/reorg policy for multi-tip operation** (F37-11).

Until these blockers are remediated under separate foundations with explicit
operator authorization, starting a testnet is prohibited by this audit’s
safety boundary.

### Smallest safe isolated-testnet sequence

| Milestone | Scope | Depends on |
|---|---|---|
| **M1** | Disposable network id + genesis/config binder + ephemeral data-dir contract; keep Protocol v1.0.0 economics unchanged | — |
| **M2** | Disposable-test-only Core process lifecycle, issuance acknowledgement, local tip height authority, disposable wallets, stop/reset/cleanup | M1 |
| **M3** | Bounded P2P transport/message validation + single-writer sync; adversarial malformed-peer tests | M2 |
| **M4** | Transaction propagation + shallow confirmation under disposable network id; optional explicit work policy (or keep PoW out of scope) | M3 |
| **M5** | Multi-writer fork/reorg policy only if required; otherwise remain single-writer | M4 |

Single-writer M2–M4 is the smallest path to an isolated disposable testnet
lab. Multi-writer reorg is not required for the first lab milestone.

### Items requiring separate operator authorization

- Any deployment or always-on public network.
- Any activation of `CANONICAL_READY_RESERVED` / `RUNNING_RESERVED` / `LISTENING_RESERVED`.
- Loading historical checkpoint balances into a live ledger.
- Main-network genesis writers or continuity migration.
- Bridge/mainnet EVM deployment treated as native L28.
- Any change to Protocol v1.0.0 economic constants.

### Items prohibited from reuse from Leap28 or Nova

- Leap28 SovereignBrain, private orchestration, memory spine, and private historical auto-activation (`PROTOCOL.md`, `NON_GOALS.md`).
- Any Nova-branded runtime or dependency (none present; do not introduce as L28 authority).
- Private source promotion without a public specification and promotion gates (`docs/l28_future_capability_registry_v0.1.md`).

### Confirmation: L28 remains independently testable

Yes. Local evidence at parent `980dad78e82b167f4527b1b92cfdd5a9878fad1e`:

- `python -m coin.invariants`
- `python -m unittest discover -s tests`
- Offline CLIs such as `coin/historical_continuity_cli.py` and `coin/node_role_conformance_cli.py`
- CI workflow `.github/workflows/ci.yml`

None of these require Leap28, Nova, network listeners, or live wallets.

### Confirmation: this audit grants no execution authority

This Foundation 37 document is an offline gap audit only. It is not permission to spend
L28, not an executable transaction or ledger command, not settlement finality, not
mining, node, wallet, or network activation, and not authorization to start a testnet.

---

## Appendix A — Domain coverage checklist

| Audit domain | Finding | Class |
|---|---|---|
| Canonical chain initialization and historical bootstrap boundary | F37-01 | PARTIAL |
| Consensus height and fail-closed state authority | F37-02 | PARTIAL |
| Transaction and coinbase validation | F37-03 | READY |
| Supply-cap and emission enforcement | F37-04 | READY |
| Deterministic ledger replay and persistence boundaries | F37-05 | PARTIAL |
| Node lifecycle and process isolation | F37-06 | BLOCKED |
| Peer discovery, transport, message validation, and synchronization | F37-07 | BLOCKED |
| Mining difficulty, canonical work validation, and reward rules | F37-08 | PARTIAL |
| Disposable test wallets and key isolation | F37-09 | PARTIAL |
| Transaction propagation and settlement confirmation | F37-10 | BLOCKED |
| Fork handling, reorganization policy, and recovery | F37-11 | BLOCKED |
| Network identity, genesis/config binding, and environment separation | F37-12 | BLOCKED |
| Observability, shutdown, reset, and cleanup | F37-13 | PARTIAL |
| Adversarial, integration, and end-to-end test coverage | F37-14 | PARTIAL |
| Foundations 31–36 relevance and explicit non-authority | F37-15 | OUT_OF_SCOPE |
| Leap28 / Nova / bridge non-reuse | F37-16 | OUT_OF_SCOPE |
