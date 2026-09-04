# Foundation 143 - Authorized Isolated Two-Agent Loopback Transport Experiment v0.1

Foundation 143 is an explicitly authorized, one-shot isolated transport experiment.

Scope is exactly two logical disposable agents on one machine:

- Agent A: 127.0.0.1:28428, designated local Core writer.
- Agent B: 127.0.0.1:28429, peer evidence only.
- IPv4 loopback only.
- No external networking.
- No production P2P runtime.
- No RPC.
- No wallet or key generation.
- No signing.
- No mining.
- No public broadcast.
- No historical L28 state.
- No real-value L28.
- No settlement.

The experiment transports HELLO, TIP_EVIDENCE, and CANDIDATE_EVIDENCE from
Agent B to Agent A and a HELLO response from Agent A to Agent B.

Replay state is preserved across one reconnect. Replaying the first Agent B
HELLO must fail closed with message_replayed.

The local Core tip must remain unchanged. Peer transport has no authority over
issuance, supply, canonical height, validation, history, ledger mutation, or
settlement.

Foundation 143 does not define production peer authentication, trusted
production time, production resource limits, confirmation count, confirmation
policy, fork choice, rollback, or reorganization policy.

The explicit operator authorization applies only to this bounded experiment.
It does not create persistent networking or testnet authority.
