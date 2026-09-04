# Foundation 145 - Option A Compatibility Review v0.1

**Status:** selection-readiness review only / non-activating

Foundation 144 left all confirmation and reorganization policies unselected.

Foundation 145 evaluates Option A: HALT ON CONFLICT.

## Candidate semantics

When valid, correctly bound peer evidence implies a canonical transition that
cannot be safely resolved under existing selected policy, synchronization
halts and the current local canonical state is retained.

No peer receives authority over canonical height, ledger mutation, issuance,
supply, validation, history, or settlement.

No automatic reorganization occurs.

No confirmation count is created.

No new finality claim is created.

No operator may manually choose a winning history.

Synchronization may resume only after a separately governed deterministic
resolution rule has been selected, implemented, tested, independently
reviewed, and explicitly authorized.

## Protocol v1.0.0 compatibility

The frozen v1.0.0 protocol already requires canonical height to come from
consensus state and requires missing required consensus or ledger state to fail
closed.

Using halt-on-conflict strictly as a non-normative implementation safety
boundary is consistent with those existing fail-closed invariants because it
does not choose a competing history or alter protocol economics.

However, making Option A itself a new normative consensus rule would extend the
protocol definition. Foundation 145 therefore does not classify normative
adoption as automatically v1-compatible.

If Option A is intended to become a protocol-level consensus invariant, a
separate governed compatibility/versioning decision is required. Any breaking
change requires v2.0.0 and must not be silently backported to v1.x.

## Recommendation

Option A is the recommended initial policy candidate because it introduces no
automatic rollback, no arbitrary confirmation count, and no peer-driven
canonical rewrite.

This recommendation is not policy selection.

Passing Foundation 145 means only:

READY_FOR_EXPLICIT_OPTION_A_POLICY_SELECTION
