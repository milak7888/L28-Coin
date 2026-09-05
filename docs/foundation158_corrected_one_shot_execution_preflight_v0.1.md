# Foundation158 Corrected One-Shot Execution Preflight v0.1

Status: `READY_FOR_EXPLICIT_EXECUTION_INVOCATION_GATE_CLOSED`

## 1. Purpose and non-execution boundary

Foundation158 prepares the exact Foundation157 corrected reconnect experiment for a future explicit execution invocation. This package is preflight only. It does not open a socket, start an experiment process, send network traffic, consume authorization, or execute the experiment.

Current state remains exactly:

- `READY_FOR_EXPLICIT_EXECUTION_INVOCATION=true`;
- `AUTHORIZATION_GRANTED=true`;
- `AUTHORIZATION_CONSUMED=false`;
- `CONSUMED_FOR_REUSE=false`;
- `VALID_FOR_ACTIVE_EXECUTION=false`;
- `EXECUTION_GATE_OPEN=false`; and
- `EXPERIMENT_EXECUTED=false`.

A separate explicit execution invocation remains mandatory. Preflight readiness is not active execution authority.

## 2. Authoritative history and bindings

The repository and executor baseline is `25d3bdc8ec77b96c0af717b1864650388559da5e`. Foundation153 authorization `L28-F153-OPTION-A-ONE-SHOT-001` remains permanently consumed. Foundation154 remains `ABORT`. Foundation155's corrected reconnect design has a later independent-review result of `PASS 15 / GAP 0 / BLOCKED 0`. Foundation157 authorization `L28-F157-CORRECTED-RECONNECT-ONE-SHOT-001` remains granted and unconsumed.

The machine-readable preflight gate binds the committed Foundation157 package, authorization gate, and tests, plus the Foundation158 helper, by exact SHA-256. No F153-F157 historical artifact is modified.

## 3. Exact future execution scope

The future invocation is limited to:

- exactly two deterministic public-fixture agents in exactly two isolated processes;
- IPv4 loopback on one local machine only;
- Agent A as the designated local Core writer and sole fixed listener at `127.0.0.1:28428`;
- Agent B as peer-evidence-only, binding exactly `127.0.0.1:0` for an OS-assigned fresh ephemeral source port in each session;
- no fixed Agent B source-port bind to `28429`;
- exactly two sessions and exactly one reconnect;
- two distinct observed Agent B source ports;
- at most 60 seconds of active execution;
- application identity bound independently of transport source port;
- replay state retained across the reconnect and replayed evidence rejected;
- mandatory Option A conflict/equivocation transition from `SYNCING` to `HALTED_CONFLICT`, with local canonical state retained and no candidate selected or applied; and
- disposable public identities and evidence only, with no secrets, historical canonical state, or real-value state.

## 4. Zero-I/O dry-run preflight

`dry_run_preflight()` validates the exact authorization, baseline, artifact digests, scope, lifecycle, readiness, and authority firewall. It constructs deterministic frames and exercises admission, application identity, replay rejection, and Option A behavior entirely in memory. It opens zero sockets, starts zero processes, and sends zero network traffic. It never creates the execution-state marker.

## 5. Future explicit invocation and lifecycle

The future `--execute-once` path requires the exact authorization ID, baseline commit, and current preflight-gate SHA-256. Missing or mismatched invocation bindings fail closed before consumption.

Immediately before any experiment setup, process, or socket start, the executor atomically creates the Foundation158 execution-state marker with exclusive creation and establishes the single 60-second deadline. Existing or ambiguous state permanently rejects another start. Successful creation sets authorization consumed, consumed-for-reuse, active, gate-open, and executed. Each potentially blocking process start is supervised through a bounded daemon start controller; deadline expiry cancels startup, initiates forced cleanup, and cannot permit retry. This is the one-way successful-start transition; it cannot be reused.

Normal completion or any abort terminates active validity, closes the gate, and retains consumed-for-reuse and permanent restart denial. Terminal-state persistence is attempted in an outer fail-safe path regardless of cleanup errors. A terminalization write failure is raised explicitly. Abort never restores or retries the authorization.

## 6. Fail-closed prerequisites and aborts

Before future start, the executor must validate the exact authorization ID, baseline and artifact bindings, granted/unconsumed state, two-agent/two-process topology, fixed Agent A listener, port-zero Agent B bind policy, no external-network path, initialized replay state, Option A availability, installed cleanup control, and 60-second guard.

Abort is mandatory for a non-loopback address, fixed client-port bind, unexpected agent/process/session/reconnect, reused source port, replay-state loss, unavailable Option A boundary, canonical-state mutation, any ledger/height/economic/protocol authority, any wallet/signing/mining/broadcast/settlement path, external-network attempt, deadline violation, incomplete evidence, or cleanup failure.

## 7. Mandatory cleanup

Every termination uses bounded escalation: terminate, bounded join, strong kill where supported if still alive, bounded final join, then explicit zero-child verification. It must close all experiment sockets, terminate both processes, leave `127.0.0.1:28428` free, leave zero experiment child processes, remove disposable state, retain the consumed marker, and leave no persistent runtime or service. Cleanup errors are retained separately; any surviving child or cleanup error is `TERMINAL_CLEANUP_FAILURE` and can never be reported as clean termination.

## 8. Authority firewall and protected invariants

Persistent P2P runtime, RPC, wallet/key creation, signing, mining, broadcast, settlement, public testnet, deployment, ledger mutation, canonical-height override, issuance, supply, validation, history, protocol authority, automatic reorganization, and fork-winner selection remain false.

Protocol v1.0.0, coinbase-only issuance, consensus-derived canonical height, protected economics and immutable historical evidence remain unchanged. `coin.tx_validation.validate_transaction` remains canonical. Bitcoin remains external evidence with zero L28 authority. Signer runtime remains blocked. Option A remains a reviewed non-normative safety boundary only.

Protected facts remain exact: hard cap `28000000`, emission ceiling `11130000`, historically mined `2824584`, treasury locked `500000`, circulating snapshot `2324584`, halving interval `210000`, reward schedule `[28,14,7,3,1,0]`, mined-through entry `100877`, and next canonical height `100878`.

Foundation158 changes no F37 status and grants no persistent authority.
