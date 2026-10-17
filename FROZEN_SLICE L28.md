# L28 — FROZEN_SLICE.md

Date: 2026-10-17
PROJECT_STATE: ACTIVE
Slice: Production Runtime Hardening and Fault Recovery

## OBJECTIVE

Harden the disposable restart-safe 28 L28 payment runtime so a real provider process fails closed on unsafe state and still completes a fresh purchase after a clean restart.

This slice does not resolve the production signer gates.

## BASELINE

`b3c5dd1f0321e07c12ac874311b47d912ff7e9e4`

Operator authorization covers bounded hardening and fault recovery for the existing disposable runtime.

It does not authorize production private keys, real custody, signer activation, production signing, canonical broadcast, mining, production settlement, deployment, a persistent public production service, external spending, exchange/listing/liquidity, Protocol v1.0 changes, or protected economics/history changes.

No production rate, skew, timeout, or topology values are invented. `F122-G07`, `F122-G08`, and the unresolved LSOD-OPS gaps stay unresolved.

`CUSTODY_READINESS` stays UNRESOLVED. `RUNTIME_HARDENING` stays UNRESOLVED. `FAULT_RECOVERY` stays UNRESOLVED. `F171_SIGNER_ELIGIBILITY_RESULT` stays BLOCKED. Signer runtime, signing, broadcast, and production settlement stay false.

## RUNTIME

- same disposable profile `L28-DISPOSABLE-PRODUCTION-ENTRY001`
- owner-only state directory and state files
- hash-chained local audit
- monotonic local payment timestamp
- bounded JSON depth and node count
- stale database inside the same directory fails closed
- corrupt or truncated state fails closed

## RESULT

PASS / ACTUAL-PRODUCT VERIFIED

Real process payment `103c4f35033ba784488b2b9e1b81dcff4415ef621cf7054b1444f1bf0e1024dd` moved balances 100/0 to 72/28. After restart, that payment was rejected and balances stayed 72/28. Fresh payment `3c8cf49e8f6e7efa59d95872eda0e738ecffcb241f21c5cb2a962950ec8c4650` completed, with the original provider balance still 28.

Real process probes rejected loose permissions, a rolled-back database, and a corrupt database before service execution.

Focused tests: 13 passed. Affected regressions: 116 passed. Security review: PASS. Critical/High findings: 0.

`RUNTIME_HARDENING` and `FAULT_RECOVERY` remain UNRESOLVED. Custody remains UNRESOLVED. Signer eligibility remains BLOCKED.

## STOP

Stop after this bounded hardening slice. Do not start production signing, deployment, or REA/Bitcoin/BTCPay work.
