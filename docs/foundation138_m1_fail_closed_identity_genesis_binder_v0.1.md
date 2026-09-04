# Foundation 138 - Disposable Testnet M1 Fail-Closed Identity + Genesis Binder v0.1

**Status:** offline implementation / non-activating

Foundation 138 implements the complete offline M1 identity/config/genesis
validation boundary defined by Foundation 137.

Implemented:

- disposable network identifiers must be distinct from MAIN identities;
- outer config and genesis network identity are bound and must match;
- deterministic domain-separated SHA-256 genesis and config hashes;
- initial disposable height and issued supply must both be zero;
- historical checkpoint import is forbidden;
- historical balances as live genesis are forbidden;
- protected Protocol v1.0.0 economic facts must match exactly;
- production keys, creator private material, and external wallet paths are forbidden;
- disposable data-directory tags are validated without filesystem access;
- explicit disposable-test-only acknowledgement is mandatory;
- unknown or malformed configuration fails closed.

The implementation performs validation and hashing only.

It does not create a genesis file, data directory, wallet, key, node, process,
socket, peer, RPC service, signer, transaction, mining process, broadcast,
deployment, bridge, testnet, or settlement path.

Passing Foundation 138 tests does not authorize starting a testnet.
Protocol v1.0.0 and all protected historical/economic records remain unchanged.
