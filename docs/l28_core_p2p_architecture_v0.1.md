# Core L28 Node and P2P Role Architecture v0.1

**Foundation:** 19

**Status:** Specification only; non-activation

**Depends on:** L28 Future Capability Registry v0.1

## Purpose

This specification separates native L28 policy from peer-to-peer transport.
It defines conceptual roles, lifecycle states, trust boundaries, message flow,
and recovery requirements without implementing or starting a node or network.

The two roles are:

- `CoreL28Node`: native validation and lifecycle-policy coordinator
- `L28P2PNode`: untrusted peer transport and synchronization coordinator

Neither conceptual role is an authorization to initialize a ledger, designate
a canonical checkpoint, begin mining, listen on a network, or connect to peers.

## Non-goals

Foundation 19 does not:

- add runtime node classes;
- rename existing runtime code;
- import historical or private implementations;
- initialize, repair, migrate, or activate a ledger;
- declare a historical checkpoint canonical;
- open a listener or make an outbound connection;
- start mining, signing, a wallet, a bridge, or a deployment;
- define a production consensus or finality algorithm.

## Role separation

| Responsibility | CoreL28Node | L28P2PNode |
|---|---:|---:|
| Native transaction validation | Owns policy | Never bypasses core |
| Supply and issuance invariants | Owns policy | No authority |
| Ledger mutation authorization | Owns policy boundary | No authority |
| Peer discovery and sessions | No transport role | Owns transport |
| Frame decoding and size limits | Receives normalized input | Owns boundary |
| Peer replay controls | Consumes evidence | Owns peer registry |
| Checkpoint acceptance policy | Owns validation policy | Relays candidates only |
| Wallet or private-key custody | Prohibited | Prohibited |
| Mining execution | Prohibited in v0.1 | Prohibited |
| Network execution | Prohibited | Prohibited in v0.1 |

`L28P2PNode` treats all peer-supplied information as untrusted. It may reject
input at the transport boundary, but it cannot convert accepted transport data
into valid native state. Only `CoreL28Node` may evaluate native validity.

## CoreL28Node responsibilities

`CoreL28Node` is a policy coordinator above the existing public validation and
ledger surfaces. It does not replace `BlocklessLedger`, transaction validation,
or protocol invariants.

Its future responsibilities are limited to:

1. reporting explicit lifecycle state;
2. binding validation to a declared network and protocol version;
3. submitting normalized candidates to existing native validators;
4. enforcing issuance-readiness and supply invariants;
5. authorizing persistence only after complete validation;
6. producing deterministic, sanitized decision reports;
7. entering fail-closed states after integrity failures;
8. coordinating pause, recovery, and shutdown policy.

It must never:

- discover historical files automatically;
- treat historical evidence as runtime state;
- infer canonical readiness from file presence;
- bypass signature, replay, transaction, or supply validation;
- sign for a miner, user, agent, treasury, or peer;
- route future mining rewards to the creator automatically;
- make network connections directly.

## L28P2PNode responsibilities

`L28P2PNode` is a transport boundary. Its future responsibilities are:

1. deterministic frame decoding;
2. protocol and network identifier checks;
3. message-size and resource limits;
4. peer authentication evidence collection;
5. nonce and replay tracking;
6. bounded peer discovery;
7. candidate synchronization and request correlation;
8. forwarding normalized candidates to `CoreL28Node`;
9. returning sanitized results to authorized peers;
10. deterministic pause and shutdown behavior.

It must never:

- mutate native ledger state directly;
- authorize minting or alter issued supply;
- designate a checkpoint canonical;
- reinterpret a rejected core decision;
- access wallet files, private keys, seeds, or signing services;
- load private historical state;
- claim that a wrapped asset is native L28.

## Core lifecycle

Foundation 19 defines only non-production lifecycle states:

| State | Meaning |
|---|---|
| `CREATED` | Object exists; no state source has been accepted |
| `EVIDENCE_ONLY` | Public evidence may be verified; no runtime state exists |
| `DISPOSABLE_TEST_READY` | Explicitly acknowledged isolated test state only |
| `PAUSED` | New candidates are rejected; inspection may continue |
| `STOPPED` | Terminal clean shutdown state |
| `FAILED` | Integrity failure; only inspection and explicit recovery are allowed |
| `CANONICAL_READY_RESERVED` | Reserved for a later approved specification |
| `RUNNING_RESERVED` | Reserved for a later approved specification |

`CANONICAL_READY_RESERVED` and `RUNNING_RESERVED` are unreachable in
Foundation 19. Their names prevent accidental substitution of test readiness
for production readiness.

Allowed core transitions are:

- `CREATED` to `EVIDENCE_ONLY` after public evidence verification;
- `CREATED` to `DISPOSABLE_TEST_READY` after explicit test-only acknowledgement;
- a nonterminal state to `PAUSED` after an administrative or integrity event;
- `PAUSED` to `STOPPED` after deterministic shutdown;
- any nonterminal state to `FAILED` after a fail-closed error;
- `FAILED` to `STOPPED` after inspection and cleanup.

No transition activates historical issuance or canonical continuation.

## P2P lifecycle

Foundation 19 defines these transport states:

| State | Meaning |
|---|---|
| `CREATED` | Transport object exists without network resources |
| `CONFIGURED` | Sanitized configuration passed static validation |
| `PAUSED` | Peer admission and message forwarding are disabled |
| `STOPPED` | No network resources are held |
| `FAILED` | Transport integrity failure; fail closed |
| `LISTENING_RESERVED` | Reserved for a later approved implementation |

`LISTENING_RESERVED` is unreachable in Foundation 19.

## Network and protocol binding

Every future P2P frame must bind at least:

- protocol version;
- explicit network identifier;
- message type;
- deterministic message identifier;
- sender or peer identity evidence;
- nonce or replay identifier;
- timestamp and expiry policy;
- payload length and payload digest.

Missing, ambiguous, duplicated, expired, oversized, or unsupported fields fail
closed before a candidate reaches native validation.

## Inbound message flow

The required future inbound sequence is:

1. receive bounded bytes from an identified peer session;
2. enforce the maximum frame size before decoding;
3. decode using a deterministic schema;
4. verify network and protocol identifiers;
5. verify message identity, nonce, timestamp, and replay status;
6. collect signature or authentication evidence;
7. normalize the candidate without mutating it;
8. submit the candidate to `CoreL28Node`;
9. run native transaction, issuance, and checkpoint policy as applicable;
10. persist only after a complete core approval;
11. emit a deterministic sanitized result;
12. update replay state only at the specified atomic boundary.

A transport success is not a native-validation success.

## Outbound message flow

Outbound messages must originate from a deterministic core result or an
explicit transport-control event. Future implementations must:

- bind the same network and protocol identifiers;
- use deterministic message identities;
- avoid exposing paths, hosts, process identifiers, or exception text;
- avoid signing with participant keys;
- apply rate, size, and peer-policy limits;
- make retries idempotent.

## Checkpoint boundary

Checkpoint data is untrusted until verified by core policy. Future checkpoint
admission requires:

- an explicitly supplied artifact or manifest;
- schema and duplicate-key rejection;
- hash, size, and record-count commitments;
- network and protocol binding;
- parent-graph and supply-invariant checks;
- provenance commitments that are enforced, not merely stored;
- a separate authorization step before canonical designation.

Foundation 19 provides no canonical-designation operation. File presence,
historical naming, or a successful evidence audit is insufficient.

## Persistence and recovery

Future persistence must be atomic, deterministic, and auditable. The design
must distinguish:

- peer replay state;
- candidate synchronization state;
- native ledger state;
- public historical evidence;
- disposable test state.

Recovery must never merge these namespaces implicitly. Corruption, partial
writes, schema mismatch, unknown version, or provenance failure must place the
affected role in `FAILED` or `PAUSED` rather than attempting silent repair.

## Mining, bridge, and wallet boundaries

Mining remains a separate future capability. P2P transport may eventually
relay a candidate, but cannot create a reward or select its recipient.

Bridge operations remain separate from native node identity. Wrapped supply
must never alter native L28 supply.

Neither node role owns wallet custody or participant signing. Authorization
evidence is verified, not created, by these roles.

## Observability

Future reports must be deterministic and sanitized. They may include stable
codes, protocol versions, logical state, counts, and content-bound report IDs.
They must not expose secrets, filesystem paths, hostnames, raw exception text,
wallet material, private artifacts, or peer credentials.

## Foundation 19 acceptance criteria

Foundation 19 is complete when:

- the two conceptual roles are unambiguous;
- lifecycle states and permitted transitions are explicit;
- P2P input cannot bypass native validation;
- checkpoint evidence cannot become canonical automatically;
- mining, bridge, wallet, and signing authority remain outside both roles;
- the companion security profile is valid deterministic JSON;
- existing protocol invariants and the complete public test suite pass;
- no runtime source, network configuration, or deployment file changes.

## Implementation boundary

Any later implementation requires a new Foundation milestone. It must begin
with inactive interfaces and adversarial tests. Runtime node construction,
network listeners, canonical checkpoint selection, and ledger activation each
require separate explicit authorization.
