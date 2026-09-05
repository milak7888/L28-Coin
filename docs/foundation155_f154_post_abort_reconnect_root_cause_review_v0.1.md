# Foundation155 F154 Post-Abort Reconnect Root-Cause Review v0.1

Status: `ROOT_CAUSE_REVIEW_COMPLETE_NO_EXECUTION_AUTHORIZED`

## 1. Scope and preserved evidence

This is a deterministic offline review of the Foundation154 `ABORT`. It creates no socket, starts no process, sends no traffic, and does not retry the consumed Foundation153 authorization. The five Foundation154 artifacts remain unchanged and retain their recorded hashes.

Foundation153 remains permanently consumed: `AUTHORIZATION_CONSUMED=true`, `CONSUMED_FOR_REUSE=true`, `VALID_FOR_ACTIVE_EXECUTION=false`, `EXPERIMENT_EXECUTED=true`, and `RESTART_ALLOWED=false`. Foundation154 remains valid as an `ABORT`; its missing replay, equivocation, and active Option A evidence remains missing rather than inferred.

## 2. Evidence reviewed

The Foundation154 helper creates Agent A's listener at `127.0.0.1:28428`. Agent B's `_connect_client()` creates an IPv4 TCP socket, sets `SO_REUSEADDR`, binds the client source endpoint to `127.0.0.1:28429`, and connects to Agent A. Agent B completes session 1 inside a context manager, closes that socket on context exit, and immediately calls `_connect_client()` again for the only reconnect.

The observed second call failed at the client-side fixed-source `bind()` with `OSError: [Errno 48] Address already in use`; it failed before the second `connect()`. Agent A then timed out waiting in its second `accept()`. This matches the F154 evidence and execution-state artifacts.

F143 used the same fixed client source-port technique and recorded a successful reconnect, but a prior success does not make immediate reuse of an identical TCP endpoint a portable contract. F142 defines two agent endpoints and offline session/reconnect bounds; it does not define a portable TCP close/rebind protocol. F152/F153 then fixed both addresses and ports without explicitly distinguishing listener ports from client source ports.

## 3. Root cause and confidence

### Confirmed proximate cause

The reconnect design required immediate reuse of Agent B's exact local TCP endpoint, `127.0.0.1:28429`, after session 1. The second client `bind()` found that endpoint unavailable and raised errno 48. Because the failure preceded `connect()`, it was not caused by DNS, an external route, peer admission, replay evaluation, or Option A.

### TCP lifecycle mechanism

A TCP close does not imply immediate release of every local endpoint/connection tuple. Depending on FIN ordering and kernel state transitions, the prior connection can remain represented during teardown, including `TIME_WAIT`. Foundation154 did not capture kernel TCP state, so this review does not claim that a specific state was directly observed. The evidence supports the narrower conclusion that the prior fixed local endpoint was not reusable at the immediate second bind; TCP teardown/TIME_WAIT behavior is the applicable mechanism.

The helper's close ordering is cooperative but not synchronized: Agent A sends its reply and leaves its accepted-socket context, while Agent B receives the reply and independently leaves its client context. There is no protocol acknowledgement proving that the kernel has completed endpoint release before the next bind.

## 4. Socket-option assessment

- `SO_REUSEADDR` was already applied to both Agent B client sockets. The failure proves it did not provide the required immediate-rebind guarantee in this run. It must not be treated as a portable same-endpoint reconnect contract.
- `SO_REUSEPORT` is not a justified correction. It may alter local bind-sharing and distribution semantics, does not itself prove safe reuse of an identical established connection tuple, and could introduce competing-binder ambiguity.
- Abortive close or zero-time `SO_LINGER` is not proposed. Reset-oriented teardown changes delivery/close semantics and could destroy evidence or mask lifecycle defects.
- Waiting for an assumed `TIME_WAIT` interval is not deterministic or portable and may conflict with the 60-second experiment limit.

## 5. Smallest proposed correction

Keep roles unchanged: Agent A remains the fixed loopback listener and designated local Core writer; Agent B remains peer-evidence-only and initiates both sessions. Change only the client source-port model:

1. Agent A listens only on fixed `127.0.0.1:28428`.
2. Agent B binds only to `127.0.0.1` with source port `0`, allowing the operating system to assign a fresh ephemeral loopback source port for each session.
3. Each assigned source address must be exactly `127.0.0.1`; each assigned source port must be an integer in `1..65535`, must differ from `28428`, and session 2 must use a different source port from session 1.
4. Agent B's authority and continuity are bound to deterministic application evidence—authorization ID, peer ID, protocol/network/genesis/config bindings, message IDs, nonces, and replay state—not to equality with a reusable TCP source port.
5. Agent A rejects non-loopback peers, excess sessions/reconnects, missing replay state, identity/binding mismatch, and every existing authority violation.

This avoids dependence on immediate reuse of a prior TCP endpoint. It neither requires nor permits DNS, `SO_REUSEPORT`, abortive close, external interfaces, additional processes, additional sessions, or longer duration.

## 6. Security-scope assessment

The correction preserves the security boundary's two agents, two processes, IPv4 loopback-only transport, two sessions, one reconnect, 60-second maximum, deterministic public identities, replay persistence, Option A halt-on-conflict, authority firewall, and cleanup requirements. It does not weaken isolation or transfer authority.

However, it changes the exact transport endpoint rule recorded by F152/F153: Agent B is no longer fixed to source port `28429`. That is an authorization-scope change even though it is security-preserving. It cannot be retroactively applied to F153.

Any future corrected experiment therefore requires all of the following before execution:

- a new one-shot, experiment-specific, non-transferable authorization;
- independent review of the revised endpoint and identity-binding contract;
- passing mock/pure-logic and offline conformance evidence;
- an explicit future execution invocation; and
- the same consume-on-start, no-retry, deadline, cleanup, and no-persistent-runtime lifecycle.

Foundation155 grants no authorization and performs no execution.

## 7. Authority and protected invariants

The proposal cannot auto-apply a candidate, select a winner, reorganize history, change canonical height, mutate a ledger, issue supply, validate transactions, alter consensus/history, or settle. Protocol v1.0.0 and `coin.tx_validation.validate_transaction` remain canonical. Bitcoin remains external evidence with zero L28 authority. Signer/runtime authority remains blocked.

Protected economics remain exact: hard cap `28000000`, emission ceiling `11130000`, historically mined `2824584`, treasury locked `500000`, circulating snapshot `2324584`, halving interval `210000`, rewards `[28,14,7,3,1,0]`, mined-through entry `100877`, and next canonical height `100878`; issuance remains coinbase-only and historical evidence immutable.

## 8. Disposition

- `PASS`: F154's ABORT and permanent authorization consumption are internally consistent and preserved.
- `PASS`: the immediate fixed-source-port rebind is identified as the confirmed failure site, with TCP teardown state correctly bounded as an unobserved mechanism.
- `GAP`: the corrected endpoint model has only offline structural/pure-logic evidence and no independently reviewed execution evidence.
- `BLOCKED`: any new execution remains blocked pending independent review, new one-shot authorization, and separate explicit invocation.

`NEW_AUTHORIZATION_REQUIRED=true` and `NO_EXECUTION_OCCURRED=true` for Foundation155.
