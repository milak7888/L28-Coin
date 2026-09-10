# Foundation 171 — Signer and Economic-Control Eligibility Gate v0.1

## Result

**PASS 5 / GAP 0 / BLOCKED 0 — commit-ready.**

Foundation170 remaining-boundary work selected `OPTION_B` inside this F171 state only. The committed F170 artifacts remain `PENDING_OPERATOR_SELECTION`. F171 records `F170_OPERATOR_SELECTION=OPTION_B` as a development-direction fact and evaluates a fail-closed, non-activating signer/economic-control eligibility gate against the existing Foundation117-122 public contracts.

The committed production evidence is unresolved. No production clock, audit backend, custody implementation, runtime hardening, or fault/recovery evidence exists. The canonical committed result is therefore `F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED`.

Eligibility is not authorization, not validation, and not invocation. The gate never signs, broadcasts, settles, mints, loads keys, or calls `coin.tx_validation.validate_transaction`.

## Gate behavior

Canonical results are exactly:

- `ELIGIBLE_FOR_FUTURE_SIGNER_AUTHORIZATION_REVIEW`
- `NOT_ELIGIBLE`
- `BLOCKED`

Missing, malformed, stale, contradictory, unavailable, or unauthorized required evidence fails closed. Duplicate request or idempotency identities cannot become eligible twice. Cumulative approved spend is checked before any accept-state record. Unresolved custody, runtime hardening, or fault/recovery evidence remains `BLOCKED`.

A complete test-local evidence bundle may project `ELIGIBLE_FOR_FUTURE_SIGNER_AUTHORIZATION_REVIEW` only when backends are labeled `TEST_LOCAL_EVIDENCE_CONTRACT_ONLY` and readiness evidence is explicitly resolved with `keys_loaded=false`. That projection is not production readiness and does not activate a signer.

## Preserved security rules

L28 Protocol v1.0.0 remains frozen. Coinbase-only issuance, canonical validator authority, immutable economics and history, and the Bitcoin external-evidence-only boundary remain unchanged.

Exact protected facts:

- hard cap 28,000,000
- emission ceiling 11,130,000
- historically mined 2,824,584
- treasury locked 500,000
- circulating snapshot 2,324,584
- halving interval 210,000
- rewards 28 → 14 → 7 → 3 → 1 → 0
- historical mined-through 100,877
- next canonical height 100,878

The signer/economic-control layer has zero authority over issuance, supply, height, consensus, history, ledger rules, settlement rules, or Bitcoin. Canonical transaction validity remains `coin.tx_validation.validate_transaction`.

## Independent security review

| Review item | Result | Evidence |
|---|---|---|
| Fail-closed eligibility, no overclaim | PASS | Committed state is `BLOCKED`; production time/audit backends remain `UNRESOLVED`. |
| No hidden activation | PASS | `F171_SIGNER_RUNTIME_ACTIVE=false`, `F171_SIGNING=false`, `F171_BROADCAST=false`, `F171_SETTLEMENT=false`. |
| Protocol firewall preserved | PASS | Eligibility cannot mint, sign, broadcast, settle, or bypass `validate_transaction`. |
| F170 selection isolation | PASS | `F170_OPERATOR_SELECTION=OPTION_B` is recorded only in F171; F170 committed files are unchanged. |
| Authority and secrets remain closed | PASS | No key load, wallet, RPC, seed, or production-secret access; `F171_PROTOCOL_AUTHORITY=false`. |

## Current state

- `F170_OPERATOR_SELECTION=OPTION_B`
- `F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED`
- `F171_SIGNER_RUNTIME_ACTIVE=false`
- `F171_SIGNING=false`
- `F171_BROADCAST=false`
- `F171_SETTLEMENT=false`
- `F171_PROTOCOL_AUTHORITY=false`
