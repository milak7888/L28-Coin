# Foundation168 Bounded Runtime Execution Package Security Review v1.0

Status: `PREPARED_NOT_AUTHORIZED_NOT_EXECUTED`

Foundation168 prepares dormant machinery for one possible future bounded loopback experiment. The committed state remains `F166_DECISION=PENDING_OPERATOR_DECISION`, with authorization, invocation, consumption, execution, and the execution gate all false. This task provides no operator decision or invocation evidence.

The authorization boundary requires two independent, exactly bound future records: `AUTHORIZE_ONE_NEW_BOUNDED_EXPERIMENT` and `AUTHORIZE_FOUNDATION168_EXECUTION_ONCE`. Artifact, experiment, old-authorization, and F159 checks precede an exclusive persistent one-shot claim. The claim occurs before backend construction and prevents reuse across both threads and helper processes. Success and abort are equally non-retryable.

The driver is limited to two child processes, IPv4 loopback, Agent A `127.0.0.1:28428`, Agent B `127.0.0.1:0`, two sessions, one reconnect, and one absolute monotonic deadline of at most 60 seconds. It strongly retains ready, result, child, supervisor, lifecycle, boundary, and F164 candidate references through cleanup. F164 remains the adapter; no alternate adapter or package entrypoint was introduced.

All claimed execution paths enter cleanup. SUCCESS is impossible unless every child is terminal, every supervisor is quiescent, cleanup is complete, and terminalization succeeds. Evidence records bounded timing, effective loopback ports, lifecycle, sanitized exception type/representation, cleanup, terminalization, claim count, and all authority-negative fields; raw exception messages are never persisted, and sensitive key categories are rejected before persistence. The post-run evaluator distinguishes `PASS`, `ABORT_ACCEPTED`, `SECURITY_FAILURE`, and `EVIDENCE_INVALID` and fails closed on malformed, contradictory, stale, reused, external-network, cleanup, or authority evidence.

Only the dormant driver and sole explicit invocation helper import runtime capability. They create no process, thread, socket, service, or background work at import time. No existing production entrypoint imports F168, and the tests use injected fakes rather than the concrete runtime backend.

The cross-module review records `PASS 16 / GAP 0 / BLOCKED 0` for authorization authenticity, atomic one-shot consumption, race/replay resistance, immutable scope, hash provenance, process and synchronization lifetime, deadline, port behavior, cleanup/terminalization, exception evidence, evidence integrity, external-network containment, protocol/economic firewall, F159 non-retry, and old-authorization non-reuse.

Protocol v1.0.0, `coin.tx_validation.validate_transaction`, economics, history, genesis, supply, snapshot, wallet, ledger, height, signer, Bitcoin, settlement, mining, and broadcast boundaries remain unchanged. F168 still requires a separate future operator authorization and separate explicit invocation. Nothing was executed.
