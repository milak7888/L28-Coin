# Foundation 142 - Isolated Two-Agent Transport Security and Authorization Gate v0.1

**Status:** prenetwork security gate only / non-activating

Foundation 142 defines the complete security boundary required before any
isolated two-agent transport experiment may be authorized.

The proposed experiment is exactly two disposable agents on one local machine.
Both endpoints are restricted to IPv4 loopback 127.0.0.1. External
connectivity is forbidden.

Agent A is the designated local Core writer. Agent B supplies peer evidence
only. Neither agent receives transport authority over issuance, supply,
transaction validation, canonical height, history, consensus, or settlement.

Peer identity for this gate uses deterministic public fixture digests. These
digests contain no secret material and are not production authentication.
Production peer authentication remains undefined.

Experiment-only limits are deterministic and bounded:

- maximum frame size: 4096 bytes;
- maximum payload size: 2048 bytes;
- maximum messages per session: 32;
- maximum sessions: 2;
- maximum reconnects: 1.

These are isolated experiment limits only. They are not production resource
policy.

Message IDs and peer nonce replay state must persist across reconnects during
the experiment. Replay causes immediate abort and planned disconnect.

The lifecycle defines startup, shutdown and reset ordering, but execution is
not authorized. Reset is limited to disposable test state.

No production wallet, private key, signer, miner, broadcaster, bridge,
historical state import, real-value L28, public network, or settlement system
is authorized.

No confirmation count or policy is defined. No fork-choice, rollback or reorg
policy is defined.

Passing Foundation 142 means only:

READY_FOR_EXPLICIT_ISOLATED_TWO_AGENT_NETWORK_AUTHORIZATION

It does not itself authorize sockets, listeners, connections, processes,
P2P runtime, RPC, networking, or a testnet.
