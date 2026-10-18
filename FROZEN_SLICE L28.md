# L28 — FROZEN_SLICE.md

Date: 2026-10-18
PROJECT_STATE: ACTIVE
Slice: Persistent Disposable Two-Node Ledger Core v0.1

## OBJECTIVE

Implement the first executable, persistent two-node L28 ledger foundation as
a disposable non-production network.

This slice proves loopback event replication, independent validation, durable
restart recovery, deterministic agreement, and fail-closed divergence handling.
It does not define consensus, confirmations, finality, canonical continuation,
or production authority.

## BASELINE

`1ed38b5ac44015e87517d321cc2d56ca9021a384`

Branch: `codex/persistent-disposable-two-node-core-v0-1`

## DELIVERABLE

- two independent local node processes communicating over IPv4 loopback;
- one disposable test-only writer and one independently validating follower;
- one validator-authorized disposable 28 L28 coinbase and one signed 28 L28
  disposable transfer;
- propagation and independent validation of both events;
- durable event storage using the existing ledger rather than a second ledger
  engine;
- restart reconstruction and comparison of transaction IDs, balances, supply,
  and deterministic state commitments;
- rejection of replay, corruption, malformed input, cross-network input, and
  conflicting state;
- Option A halt on divergence without selecting or rewriting canonical history;
- one real two-process CLI workflow with observable evidence.

Authorized paths:

- `FROZEN_SLICE L28.md`
- `SYSTEM_STATE L28.md`
- `DEFER L28.md`
- `README.md`
- `coin/ledger.py`
- `coin/persistent_disposable_testnet_node.py`
- `tests/test_persistent_disposable_testnet_node.py`

## ACCEPTANCE CRITERIA

1. Two separate node processes communicate over IPv4 loopback.
2. Both independently run the existing canonical transaction validator for the
   same two disposable events.
3. Durable restart reproduces identical transaction IDs, balances, supply, and
   state commitments.
4. Replay is rejected after restart.
5. Corrupt, malformed, cross-network, and divergent input fails closed.
6. Divergence invokes Option A halt and never selects or rewrites history.
7. Focused tests and directly affected regressions pass once.
8. The actual two-process CLI workflow passes within 120 seconds.
9. One consolidated security review finds no unresolved Critical/High
   implementation issue.
10. Protocol v1.0.0, protected economics, canonical history, custody, F171, and
    all production gates remain unchanged and blocked.

## SAFETY BOUNDARY

Loopback only, with at most two node processes and a 120-second execution
bound. Disposable test material only. An ephemeral disposable Ed25519 identity
may be generated for the test transfer, but no private test material may be
persisted, printed, logged, committed, or returned as evidence.

No historical import, production keys, real mining, public networking,
settlement, canonical broadcast, deployment, EVD-001 integration, DigitalOcean
spending, Protocol/economic/history change, custody change, F171 change, merge,
or push.

The disposable coinbase starts a new test-only network at height zero and may
not be treated as canonical issuance or historical continuation.

## ROLLBACK

Stop both local processes, close their loopback sockets, and remove only the
explicitly tagged temporary slice directories. On failure, preserve the base
commit and do not commit.

## STOP

After implementation, focused and directly affected tests, actual-product CLI
verification, observable evidence, consolidated security review, system-state
update, exact-path staging, and one local commit, stop. Do not merge, push,
deploy, expose networking, or begin another milestone.
