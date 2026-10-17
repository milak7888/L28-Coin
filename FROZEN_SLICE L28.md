# L28 — FROZEN_SLICE.md

Date: 2026-10-17
PROJECT_STATE: ACTIVE
Slice: Disposable Custody Continuity — Restart-Stable Isolated Signer

## OBJECTIVE

Take the already-working isolated non-production signer and prove that the signer can stop and restart while retaining the same disposable signer identity through an explicit test-only custody boundary.

Target:

initialize disposable custody → isolated signer starts with identity A → complete one 28 L28 paid service transaction → stop the signer process → restart the signer using the same custody directory → identity remains exactly A → replay of the original payment stays rejected → a fresh payment to identity A succeeds → the result and receipt verify → corrupt, replaced, or unsafe custody fails closed.

This slice is test-only disposable custody. It is not production custody.

## BASELINE

`16da76b59593d0505b18f9eb89e3c37c9258a4ed`

Profile: `L28-DISPOSABLE-CUSTODY-CONTINUITY001`

The caller supplies the custody directory. There is no default path and no search of the home directory, environment, keychain, wallet, SSH, browser storage, or Bitcoin Core configuration.

`CUSTODY_READINESS` stays UNRESOLVED. `RUNTIME_HARDENING` stays UNRESOLVED. `FAULT_RECOVERY` stays UNRESOLVED. `F171_SIGNER_ELIGIBILITY_RESULT` stays BLOCKED. `SIGNER_RUNTIME_ACTIVE` stays false. Production signing, broadcast, and production settlement stay false.

## STATUS

PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED

Published commit:

`522d181da436a0d936eee7b0e4d8e2e7389f51f6`

Signer identity `l28disp_adbe504225163cbd10d6ca2e3416a0f94de3a1f8e92b928c7598c973d1917a3e` was unchanged after a real signer-process restart on the same disposable custody directory.

Payment `b1cdee2cec21cae9bf1e44d2aa5710079463d6d25c4a19c6a82271c93c94bbd4` moved balances 100/0 to 72/28. Canonical validation passed. After the signer restarted, that payment was rejected and balances stayed 72/28. Fresh payment `54ec2457814cfd717250764ebf70c85ce24ff3970934f355fa27565cfcd9284b` paid the same identity, 72/28 to 44/56. The result and receipt verified.

Truncated custody, unexpected identity replacement, and unsafe permissions failed closed before signing.

Focused tests: 11 passed. Affected regressions: 73 passed. Security review: PASS. Critical/High findings: 0.

`CUSTODY_READINESS` stays UNRESOLVED. `RUNTIME_HARDENING` stays UNRESOLVED. `FAULT_RECOVERY` stays UNRESOLVED. `F171_SIGNER_ELIGIBILITY_RESULT` stays BLOCKED. `SIGNER_RUNTIME_ACTIVE` stays false. Production signing, broadcast, and production settlement stay false.

Production signing and production custody remain NOT AUTHORIZED / NOT STARTED.

## STOP

Stop after this disposable custody-continuity proof. Do not start production signing, deployment, exchange work, or REA/Bitcoin/BTCPay work.
