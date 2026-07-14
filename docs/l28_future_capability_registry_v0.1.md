# L28 Future Capability Registry v0.1

**Foundation:** 18

**Status:** Planning only; non-activation

**Scope:** Public, sanitized capability classification

## Purpose

This registry preserves L28 concepts for deliberate future implementation
without copying private source, exposing private infrastructure, or changing
canonical L28 economics.

The registry does not claim that a candidate capability is running,
production-ready, canonical, deployed, or approved for activation.

## Fixed boundaries

- L28 is the native blockless coin.
- Leap28 is a separate autonomous AI platform.
- Native L28 has a maximum supply of 28,000,000.
- The maximum coinbase reward is 28 L28.
- Future rewards belong to the successful miner or explicitly authorized
  protocol earner.
- Future rewards are never automatically routed to the creator.
- A bridge contract or wrapped representation does not define native L28.
- Private historical state must never be discovered or activated automatically.
- Private source is not promoted directly into the public repository.

## Classification

| Classification | Meaning |
|---|---|
| Canonical public | Implemented and governed by the public L28 protocol |
| Future candidate | Preserved concept requiring specification and review |
| Historical utility | Retained noncanonical operator or audit concept |
| Inactive prototype | Experimental design that is not activation-ready |
| Rejected incompatible | Conflicts with L28 identity, economics, security, or governance |

## Canonical public foundations

- Native L28 identity and monetary invariants
- Machine-to-machine exchange protocol
- Offline historical-continuity verification

## Future candidates

- Core node lifecycle
- Authenticated peer-to-peer networking
- Advanced mining and Proof-of-Intelligence
- DAG candidate selection and finality
- Universal bridge and wrapped representations
- Privacy and zero-knowledge options
- Deterministic oracle and policy inputs
- Auditable treasury governance
- Checkpoint portability and deterministic recovery
- Deterministic scalability and sharding
- AI-agent earning and machine-economy protocols

Every candidate remains inactive until it passes the promotion gates.

## Node-role separation

Earlier design work used the same `L28Node` name for two distinct roles.
Future specifications use conceptual names:

- `CoreL28Node`: native state, transaction, issuance, and lifecycle rules
- `L28P2PNode`: peer discovery, synchronization, and network messaging

The two identities are distinct. This registry does not rename, import, or
activate existing runtime code.

## Historical utilities

The following concepts are retained rather than deleted:

- A guarded historical genesis-checkpoint writer
- Read-only historical supply reporting
- Read-only historical checkpoint verification

They do not establish canonical continuation, a spendable balance, or
authorization to initialize or migrate a ledger.

## Inactive and incompatible work

Alternative nucleus research is retained as an inactive prototype. A useful
technical concept may be reconsidered only through a new public specification
that begins with canonical L28 identity and economics.

The following ideas are explicitly rejected:

- Noncanonical alternative supply and allocation models
- Automatic creator routing of future rewards
- Automatic activation of private historical state
- Treating a bridge contract as native L28 identity
- Hidden or unilateral mint, release, or emergency authority

## Promotion gates

Every future capability must proceed through:

1. A standalone public specification.
2. Identity and economic compatibility review.
3. A security and threat model.
4. A dedicated Foundation branch.
5. Deterministic and adversarial tests.
6. Successful continuous integration.
7. Review before merge.
8. Separate explicit authorization before deployment or activation.

## Recommended next specification

The next specification should define the Core L28 Node and P2P Role
Architecture:

- `CoreL28Node` responsibilities
- `L28P2PNode` responsibilities
- Explicit lifecycle states
- Canonical-checkpoint boundaries
- Fail-closed startup and recovery
- No runtime activation

## Historical-continuity boundary

This registry does not change the public historical-continuity conclusions:

- Historical evidence remains evidence only.
- Canonical continuation has not been activated.
- A spendable historical wallet balance has not been proven.
- Private ledger material is not bundled or discovered.
- No migration, initialization, mining, or network startup is performed.
