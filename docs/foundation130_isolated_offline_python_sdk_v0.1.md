# Foundation 130 — Isolated Offline Python SDK v0.1

**Status:** implementation / deterministic offline / non-activating

Foundation 130 implements a thin Python client binding for the canonical
`l28-universal-ai-access-interface/v0.1`.

The SDK accepts complete canonical UAII envelopes and delegates unchanged
canonical evaluation to `process_uaii_request`.

Named convenience methods correspond exactly one-to-one with the eight
existing UAII v0.1 operations. They do not introduce alternate schemas,
validators, defaults, grant flags, authority, or settlement behavior.

The SDK does not implement or activate networking, HTTP, MCP runtime,
servers, listeners, wallets, signing, broadcast, transaction submission,
mining, bridges, settlement, deployment, or package publication.

Protocol v1.0.0 remains frozen.

`coin.tx_validation.validate_transaction` remains the sole L28
transfer/coinbase validation authority.

Foundation 127 canonical preservation artifacts remain unchanged.
