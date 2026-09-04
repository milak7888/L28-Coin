# Foundation 136 — Offline UAII Adversarial Validation v0.1

**Status:** deterministic offline validation / non-activating

Foundation 136 adds adversarial checks for the existing UAII JSON boundary.

The matrix covers invalid input type, UTF-8 failure, BOM input, invalid
top-level JSON, floats and non-finite values, duplicate keys, received-size
limits, recursive property-name grammar, canonical ordering, Unicode
serialization, and lone-surrogate rejection.

The existing community conformance runner includes this matrix in full mode.

No Protocol v1.0.0, economics, historical state, UAII implementation, adapter,
SDK, wallet, signer, ledger, network, mining, broadcast, deployment, testnet,
or settlement behavior is changed.

The suite is deterministic and offline. PASS is conformance evidence only;
it is not production security certification or activation authorization.
