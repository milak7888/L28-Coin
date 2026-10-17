# L28 — DEFER.md

Last updated: 2026-10-17

Purpose:
Store useful ideas and future work that are NOT required to complete the current frozen slice.

Nothing in this file is automatically approved.
Review only when selecting the next frozen slice.

## CURRENT SLICE — DO NOT DUPLICATE HERE
The completed frozen slice is:

**Isolated Non-Production Signer Runtime**

Status: PASS / ACTUAL-PRODUCT VERIFIED. STOP CONDITION REACHED.

Disposable signing runs in a separate localhost process. Production signing, custody, deployment, and settlement remain NOT AUTHORIZED / NOT STARTED. `SIGNER_RUNTIME_ACTIVE` remains false. `F171_SIGNER_ELIGIBILITY_RESULT` remains BLOCKED.

## COMPLETED PRODUCT STAGES — NOT DEFERRED
Already complete/published:

1. disposable offline L28 transfer
2. two-agent useful service transaction
3. HTTP/JSON + MCP external access
4. cross-AI interoperability
5. isolated local network
6. limited testnet — two-node private-network paid service
7. public testnet — internet-reachable paid AI service
8. production entry — durable restart-safe paid AI service
9. production runtime hardening and fault recovery

Do not recreate these as new milestones.

## WEB RESEARCH SERVICE — FUTURE
A later useful service may perform bounded web research and return structured JSON.

This is deferred because the current slice intentionally proves the purchase loop without external network/API dependencies.

When authorized later:
- make external networking explicit
- bound domains/time/resource use
- distinguish service web access from L28 settlement authority
- keep payment validation local/canonical

## NETWORKING — FUTURE AUTHORIZATION
The limited two-node private-network transaction is complete and is not deferred.

The public-testnet experiment is complete and is not deferred.

Still deferred:

- broader controlled peer communication
- persistent P2P runtime
- production deployment
- production signing and settlement
- REA, Bitcoin Core, and BTCPay study

Production remains NOT AUTHORIZED. Do not treat localhost or LAN evidence as this public-testnet result.

## PRODUCTION — FUTURE
- real custody architecture
- production signer
- production key lifecycle
- production runtime hardening gate — remains UNRESOLVED
- production fault/recovery gate — remains UNRESOLVED
- production monitoring
- deployment
- production settlement
- operator/user wallet experience

Do not pull production controls into disposable execution unless genuinely required for the current safety boundary.

`F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED` remains a production signer condition and does not invalidate authorized disposable test-only slices.

## MARKET / ECOSYSTEM — FUTURE
- service marketplace
- provider reputation
- agent service catalogs
- dynamic pricing
- escrow/dispute concepts
- broader developer ecosystem
- third-party service providers
- exchange/listing/liquidity work
- token-price/speculation work

Utility comes before speculation.

## OPTIONAL PRODUCT IDEAS
Possible later L28-paid machine services:
- bounded web research
- structured data extraction
- document analysis
- inference/model access
- API access
- verification/scoring
- automation
- specialized agent tasks
- data transformation
- compute/storage access

Do not broaden the current slice to include them.

## DEFERRED ENGINEERING
Unless a frozen acceptance criterion requires them:
- new test frameworks
- new evaluator frameworks
- generic readiness gates
- broad governance layers
- speculative abstractions
- unnecessary refactors
- duplicate APIs
- replacement of existing UAII/MCP/REST/SDK work
- documentation-only foundations
- evidence inventories that leave user-visible capability unchanged
- new signer-readiness programs unrelated to current disposable execution

## STRATEGIC LOOP RULE
If proposed work would create another document/gate whose result is still the same top-level blocker without producing a new runnable capability, leave it deferred.

The active work must change what L28 can actually DO.

## CURRENT FROZEN-SLICE RULE
The Isolated Non-Production Signer Runtime slice has reached its stop condition.

Production signing, custody, deployment, and settlement remain NOT AUTHORIZED / NOT STARTED. `SIGNER_RUNTIME_ACTIVE` remains false. REA, Bitcoin Core, and BTCPay study remain deferred.
