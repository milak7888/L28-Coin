# L28 M2M Transcript Validation v0.1

**Document:** L28 M2M Offline Exchange Transcript Validator v0.1
**Status:** Offline verify-only coordination validation (Foundation 6)
**Normative subordination:** This document is subordinate to [L28 Protocol v1.0.0](../../PROTOCOL.md) and to [protocol_v0.1.md](protocol_v0.1.md). L28 Protocol v1.0.0 prevails on conflict.
**Related:** [state_machine.md](state_machine.md), [message_schema_v0.1.md](message_schema_v0.1.md), [interoperability_profile_v0.1.md](interoperability_profile_v0.1.md), [test_vectors_transcript_v0.1.json](test_vectors_transcript_v0.1.json)

## 1. Purpose

Foundation 6 defines offline validation of a complete ordered exchange of already-signed M2M envelopes for one `transaction_id`.

Runtime: `coin/m2m_transcript_validator.py`.

This milestone:

- verifies transcripts only;
- reuses Foundation 5 envelope verification;
- MUST NOT sign, spend, submit transactions, query a ledger, or operate a network;
- MUST NOT create a wallet, persistent replay database, or deployment surface.

Successful validation proves coordination-consistency of a signed message sequence under M2M v0.1. It does NOT prove service delivery, L28 transfer acceptance, irreversible finality, or settlement completion.

## 2. Public API

- `verify_transcript(envelopes, *, require_terminal=False) -> TranscriptResult`
- `verify_transcript_json(raw, *, require_terminal=False) -> TranscriptResult`

`verify_transcript_json` is the primary untrusted-input boundary and accepts one JSON array of envelope objects under the shared L28-M2M JSON profile (duplicate-key detection, no floats/NaN/Infinity, safe integers, no lone surrogates).

Transcript length is bounded by `MAX_TRANSCRIPT_MESSAGES = 64`. Empty transcripts reject.

Validation is deterministic, does not mutate caller envelopes, performs no filesystem writes, and retains no state after returning.

## 3. Participants and roles

Participants are inferred from the verified `service_request`:

| Role | Meaning |
|---|---|
| Requester / payer | `service_request` sender |
| Provider / payee | `service_request` recipient |

Documented message directions:

| Message | Allowed sender |
|---|---|
| `service_request` | Requester |
| `service_quote` | Provider |
| `payment_authorization` | Requester |
| `settlement_reference` | Requester **or** Provider ([protocol_v0.1.md](protocol_v0.1.md) §5.4) |
| `service_receipt` | Provider |
| `failure_notice` | Requester or Provider, only for transitions authorized by [state_machine.md](state_machine.md) |

## 4. Chain requirements

- Exchange identity field: `transaction_id` (constant for the transcript)
- Linkage field: `previous_message_id`
- First message MUST be `service_request` with `previous_message_id = null`
- Each later `previous_message_id` MUST equal the immediately preceding verified `message_id`
- `message_id` values MUST be unique
- Replays, reorders, and omitted intermediate messages reject
- No envelope may follow a terminal state

## 5. State machine

Nonterminal: `requested`, `quoted`, `authorized`, `settled`
Terminal: `completed`, `rejected`, `expired`, `cancelled`, `failed`, `disputed`

Happy path:

```
service_request → requested
service_quote → quoted
payment_authorization → authorized
settlement_reference → settled
service_receipt → completed
```

Partial transcripts (`require_terminal=False`) may succeed in a nonterminal state.
`require_terminal=True` rejects nonterminal endings with `incomplete_transcript`.

`failure_notice` may enter only a documented terminal state for the current state and authorized sender. It does not reverse L28 settlement. `disputed` does not imply refund or reversal.

## 6. Amount and citation consistency

Exact integers only. Across the chain:

- quote amount is positive and ≤ request `max_amount`
- authorization references the quote and equals quoted amount
- settlement cites the authorization, payer/payee identities, and amount
- L28 transaction ID recomputes through Foundation 5 citation verification
- receipt references the exact settlement message and L28 transaction ID

The validator verifies citation consistency only. It does not query balances or a ledger and does not claim acceptance or finality.

## 7. Nonces and time order

Within one transcript:

- each sender MUST NOT reuse a nonce (exact string equality)
- `created_at` values MUST be monotonically nondecreasing
- a later envelope with `created_at` greater than the prior envelope `expires_at` rejects
- fixture timestamps are not compared to wall-clock time

## 8. Stable result codes

Success: `ok`

Input: `invalid_json`, `duplicate_key`, `transcript_not_array`, `empty_transcript`, `transcript_too_large`, `transcript_element_not_object`

Envelope: `envelope_verification_failed`

Identity/chain: `exchange_id_mismatch`, `first_message_not_request`, `invalid_first_previous_message`, `message_chain_broken`, `duplicate_message_id`, `duplicate_nonce`, `timestamp_regression`, `prior_message_expired`, `participant_mismatch`, `role_mismatch`

State: `invalid_transition`, `message_after_terminal`, `incomplete_transcript`, `invalid_terminal_state`, `unauthorized_terminal_transition`

Economics/citations: `quote_reference_mismatch`, `amount_mismatch`, `service_terms_mismatch`, `settlement_participant_mismatch`, `settlement_citation_invalid`, `receipt_reference_mismatch`

## 9. Test vectors

Deterministic public fixtures: [test_vectors_transcript_v0.1.json](test_vectors_transcript_v0.1.json).

All vectors are `test_only`, `live: false`, `accepted_settlement: false`, and `private_material_committed: false`.
