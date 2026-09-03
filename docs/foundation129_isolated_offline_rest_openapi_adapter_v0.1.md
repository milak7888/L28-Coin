# Foundation 129 — Isolated Offline REST/OpenAPI Adapter v0.1

**Status:** implementation / deterministic offline / non-activating

Foundation 129 adds an in-process REST-style transport mapping and static
OpenAPI description for the canonical
`l28-universal-ai-access-interface/v0.1`.

Each POST path maps exactly one-to-one to an existing supported UAII
operation and delegates canonical evaluation to `process_uaii_request`.

The OpenAPI document is descriptive only. It contains no server endpoint and
starts no listener.

This milestone does not implement or activate HTTP networking, sockets,
servers, deployment, authentication infrastructure, wallets, signing,
broadcast, transaction submission, mining, bridges, or settlement.

HTTP transport success is not L28 settlement.

Protocol v1.0.0 remains frozen. `coin.tx_validation.validate_transaction`
remains the sole L28 transfer/coinbase validation authority.

Foundation 127 canonical preservation artifacts remain unchanged.
