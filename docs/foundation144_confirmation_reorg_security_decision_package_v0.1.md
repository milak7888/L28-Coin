# Foundation 144 - Confirmation/Reorg Security Decision Package v0.1

**Status:** offline decision package only / non-activating

Foundation 143 produced real isolated loopback propagation evidence. It did
not define confirmation, finality, fork-choice, rollback, or reorganization
policy.

Foundation 144 therefore does not implement consensus behavior. It records the
security decisions that must be made before any confirmation or reorg logic can
be implemented.

## Mandatory invariants

Any future policy must preserve all frozen L28 Protocol v1.0.0 authority rules:

- canonical height comes only from consensus state;
- missing required consensus, ledger, or supply state fails closed;
- peer evidence never gains ledger, issuance, supply, validation, history,
  canonical-height, or settlement authority;
- canonical transaction validation remains
  `coin.tx_validation.validate_transaction`;
- historical economic and ledger records remain immutable;
- identical public validation rules apply to all participants;
- no subsystem or operator may override consensus authority.

## Threat model

The decision must address stale peers, conflicting tips, equivocation,
partitions and reconnects, deep reorg attempts, oscillating candidate tips,
missing required state, and invalid candidate histories.

Until a policy is selected, conflicting canonical evidence must not cause an
automatic canonical transition. The existing local canonical state is retained
and the decision fails closed.

## Candidate policy families

### Option A - Halt on conflict

No automatic reorganization. A conflict stops synchronization until a future
governed deterministic protocol rule defines resolution and resumption.

### Option B - Bounded reorganization

A future deterministic fork-choice rule may permit rollback only within an
explicitly defined maximum depth. Confirmation count, fork-choice, tie-break,
partition recovery, and deep-reorg rejection rules remain undecided.

### Option C - Finality floor

A future deterministic confirmation threshold creates a finality floor.
Conflicts above that floor require a separately defined deterministic
fork-choice rule. Threshold, finality rule, tie-break, and recovery behavior
remain undecided.

Foundation 144 selects none of these options and assigns no numeric
confirmation count or reorg depth.

## Required future evidence

A selected policy must receive deterministic unit tests, conflicting-tip
adversarial tests, partition/reconnect tests, equivocation tests, deep-reorg
boundary tests, oscillation-resistance tests, missing-state fail-closed tests,
protected-economic-fact preservation checks, canonical-validator preservation,
and independent security review.

Passing Foundation 144 means only:

`READY_FOR_EXPLICIT_CONFIRMATION_REORG_POLICY_DECISION`

It does not authorize implementation, networking, mining, signing, broadcast,
testnet operation, settlement, or production deployment.
