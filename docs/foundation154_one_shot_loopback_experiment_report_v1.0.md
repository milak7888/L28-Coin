# Foundation154 One-Shot Bounded Loopback Experiment Report v1.0

Status: `ABORT`

Foundation154 executed the single invocation authorized by `L28-F153-OPTION-A-ONE-SHOT-001` from parent `fd3bf5d08bea5ec57b4f127b6f5e47a56d790ab6`. The execution started exactly two isolated agent processes and therefore atomically consumed the authorization for reuse. It is permanently non-restartable.

## Pre-execution gates

- Exact committed F152/F153 authorization and source digests: `PASS`.
- Pre-start lifecycle: granted, unconsumed, inactive, and unexecuted.
- Fixed scope: two agents, two processes, IPv4 loopback `127.0.0.1:28428` and `127.0.0.1:28429`, two sessions, one reconnect, and at most 60 seconds.
- Both ports had no listener before invocation.
- Foundation154 dry-run/focused tests: `8 passed` with zero sockets and processes.
- F141-F153 regressions: `167 passed`.
- Protocol regression: `42 passed`.

## Execution outcome

Session 1 completed between the two deterministic public fixture agents. Agent B then made the one permitted reconnect attempt. The operating system rejected the fixed source-port re-bind with `OSError: [Errno 48] Address already in use`. Agent A subsequently reached its bounded accept timeout. The controller exited after approximately `5.084247` seconds, well inside the 60-second ceiling.

This is recorded as `ABORT`, not `PASS`. The reconnect did not establish, so the active experiment did not prove replay persistence/rejection or the Option A equivocation-to-`HALTED_CONFLICT` path. Offline preflight continued to prove that the existing deterministic Option A assessment produces `HALT_SYNC_PEER_EQUIVOCATION` and transitions `SYNCING` to `HALTED_CONFLICT`, but that is not substituted for missing runtime evidence.

No retry was attempted or is permitted.

## Lifecycle and cleanup

At successful process start, `AUTHORIZATION_CONSUMED`, `CONSUMED_FOR_REUSE`, `VALID_FOR_ACTIVE_EXECUTION`, and `EXPERIMENT_EXECUTED` became true. At abort, active validity became false while consumption and reuse denial remained true.

Cleanup checks found no listener on either fixed port, no Foundation154 child process, and no remaining Foundation154 disposable data directory. No persistent service or reusable runtime was created.

## Authority and protocol boundary

The experiment performed no candidate application, reorganization, winner selection, canonical-height override, ledger mutation, issuance, supply, validation, consensus, history, or settlement action. It created no wallet, key, signature, mining, broadcast, deployment, or public-testnet behavior. Bitcoin remains external evidence with zero L28 authority.

Protocol v1.0.0 and `coin.tx_validation.validate_transaction` retain their baseline SHA-256 digests. The protected economics and historical facts remain unchanged: hard cap `28000000`, emission ceiling `11130000`, historically mined `2824584`, treasury locked `500000`, circulating snapshot `2324584`, halving interval `210000`, reward schedule `[28,14,7,3,1,0]`, historical mined-through entry `100877`, and next canonical height `100878`.

## F37 reassessment

Foundation154 advances no F37 status. F37-07 remains `PARTIAL_ISOLATED_LOOPBACK_TRANSPORT_EVIDENCE`; F37-10 remains `PARTIAL_ISOLATED_LOOPBACK_PROPAGATION_EVIDENCE`; F37-11 remains `OFFLINE_OPTION_A_REVIEWED_NON_NORMATIVE`. No runtime, network, testnet, or production authorization follows.
