# Bitcoin Interoperability — Security Conformance Plan v0.1

**Foundation:** 94

**Status:** conformance plan / non-activating

**Plan version:** `bitcoin-interoperability-conformance-plan/v0.1`

**Authoritative design input:** `docs/bitcoin_interoperability_spec.md`
(Foundation 93; document version `bitcoin-interoperability-spec/v0.1`)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Parent:** `05932da2c3dce3f930f733feb67f7002982b484b`

**Branch:** `foundation94-bitcoin-security-conformance-plan`

**Implementation:** none

**Fixtures:** none

**Network execution:** none

**Normative subordination:** This document is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md). On conflict, Protocol v1.0.0 prevails.
This plan is also subordinate to Foundation 93 for Bitcoin identity, custody,
proof, reorg, and supply-firewall rules, and to Universal Access Interface
v0.1 (`docs/universal_access_interface_v0.1.md`) for any later public
interface mapping. This plan MUST NOT redefine UAII v0.1, settlement,
issuance, supply, consensus height authority, historical evidence, or
`validate_transaction`.

**Related locked contracts (consumed, not replaced):**

- `PROTOCOL.md` — sole native settlement and issuance authority
- `docs/bitcoin_interoperability_spec.md` — Bitcoin adapter boundary
- `docs/universal_access_interface_v0.1.md` — canonical agent-facing interface
- `docs/universal_access_conformance_plan_v0.1.md` — UAII case/fixture pattern
- `conformance/universal_access/v0.1/**` — existing UAII fixtures (untouched)
- `tests/test_universal_access_*fixtures.py` — existing isolated UAII runners (untouched)
- Historical evidence and protected economic constants — immutable

---

## 1. Purpose and non-activation

### 1.1 Purpose

Foundation 94 defines the **deterministic, non-networked conformance plan**
that MUST pass before any Bitcoin interoperability adapter implementation is
allowed.

This is **plan only**. It reserves case IDs, fixture IDs, safety assertions,
error concepts, and activation gates. It does **not** create fixtures,
schemas, test runners, Bitcoin adapters, RPC clients, wallets, signers,
network code, or bridge code.

### 1.2 Explicit non-activation

Foundation 94 MUST NOT:

- create fixture files, schemas, or test runners
- implement a Bitcoin adapter
- connect Bitcoin Core or use Bitcoin RPC
- start a Bitcoin node or perform SPV networking
- create, import, or use wallets
- generate keys
- sign or broadcast Bitcoin transactions
- mine BTC
- deploy contracts or execute `contracts/deploy_bridge.py`
- start L28 networking
- mutate ledger state
- modify consensus
- modify Protocol v1.0.0
- add Bitcoin operations to UAII v0.1
- select a production proof architecture
- hard-code a production confirmation count
- choose a production observer quorum

Passing, merging, or later executing fixtures derived from this plan is
**not** permission to spend L28, mint L28, mine BTC, open listeners, or
treat Bitcoin state as L28 state.

---

## 2. Scope and terminology

### 2.1 In scope (planning only)

| Area | Plan content |
|---|---|
| Network identity | Explicit Bitcoin network labels; no default inference |
| Proof validation | Structural public-proof accept/reject under caller-supplied test policy |
| Wrong-network evidence | No cross-network repair or coercion |
| Reorg / stale evidence | Probabilistic confirmations; fail closed on unavailable tip |
| Replay / duplicate | Evidence-id and txid/outpoint uniqueness |
| Observer agreement | Test-local agreement/disagreement; quorum unset |
| Secret / signing / broadcast | Forbidden material and unauthorized operations |
| L28 economic firewall | Exact protected Protocol constants; no adapter override |
| Native / wrapped identity | BTC, wrap, and bridge never become native L28 |
| Deterministic serialization | Identical bytes → equivalent public outcome |

### 2.2 Out of scope (forbidden in this Foundation)

- Creating files under a fixture directory
- Machine-readable JSON Schema / fixture packs
- Executable test harnesses
- Bitcoin or L28 adapter implementations
- RPC, DNS, P2P, or any network call
- Wallet, signer, miner, or bridge activation
- Production proof-architecture selection
- Production confirmation or quorum numbers

### 2.3 Terminology

| Term | Meaning |
|---|---|
| Fixture | Deferred deterministic fictional input bundle; not created here |
| Case | One planned assertion tuple: fixture + evaluation + expected outcome |
| Positive (`POS`) | Expected observation-accept under declared test policy; all grant flags false |
| Negative (`NEG`) | Expected reject with a stable conceptual error code |
| Boundary (`BND`) | Edge values at a caller-supplied **test** policy limit |
| Fail-closed (`FCL`) | Required state missing, conflicting, or unsafe; reject with no repair |
| Caller-supplied test policy | Fixture-local confirmation/reorg/quorum/proof-structure object; **not** production policy |
| Disposable identifier | Fictional public Bitcoin or L28 label never used for production funds |
| Case ID | `BTC-CONF-v0.1-<FAMILY>-<POLARITY>-NNN` |
| Fixture ID | `fx-btc-v01-NNNN` reserved for future use |

Bitcoin network identity never becomes L28 network identity. A future
observation success is **external Bitcoin evidence at most**.

---

## 3. Versioning and identifier model

### 3.1 Versioning

| Item | Value |
|---|---|
| Plan document | `bitcoin-interoperability-conformance-plan/v0.1` |
| Design profile under test | `bitcoin-interoperability-spec/v0.1` |
| Protocol | `1.0.0` |
| Case-ID namespace | `BTC-CONF/v0.1` |
| Fixture-ID namespace | `fx-btc-v01` |
| UAII profile | unchanged `l28-universal-ai-access-interface/v0.1` (no Bitcoin operations added) |

Future plan revisions MUST bump the plan version and MUST NOT silently
redefine case IDs or fixture IDs. Deprecated IDs remain listed as superseded.

### 3.2 Case ID model

```text
BTC-CONF-v0.1-<FAMILY>-<POLARITY>-NNN
```

| Token | Rule |
|---|---|
| `FAMILY` | `NID` `PRF` `WRN` `REO` `RPL` `AGR` `SEC` `ECO` `IDN` `DET` |
| `POLARITY` | `POS` = positive; `NEG` = negative; `BND` = boundary; `FCL` = fail_closed |
| `NNN` | Three-digit suffix, unique within family+polarity, starting at `001` |

Ordering rules:

1. Catalog tables appear in the family order listed above.
2. Within a family, sort by polarity: `POS`, then `NEG`, then `BND`, then `FCL`.
3. Within a polarity group, sort by numeric suffix ascending.
4. Case IDs MUST be unique across this entire plan version.
5. Future additions append new numeric suffixes; they MUST NOT reorder existing IDs.

### 3.3 Fixture ID model

```text
fx-btc-v01-NNNN
```

All fixture IDs in this plan are **reserved names** for a later authorized
fixture foundation. They MUST be unique across this plan version and MUST
NOT collide with UAII fixture IDs (`fx-uai-v01-NNNN`).

This Foundation maps each planned case to exactly one reserved fixture ID.

---

## 4. Determinism rules

When a later foundation implements fixtures or a runner, it MUST:

1. Use **caller-supplied timestamps only** (no system clock, no TZ defaults,
   no process-environment time).
2. Use **caller-supplied confirmation / reorg / quorum / proof-structure
   policy only**. Those numbers are test-local and are **not** production
   policy.
3. Use **canonical serialization** of public objects (exact documented field
   order; UTF-8 JSON).
4. Emit **stable error codes** from §7. No free-text-only failures.
5. Keep **no hidden state**. Evaluation state required by a case MUST appear
   in the fixture.
6. Perform **no network**, **no DNS**, **no RPC**.
7. Derive **no environment authority** (no env vars, no host files, no
   operator wallets).
8. Depend on **no production wallet, address, transaction, or balance**.
9. Guarantee **identical input bytes ⇒ equivalent public outcome**.
10. Keep every safety assertion in §5.2 `false`.

Forbidden inference sources include: wall clock, DNS, Bitcoin Core, public
explorers, EVM RPCs, process environment, and “best effort” network defaults.

---

## 5. Future fixture format (not created here)

### 5.1 Logical fixture object (exact conceptual order)

Planned machine-readable fixtures (deferred) MUST use this conceptual key
order:

1. `fixture_id` — unique; pattern `fx-btc-v01-NNNN`
2. `plan_version` — `"bitcoin-interoperability-conformance-plan/v0.1"`
3. `design_profile` — `"bitcoin-interoperability-spec/v0.1"`
4. `case_id` — unique `BTC-CONF-v0.1-…` reference
5. `family` — one of the ten family codes
6. `polarity` — `"positive"` \| `"negative"` \| `"boundary"` \| `"fail_closed"`
7. `description` — short public string
8. `fixed_clock` — object with caller-supplied Unix-second ints only
9. `test_policy` — caller-supplied confirmation/reorg/quorum/proof-structure
   object; explicitly `not_production_policy=true`
10. `bitcoin_evidence` — fictional public Bitcoin-labeled object or omission
    under test
11. `observer_views` — optional fictional observer array
12. `prior_accept_state` — optional fictional prior observation record
13. `l28_invariants` — exact protected Protocol constants
14. `request` — future adapter-facing public object under test
15. `expected` — accept/reject public outcome
16. `safety` — object asserting absence of secrets and production material

### 5.2 Required safety assertions

Every future fixture MUST declare, and every future runner MUST verify, fields
equivalent to:

| Assertion | Required value |
|---|---|
| `contains_private_keys` | `false` |
| `contains_credentials` | `false` |
| `uses_real_wallet` | `false` |
| `uses_real_balance` | `false` |
| `uses_real_transaction` | `false` |
| `network_call_performed` | `false` |
| `signing_performed` | `false` |
| `broadcast_performed` | `false` |
| `ledger_mutated` | `false` |
| `settlement_finalized` | `false` |
| `spend_authorized` | `false` |
| `execution_authorized` | `false` |
| `adapter_override_allowed` | `false` |

Fixtures MUST NEVER contain real keys, credentials, wallets, balances,
transactions, production addresses, RPC endpoints, or canonical
historical-ledger mutations.

### 5.3 Disposable public identifiers (fictional only)

| Alias | Disposable public value |
|---|---|
| `NET_MAIN` | `bitcoin-test-mainnet` |
| `NET_TEST` | `bitcoin-test-testnet` |
| `NET_SIGNET` | `bitcoin-test-signet` |
| `NET_REGTEST` | `bitcoin-test-regtest` |
| `NET_UNKNOWN` | `bitcoin-test-unknown-network` |
| `TXID_A` | `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` |
| `TXID_B` | `bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb` |
| `BLOCK_A` | `cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc` |
| `BLOCK_B` | `dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd` |
| `EVIDENCE_A` | `evidence-btc-conf-a` |
| `OUTPOINT_A` | `txid=TXID_A, vout=0` |

These labels are **test vocabulary**. They MUST NOT be resolved via DNS,
RPC, or a live Bitcoin network. They MUST NEVER be copied into L28
`asset_id`, L28 height, or L28 supply fields.

### 5.4 Forbidden-field markers (not secrets)

Negative secret cases MUST use obvious disposable markers only. No real
secret values MAY appear in fixtures.

| Field under test | Allowed marker only |
|---|---|
| `private_key` | `FORBIDDEN_FIELD_MARKER_NOT_A_KEY` |
| `seed_phrase` / `mnemonic` | `FORBIDDEN_FIELD_MARKER_NOT_A_MNEMONIC` |
| `xprv` | `FORBIDDEN_FIELD_MARKER_NOT_AN_XPRV` |
| `rpc_user` / `rpc_password` / `rpc_cookie` | `FORBIDDEN_FIELD_MARKER_NOT_A_CREDENTIAL` |

A runner that accepts these markers as credentials, or that logs them as
secrets, fails conformance.

### 5.5 Caller-supplied test policy (not production)

Illustrative test-local policy fragment (fictional; non-executing):

```json
{
  "not_production_policy": true,
  "production_proof_architecture": "BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION",
  "production_confirmation_count": "BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION",
  "production_quorum": "BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION",
  "test_min_confirmations": 2,
  "test_observer_count": 2,
  "test_require_merkle_path": true,
  "test_require_network_identity": true
}
```

`test_min_confirmations` and `test_observer_count` exist only so boundary
and agreement cases can evaluate deterministically. They are **not** a
production confirmation count and **not** a production quorum.

Production proof architecture remains
`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

Production confirmation policy remains
`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

Quorum design remains
`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

---

## 6. Case format

### 6.1 Logical case object (exact conceptual order)

1. `case_id` — unique `BTC-CONF-v0.1-<FAMILY>-<POLARITY>-NNN`
2. `fixture_id` — reserved `fx-btc-v01-NNNN`
3. `family` — family code
4. `polarity` — `positive` \| `negative` \| `boundary` \| `fail_closed`
5. `request` — public Bitcoin-labeled observation object under test
6. `expected` — accept fields and/or conceptual error code
7. `safety_assertions` — full §5.2 set
8. `l28_invariants` — exact protected constants; `adapter_override_allowed=false`
9. `adapter_expectation` — identical public outcome across any later adapters

### 6.2 Observation-accept flags

Any planned **positive** observation outcome MUST keep:

| Flag | Value |
|---|---|
| `execution_authorized` | `false` |
| `spend_authorized` | `false` |
| `signing_authorized` | `false` |
| `broadcast_authorized` | `false` |
| `ledger_mutated` | `false` |
| `settlement_finalized` | `false` |
| `transaction_submitted` | `false` |
| `l28_issuance_authorized` | `false` |
| `native_asset` | `false` for BTC and wrapped-BTC |
| `adapter_override_allowed` | `false` |

Replay, reject, and fail-closed outcomes MUST also keep every grant/mutation
flag `false`. A replay failure MUST NOT imply settlement, spending, or
ledger mutation.

---

## 7. Error / result model

This plan defines **stable conceptual errors** for a future Bitcoin
observation adapter. It does **not** redefine UAII v0.1 codes or add
Bitcoin operations to `l28-universal-ai-access-interface/v0.1`.

| Conceptual code | Meaning |
|---|---|
| `schema_invalid` | Malformed JSON, duplicate key, unknown required-strict field, bad types |
| `network_identity_invalid` | Unknown, missing, or unusable Bitcoin network identity |
| `network_mismatch` | Proof/evidence network ≠ declared network |
| `proof_invalid` | Malformed or mutated public proof |
| `proof_insufficient` | Structurally present but below caller-supplied test policy |
| `proof_stale` | Proof bound to orphaned or no-longer-canonical evidence |
| `reorg_detected` | Declared tip no longer ancestors the previously accepted block |
| `replay_detected` | Evidence id presented after acceptance |
| `duplicate_evidence` | Same txid/outpoint evidence already present |
| `observer_disagreement` | Independent observers report incompatible public facts |
| `required_state_unavailable` | Required tip, proof, evidence-id, or quorum state missing |
| `secret_material_forbidden` | Private key, seed, xprv, RPC credential, or equivalent present |
| `operation_unsupported` | Bitcoin signing, broadcast, or other unauthorized operation |
| `authority_denied` | Observer/adapter claimed a grant it does not have |
| `adapter_override_forbidden` | Attempt to override L28 validation, economics, height, or history |
| `asset_identity_invalid` | Native / wrapped / bridge identity cannot be established safely |

UAII v0.1 remains the agent-facing profile for L28 operations. A later
Bitcoin observation profile, if authorized, MUST version separately and MAY
map the conceptual codes above without silently extending UAII v0.1.

---

## 8. Protected L28 invariants

Every Bitcoin conformance case MUST preserve Protocol v1.0.0 and these
exact facts (MUST NOT redefine or override):

| Fact | Value |
|---|---:|
| Hard cap | 28,000,000 L28 |
| Emission ceiling | 11,130,000 L28 |
| Historically mined | 2,824,584 L28 |
| Treasury locked | 500,000 L28 |
| Circulating snapshot | 2,324,584 L28 |
| Issuance | coinbase only |
| L28 height | consensus-derived |
| Historical evidence | immutable |
| Adapter override allowed | false |

Bitcoin satoshi amounts MUST remain satoshi amounts. Bitcoin height MUST
remain Bitcoin height. Neither MAY be coerced into L28 units or L28
canonical height.

Invariant fragment (fictional public constants only):

```json
{
  "protocol_version": "1.0.0",
  "hard_cap_l28": 28000000,
  "emission_ceiling_l28": 11130000,
  "historically_mined_l28": 2824584,
  "treasury_locked_l28": 500000,
  "circulating_snapshot_l28": 2324584,
  "issuance_mechanism": "coinbase_only",
  "height_authority": "consensus_derived",
  "historical_evidence": "immutable",
  "adapter_override_allowed": false
}
```

---

## 9. Planned case catalog

Counts below are planned cases for a future suite. This Foundation does
**not** implement them.

### 9.1 `BTC-NID` — network identity

Rules: Bitcoin network identity never becomes L28 network identity. No
default network inference. Unknown or missing identity fails closed.

| case_id | fixture_id | polarity | Summary | Expected |
|---|---|---|---|---|
| `BTC-CONF-v0.1-NID-POS-001` | `fx-btc-v01-0001` | positive | Explicit supported network identity `NET_MAIN` on evidence and declaration | observation accept; Bitcoin-labeled only; all grant flags false |
| `BTC-CONF-v0.1-NID-NEG-001` | `fx-btc-v01-0002` | negative | Unknown network `NET_UNKNOWN` | `network_identity_invalid` |
| `BTC-CONF-v0.1-NID-NEG-002` | `fx-btc-v01-0003` | negative | Missing network identity | `network_identity_invalid` |
| `BTC-CONF-v0.1-NID-NEG-003` | `fx-btc-v01-0004` | negative | Proof network ≠ declared network | `network_mismatch` |
| `BTC-CONF-v0.1-NID-FCL-001` | `fx-btc-v01-0005` | fail_closed | Conflicting network identity evidence in the same evaluation | `network_identity_invalid` or `required_state_unavailable`; no default network |

### 9.2 `BTC-PRF` — proof validation

Do **not** select a production proof architecture. Cases evaluate
**structural** public-proof objects against a caller-supplied **test**
policy only.

Production proof architecture:
`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

| case_id | fixture_id | polarity | Summary | Expected |
|---|---|---|---|---|
| `BTC-CONF-v0.1-PRF-POS-001` | `fx-btc-v01-0006` | positive | Structurally valid public proof under caller-supplied test policy | observation accept; flags false; no architecture selected |
| `BTC-CONF-v0.1-PRF-NEG-001` | `fx-btc-v01-0007` | negative | Malformed proof | `proof_invalid` |
| `BTC-CONF-v0.1-PRF-NEG-002` | `fx-btc-v01-0008` | negative | Incomplete proof (required public path/header field omitted) | `proof_insufficient` |
| `BTC-CONF-v0.1-PRF-NEG-003` | `fx-btc-v01-0009` | negative | Mutated transaction or proof digest | `proof_invalid` |
| `BTC-CONF-v0.1-PRF-BND-001` | `fx-btc-v01-0010` | boundary | Minimum structurally sufficient proof under the test policy | accept structurally; flags false |
| `BTC-CONF-v0.1-PRF-FCL-001` | `fx-btc-v01-0011` | fail_closed | Required proof state unavailable | `required_state_unavailable`; no invented proof |

### 9.3 `BTC-WRN` — wrong-network evidence

No cross-network repair or coercion.

| case_id | fixture_id | polarity | Summary | Expected |
|---|---|---|---|---|
| `BTC-CONF-v0.1-WRN-NEG-001` | `fx-btc-v01-0012` | negative | Mainnet evidence presented as testnet | `network_mismatch` |
| `BTC-CONF-v0.1-WRN-NEG-002` | `fx-btc-v01-0013` | negative | Testnet evidence presented as mainnet | `network_mismatch` |
| `BTC-CONF-v0.1-WRN-NEG-003` | `fx-btc-v01-0014` | negative | Signet evidence presented as mainnet | `network_mismatch` |
| `BTC-CONF-v0.1-WRN-NEG-004` | `fx-btc-v01-0015` | negative | Regtest evidence presented as mainnet | `network_mismatch` |
| `BTC-CONF-v0.1-WRN-FCL-001` | `fx-btc-v01-0016` | fail_closed | Proof cannot be bound to the declared network | `network_mismatch` or `required_state_unavailable`; no coercion |

### 9.4 `BTC-REO` — reorg / stale evidence

Bitcoin confirmations are probabilistic. Do **not** define a production
confirmation count.

Production confirmation policy:
`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

| case_id | fixture_id | polarity | Summary | Expected |
|---|---|---|---|---|
| `BTC-CONF-v0.1-REO-POS-001` | `fx-btc-v01-0017` | positive | Evidence remains on the declared canonical branch under test policy | observation accept; flags false |
| `BTC-CONF-v0.1-REO-NEG-001` | `fx-btc-v01-0018` | negative | Orphaned or stale evidence | `proof_stale` |
| `BTC-CONF-v0.1-REO-NEG-002` | `fx-btc-v01-0019` | negative | Previously accepted observation reused after reorg | `reorg_detected` or `proof_stale`; no reuse |
| `BTC-CONF-v0.1-REO-BND-001` | `fx-btc-v01-0020` | boundary | Confirmations exactly equal caller-supplied **test** policy | accept under that test policy only; not a production count |
| `BTC-CONF-v0.1-REO-FCL-001` | `fx-btc-v01-0021` | fail_closed | Canonical Bitcoin state unavailable or conflicting | `required_state_unavailable`; not “zero confirmations” |

### 9.5 `BTC-RPL` — replay / duplicate

Replay failure MUST NOT imply settlement, spending, or ledger mutation.

| case_id | fixture_id | polarity | Summary | Expected |
|---|---|---|---|---|
| `BTC-CONF-v0.1-RPL-POS-001` | `fx-btc-v01-0022` | positive | First presentation of `EVIDENCE_A` | observation accept; flags false |
| `BTC-CONF-v0.1-RPL-NEG-001` | `fx-btc-v01-0023` | negative | Replay of `EVIDENCE_A` after acceptance | `replay_detected`; `settlement_finalized=false` |
| `BTC-CONF-v0.1-RPL-NEG-002` | `fx-btc-v01-0024` | negative | Duplicate txid/outpoint evidence | `duplicate_evidence`; flags false |
| `BTC-CONF-v0.1-RPL-FCL-001` | `fx-btc-v01-0025` | fail_closed | Evidence-id state required but unavailable | `required_state_unavailable`; no implied first-seen accept |

### 9.6 `BTC-AGR` — observer agreement

Do **not** choose a production quorum count.

Quorum design:
`BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION`.

| case_id | fixture_id | polarity | Summary | Expected |
|---|---|---|---|---|
| `BTC-CONF-v0.1-AGR-POS-001` | `fx-btc-v01-0026` | positive | Independent observers agree under caller-supplied test policy | observation accept; flags false |
| `BTC-CONF-v0.1-AGR-NEG-001` | `fx-btc-v01-0027` | negative | Observers disagree on block hash / tip | `observer_disagreement` |
| `BTC-CONF-v0.1-AGR-NEG-002` | `fx-btc-v01-0028` | negative | Observers disagree on transaction inclusion | `observer_disagreement` |
| `BTC-CONF-v0.1-AGR-FCL-001` | `fx-btc-v01-0029` | fail_closed | Required test-local quorum unavailable | `required_state_unavailable`; no majority invention |

### 9.7 `BTC-SEC` — secret / signing / broadcast security

Expected stable concepts: `secret_material_forbidden`,
`operation_unsupported`, `authority_denied`.

No real secret values. Use §5.4 markers only.

| case_id | fixture_id | polarity | Summary | Expected |
|---|---|---|---|---|
| `BTC-CONF-v0.1-SEC-NEG-001` | `fx-btc-v01-0030` | negative | `private_key` field present | `secret_material_forbidden` |
| `BTC-CONF-v0.1-SEC-NEG-002` | `fx-btc-v01-0031` | negative | `seed_phrase` / `mnemonic` present | `secret_material_forbidden` |
| `BTC-CONF-v0.1-SEC-NEG-003` | `fx-btc-v01-0032` | negative | `xprv` present | `secret_material_forbidden` |
| `BTC-CONF-v0.1-SEC-NEG-004` | `fx-btc-v01-0033` | negative | RPC credentials present | `secret_material_forbidden` |
| `BTC-CONF-v0.1-SEC-NEG-005` | `fx-btc-v01-0034` | negative | Attempted Bitcoin signing | `operation_unsupported` |
| `BTC-CONF-v0.1-SEC-NEG-006` | `fx-btc-v01-0035` | negative | Attempted Bitcoin broadcast | `operation_unsupported` |
| `BTC-CONF-v0.1-SEC-NEG-007` | `fx-btc-v01-0036` | negative | Observer claims `signing_authorized=true` | `authority_denied` |
| `BTC-CONF-v0.1-SEC-FCL-001` | `fx-btc-v01-0037` | fail_closed | Secret material appears anywhere in adapter input or output | `secret_material_forbidden`; do not log the marker as a secret |

### 9.8 `BTC-ECO` — L28 economic / authority firewall

| case_id | fixture_id | polarity | Summary | Expected |
|---|---|---|---|---|
| `BTC-CONF-v0.1-ECO-NEG-001` | `fx-btc-v01-0038` | negative | Hard-cap override | `adapter_override_forbidden` |
| `BTC-CONF-v0.1-ECO-NEG-002` | `fx-btc-v01-0039` | negative | Emission-ceiling override | `adapter_override_forbidden` |
| `BTC-CONF-v0.1-ECO-NEG-003` | `fx-btc-v01-0040` | negative | Historically-mined override | `adapter_override_forbidden` |
| `BTC-CONF-v0.1-ECO-NEG-004` | `fx-btc-v01-0041` | negative | Treasury locked or circulating snapshot override | `adapter_override_forbidden` |
| `BTC-CONF-v0.1-ECO-NEG-005` | `fx-btc-v01-0042` | negative | Non-coinbase issuance claim | `adapter_override_forbidden` |
| `BTC-CONF-v0.1-ECO-NEG-006` | `fx-btc-v01-0043` | negative | Bitcoin height supplied as L28 canonical height | `adapter_override_forbidden` |
| `BTC-CONF-v0.1-ECO-NEG-007` | `fx-btc-v01-0044` | negative | `validate_transaction` override | `adapter_override_forbidden` |
| `BTC-CONF-v0.1-ECO-FCL-001` | `fx-btc-v01-0045` | fail_closed | Historical evidence mutation | `adapter_override_forbidden`; history remains immutable |

### 9.9 `BTC-IDN` — native / wrapped identity confusion

Native identity ambiguity MUST fail closed.

| case_id | fixture_id | polarity | Summary | Expected |
|---|---|---|---|---|
| `BTC-CONF-v0.1-IDN-POS-001` | `fx-btc-v01-0046` | positive | Bitcoin evidence remains labeled external Bitcoin evidence | accept as Bitcoin-domain only; `native_asset=false` |
| `BTC-CONF-v0.1-IDN-NEG-001` | `fx-btc-v01-0047` | negative | BTC represented as native L28 | `asset_identity_invalid` |
| `BTC-CONF-v0.1-IDN-NEG-002` | `fx-btc-v01-0048` | negative | Wrapped BTC represented as BTC | `asset_identity_invalid` |
| `BTC-CONF-v0.1-IDN-NEG-003` | `fx-btc-v01-0049` | negative | Wrapped L28 represented as native L28 | `asset_identity_invalid` |
| `BTC-CONF-v0.1-IDN-NEG-004` | `fx-btc-v01-0050` | negative | Bridge contract claimed to define native L28 identity | `asset_identity_invalid` |
| `BTC-CONF-v0.1-IDN-FCL-001` | `fx-btc-v01-0051` | fail_closed | Asset identity cannot be established | `asset_identity_invalid`; no wrap/native guess |

### 9.10 `BTC-DET` — deterministic serialization

No system clock. No network-derived defaults. No environment-derived
authority. No nondeterministic values.

| case_id | fixture_id | polarity | Summary | Expected |
|---|---|---|---|---|
| `BTC-CONF-v0.1-DET-POS-001` | `fx-btc-v01-0052` | positive | Identical canonical public inputs produce equivalent public outputs | byte-stable public outcome |
| `BTC-CONF-v0.1-DET-POS-002` | `fx-btc-v01-0053` | positive | Repeated evaluation of the same fixture produces the same result | identical public outcome |
| `BTC-CONF-v0.1-DET-NEG-001` | `fx-btc-v01-0054` | negative | Duplicate JSON key | `schema_invalid` |
| `BTC-CONF-v0.1-DET-NEG-002` | `fx-btc-v01-0055` | negative | Unsupported / unknown field where strict schema applies | `schema_invalid` |
| `BTC-CONF-v0.1-DET-BND-001` | `fx-btc-v01-0056` | boundary | Canonical lowercase hex identifiers | accept if else valid; uppercase MUST NOT be repaired |
| `BTC-CONF-v0.1-DET-FCL-001` | `fx-btc-v01-0057` | fail_closed | Input would require system clock, network, or environment inference | `required_state_unavailable` or `schema_invalid`; no inference |

Illustrative observation-accept fragment (fictional; non-executing):

```json
{
  "ok": true,
  "code": "bitcoin_observation_ok",
  "result": {
    "evidence_domain": "bitcoin",
    "bitcoin_network": "bitcoin-test-mainnet",
    "native_asset": false,
    "asset_id": "BTC-EXTERNAL",
    "txid": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "output_index": 0,
    "amount_satoshis": 1,
    "execution_authorized": false,
    "spend_authorized": false,
    "signing_authorized": false,
    "broadcast_authorized": false,
    "ledger_mutated": false,
    "settlement_finalized": false,
    "l28_issuance_authorized": false,
    "adapter_override_allowed": false
  }
}
```

---

## 10. Coverage matrix

| Family | POS | NEG | BND | FCL | Total |
|---|---:|---:|---:|---:|---:|
| `NID` network identity | 1 | 3 | 0 | 1 | 5 |
| `PRF` proof validation | 1 | 3 | 1 | 1 | 6 |
| `WRN` wrong-network evidence | 0 | 4 | 0 | 1 | 5 |
| `REO` reorg / stale | 1 | 2 | 1 | 1 | 5 |
| `RPL` replay / duplicate | 1 | 2 | 0 | 1 | 4 |
| `AGR` observer agreement | 1 | 2 | 0 | 1 | 4 |
| `SEC` secret / signing / broadcast | 0 | 7 | 0 | 1 | 8 |
| `ECO` L28 economic firewall | 0 | 7 | 0 | 1 | 8 |
| `IDN` native / wrapped identity | 1 | 4 | 0 | 1 | 6 |
| `DET` deterministic serialization | 2 | 2 | 1 | 1 | 6 |
| **Plan total** | **8** | **36** | **3** | **10** | **57** |

Reserved fixture IDs: `fx-btc-v01-0001` through `fx-btc-v01-0057` (57 unique).

---

## 11. Universal Access relationship

This plan does **not** add Bitcoin operations to UAII v0.1 and does **not**
redefine UAII case IDs, fixture IDs, or error codes.

Existing UAII artifacts remain authoritative for L28 agent access:

- `docs/universal_access_interface_v0.1.md`
- `docs/universal_access_conformance_plan_v0.1.md`
- `conformance/universal_access/v0.1/**`
- `tests/test_universal_access_*fixtures.py`

A future Bitcoin observation operation, if authorized, MUST:

1. Publish a new interface profile or plan version.
2. Keep Bitcoin fields in a Bitcoin-labeled object.
3. Keep all grant/mutation flags false for observation.
4. Reject secret fields at the envelope.
5. Remain subordinate to Protocol v1.0.0 and `validate_transaction`.
6. Implement the cases in §9 before any adapter implementation.

On conflict: Protocol v1.0.0 prevails over UAII; UAII prevails over this
plan for L28 interface field names; Foundation 93 prevails over this plan
for Bitcoin identity and custody rules.

---

## 12. Deferred machine-readable layout (NOT created by Foundation 94)

The following paths are **proposed only**. Foundation 94 MUST NOT create
them.

```text
# DEFERRED — do not create in Foundation 94
conformance/bitcoin_interoperability/v0.1/
  README.md
  schemas/
    observation.schema.json
    fixtures.schema.json
    cases.schema.json
  fixtures/
    fx-btc-v01-0001.json
    ...
    fx-btc-v01-0057.json
  cases/
    BTC-CONF-v0.1-NID-POS-001.json
    ...
```

Creating schemas, fixture files, or runners requires a later explicit
authorization distinct from Foundation 94.

---

## 13. Activation firewall

Passing Foundation 94, or later passing fixtures derived from this plan,
DOES NOT authorize:

- Bitcoin RPC
- Bitcoin Core connection
- SPV networking
- wallet creation or import
- key generation
- signing
- broadcasting
- mining
- bridge deployment
- L28 networking
- settlement
- ledger mutation
- Protocol v1.0.0 changes

Observation-accept in a fixture is not Bitcoin finality and is not L28
settlement.

---

## 14. Implementation gate

Bitcoin adapter implementation remains **blocked** until each of the
following is separately completed:

1. Foundation 94 conformance plan (this document; plan only)
2. Machine-readable fixtures
3. Deterministic isolated test runner
4. Threat-model review
5. Proof-model decision
6. Reorg / finality decision
7. Custody / signing architecture
8. Independent security review
9. Explicit operator authorization

Absence of any gate is a block, not a default-allow. This document
satisfies item 1 only as a plan. It does not satisfy items 2–9.

---

## 15. Document control

| Field | Value |
|---|---|
| Foundation | 94 |
| Status | conformance plan / non-activating |
| Parent | `05932da2c3dce3f930f733feb67f7002982b484b` |
| Path | `docs/bitcoin_interoperability_conformance_plan_v0.1.md` |
| Implementation | none |
| Fixtures | none |
| Network execution | none |
| Planned case total | 57 |
| Planned fixture IDs | `fx-btc-v01-0001` … `fx-btc-v01-0057` |
| Bitcoin operations added to UAII v0.1 | none |
| Production proof architecture | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production confirmation count | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Production quorum | `BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION` |
| Payment model authorized | none |
