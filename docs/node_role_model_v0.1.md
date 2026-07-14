# L28 Inert Node-Role Model v0.1

**Foundation:** 21
**Status:** In-memory reference model; non-activation
**Model:** `l28-node-role-model/v0.1`
**Architecture input:** `l28-core-p2p-architecture/v0.1`
**Security-profile input:** `l28-core-p2p-security/v0.1`

## Purpose

Foundation 21 introduces an inert reference model for the lifecycle roles
defined by the public Foundation 19 architecture.

The model turns the documented lifecycle tables into immutable, testable state
transitions. It does not construct a runtime node, open a network connection,
load a ledger, or activate any L28 subsystem.

The implementation deliberately uses model names rather than runtime node
names:

- `CoreNodeRoleModel` represents the `CoreL28Node` policy role.
- `P2PNodeRoleModel` represents the `L28P2PNode` transport role.
- `NodeRoleTransitionResult` records one deterministic transition decision.

## Inert boundary

The model:

- exists only in memory;
- has no filesystem API;
- has no network API;
- has no persistence or recovery API;
- has no ledger, checkpoint, transaction, or mining API;
- has no wallet, key, signature, bridge, or deployment API;
- starts no thread, process, task, server, listener, or peer session;
- performs no automatic state discovery; and
- makes no claim that a runtime L28 node exists.

Importing or constructing a model has no external side effect.

## Immutability

Both role models are frozen data classes. Public construction accepts no state
argument and always produces `CREATED`.

A transition never mutates the original model. A successful transition returns
a new model and a successful `NodeRoleTransitionResult`. A failed transition
returns the original model object and a failed result.

This makes a transition decision explicit and prevents partial in-place state
changes.

## Transition result

Every result contains:

- `ok`
- `code`
- `role`
- `previous_state`
- `requested_state`
- `resulting_state`
- `model_version`

The stable result codes are:

| Code | Meaning |
|---|---|
| `transitioned` | The requested transition is explicitly allowed. |
| `state_invalid` | The requested value is empty, non-string, or unknown. |
| `reserved_state_unreachable` | The request targets a reserved state. |
| `transition_not_allowed` | Both states are known but the transition is absent. |

## Core role states

The Core role contains these active model states:

- `CREATED`
- `EVIDENCE_ONLY`
- `DISPOSABLE_TEST_READY`
- `PAUSED`
- `STOPPED`
- `FAILED`

Its reserved states are:

- `CANONICAL_READY_RESERVED`
- `RUNNING_RESERVED`

The allowed Core transitions are:

| From | To |
|---|---|
| `CREATED` | `EVIDENCE_ONLY` |
| `CREATED` | `DISPOSABLE_TEST_READY` |
| `CREATED` | `PAUSED` |
| `EVIDENCE_ONLY` | `PAUSED` |
| `DISPOSABLE_TEST_READY` | `PAUSED` |
| `PAUSED` | `STOPPED` |
| `CREATED` | `FAILED` |
| `EVIDENCE_ONLY` | `FAILED` |
| `DISPOSABLE_TEST_READY` | `FAILED` |
| `PAUSED` | `FAILED` |
| `FAILED` | `STOPPED` |

## P2P role states

The P2P role contains these active model states:

- `CREATED`
- `CONFIGURED`
- `PAUSED`
- `STOPPED`
- `FAILED`

Its reserved state is:

- `LISTENING_RESERVED`

The allowed P2P transitions are:

| From | To |
|---|---|
| `CREATED` | `CONFIGURED` |
| `CREATED` | `PAUSED` |
| `CONFIGURED` | `PAUSED` |
| `PAUSED` | `STOPPED` |
| `CREATED` | `FAILED` |
| `CONFIGURED` | `FAILED` |
| `PAUSED` | `FAILED` |
| `FAILED` | `STOPPED` |

## Reserved-state enforcement

Reserved states are present so the model can recognize and reject them by
name. They are not valid destinations, initial states, or restorable states.

Both the public transition method and the internal validated-state factory
reject reserved states. A reserved-state request leaves the current model
unchanged and returns `reserved_state_unreachable`.

Foundation 21 provides no path into `CANONICAL_READY_RESERVED`,
`RUNNING_RESERVED`, or `LISTENING_RESERVED`.

## Terminal behavior

`STOPPED` is terminal for both models. No transition originates from it.

Self-transitions are not implicitly accepted. They fail with
`transition_not_allowed` unless a future version explicitly adds them to the
public security profile.

## Example

```python
from coin.node_role_model import CoreNodeRoleModel

created = CoreNodeRoleModel()
evidence_only, result = created.transition("EVIDENCE_ONLY")

assert result.ok
assert created.state == "CREATED"
assert evidence_only.state == "EVIDENCE_ONLY"
```

This example evaluates an inert state change only. It does not start a node or
load historical evidence.

## Profile alignment

The state sets, reserved-state sets, and transition pairs are copied from the
public Foundation 19 security profile and checked against that profile by the
Foundation 21 tests.

Any change to those public lifecycle commitments requires a separately
reviewed profile version, model version, documentation update, and test update.

## Interpretation boundaries

Passing the Foundation 21 tests proves that the inert model implements the
published lifecycle tables and fails closed for unsupported transitions.

It does not prove:

- that a runtime `CoreL28Node` or `L28P2PNode` exists;
- that any L28 node, listener, network, or peer is running;
- that a ledger or checkpoint is loaded, canonical, or active;
- that transaction admission or persistence is implemented;
- that mining or reward issuance is active;
- that a wallet can sign or spend;
- that a bridge or wrapped asset is deployed; or
- that reserved activation states are authorized.

Foundation 21 does not change L28 identity, supply, reward, historical
continuity evidence, consensus policy, or protocol economics.

Any future runtime adapter must be a separate milestone with explicit I/O,
resource, persistence, recovery, authentication, and activation review.
