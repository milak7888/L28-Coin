# L28 Coin Identity and Historical Continuity Audit

**Foundation:** 16

**Status:** Historical evidence report; non-activation

**Audit date:** 2026-07-14

**Protocol baseline:** L28 Protocol v1.0.0

## Purpose

This report records sanitized evidence about the identity and historical
continuity of L28 Coin. It does not activate a ledger, initialize issuance,
start mining, prove a wallet balance, or create a replacement currency.

L28 is a native blockless/DAG coin—not a token identified by one smart-contract
address. Continuity depends on its protocol, network identity, preserved
historical evidence, and an explicitly trusted checkpoint.

## Preserved snapshot

| Property | Verified value |
|---|---:|
| Claimed timestamp | `2025-11-15T13:08:38.085676Z` |
| SHA-256 | `6580333e4dba688f242d82a9ea7253369b7723273b3392dc6d8ae9b78d9b2d11` |
| Size | 30,658,355 bytes |
| Physical records | 72,098 |
| Issuance records | 72,096 |
| Treasury-lock attestations | 2 |
| Last issuance height | 100,877 |
| Final entry height | 100,879 |
| Final entry hash | `589034a1c80f6ba8f5d6b90baf0cf247b0b71a0b63e677f1b89028be643156d4` |

The claimed local timestamp is not independently proven as a publicly
timestamped publication.

## Raw-DAG relationship

The preserved raw DAG contains 102,263 issuance candidates across the same
72,096 represented heights.

The snapshot issuance content reconstructs deterministically by selecting the
first physical raw candidate for every represented height, ordering the
selected records by ascending height, applying default JSON serialization, and
appending the two chained treasury-lock attestations.

This selects 72,096 candidates and excludes 30,167 competing candidates.

Every snapshot issuance parent resolves either inside the snapshot or in the
raw DAG. However, 20,671 parents exist only in the raw DAG, so the snapshot is
not a self-contained complete parent graph.

## Historical economic quantities

| Quantity | L28 |
|---|---:|
| Historical declared supply | 2,824,584 |
| Physically recorded reward total | 2,018,688 |
| Missing-height implied amount | 805,896 |
| Treasury-lock commitment | 500,000 |
| Derived unlocked amount | 2,324,584 |
| Consolidated amount | 2,018,660 |
| Unconsolidated genesis reward | 28 |

The declared supply follows the height formula:

`current_supply = 28 × (entry_height + 1)`

The 2,324,584 figure is arithmetic derived from declared supply minus one
500,000 lock commitment. It is not proof of a live spendable balance or current
market circulation.

The two treasury records contain the same economic commitments and are treated
as repeated attestations of one lock. They must not be counted as two
independent 500,000 L28 locks without stronger evidence.

## Allocation and consolidation

Sanitized allocation evidence consistently links the designated creator
identity to the historical gross allocation. No conflicting creator address
was found in the permitted artifacts.

The consolidation artifact contains 205 unique records totaling 2,018,660 L28.
It excludes the 28 L28 height-zero genesis reward.

These records do not prove the creator wallet’s live balance or spending
authority. The consolidation writer source and its execution provenance were
not recoverable within the authorized evidence boundary.

## Future mining

Public v1 code requires an accepted coinbase receiver to match its declared
miner. No automatic creator-reward routing exists.

L28 Protocol v1.0.0 does not define or enforce a canonical proof-of-work
formula. Difficulty 18 appears only in two conflicting, dormant helpers.
Neither helper is integrated with coinbase proof validation.

Mining therefore remains inactive. A proof rule must not be silently added to
the frozen v1 protocol.

## Continuity requirements

Continuation as the same L28 requires:

- no replacement genesis;
- no re-minting of historical supply;
- no copying private historical ledger files into this repository;
- explicit trusted checkpoint initialization;
- fail-closed behavior until canonical state is available;
- version-compliant miner-proof and winner authorization;
- no claim of live circulation or wallet spendability without separate proof.

## Conclusion

The audit supports preservation of the original L28 identity and historical
economic commitments. It did not create a new L28, activate a ledger, or mint
replacement supply.

Canonical continuation, live spendability, and an enforceable mining-winner
rule remain unproven and inactive.
