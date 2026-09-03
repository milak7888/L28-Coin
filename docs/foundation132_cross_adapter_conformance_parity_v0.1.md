# Foundation 132 — Cross-Adapter UAII Conformance Parity v0.1

**Status:** deterministic offline conformance / non-activating

Foundation 132 adds cross-adapter conformance checks for the canonical
`l28-universal-ai-access-interface/v0.1`.

Covered surfaces:

- canonical UAII reference core
- isolated MCP adapter
- isolated REST/OpenAPI adapter
- isolated Python SDK
- isolated TypeScript SDK

The parity suite verifies:

1. all adapters expose the same eight canonical UAII operations;
2. MCP, REST, and Python produce the same canonical public result as
   `process_uaii_request` for an equivalent request;
3. TypeScript serializes the same canonical UAII request bytes;
4. adapter authority remains closed for networking, signing, spending,
   transaction submission, and settlement.

This milestone modifies no adapter implementation and does not activate
servers, listeners, networking, package publication, wallets, signing,
broadcast, mining, bridges, transaction submission, or settlement.

Protocol v1.0.0 and Foundation 127 canonical preservation remain unchanged.

TypeScript validation uses the already-installed Node native TypeScript
runtime. No dependency installation or package publication occurs.
