# L28 — FROZEN_SLICE.md

Date: 2026-10-18
PROJECT_STATE: ACTIVE
Slice: Public-Testnet Discoverable Release Candidate v0.1

## OBJECTIVE

Create one self-describing, versioned NON-PRODUCTION public-testnet release
candidate from the already-published one-shot paid-service implementation.

This slice adds machine-readable discovery and reproducible release packaging.
It does not deploy, expose public networking, integrate EVD-001, or change the
existing payment, validation, result, receipt, or replay authority paths.

## BASELINE

`b2674aff02f67da002442a87f3ff739c73563d11`

Release candidate: `l28-public-testnet-v0.1.0-rc1`

Network identity: `L28-DISPOSABLE-PUBLIC001`

## DELIVERABLE

- machine-readable `GET /v1/l28/public-testnet/services` discovery;
- exact service ID, 28 L28 price, network/profile, limits, and session paths;
- requester validation of discovery before quote or payment;
- HTTP/JSON access instructions and accurate existing local-only MCP stdio
  instructions;
- one executable end-to-end example;
- a versioned release manifest, SHA-256 inventory, deployment boundary, and
  rollback plan;
- explicit NON-PRODUCTION DISPOSABLE TESTNET designation.

Authorized paths:

- `FROZEN_SLICE L28.md`
- `SYSTEM_STATE L28.md`
- `README.md`
- `coin/public_testnet_service_demo.py`
- `tests/test_public_testnet_service_demo.py`
- `docs/public_testnet_release_v0.1.md`
- `release/public-testnet-v0.1.0-rc1/manifest.json`
- `release/public-testnet-v0.1.0-rc1/SHA256SUMS`

## ACCEPTANCE CRITERIA

1. Discovery returns one exact service catalog entry for
   `l28.service.structured_text_analysis/v0.1` priced at 28 disposable L28.
2. The requester validates the catalog before provider hello, request, quote,
   payment, work, result, or receipt processing.
3. Missing, malformed, inconsistent, or tampered discovery fails before
   payment; invalid payment and replay continue to fail closed.
4. The actual local provider/requester product completes:
   DISCOVER → REQUEST → QUOTE → PAY → VERIFY → WORK → RECEIPT.
5. Existing canonical transaction validation, result verification, signed
   receipt verification, and replay rejection remain unchanged.
6. HTTP/JSON instructions and one executable example are exact. MCP guidance
   accurately describes the existing stdio-only local adapter and makes no
   public-network claim.
7. The v0.1.0-rc1 manifest and SHA-256 inventory reproduce the authorized
   release artifacts.
8. Focused tests, directly affected regressions, adversarial checks,
   `git diff --check`, and one consolidated security review pass with no
   unresolved Critical/High implementation findings.
9. Protocol v1.0.0, protected economics/history, production custody, F171, and
   all production gates remain unchanged and blocked.

## SAFETY BOUNDARY

No external networking, public ingress, deployment, provider/account mutation,
external spending, secret access, production keys, production custody, mining,
broadcast, settlement, merge, or push.

Do not integrate or modify EVD-001. Do not create a networked MCP server, a new
payment validator, a second payment engine, or another authority path.

All executable verification is local, disposable, bounded, and non-production.
Public HTTPS exposure requires separate explicit operator authorization.

## STOP

After implementation, focused/adversarial tests, directly affected regressions,
actual local product verification, consolidated security review, reproducible
release evidence, `SYSTEM_STATE L28.md` update, exact-path staging, and one
local commit, stop. Do not merge, push, deploy, or open public networking.
