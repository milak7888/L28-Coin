# L28 — FROZEN_SLICE.md

Date: 2026-10-17
PROJECT_STATE: ACTIVE
Slice: Isolated Non-Production Signer Runtime

## OBJECTIVE

Run disposable signing in a separate localhost process from payment validation and durable state.

The signer holds one in-memory key, signs only the existing disposable service artifacts, and does not become consensus, custody, or settlement authority.

## BASELINE

`6dc5c4bbdf33ee94a952afdc7301ff10192bac1c`

This authorization does not authorize production private keys, real custody, production signer activation, production signing, canonical broadcast, mining, production settlement, deployment, or Protocol v1.0 changes.

`CUSTODY_READINESS` stays UNRESOLVED. `RUNTIME_HARDENING` stays UNRESOLVED. `FAULT_RECOVERY` stays UNRESOLVED. `F171_SIGNER_ELIGIBILITY_RESULT` stays BLOCKED. `SIGNER_RUNTIME_ACTIVE` stays false. Production signing, broadcast, and production settlement stay false.

## RESULT

PASS / ACTUAL-PRODUCT VERIFIED

Payment `eab61398b14764be20044ac4f0c32a8d4f1b1da60626d2f79c73b808061557c5` moved balances 100/0 to 72/28. After the payment process restarted against the same signer, that payment was rejected and balances stayed 72/28. Fresh payment `844b6e882adc77846ee2deb2fbb0b093e68c1610625d9edde46a7bc467eea877` paid the same signer identity, 72/28 to 44/56.

The key was not written. Canonical validation still ran in the payment process.

Focused tests: 3 passed. Affected regressions: 103 passed. Security review: PASS. Critical/High findings: 0.

## STOP

Stop after this isolated disposable signer. Do not start production signing, deployment, or REA/Bitcoin/BTCPay work.
