# Foundation 140 - Core Runtime Boundary and Ephemeral State Lifecycle v0.1

**Status:** offline tested boundary / non-activating

Foundation 140 consumes the Foundation 138 M1 identity binding and Foundation
139 M2 offline preparation bundle without starting a Core process.

Implemented in the production boundary module:

- deterministic binding to network_id, genesis_hash, config_hash and local tip;
- fail-closed mismatched identity and stale or unavailable tip checks;
- deterministic genesis artifact materialization to canonical bytes only;
- explicit runtime and process authority flags fixed false;
- process start and stop hooks represented as interfaces only;
- no production filesystem mutation implementation;
- no transition to reserved running states.

Implemented only under tests:

- isolated temporary disposable state-directory creation;
- deterministic binding marker creation;
- reset behavior that destroys disposable test state and recreates it;
- cleanup behavior that removes the temporary sandbox;
- path containment checks preventing sandbox escape.

The test-only filesystem helper is not imported by L28 production code.

No node, process, socket, peer, RPC server, wallet, key generator, signer, miner,
broadcast path, bridge, public testnet, or settlement process is started or
authorized.

Protocol v1.0.0 and protected historical and economic facts remain unchanged.
