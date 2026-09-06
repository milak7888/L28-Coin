# Foundation160 Offline Spawn/Bootstrap Lifetime Design v0.1

Status: `PASS_OFFLINE_DESIGN_NO_EXECUTION_AUTHORITY`

## Purpose and boundary

Foundation160 provides a pure-Python lifecycle model for a future parent-owned spawn/bootstrap resource bundle. It does not modify or execute the consumed F158 helper, retry F159, create a process or socket, use a network, consume authorization, or authorize an experiment.

F159 remains `ABORT`. The SemLock/FileNotFoundError output remains `OPERATOR_OBSERVED_NOT_MACHINE_PERSISTED`; the F159 root cause remains `NOT_PROVEN`. The shared-ready lifetime issue remains a hypothesis only.

## Parent-owned bundle

The model strongly retains the synchronization/ready object, result channel, child/process lifecycle objects, and startup-supervisor lifecycle objects. Parent ownership spans, in strict order:

1. `PROCESS_OBJECT_CONSTRUCTION`
2. `PROCESS_START_SUPERVISION`
3. `CHILD_BOOTSTRAP_WINDOW`
4. `ACTIVE_EXECUTION`
5. `CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL`

Dropping child argument references cannot remove the parent's ready or result-channel references. Skipped, repeated, backward, post-release, and otherwise invalid lifecycle transitions fail closed.

Resource release is permitted only in the cleanup phase after every child lifecycle object is terminal and every startup supervisor is quiescent. Any failed prerequisite leaves every parent-owned reference intact. Successful release clears ready, result channel, child lifecycle, and supervisor lifecycle references together. Any future live implementation must adopt this contract before a new experiment can be considered for security review.

## Offline validation model

Tests use only fake tokens, weak references, garbage collection, and lifecycle state. They verify ready and result-channel survival through every phase, child-argument release independence, live-child and active-supervisor release denial, terminal/quiescent release, and invalid-transition rejection.

The new Python files import none of `multiprocessing`, `socket`, `subprocess`, `threading`, or `asyncio` and call none of the prohibited runtime entry points. This is an offline design contract, not a live implementation.

## Historical and future authority

The F158 helper remains SHA-256 `56d3a8b796ff245cf29124886c0da64b3ab605a640fc45d14a0a26e20ea8e9b6`. The F158 consumption marker remains SHA-256 `1a9343a8ca2835c9125c2f80c6a3a91275bd6d498a27ee0039d603417b666605`.

`NEW_AUTHORIZATION_REQUIRED=true`, `SEPARATE_SECURITY_REVIEW_REQUIRED=true`, `SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED=true`, and `F159_RETRY_FORBIDDEN=true`. F157/F158/F159 consumption state cannot be reused. Foundation160 grants no execution authority and cannot be used as authorization for future runtime work.

Protocol v1.0.0, protected economics/history, `coin.tx_validation.validate_transaction`, the Bitcoin boundary, signer blocks, F37 statuses, and all runtime/economic/consensus authority restrictions remain unchanged.
