# L28 M2M State Machine v0.1

**Document:** L28 M2M Protocol v0.1 state machine
**Status:** Specification (documentation only)
**Normative subordination:** This document is subordinate to [L28 Protocol v1.0.0](../../PROTOCOL.md) and to [protocol_v0.1.md](protocol_v0.1.md). L28 Protocol v1.0.0 prevails on conflict.

## 1. Purpose

This document defines deterministic states and permitted transitions for one M2M transaction identified by a single `transaction_id`.

Normative language follows RFC 2119 / RFC 8174 uppercase usage.

## 2. States

| State | Meaning | Terminal? |
|---|---|---|
| `requested` | Valid `service_request` accepted | No |
| `quoted` | Valid `service_quote` accepted | No |
| `authorized` | Valid `payment_authorization` accepted | No |
| `settled` | Valid `settlement_reference` independently verified against L28 | No |
| `completed` | Valid `service_receipt` accepted after settlement | Yes |
| `rejected` | Quote or request rejected before settlement | Yes |
| `expired` | Quote or authorization expired before the next required step | Yes |
| `cancelled` | Permitted cancellation before settlement | Yes |
| `failed` | Unrecoverable coordination failure without asserting L28 reversal | Yes |
| `disputed` | Conflicting authenticated completion evidence after settlement | Yes |

Terminal states MUST NOT accept further happy-path progress messages. Additional `failure_notice` messages MAY be retained as evidence but MUST NOT change a terminal state except where this document explicitly allows a move into `disputed` from `settled` or `completed` under conflicting-receipt rules.

## 3. Parties that may cause transitions

| Transition cause | Allowed party |
|---|---|
| Create `requested` | Requester via `service_request` |
| `requested -> quoted` | Provider via `service_quote` |
| `requested -> rejected` | Provider via `failure_notice` with `quote_rejected` or equivalent pre-quote refusal code, or requester cancellation where no quote exists |
| `requested -> cancelled` | Requester via `failure_notice` with `cancelled_by_sender` |
| `requested -> expired` | Either party locally when request envelope expires with no accepted quote |
| `quoted -> authorized` | Requester via `payment_authorization` |
| `quoted -> rejected` | Requester via `failure_notice` with `quote_rejected` |
| `quoted -> expired` | Either party locally when quote expires with no authorization |
| `quoted -> cancelled` | Requester via `failure_notice` with `cancelled_by_sender` |
| `authorized -> settled` | Requester or provider via verified `settlement_reference` |
| `authorized -> expired` | Either party locally when authorization expires with no verified settlement |
| `authorized -> failed` | Either party via authenticated `failure_notice` for unverifiable settlement or chain failure |
| `authorized -> cancelled` | Not permitted after authorization once settlement may be in flight; use `failed` or wait for expiry/verification outcome |
| `settled -> completed` | Provider via `service_receipt` |
| `settled -> failed` | Provider via `failure_notice` with `service_incomplete` |
| `settled -> disputed` | Either party upon detecting conflicting receipts or contradictory settlement citations |
| `completed -> disputed` | Either party upon detecting a conflicting authenticated receipt |

## 4. Required happy path

At minimum, conforming implementations MUST support:

```
requested -> quoted -> authorized -> settled -> completed
```

No implementation MAY skip `settled` and treat a receipt as complete without verified L28 settlement evidence.

## 5. Transition table

### 5.1 Into `requested`

- Trigger: valid `service_request`
- Preconditions: `transaction_id` is unused in local state
- Effects: create transaction state `requested`
- Failure: duplicate `transaction_id` or invalid envelope/payload MUST reject with no state creation

### 5.2 `requested -> quoted`

- Trigger: valid `service_quote` from provider
- Preconditions: quote references the accepted request; amount <= `max_amount`; chain valid
- Failure: invalid quote MUST leave state `requested`

### 5.3 `requested -> rejected` / `cancelled` / `expired` / `failed`

- `rejected`: provider refuses to quote, or authenticated refusal before quote acceptance
- `cancelled`: requester cancels before quote acceptance
- `expired`: request expires
- `failed`: unrecoverable validation or processing failure after state exists

### 5.4 `quoted -> authorized`

- Trigger: valid `payment_authorization` from requester
- Preconditions: quote not expired; authorized amount equals quote amount; identities consistent
- Failure: leave state `quoted`

### 5.5 `quoted -> rejected` / `expired` / `cancelled` / `failed`

- `rejected`: requester declines quote
- `expired`: `quote_expires_at` passed with no authorization
- `cancelled`: requester cancels before authorization
- `failed`: chain break or authenticated processing failure

### 5.6 `authorized -> settled`

- Trigger: valid `settlement_reference` whose L28 record independently verifies
- Preconditions:
  - authorization not expired;
  - L28 sender/receiver/amount match authorization;
  - `l28_tx_id` not already bound to a different local M2M `transaction_id`;
  - L28 source of truth available
- Failure behavior: if verification fails, state MUST remain `authorized` or move to `failed` if the failure is terminal and authenticated; state MUST NOT become `settled`

### 5.7 `authorized -> expired` / `failed`

- `expired`: authorization expires without verified settlement
- `failed`: settlement repeatedly unverifiable, chain broken, or authenticated fatal coordination error

Cancellation after authorization is NOT a silent success path. Because settlement may already be in progress in L28, M2M MUST NOT pretend cancellation reverses L28 value movement.

### 5.8 `settled -> completed`

- Trigger: valid `service_receipt` from provider
- Preconditions: receipt cites the accepted settlement; no conflicting receipt exists
- Effect: terminal success state `completed`

### 5.9 `settled -> failed`

- Trigger: provider `failure_notice` with `service_incomplete`
- Effect: terminal coordination failure after payment evidence exists
- Important: this does NOT reverse L28 settlement

### 5.10 Into `disputed`

- From `settled` or `completed` when two validly signed receipts disagree on `result_hash`, or when two verified settlement citations conflict for the same `transaction_id`
- `disputed` is terminal for v0.1 automated progression
- Resolution via escrow, arbitration, or refund is outside v0.1

## 6. Safe handling requirements

### 6.1 Quote rejection

Requester MAY reject a quote before authorization. The state MUST become `rejected`. No L28 settlement SHOULD be submitted for a rejected quote.

### 6.2 Quote expiration

If `quote_expires_at` passes with no valid authorization, state MUST become `expired`. Late authorizations MUST be rejected.

### 6.3 Authorization expiration

If `authorization_expires_at` passes with no verified settlement reference, state MUST become `expired`. Late settlement references MUST be rejected for M2M progression. Any L28 transfer that nonetheless occurred remains governed solely by L28 Protocol v1.0.0 and is outside M2M reversal authority.

### 6.4 Duplicate messages

A message whose `message_id` was already accepted MUST be ignored idempotently if byte-for-byte identical in canonical form, or rejected if the same `message_id` appears with different content. Duplicates MUST NOT advance state twice.

### 6.5 Reordered messages

Messages that do not correctly chain through `previous_message_id` MUST be rejected. Implementations MUST NOT apply out-of-order effects.

### 6.6 Repeated settlement references

- Identical replay of the same valid `settlement_reference` for the same `transaction_id` MUST be idempotent once `settled`.
- A different `transaction_id` reusing the same `l28_tx_id` MUST be rejected by parties that observe the binding.

### 6.7 Payment without service completion

State MAY remain `settled` indefinitely until receipt, failure, or dispute. M2M v0.1 does not auto-refund.

### 6.8 Service completion without valid settlement

A `service_receipt` received without prior verified `settled` state MUST be rejected. State MUST NOT become `completed`.

### 6.9 Conflicting receipts

If two authenticated receipts for one `transaction_id` disagree, state MUST become `disputed`.

### 6.10 Invalid signatures

Messages with invalid signatures MUST be rejected with no state advance. They do not create authoritative failure transitions unless an already-authenticated party emits a valid `failure_notice`.

### 6.11 Unknown transaction IDs

Except for a valid initial `service_request`, messages that refer to an unknown `transaction_id` MUST be rejected.

## 7. Idempotency and determinism

For a given local input sequence of accepted messages, the resulting state MUST be deterministic.

Processors MUST key idempotency on at least:

- `transaction_id`
- `message_id`
- bound `l28_tx_id` when present

## 8. Interaction with L28 settlement truth

State names `authorized`, `settled`, and `completed` are M2M coordination states.

- `authorized` means permission to attempt L28 settlement, not that value moved.
- `settled` means an L28 record was independently verified.
- `completed` means the provider asserted completion after that verification.

No M2M state transition creates, burns, locks, unlocks, or reverses L28 units.
