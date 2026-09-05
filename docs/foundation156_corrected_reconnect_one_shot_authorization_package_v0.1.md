# Foundation156 Corrected Reconnect One-Shot Authorization Package v0.1

Status: `AUTHORIZATION_GRANTED_EXECUTION_GATE_CLOSED_NOT_CONSUMED`

## 1. Purpose and non-activation boundary

Foundation156 prepared a new decision package for the corrected reconnect design independently reviewed in Foundation155. Foundation157 records the operator's explicit selection of `AUTHORIZE_ONE_CORRECTED_BOUNDED_ISOLATED_RUNTIME_EXPERIMENT`. This grants one new bounded authorization but does not open an execution gate, implement a runtime, or execute any socket, process, or network behavior.

Current state is exactly:

- `AUTHORIZATION_GRANTED=true`;
- `AUTHORIZATION_CONSUMED=false`;
- `CONSUMED_FOR_REUSE=false`;
- `VALID_FOR_ACTIVE_EXECUTION=false`;
- `EXPERIMENT_EXECUTED=false`; and
- `EXECUTION_GATE_OPEN=false`.

Authorization recording and experiment execution remain separate actions. This recorded authorization does not execute the experiment; a later explicit execution invocation and all fail-closed prerequisites are still required.

## 2. Authoritative history and bindings

Foundation153 authorization `L28-F153-OPTION-A-ONE-SHOT-001` was consumed by Foundation154 and is permanently non-restartable. Its committed authorization JSON remains an immutable pre-execution snapshot. The current terminal lifecycle evidence is Foundation154's execution-state artifact: `AUTHORIZATION_CONSUMED=true`, `CONSUMED_FOR_REUSE=true`, `VALID_FOR_ACTIVE_EXECUTION=false`, `EXPERIMENT_EXECUTED=true`, and `RESTART_ALLOWED=false`.

Foundation154 remains `ABORT`. The committed Foundation155 record disposition is `PASS 2 / GAP 1 / BLOCKED 1`. A later independent review of Foundation155 separately concluded `PASS 15 / GAP 0 / BLOCKED 0` for its requested review points. Foundation156 binds the committed Foundation155 review and machine-readable decision by exact SHA-256 at baseline `2d5b6c65255cc21b50ea6632231c6c18f02dfd1b`. None of F153-F155 is rewritten or reused as authorization.

## 3. Exact corrected proposed experiment

Any future authorization may cover only this exact proposed experiment:

- exactly two deterministic public-fixture agents in exactly two isolated processes;
- IPv4 loopback on one local machine only;
- Agent A is the designated local Core writer and sole fixed listener at `127.0.0.1:28428`;
- Agent B remains peer-evidence-only and binds `127.0.0.1:0` for an OS-assigned fresh ephemeral source port for each session;
- Agent B must never bind fixed source port `28429`;
- each observed Agent B source address must equal `127.0.0.1`, each assigned source port must be an integer in `1..65535`, must differ from `28428`, and the two sessions must use distinct client source ports;
- exactly two sessions and exactly one reconnect;
- at most 60 seconds of active execution after atomic consumption;
- replay state persists across reconnect independently of the transport source port;
- application continuity is bound to authorization ID, peer ID, protocol version, network ID, genesis hash, config hash, message ID, and nonce replay key;
- only deterministic public fixture identities and evidence; and
- no external interface, route, discovery, production identity, secret, historical canonical state, or real-value state.

Agent A must use the reviewed Option A boundary for conflict and peer-equivocation assessment. Conflict or equivocation must transition `SYNCING -> HALTED_CONFLICT`, retain current local canonical state, remain sticky, and never select or apply a candidate.

This corrected endpoint contract differs from Foundation153's fixed Agent B port. It requires a new authorization and cannot reuse Foundation153.

## 4. Operator decision options

The accountable L28 repository operator explicitly selected exactly one:

- `A — AUTHORIZE_ONE_CORRECTED_BOUNDED_ISOLATED_RUNTIME_EXPERIMENT`
- `B — DEFER`
- `C — REJECT_AND_REVISE`

`SELECTED_DECISION=AUTHORIZE_ONE_CORRECTED_BOUNDED_ISOLATED_RUNTIME_EXPERIMENT`.

Options B and C remain unselected. The decision source is the explicit Foundation157 operator instruction. The new authorization identifier is `L28-F157-CORRECTED-RECONNECT-ONE-SHOT-001`.

## 5. Lifecycle contract

### Initial decision-ready state (historical)

Before the Foundation157 selection, authorization was not granted, not consumed, inactive, unexecuted, and closed.

### Authorized pre-start state (current)

The explicit operator selection of option A sets `AUTHORIZATION_GRANTED=true`. Consumption, active validity, execution, and gate opening remain false until a separate valid execution invocation satisfies every prerequisite. Options B and C grant nothing.

### Successful start

The first successful start must atomically set `AUTHORIZATION_CONSUMED=true`, `CONSUMED_FOR_REUSE=true`, `VALID_FOR_ACTIVE_EXECUTION=true`, and `EXPERIMENT_EXECUTED=true`. That transition permanently rejects every second or repeated start while leaving only the already-started execution valid.

### Termination

Normal completion, abort, or the 60-second deadline—whichever occurs first—sets `VALID_FOR_ACTIVE_EXECUTION=false`. Consumption and reuse denial remain true forever. Restart is forbidden regardless of result.

## 6. Fail-closed prerequisites

Before any future process or socket start, a separately reviewed executor must prove:

1. exact repository, baseline, authorization ID, artifact digest, and scope bindings;
2. a new explicit authorization is granted, unconsumed, unexpired, and not previously invoked;
3. exactly two agents and exactly two isolated processes;
4. fixed listener `127.0.0.1:28428` is free and no other listener is permitted;
5. Agent B's client bind policy is exactly `127.0.0.1:0`, with fixed source port `28429` forbidden;
6. DNS, hostnames, non-loopback binds/routes/connections, `SO_REUSEPORT`, abortive close, and timing-delay reuse workarounds are absent;
7. application identity and replay state persist independently of client transport source ports;
8. the reviewed Option A halt/retention/stickiness boundary is available;
9. deterministic public-only evidence and two fresh isolated data directories are available;
10. duration, session, reconnect, message, and resource limits are enforced; and
11. evidence capture and complete cleanup plans are ready.

Missing, malformed, conflicting, stale, changed, or unverifiable evidence fails closed before start. No automatic execution is allowed.

## 7. Evidence, abort, and cleanup requirements

A future execution report must record the new authorization ID and digests, atomic lifecycle transitions, exact processes and agents, fixed listener, both assigned client source ports, both sessions, one reconnect, ordered public message identifiers/digests, application identity continuity, replay rejection, Option A assessment/halt/stickiness, unchanged local canonical state, duration, termination result, and cleanup.

Abort is mandatory for any fixed Agent B source port, reused client source port, non-loopback endpoint, excess process/agent/session/reconnect, missing replay state, identity mismatch, Option A failure, duration/resource breach, authority claim, state mutation, unexpected exit, or incomplete evidence/cleanup. Abort consumes a successfully started authorization and never permits retry.

Cleanup must stop admission, close all experiment sockets, stop both processes, remove both isolated data directories and replay state after evidence finalization, verify the fixed listener is free, leave zero child processes, and retain the consumed marker. No persistent runtime or service may remain.

## 8. Authority firewall and protected invariants

Persistent P2P/runtime, RPC, wallet/key creation, signing, mining, broadcast, settlement, public testnet, deployment, ledger mutation, canonical-height override, issuance, supply, validation, consensus, history, protocol authority, automatic reorganization, and fork-winner selection remain false.

Protocol v1.0.0, coinbase-only issuance, consensus-derived canonical height, immutable historical evidence, and `coin.tx_validation.validate_transaction` remain authoritative and unchanged. Bitcoin remains external evidence with zero L28 authority. Signer runtime remains blocked. Option A remains a reviewed non-normative safety boundary only.

Protected facts remain exact: hard cap `28000000`, emission ceiling `11130000`, historically mined `2824584`, treasury locked `500000`, circulating snapshot `2324584`, halving interval `210000`, reward schedule `[28,14,7,3,1,0]`, mined-through entry `100877`, and next canonical height `100878`.

Foundation156/Foundation157 changes no F37 status. The new authorization is one-shot, experiment-specific, non-transferable, non-persistent, and unusable for any second start after successful consumption. It grants no present execution authority because the separate execution invocation has not occurred and `EXECUTION_GATE_OPEN=false`.
