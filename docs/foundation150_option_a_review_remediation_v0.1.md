# Foundation 150 - Option A Review Remediation v0.1

**Status:** local remediation candidate; independent review remains pending

Foundation150 remediates only the two findings identified from the
Foundation149 Option A independent-review boundary.

## Finding 1 - peer-equivocation halt integration

Peer-equivocation evidence now has a deterministic assessment form consumable
by `transition_sync_state`. Conflicting histories from the same peer produce
`HALT_SYNC_PEER_EQUIVOCATION`, transition `SYNCING` to `HALTED_CONFLICT`, record
the first divergence height, and retain the current local canonical state.

The existing `detect_equivocation` Boolean interface remains compatible and is
implemented through the same deterministic assessment. Non-equivocating prefix
or extension evidence produces `NO_PEER_EQUIVOCATION` and authorizes no
canonical transition.

## Finding 2 - forged assessment and state rejection

Before any state transition, the policy now rejects an `OptionAAssessment` that
claims candidate application, automatic reorganization, winner selection,
confirmation, canonical-height override, ledger mutation, issuance, supply,
validation, history, or settlement authority. Contradictory conflict, halt,
divergence, length, or local-state-retention invariants fail closed.

Both transition and resume paths reject an `OptionAPolicyState` claiming that
canonical state changed or the ledger was mutated. Assessment codes and
policy-state statuses require exact built-in `str` values before set-membership
checks, so type-corrupt values and unhashable `str` subclasses cannot leak raw
`TypeError`. Errors use deterministic `OptionAPolicyError` codes:

- `assessment_authority_invalid`;
- `assessment_retain_state_required`;
- `assessment_invariant_invalid`; and
- `policy_state_mutation_invalid`; or
- `policy_state_invalid`.

## Preserved boundaries

This remediation is deterministic and offline only. It adds no network,
socket, RPC, wallet, key, signing, mining, broadcast, settlement, persistence,
or runtime authority. It does not change Protocol v1.0.0, protected economics,
historical evidence, canonical-height derivation, or the canonical transaction
validator.

Candidate histories and peer observations remain external evidence only. They
cannot select a winner, apply a candidate, reorganize canonical state, mutate a
ledger, or obtain L28 issuance, supply, validation, history, consensus, or
settlement authority.

## Review status

Foundation150 does not mark the Foundation149 independent review `PASS` and is
not independent approval. `F37-11` remains pending independent review. Any
networking, runtime, testnet, or activation step requires separate explicit
authorization and is outside this remediation.
