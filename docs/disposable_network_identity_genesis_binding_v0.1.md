# L28 Disposable Network Identity and Genesis Binding v0.1

**Foundation:** 38

**Status:** Offline specification only; non-activation

**Milestone:** M1 only (Foundation 37 sequence)

**Audit parent finding:** F37-12

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN) — immutable

## Purpose

Foundation 38 defines the bounded offline specification for a **disposable**
L28 network identity and genesis-binding document. It closes Foundation 37
finding F37-12 at the specification level by requiring:

- a deterministic disposable network ID and chain ID;
- a canonical disposable genesis document and digest;
- explicit protocol-version and environment binding;
- hard separation from historical and canonical L28 state;
- fail-closed config loading and mismatch rejection;
- identity binding requirements for future peer handshake and ledger/replay
  surfaces;
- reset, cleanup, and reproducibility rules;
- schema, canonical serialization, size/type limits, and malformed-input
  rejection.

This document does **not** implement runtime code, start a node or network,
create live genesis, mine, open wallets, or authorize a testnet. It grants
**no execution authority**.

## Public identifiers

| Identifier | Value |
|---|---|
| Profile | `l28-disposable-network-identity-genesis-binding/v0.1` |
| Verifier profile | `l28-disposable-network-identity-genesis-binding-verifier/v0.1` |
| Report profile | `l28-disposable-network-identity-genesis-binding-report/v0.1` |
| Environment class | `DISPOSABLE_TEST` |
| Bound protocol version | `l28-protocol/1.0.0` |
| Forbidden environment labels | `MAIN`, `CANONICAL`, `HISTORICAL`, `PRODUCTION` |
| Maximum encoded genesis document size | `8192` bytes |
| Maximum encoded binding-config size | `8192` bytes |

## Relationship to Foundation 37 / F37-12

F37-12 required an explicit disposable network identifier, genesis binding, and
hard separation from main-network or historical checkpoint identity.

This specification addresses that requirement by defining the normative identity
objects, digests, rejection rules, and future binding surfaces. Implementation
of verifiers and later Core/P2P wiring remains a subsequent foundation and is
**out of scope for Foundation 38**.

Evidence of the current gap this specification targets:

- `coin/tx_validation.py` — `validate_transaction(..., network: str = "MAIN")`
- `coin/ledger.py` — `_current_balance_lookup(..., network: str = "MAIN")`,
  `initialize_disposable_test_issuance_state`
- `docs/l28_core_p2p_architecture_v0.1.md` — future frames must bind protocol
  version and network identifier
- `docs/bounded_testnet_readiness_gap_audit_v0.1.md` — finding F37-12
- `PROTOCOL.md` — empty directory / clone is not trusted main-network genesis
- `docs/l28_historical_continuity_manifest_v0.1.json` — activation flags remain
  false; historical evidence is not runtime state

## Protected economic facts (immutable)

Foundation 38 MUST NOT alter Protocol v1.0.0 economics. Any conforming genesis
or binding document MUST echo these facts and MUST fail closed if they differ:

| Fact | Required value | Evidence |
|---|---:|---|
| Protocol | v1.0.0 FROZEN | `PROTOCOL.md` |
| Hard cap | `28_000_000` | `coin/tx_validation.py` `L28_MAX_SUPPLY` |
| Emission ceiling | `11_130_000` | `coin/tx_validation.py` `L28_EMISSION_CEILING` |
| Halving interval | `210_000` | `coin/tx_validation.py` `L28_HALVING_INTERVAL` |
| Max coinbase reward | `28` | `coin/tx_validation.py` `L28_MAX_COINBASE_REWARD` |
| Reward schedule | `(28, 14, 7, 3, 1)` | `coin/tx_validation.py` `L28_REWARD_SCHEDULE` |

Historical checkpoint constants remain reference-only and MUST NOT appear as
loaded balances, reminted supply, or genesis UTXO/state in a disposable
genesis document:

- `L28_HISTORICAL_MINED`
- `L28_HISTORICAL_LAST_ENTRY`
- `L28_NEXT_HEIGHT_AFTER_CHECKPOINT`

Evidence: `coin/tx_validation.py`; `docs/l28_identity_historical_continuity_audit.md`.

## Non-goals (M1)

Foundation 38 does not:

- implement production modules, tests, CLIs, or configuration files;
- create or write a live genesis on disk;
- start Core/P2P processes (M2+);
- define peer transport codecs beyond identity-binding requirements (M3);
- define transaction gossip or confirmation (M4);
- define fork/reorg policy (M5);
- load historical ledgers or continuity manifests into runtime state;
- reuse Leap28 or Nova identity, authority, state, or code;
- grant `execution_authorized=true` under any success path.

## Deterministic disposable network ID and chain ID

### Network ID

A conforming disposable network ID is the exact UTF-8 string:


    l28-disposable-test/v0.1

Rules:

- MUST equal that string exactly (case-sensitive).
- MUST NOT equal `MAIN`, `main`, empty string, or any historical/continuity
  profile identifier.
- MUST NOT be derived from Leap28, Nova, bridge, or EVM chain names.

### Chain ID

The disposable chain ID is lowercase hexadecimal SHA-256 over:

1. UTF-8 bytes of `l28-disposable-network-identity-genesis-binding/v0.1`;
2. one NUL byte (`0x00`);
3. UTF-8 bytes of the network ID `l28-disposable-test/v0.1`;
4. one NUL byte;
5. UTF-8 bytes of the bound protocol version `l28-protocol/1.0.0`.


    chain_id = hex(sha256(
      UTF8(profile) || 0x00 || UTF8(network_id) || 0x00 || UTF8(protocol_version)
    ))

The resulting `chain_id` is exactly 64 lowercase hexadecimal characters and is
deterministic across independent implementations that follow this formula.

## Canonical disposable genesis document

### Exact schema and field order

The genesis document is one JSON object with exactly these fields in this order:


    {
      "genesis_version": "l28-disposable-network-identity-genesis-binding/v0.1",
      "environment": "DISPOSABLE_TEST",
      "network_id": "l28-disposable-test/v0.1",
      "chain_id": "64 lowercase hexadecimal characters",
      "protocol_version": "l28-protocol/1.0.0",
      "economics": {
        "hard_cap": 28000000,
        "emission_ceiling": 11130000,
        "halving_interval": 210000,
        "max_coinbase_reward": 28,
        "reward_schedule": [28, 14, 7, 3, 1]
      },
      "historical_state_imported": false,
      "canonical_continuation": false,
      "initial_issued_supply": 0,
      "initial_height": 0,
      "execution_authorized": false,
      "acknowledgement": "disposable-test-only"
    }

Nested `economics` MUST contain exactly these fields in this order:

1. `hard_cap`
2. `emission_ceiling`
3. `halving_interval`
4. `max_coinbase_reward`
5. `reward_schedule`

Unknown, missing, reordered, duplicated, or incorrectly typed fields fail
closed. Duplicate JSON keys fail closed at every nesting depth. Non-finite JSON
numbers fail closed. Invalid UTF-8 fails closed.

### Field rules

| Field | Rule |
|---|---|
| `genesis_version` | Exact profile identifier |
| `environment` | Exact string `DISPOSABLE_TEST` |
| `network_id` | Exact disposable network ID |
| `chain_id` | Exact recomputed chain ID (never trusted as caller claim alone) |
| `protocol_version` | Exact `l28-protocol/1.0.0` |
| `economics.*` | Exact Protocol v1.0.0 integers/array above |
| `historical_state_imported` | JSON boolean `false` only |
| `canonical_continuation` | JSON boolean `false` only |
| `initial_issued_supply` | Exact integer `0` |
| `initial_height` | Exact integer `0` |
| `execution_authorized` | JSON boolean `false` only |
| `acknowledgement` | Exact string `disposable-test-only` |

Any attempt to embed historical balances, historical heights, creator allocation
tables, continuity-manifest digests as loaded state, or non-zero initial supply
fails closed.

### Genesis digest

`genesis_digest` is lowercase hexadecimal SHA-256 over:

1. UTF-8 bytes of `l28-disposable-network-identity-genesis-binding/v0.1`;
2. one NUL byte;
3. canonical JSON bytes of the complete genesis document.

Canonical JSON for digests uses:

- UTF-8;
- `ensure_ascii=false`;
- `allow_nan=false`;
- `sort_keys=true`;
- separators `(",", ":")`.

Wire/document field order for schema acceptance remains the exact order defined
above. Digest canonicalization uses sorted keys and MUST be applied only after
the document has already passed exact schema/order validation.

Semantic mutation of any accepted field MUST change `genesis_digest` or fail
schema validation.

## Binding configuration document

A separate binding-config object may accompany the genesis document for future
ephemeral data-dir contracts. When present, it is one JSON object with exactly
these fields in this order:


    {
      "binding_version": "l28-disposable-network-identity-genesis-binding/v0.1",
      "environment": "DISPOSABLE_TEST",
      "network_id": "l28-disposable-test/v0.1",
      "chain_id": "64 lowercase hexadecimal characters",
      "protocol_version": "l28-protocol/1.0.0",
      "genesis_digest": "64 lowercase hexadecimal characters",
      "data_dir_tag": "l28-disposable-test",
      "execution_authorized": false
    }

Rules:

- `chain_id` MUST equal the recomputed chain ID.
- `genesis_digest` MUST equal the recomputed genesis digest of the paired
  genesis document.
- `data_dir_tag` MUST equal `l28-disposable-test` exactly and is a logical tag
  only in M1 (no filesystem access is performed by Foundation 38).
- `execution_authorized` MUST be JSON boolean `false`.

Maximum encoded size: `8192` bytes.

## Explicit separation from historical / canonical L28 state

A conforming disposable identity MUST fail closed if any of the following are
true:

1. `environment` is not `DISPOSABLE_TEST`;
2. `network_id` equals `MAIN` or any forbidden label;
3. `canonical_continuation` is not `false`;
4. `historical_state_imported` is not `false`;
5. `initial_issued_supply` or `initial_height` is not `0`;
6. economics fields disagree with Protocol v1.0.0 constants;
7. the document references or embeds contents of
   `docs/l28_historical_continuity_manifest_v0.1.json` as runtime balances;
8. acknowledgement is missing or not exactly `disposable-test-only`.

Empty directories, zero counters, clone presence, or continuity-manifest validity
MUST NOT be treated as disposable genesis or as main-network genesis
(`PROTOCOL.md`; `coin/ledger.py` issuance gate comments;
`tests/test_protocol_conformance.py` `test_empty_directory_is_not_canonical_genesis`).

Leap28 and Nova identities, private orchestration labels, and bridge/EVM
network names are prohibited identity sources.

## Fail-closed config loading and mismatch rejection

Future implementations of this profile (not Foundation 38 itself) MUST:

1. accept only caller-supplied genesis/binding bytes or one explicit
   regular-file path;
2. reject directories, symbolic links, missing paths, and oversized inputs before
   parsing;
3. require valid UTF-8 and valid JSON;
4. reject duplicate keys at every depth and non-finite numbers;
5. recompute `chain_id` and `genesis_digest` and reject caller mismatches;
6. reject any mix of disposable identity with `MAIN` / historical / canonical
   labels;
7. return sanitized stable error codes only.

Foundation 38 specifies these rules; it does not perform filesystem I/O.

## Peer handshake identity binding (future surface)

Per `docs/l28_core_p2p_architecture_v0.1.md`, every future P2P frame MUST bind
at least protocol version and explicit network identifier.

When M3 implements transport, handshake and frames MUST additionally bind:

- `network_id` = `l28-disposable-test/v0.1`;
- `chain_id` = recomputed disposable chain ID;
- `protocol_version` = `l28-protocol/1.0.0`;
- `genesis_digest` of the local disposable genesis document.

Mismatch on any bound field MUST fail closed and MUST NOT fall back to `MAIN`
or historical identity. Foundation 38 does not define codecs, listeners, or
sockets.

## Ledger / replay identity binding (future surface)

Future disposable ledger and replay paths MUST bind persisted state to:

- `network_id`;
- `chain_id`;
- `genesis_digest`;
- `protocol_version`.

Rules for later foundations:

1. Loading state whose binding tuple mismatches the active disposable identity
   MUST fail closed.
2. `initialize_disposable_test_issuance_state` in `coin/ledger.py` remains a
   separate acknowledgement gate and MUST NOT be treated as main-network
   genesis; future wiring MAY require the Foundation 38 genesis digest to be
   presented alongside that acknowledgement.
3. Disk load alone MUST continue to leave canonical issuance unreadied
   (`coin/ledger.py` `load_from_disk`).
4. Replay MUST NOT import historical continuity quantities as balances.

Foundation 38 does not modify `coin/ledger.py` or `coin/tx_validation.py`.

## Reset, cleanup, and reproducibility

### Reset / cleanup requirements (normative for later implementation)

1. Disposable state directories MUST be tagged with `data_dir_tag`
   `l28-disposable-test`.
2. Reset/cleanup MUST wipe only that tagged disposable directory.
3. Reset MUST NOT touch historical archives, continuity manifests, or any path
   not explicitly tagged disposable.
4. After reset, re-acceptance of genesis requires full revalidation of the
   genesis document and binding config.

### Reproducibility

Given identical genesis document bytes:

- recomputed `chain_id` MUST match across runs;
- recomputed `genesis_digest` MUST match across runs;
- verification results (`ok`, `code`, checks, digests) MUST be identical for
  identical bytes.

Compact and pretty JSON that parse to the same logical object MUST produce
equal verification results after schema acceptance.

## Schema, serialization, and input limits

| Limit | Value |
|---|---:|
| Max genesis document bytes | 8192 |
| Max binding-config bytes | 8192 |
| Top-level type | object only |
| UTF-8 | required |
| Duplicate keys | rejected at every depth |
| Non-finite numbers | rejected |
| Field order | exact schema order required for acceptance |
| Digest canonicalization | sorted-keys compact JSON as defined above |

Unsupported input types, oversized inputs, invalid UTF-8, malformed JSON,
non-object top-level values, and schema/order failures fail closed.

## Required public APIs (future implementation contract)

A later implementing foundation MUST provide these offline public functions and
MUST NOT grant runtime activation from them:

1. `verify_disposable_network_genesis_json(payload) -> DisposableGenesisResult`
2. `verify_disposable_network_binding_config_json(payload, *, expected_genesis_digest: str) -> DisposableBindingResult`
3. `compute_disposable_chain_id(*, network_id: str, protocol_version: str) -> str`
4. `compute_disposable_genesis_digest(genesis_object: Mapping[str, Any]) -> str`

Optional CLI MAY accept one explicit regular-file path and MUST reject
directories and symbolic links. Core verification MUST accept JSON text or
bytes only.

`DisposableGenesisResult` / `DisposableBindingResult` success fields MUST include
at least:

- `ok: bool`
- `code: str`
- `network_id: str`
- `chain_id: str`
- `genesis_digest: str` (genesis verifier) or mirrored digest (binding verifier)
- `protocol_version: str`
- `checks: list[str]`
- `execution_authorized: bool` — MUST be `False` on every path
- `report_id: str` (deterministic over sanitized success/failure body)

## Stable error codes

Public failure codes MUST be stable and sanitized. Minimum set:

| Code | Meaning |
|---|---|
| `ok` | Verification succeeded |
| `input_type_invalid` | Unsupported payload type |
| `input_too_large` | Encoded size exceeds limit |
| `encoding_invalid` | Invalid UTF-8 |
| `json_invalid` | Malformed JSON or non-finite number |
| `duplicate_key` | Duplicate key at any depth |
| `invalid_top_level` | Top-level value is not an object |
| `schema_invalid` | Missing/unknown/reordered/wrong-type fields |
| `environment_invalid` | Environment is not `DISPOSABLE_TEST` |
| `network_id_invalid` | Network ID is not the disposable ID |
| `protocol_version_invalid` | Protocol version mismatch |
| `economics_invalid` | Economics disagree with Protocol v1.0.0 |
| `historical_import_forbidden` | Historical/canonical flags or non-zero initial state |
| `chain_id_invalid` | Declared chain ID ≠ recomputed |
| `genesis_digest_invalid` | Declared/paired genesis digest ≠ recomputed |
| `acknowledgement_invalid` | Acknowledgement missing or not exact |
| `execution_authorized_invalid` | `execution_authorized` is not JSON `false` |
| `binding_mismatch` | Binding config does not match genesis identity |
| `internal_error` | Sanitized unexpected failure |

Results MUST NOT expose raw exception text, filesystem paths, credentials, or
secrets.

## Required success checks

On success, `checks` MUST equal this exact tuple/order:

1. `schema_exact`
2. `environment_disposable`
3. `network_id_bound`
4. `protocol_version_bound`
5. `economics_v1_immutable`
6. `historical_separated`
7. `chain_id_bound`
8. `genesis_digest_bound`
9. `execution_authorized_false`

## Required test groups (future implementing suite)

A conforming implementation suite MUST provide:

1. **Deterministic identity** — chain ID and genesis digest stable across runs.
2. **Exact schema acceptance** — ordered valid genesis and binding config pass.
3. **Economics immutability** — any mutated cap/schedule/ceiling fails closed.
4. **Historical/canonical separation** — `MAIN`, historical import flags,
   non-zero initial supply/height, and continuity-as-state attempts fail.
5. **Mismatch matrix** — wrong `chain_id`, `genesis_digest`, protocol version,
   network ID, environment, and acknowledgement fail with stable codes.
6. **Malformed and size-limit matrix** — type, size, UTF-8, JSON, duplicate-key,
   non-finite, top-level, schema/order failures.
7. **Non-activation matrix** — every path keeps `execution_authorized=false`;
   no wallet/network/mining/ledger activation APIs are invoked.
8. **Static hygiene** — no Leap28/Nova imports; no socket/network listeners in
   the M1 verifier module.

## Acceptance criteria

PASS only if:

- all required test groups succeed;
- recomputed digests match for identical fixtures;
- Protocol v1.0.0 economics are enforced verbatim;
- historical/canonical mix is rejected;
- `execution_authorized` is always `false`;
- no runtime node, peer, miner, wallet, or testnet is started.

FAIL if any group fails, if economics are altered, if historical state is
imported, if Leap28/Nova identity is accepted, or if success implies activation.

## Milestone dependencies

| Milestone | Relationship to Foundation 38 |
|---|---|
| **M1 (this foundation)** | Specification of disposable identity + genesis binding |
| **M2** | Disposable Core process MUST load/verify Foundation 38 genesis/binding before any disposable issuance acknowledgement wiring |
| **M3** | P2P handshake/frames MUST bind Foundation 38 `network_id`, `chain_id`, `protocol_version`, `genesis_digest` |
| **M4** | Propagation/confirmation MUST be scoped to the Foundation 38 identity tuple |
| **M5** | Fork/reorg policy, if any, MUST remain inside the same disposable identity and MUST NOT bridge to `MAIN`/historical |

Foundation 38 implements **M1 specification only**. M2–M5 remain blocked pending
their own foundations.

## Security boundary

This specification and any future offline verifier for it MUST NOT:

- load or unlock a wallet;
- access private keys, seeds, credentials, or secrets;
- create live genesis files as part of Foundation 38;
- read or mutate ledgers;
- open network connections or listeners;
- start mining, deployment, checkpoints, or runtime nodes;
- import Leap28 or Nova authority, state, or code;
- treat continuity-manifest success as genesis or spendability.

## Non-authorization statement

A completed Foundation 38 specification, and any later successful verification
of a disposable genesis document under this profile, is offline identity
evidence only. It is not permission to spend L28, not an executable
transaction, not a ledger command, not settlement finality, not main-network
genesis, and not authorization to start a node, network, miner, wallet, or
testnet.

`execution_authorized` MUST remain the JSON boolean `false` on every conforming
document and every success or failure result path.
