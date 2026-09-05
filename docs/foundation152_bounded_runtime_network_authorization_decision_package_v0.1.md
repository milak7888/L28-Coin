# Foundation 152 - Bounded Runtime/Network Authorization Decision Package v0.1

**Status:** option A selected / one-shot authorization granted but not consumed /
`EXPERIMENT_EXECUTED=false`

## 1. Purpose and evidence boundary

Foundation152 prepared the explicit operator decision gate. Foundation153 now
records the operator's selection of exactly one bounded future experiment. No
experiment is executed or implemented by these records. The updated canonical
machine-readable gate is
`docs/l28_foundation152_runtime_network_decision_gate_v0.1.json`.

The proposal is bounded by current repository evidence:

- F37-07 is `PARTIAL_ISOLATED_LOOPBACK_TRANSPORT_EVIDENCE`, established by the
  completed, non-persistent Foundation143 experiment.
- F37-10 is `PARTIAL_ISOLATED_LOOPBACK_PROPAGATION_EVIDENCE`, limited to the
  prior isolated transport of `HELLO`, `TIP_EVIDENCE`, and
  `CANDIDATE_EVIDENCE`.
- F37-11 is `OFFLINE_OPTION_A_REVIEWED_NON_NORMATIVE`. The reviewed boundary
  halts on conflict and retains the current local canonical state; it is not a
  Protocol v1.0.0 rule and has not been exercised in a runtime process.

Foundation143's authorization expired when that one-shot experiment ended.
Foundation151 made only the next decision gate ready. The new Foundation153
authorization is separate, experiment-specific, non-transferable, and not yet
consumed.

## 2. Smallest proposed future experiment

The operator selected
`AUTHORIZE_ONE_BOUNDED_ISOLATED_RUNTIME_EXPERIMENT`. The authorized future
experiment consists of:

- exactly two disposable logical agents in exactly two isolated local
  processes on one machine;
- Agent A, the designated local Core writer, at `127.0.0.1:28428` in
  `process-a`;
- Agent B, peer-evidence-only, at `127.0.0.1:28429` in `process-b`;
- IPv4 loopback only, with no external bind, route, discovery, or connection;
- only `HELLO`, `TIP_EVIDENCE`, and `CANDIDATE_EVIDENCE` frames;
- at most 4,096 bytes per frame, 2,048 bytes per payload, 32 messages per
  session, two sessions, one reconnect, and 60 seconds wall duration; and
- three required scenarios: a bound evidence exchange, replay rejection across
  the allowed reconnect, and peer equivocation causing
  `SYNCING -> HALTED_CONFLICT` while the local canonical state is retained.

This is the smallest incremental experiment because it reuses the proven
Foundation142/143 topology and bounds while adding only the missing process
isolation and runtime integration evidence for reviewed Option A. It does not
propose persistent P2P, public connectivity, RPC, transactions, confirmation,
reorganization, testnet, or production behavior.

## 3. Lifecycle and isolation

Before any future start, an exact-scope authorization must be valid and
unconsumed. Two new disposable data directories may then be prepared beneath
`SYSTEM_TEMPORARY_DIRECTORY/foundation152/<authorization_id>/`, one for each
agent. Pre-existing, shared, historical, real-value, wallet, key, or production
state is forbidden.

After all prerequisites pass, the successful execution-start transition
atomically consumes the authorization for reuse and activates only that
execution. The proposed order then starts process A, starts process B, and opens
only the declared loopback endpoints. Stop order is message-admission stop,
endpoint closure, process B stop, process A stop, evidence finalization, then
removal of the current authorization's disposable state.

Message IDs and peer nonce keys would be scoped to the authorization ID and
peer ID. They must persist across the single allowed reconnect, must not be
reused across authorizations, and must cause fail-closed abort on duplication.
Reset would apply only to the current disposable authorization state and could
not permit restart.

## 4. Option A integration and abort boundary

Peer equivocation or an unresolved conflict must produce the reviewed
fail-closed Option A assessment and transition synchronization from `SYNCING`
to `HALTED_CONFLICT`. The current local canonical state must remain unchanged,
the halt must be sticky, and resume is forbidden within the experiment. Any
future resume still requires a separately governed deterministic resolution.

The experiment must abort before a new start on missing, invalid, or previously
consumed authorization; and during execution on non-loopback or undeclared
transport; resource-bound breach;
identity mismatch; replay; conflict; failed Option A halt/retention invariant;
any mutation or authority claim; unexpected process or partial failure;
incomplete evidence; or cleanup-boundary violation. Abort cannot select a
winner, apply a candidate, reorganize, or resume synchronization.

## 5. Required evidence and cleanup

A future evidence report would have to record the authorization scope digest
and consumption result; exact process identities and lifecycle outcomes;
actual endpoints; ordered public frame IDs and SHA-256 digests; replay-state
scope and rejection code; Option A assessment and state transition; local
canonical state before and after; abort reason; and cleanup result. Missing
evidence fails the experiment. Secrets and private material are forbidden.

Both endpoints must close, both processes must stop, both disposable data
directories must be removed, and the authorization must remain irreversibly
consumed. A cleanup failure makes the experiment fail and grants no recovery,
restart, or persistent-service authority.

## 6. One-shot authorization state and requirements

Foundation153 supplies the separate authorization artifact. It binds the
Foundation152 profile, baseline commit, exact experiment scope, operator
decision, and record. `AUTHORIZATION_GRANTED=true`,
`AUTHORIZATION_CONSUMED=false`, `CONSUMED_FOR_REUSE=false`,
`VALID_FOR_ACTIVE_EXECUTION=false`, and `EXPERIMENT_EXECUTED=false`.

The authorization has a maximum execution window of 60 seconds and a maximum
execution count of one. A successful execution-start transition must atomically
set `AUTHORIZATION_CONSUMED=true`, `CONSUMED_FOR_REUSE=true`, and
`VALID_FOR_ACTIVE_EXECUTION=true`. Consumption immediately and permanently
forbids a second start, but it does not invalidate the execution that consumed
the authorization.

That one active execution remains valid only until the earliest of normal
completion, abort, or the 60-second maximum deadline. Termination sets
`VALID_FOR_ACTIVE_EXECUTION=false` while both consumed fields remain true and
restart remains permanently denied. Missing, malformed, mismatched, invalid,
or previously consumed authorization must fail closed before a new start.

## 7. Operator decision options

The operator selected option A. Options B and C remain unselected:

| Option | Decision value | Effect |
|---|---|---|
| A | `AUTHORIZE_ONE_BOUNDED_ISOLATED_RUNTIME_EXPERIMENT` | **Selected.** Grants only the exact future one-shot experiment and does not execute it in Foundation153. |
| B | `DEFER` | Leaves all execution authority false. |
| C | `REJECT_AND_REVISE` | Rejects this proposal; any revision requires a new reviewed decision package. |

The prior `DECISION_READY` state was not authorization. The operator decision
now grants `AUTHORIZED_TO_EXECUTE=true` only for the exact one-shot scope after
all execution prerequisites pass. Current task state remains
`AUTHORIZATION_CONSUMED=false`, `CONSUMED_FOR_REUSE=false`,
`VALID_FOR_ACTIVE_EXECUTION=false`, and `EXPERIMENT_EXECUTED=false`.

## 8. Authority firewall and non-activation

Foundation153 grants bounded network, socket, filesystem-runtime, and
process-runtime capability only for the exact future one-shot experiment. No
such capability is exercised in this task. Persistent or general P2P, network,
socket, filesystem-runtime, and process-runtime authority remains false.

RPC, wallet or key creation, signing, mining, broadcast, settlement,
deployment, public testnet, ledger mutation, canonical-height override,
issuance, supply, validation, consensus, history, automatic reorganization,
confirmation claims, and fork-winner selection remain false without exception.

Protocol v1.0.0 remains frozen. Coinbase-only issuance,
consensus-derived canonical height, immutable historical evidence, and
`coin.tx_validation.validate_transaction` remain authoritative. Protected
facts remain exactly: hard cap `28000000`, emission ceiling `11130000`,
historically mined `2824584`, treasury locked `500000`, circulating snapshot
`2324584`, halving interval `210000`, reward schedule `[28,14,7,3,1,0]`,
historical mined-through entry `100877`, and next canonical height `100878`.

Bitcoin remains external evidence only and has zero authority over L28
issuance, supply, height, validation, consensus, history, or settlement. Signer
runtime remains blocked. Option A remains a non-normative reviewed safety
boundary. Foundation153 grants no implementation, persistent activation,
deployment, public testnet, or authority outside the exact one-shot experiment.
The experiment has not started and this authorization has not been consumed.
