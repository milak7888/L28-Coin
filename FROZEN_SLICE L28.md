# L28 — FROZEN_SLICE.md

Date: 2026-10-16
PROJECT_STATE: ACTIVE
Slice: Production Entry — Durable Restart-Safe Paid AI Service

## OBJECTIVE

Take the already-working public-testnet 28 L28 AI service purchase and make the provider state survive a process restart without duplicate payment application, replay reopening, or loss of machine-readable payment evidence.

Requester
→ provider
→ quote exactly 28 L28
→ signed disposable payment
→ canonical validation
→ durable exactly-once state commit
→ useful work
→ result
→ receipt
→ provider process stops
→ provider restarts using the same test-only state directory
→ replay of the first payment is rejected
→ a fresh second transaction can complete
→ durable evidence remains consistent

This slice is not production signer activation.

## BASELINE

`d3f533b5b4e1b60d9f96ba925d08699fc247ae2d`

Operator authorization covers bounded production-entry engineering for this disposable runtime only.

It does not authorize production private keys, real custody, signer activation, production signing, canonical broadcast, mining, production settlement, deployment, a persistent public production service, external spending, exchange/listing/liquidity, Protocol v1.0 changes, or protected economics/history changes.

`CUSTODY_READINESS` stays UNRESOLVED. `F171_SIGNER_ELIGIBILITY_RESULT` stays BLOCKED. Signer runtime, signing, broadcast, and production settlement stay false.

## RUNTIME

- `network_id=L28-DISPOSABLE-PRODUCTION-ENTRY001`
- test-only disposable state
- initial balances 100/0
- price 28 L28
- first result 72/28
- explicit state directory
- no historical import
- no production secret material

## RESULT

PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED

Published commit:

`c0f5467bb2f58a2f59a47cbc2920dcb2e5b3f1a6`

The real provider process completed the 28 L28 purchase, stopped, and restarted on the same disposable state directory. Replay of payment `896222f3a3e07752e91ad9dd1b2f1edec4897b15e8b19505b6eebbad5e939b1e` was rejected and balances stayed 72/28. Fresh payment `5a008e8e2ee662c2f9079a19e7fccb0700438d8a45e2369ecab9a354f15d08ad` completed, with the original provider balance still 28.

Focused tests: 10 passed. Affected regressions: 58 passed. Security review: PASS. Critical/High findings: 0.

`RUNTIME_HARDENING` and `FAULT_RECOVERY` remain UNRESOLVED. Custody remains UNRESOLVED. Signer eligibility remains BLOCKED. Signing, broadcast, mining, and production settlement remain false.

## STOP

Stop after this bounded restart-safe runtime. Do not start production signing, deployment, or REA/Bitcoin/BTCPay work.
