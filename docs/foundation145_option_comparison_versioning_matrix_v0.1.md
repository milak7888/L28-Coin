# Foundation 145 - Confirmation/Reorg Option and Versioning Matrix v0.1

| Option | Initial recommendation | Automatic reorg | New numeric threshold | New fork-choice semantics | Current classification |
|---|---|---:|---:|---:|---|
| A - Halt on conflict | YES | No | No | No winner selected | Safest candidate for explicit selection |
| B - Bounded reorg | No | Yes | Required | Required | Requires additional consensus decisions |
| C - Finality floor | No | Possible | Required | Required | Requires additional consensus decisions |

## Option A

Cdidate conflict action:
`HALT_SYNC_AND_RETAIN_CURRENT_LOCAL_CANONICAL_STATE`

Candidate resume rule:
`RESUME_ONLY_AFTER_GOVERNED_DETERMINISTIC_RESOLUTION_RULE`

Confirmation semantics:
`NO_CONFIRMATION_CLAIM`

Finality semantics:
`NO_NEW_FINALITY_CLAIM`

Operator discretionary fork choice:
`FORBIDDEN`

Option A may be used as a non-normative fail-closed implementation boundary
without changing frozen economic or transaction-validation invariants.

Normative protocol adoption still requires an explicit governed
compatibility/versioning decision.

## Options B and C

Both require new deterministic consensus semantics before implementation,
including values or rules that Foundation 144 intentionally left undefined.

Neither is selected or implemented by Foundation 145.
