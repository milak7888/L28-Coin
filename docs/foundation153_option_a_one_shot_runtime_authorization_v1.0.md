# Foundation 153 - Option A One-Shot Runtime Authorization v1.0

**Status:** `AUTHORIZATION_GRANTED=true` /
`AUTHORIZATION_CONSUMED=false` / `CONSUMED_FOR_REUSE=false` /
`VALID_FOR_ACTIVE_EXECUTION=false` / `EXPERIMENT_EXECUTED=false`

## 1. Operator decision and authority

The L28 repository operator explicitly selects
`AUTHORIZE_ONE_BOUNDED_ISOLATED_RUNTIME_EXPERIMENT` from the Foundation152
decision package. Authorization ID `L28-F153-OPTION-A-ONE-SHOT-001` grants only
the exact future experiment defined below.

This record is explicit, one-shot, experiment-specific, non-transferable, and
non-reusable. It creates no persistent networking authority. It neither
implements nor executes the experiment, and it does not claim a human signature
or identity beyond the accountable repository-operator role evidenced by the
operator instruction.

The canonical authorization state is
`docs/l28_foundation153_option_a_one_shot_runtime_authorization_v1.0.json`.
That artifact binds the exact updated Foundation152 document and status JSON by
SHA-256 digest and binds parent commit
`84f7b05ecf10f91dbfcdd5d8909b0df4a673f1f2`.

## 2. Exact authorized future experiment

The authorization permits exactly one future experiment with all of these
bounds:

- exactly two disposable agents in exactly two isolated local processes;
- Agent A at `127.0.0.1:28428`, designated local Core writer;
- Agent B at `127.0.0.1:28429`, peer evidence only;
- IPv4 loopback on one local machine, with no external interface, route,
  discovery, bind, or connection;
- exactly two sessions and exactly one reconnect;
- no more than 32 messages per session, 4,096 bytes per frame, and 2,048 bytes
  per payload;
- only `HELLO`, `TIP_EVIDENCE`, and `CANDIDATE_EVIDENCE` messages;
- replay message IDs and peer nonce state preserved across the reconnect and
  isolated to this authorization ID and peer;
- a maximum execution window of 60 seconds after atomic consumption;
- mandatory conflict and peer-equivocation assessment through the reviewed
  Option A boundary;
- required `SYNCING -> HALTED_CONFLICT`, retained local canonical state, sticky
  halt, and no resume during the experiment; and
- disposable public identities and evidence only, with no production identity,
  secret, historical, canonical, or real-value state.

No scope expansion is permitted.

## 3. Current execution-gate state

The authorization is granted but has not been consumed. The experiment has not
been executed. The execution gate remains closed in this task because no
executor is implemented or invoked and the deterministic prerequisites have
not been evaluated for an execution attempt.

Opening the future execution gate requires an explicit execution invocation,
exact source-binding verification, passing Foundation152 and Foundation153
tests, a separately reviewed test-only executor, two fresh isolated data
directories, exact loopback endpoint enforcement, Option A and replay-state
preflight, a complete evidence sink, and a verified cleanup plan. Missing or
false prerequisites fail closed before any process or socket start.

An execution invocation is not a new scope or policy decision. It may only
consume the authorization already recorded here under these exact bounds.

## 4. Consumption, expiration, and lifecycle

When the authorized execution successfully starts, one atomic transition must
set `AUTHORIZATION_CONSUMED=true`, `CONSUMED_FOR_REUSE=true`, and
`VALID_FOR_ACTIVE_EXECUTION=true`. That transition occurs exactly once.
Consumption immediately prevents a second start or reuse; it does not
invalidate the execution that successfully consumed the authorization.

The same active execution remains valid only until the earliest of normal
completion, abort, or the 60-second maximum deadline. Termination sets
`VALID_FOR_ACTIVE_EXECUTION=false`, while `AUTHORIZATION_CONSUMED=true` and
`CONSUMED_FOR_REUSE=true` remain permanent. Restart after completion, abort,
deadline, stop, or cleanup is forbidden.

Current state remains:

- `AUTHORIZATION_GRANTED=true`;
- `AUTHORIZATION_CONSUMED=false`;
- `CONSUMED_FOR_REUSE=false`;
- `VALID_FOR_ACTIVE_EXECUTION=false`;
- `EXPERIMENT_EXECUTED=false`; and
- execution count `0`.

## 5. Abort criteria

Before start, the attempt must fail closed if the gate is not open, any
prerequisite is absent, the authorization is invalid or changed, a source
binding mismatches, or the authorization is already consumed.

During a future run, immediate abort and cleanup are required for any undeclared
agent, process, address, port, or message type; any non-loopback interface,
route, bind, or connection; production identity or secret material; historical
or real-value state; resource or duration breach; binding mismatch; replay;
conflict or equivocation; Option A halt, retention, or stickiness failure; any
canonical-state, ledger, or authority claim; unexpected process exit, partial
failure, or second start; or incomplete evidence or cleanup.

Abort cannot select a fork winner, apply a candidate, automatically reorganize,
resume synchronization, or mutate canonical state.

## 6. Evidence and cleanup prerequisites

A future result must capture the authorization ID, exact scope digest, and
atomic-consumption transition; process, agent, endpoint, start, and stop
observations; ordered public frame IDs and SHA-256 digests; both sessions and
the reconnect; replay rejection; Option A assessment and sticky halt; local
canonical state before and after; and completion, abort, timeout, and cleanup
results. Missing evidence prevents `PASS`. Secrets and private evidence are
forbidden.

Cleanup must stop message admission, close both loopback endpoints, stop both
processes, finalize evidence, remove both disposable data directories and
replay state, and retain the consumed authorization marker. Cleanup failure is
experiment failure and cannot authorize restart or persistent operation.

## 7. Persistent and protocol authority remain false

The one-shot grant permits bounded network, socket, disposable filesystem, and
process lifecycle capability only during its single consumed execution window.
Consumption for reuse does not invalidate that already-started execution; the
separate `VALID_FOR_ACTIVE_EXECUTION` state controls its bounded lifetime.
Persistent P2P, network, socket, process, filesystem, listener, session, or
service authority remains false.

RPC, wallet or key creation, signing, mining, broadcast, settlement, public
testnet, deployment, ledger mutation, canonical-height override, issuance,
supply, validation, consensus, history, settlement authority, confirmation
claims, automatic reorganization, and fork-winner selection remain false.

Protocol v1.0.0, coinbase-only issuance, consensus-derived canonical height,
immutable historical evidence, and `coin.tx_validation.validate_transaction`
remain unchanged and authoritative. Protected economics remain exactly: hard
cap `28000000`, emission ceiling `11130000`, historically mined `2824584`,
treasury locked `500000`, circulating snapshot `2324584`, halving interval
`210000`, reward schedule `[28,14,7,3,1,0]`, historical mined-through entry
`100877`, and next canonical height `100878`.

Bitcoin remains external evidence only with zero L28 authority. Signer runtime
remains blocked. Option A remains reviewed, non-normative, and limited to
fail-closed safety. Foundation153 grants no production or public-testnet
authority and performs no experiment.
