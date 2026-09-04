# Foundation 146 - Explicit Option A Selection v0.1

Option A, HALT ON CONFLICT, is selected for deterministic offline implementation.

The selection is strictly a non-normative implementation safety boundary.

It does not modify frozen L28 Protocol v1.0.0 and does not create a new
confirmation count, fork-choice winner, reorganization depth, or finality rule.

On unresolved conflicting candidate histories, synchronization must halt and
the current local canonical state must remain unchanged.

No peer or operator may select a winning history.

Resume requires a separately governed deterministic resolution rule.

Any future attempt to make this behavior a normative consensus invariant
requires a governed compatibility/versioning decision. Any breaking protocol
change requires v2.0.0.

This selection authorizes offline deterministic implementation and testing only.
It does not authorize networking, runtime activation, testnet operation,
signing, mining, broadcast, settlement, or deployment.
