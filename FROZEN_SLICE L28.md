# L28 — FROZEN_SLICE.md

Date: 2026-10-16
PROJECT_STATE: ACTIVE
Slice: Public Testnet — Internet-Reachable Paid AI Service

## OBJECTIVE

Expose exactly one existing useful L28 service across a real public internet boundary and complete one 28 L28 machine-to-machine purchase.

Remote AI/agent requester
→ public HTTPS internet endpoint
→ L28 provider
→ service request
→ quote exactly 28 L28
→ disposable signed payment
→ canonical transaction validation
→ BlocklessLedger application
→ useful structured-text work
→ signed result
→ signed machine-readable receipt
→ requester verifies result and receipt

Service remains `l28.service.structured_text_analysis/v0.1`.

Do not add a marketplace or another service.

## BASELINE

`ab108ae215ed1f27c442f0aa9a7839f040dd0a10`

Operator authorization:

`AUTHORIZE NEXT FROZEN SLICE: L28 PUBLIC TESTNET`

This authorization covers only this disposable public-testnet experiment. It does not authorize production, production keys, production settlement, mining, canonical broadcast, persistent production deployment, exchange/listing/liquidity, external spending, or Protocol v1.0 changes.

It does not change `RUNTIME_AUTHORIZED`, `NETWORK_AUTHORIZED`, `TESTNET_START_AUTHORIZED`, `SIGNING_AUTHORIZED`, `MINING_AUTHORIZED`, `BROADCAST_AUTHORIZED`, or `SETTLEMENT_AUTHORIZED`.

## IDENTITY

- `network_id=L28-DISPOSABLE-PUBLIC001`
- `data_dir_tag=l28-disposable-testnet:public001`
- initial height 0
- initial issued supply 0
- no historical checkpoint
- no historical balances
- disposable state only
- protected economics unchanged
- canonical history untouched
- production keys forbidden

## PAYMENT AND SERVICE

Price remains 28 L28. Disposable balances move 100/0 → 72/28.

Reuse the existing request, quote, payment authorization, signed transfer, `coin.tx_validation.validate_transaction`, `BlocklessLedger`, and result/receipt semantics.

Work must not execute before verified payment.

## PUBLIC INTERNET

Actual-product pass requires the requester to reach the provider through a public internet endpoint. Localhost, RFC1918, same-machine loopback, and direct LAN paths do not pass.

Prefer HTTPS. The requester must use the public HTTPS URL, not a LAN address.

Operator authorization:

`AUTHORIZE PUBLIC TESTNET BLOCKER CORRECTION: INSTALL CLOUDFLARED AND USE ONE EPHEMERAL QUICK TUNNEL`

That authorization supersedes the earlier install restriction only for `cloudflared` and one ephemeral Quick Tunnel to the localhost provider. It does not authorize a Cloudflare account, login, named tunnel, token, credential file, or persistent service install.

Do not purchase hosting, create accounts, or read secret tokens.

If `cloudflared` cannot be installed with an already-available method, stop with:

`BLOCKER=CLOUDFLARED_INSTALL_METHOD_UNAVAILABLE`

If no public `https://*.trycloudflare.com` ingress is actually used, stop actual-product verification with:

`BLOCKER=PUBLIC_TESTNET_ENDPOINT_UNAVAILABLE`

## STOP

The provider is one-shot and bounded. Stop after one bounded experiment. Do not start production.

## ACCEPTANCE

Status: STOP CONDITION REACHED

- IMPLEMENTATION — PASS
- AUTOMATED TESTS — PASS
- ACTUAL-PRODUCT VERIFICATION — PASS
- EVIDENCE — PASS
- SECURITY REVIEW — PASS
- ACCEPTANCE CRITERIA — PASS

Public endpoint:

`https://remaining-successful-springs-new.trycloudflare.com`

Payment tx id:

`c95bbee5d1e9b5d8dadf66db319099f2930bd7edc624335f3a0f4e2beec579d2`

The Surface requester and the Mac provider showed that same id. Balances moved 100/0 → 72/28. The result is PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED on remote main at commit `3fa23117aafbc1ee78c7bec0e52259008a2783ff`.
