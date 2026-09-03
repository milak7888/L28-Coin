# Foundation 128 — Isolated Offline MCP Adapter v0.1

**Status:** implementation / deterministic offline / non-activating

Foundation 128 implements the first bounded MCP exposure slice for the
canonical `l28-universal-ai-access-interface/v0.1`.

The adapter is a pure in-process mapping layer:

MCP tool declaration → canonical UAII envelope → `process_uaii_request`

It does not implement or start an MCP server, stdio session, HTTP listener,
socket, network service, wallet, signer, broadcast path, transaction
submission path, settlement process, miner, bridge, or deployment.

Each exposed tool maps exactly one-to-one to an existing supported UAII v0.1
operation. The adapter does not add operations or modify UAII field names,
ordering, schemas, economics, validation, or authority.

`coin.tx_validation.validate_transaction` remains the sole L28
transfer/coinbase validation authority.

The Foundation 127 canonical preservation manifest remains unchanged and
must continue to pass.

Future live MCP framing/runtime exposure requires a separate milestone and
explicit authorization.
