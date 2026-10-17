# L28 — SYSTEM_STATE.md

Last updated: 2026-10-16

## PROJECT STATE
PROJECT_STATE: ACTIVE

Only the operator may change PROJECT_STATE.

## PRODUCT DIRECTION
L28 is being built toward a functional machine-to-machine AI payment use case.

North-star flow:

DISCOVER → REQUEST → QUOTE → PAY → WORK → VERIFY → RECEIPT → REUSE

Product path:

1. disposable offline L28 transfer — COMPLETE/PUBLISHED
2. two-agent useful service transaction — COMPLETE/PUBLISHED
3. HTTP/JSON + MCP external access — COMPLETE/PUBLISHED
4. cross-AI interoperability — COMPLETE/PUBLISHED
5. isolated local network — COMPLETE/PUBLISHED
6. limited testnet — PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED
7. public testnet — PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED
8. production entry — durable restart-safe paid AI service — PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED
9. production runtime hardening and fault recovery — PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED
10. isolated non-production signer runtime — PASS / ACTUAL-PRODUCT VERIFIED

## REPOSITORY
Local: `/Users/pjaydondup/Projects/L28-Coin`
Remote: `https://github.com/milak7888/L28-Coin.git`
Public: `milak7888/L28-Coin`

Latest independently verified remote `main`:

`cb20eec3110dfa5a26b06736ef8c4e8bc6748482`

Commit:

`Implement isolated local network service transaction`

Parent:

`91297fabd134b196049204f2b4d966f98bd139dc`

Changed paths in that commit:

- `SYSTEM_STATE L28.md`
- `coin/isolated_local_network_service_demo.py`
- `tests/test_isolated_local_network_service_demo.py`
## CANONICAL PROTOCOL
L28 Protocol v1.0.0 is frozen.

Canonical validator:

`coin.tx_validation.validate_transaction`

Core invariants:

- coinbase-only issuance
- no admin/governance/manual/discretionary mint
- canonical height comes from consensus state only
- missing required state fails closed
- no subsystem/operator override of issuance, supply, validation, height, consensus, history, or settlement
- same public validation rules for all

## PROTECTED ECONOMICS
Immutable:

- hard cap: 28,000,000 L28
- emission ceiling: 11,130,000 L28
- historically mined: 2,824,584 L28
- treasury locked: 500,000 L28
- circulating snapshot: 2,324,584 L28
- halving interval: 210,000
- rewards: 28 → 14 → 7 → 3 → 1 → 0
- historical mined-through: 100,877
- next canonical height: 100,878

Historical ledger/allocation/wallet/genesis/hash/snapshot/supply records are immutable.

Disposable test state is never canonical history.

## WORKING CAPABILITY — DISPOSABLE OFFLINE TRANSFER
Published capability:

`python -m coin.disposable_offline_transfer_demo`

Verified behavior:

- creates disposable in-memory Ed25519 participants
- Alice begins with 100 disposable L28
- Bob begins with 0 disposable L28
- signs a 28 L28 transfer
- calls `coin.tx_validation.validate_transaction`
- applies state through `BlocklessLedger.add_transaction`
- Alice becomes 72
- Bob becomes 28
- invalid signature rejected
- replay rejected
- insufficient balance rejected
- malformed amount rejected
- rejected transfers do not mutate disposable balances
- issued supply remains untouched
- canonical history remains untouched
- no public network is used
- no production keys are used

Automated verification for that slice:

- focused disposable-transfer tests: 10 passed
- protocol conformance: 42 passed

Slice result:

PASS and published to remote `main`.

## WORKING CAPABILITY — TWO-AGENT USEFUL SERVICE TRANSACTION
Published capability:

`python -m coin.two_agent_service_transaction_demo --input "L28 enables machine payments between autonomous systems."`

Service:

`structured_text_analysis`

Verified end-to-end behavior:

- Agent A creates a signed service request
- Agent B creates a signed quote for exactly 28 L28
- Agent A creates an actual disposable signed L28 payment
- payment passes the canonical validation path
- payment executes through the existing disposable ledger path
- Agent A balance changes 100 → 72
- Agent B balance changes 0 → 28
- Agent B independently verifies request/quote/payment/party/amount binding
- useful work executes only after successful payment verification
- deterministic structured-text result is returned and independently verifiable
- signed machine-readable receipt is produced and verifies using public material
- invalid signature/replay/wrong amount/wrong party/quote mismatch fail closed
- failed payment does not execute work
- tampered result/receipt fail closed
- canonical history remains untouched
- protected economics remain unchanged
- no production keys are used

Automated verification:

- focused two-agent transaction tests: 10 passed
- affected regressions: 52 passed

Published commit:

`90d6ec4b16c44f30f69d6cd7d90c9238fb3aa2e7`

Slice result:

PASS and published to remote `main`.

## WORKING CAPABILITY — HTTP/JSON + MCP EXTERNAL ACCESS
Published capability:

`python -m coin.two_agent_service_external_access_demo --input "L28 enables machine payments between autonomous systems."`

Service:

`l28.service.structured_text_analysis/v0.1`

Verified HTTP/JSON behavior:

- real local HTTP runtime exists
- hard-bound to `127.0.0.1`
- purchase endpoint:
  `POST /v1/l28/services/structured_text_analysis/purchase`
- separate local caller crosses the actual loopback HTTP runtime boundary
- successful purchase returns HTTP 200
- 28 L28 payment semantics are preserved
- useful work and signed receipt are verified
- malformed/unsupported input fails closed

Verified MCP behavior:

- real local MCP runtime exists as a separate process
- transport is stdio only
- purchased-service tool:
  `l28_purchase_structured_text_analysis`
- separate caller crosses the actual MCP stdio runtime boundary
- same 28 L28 purchase semantics are preserved
- useful work and signed receipt are verified
- malformed/unsupported protocol/tool input fails closed
- MCP creates no network listener

Shared verified behavior:

- both transports delegate to the same two-agent transaction core
- no duplicate payment validator
- no duplicate payment engine
- disposable balance semantics remain `100/0 → 72/28`
- stable service/payment semantics are equivalent
- canonical history remains untouched
- no production keys
- no production settlement

Automated verification:

- focused HTTP/MCP tests: 11 passed
- affected regressions: 27 passed

Published commit:

`4016cd180643c515865438575ad603d60b54c6e2`

Slice result:

PASS and published to remote `main`.

## WORKING CAPABILITY — CROSS-AI INTEROPERABILITY
Published capability:

`python -m coin.cross_ai_interoperability_demo --input "L28 enables machine payments between autonomous systems."`

This capability proves provider-format interoperability using two distinct AI-provider request shapes while preserving one L28 purchase core.

### OpenAI-Compatible Path

Verified behavior:

- accepts an OpenAI-compatible function/tool-call shape
- tool name:
  `l28_purchase_structured_text_analysis`
- provider request id is preserved in evidence
- adapter validates bounded JSON arguments
- delegates through the existing real HTTP/JSON L28 runtime
- does not call the two-agent core directly
- receives exactly 28 L28 quote semantics
- payment is applied and verified
- useful service executes
- result and signed receipt verify

Actual-product evidence:

- `openai_compatible_call=true`
- `openai_provider_request_id=call_001`
- `openai_transport=http_json`
- `openai_external_call=true`
- `openai_purchase_verified=true`
- `openai_quoted_amount=28`
- `openai_payment_verified=true`
- `openai_service_executed=true`
- `openai_receipt_verified=true`

### Anthropic-Compatible Path

Verified behavior:

- accepts an Anthropic-compatible `tool_use` shape
- tool name:
  `l28_purchase_structured_text_analysis`
- provider request id is preserved in evidence
- adapter validates bounded input
- delegates through the existing real MCP stdio L28 runtime
- does not call the two-agent core directly
- receives exactly 28 L28 quote semantics
- payment is applied and verified
- useful service executes
- result and signed receipt verify

Actual-product evidence:

- `anthropic_compatible_call=true`
- `anthropic_provider_request_id=toolu_001`
- `anthropic_transport=mcp_stdio`
- `anthropic_external_call=true`
- `anthropic_purchase_verified=true`
- `anthropic_quoted_amount=28`
- `anthropic_payment_verified=true`
- `anthropic_service_executed=true`
- `anthropic_receipt_verified=true`

### Cross-Provider Equivalence

Verified:

- both paths purchase the same L28 service
- both preserve price = 28 L28
- both preserve the same canonical validation/payment semantics
- both preserve `100/0 → 72/28`
- deterministic service output is equivalent for the same input
- both verify result and signed receipt
- `same_l28_service=true`
- `same_l28_core_transaction=true`
- `stable_semantics_equivalent=true`
- `service_output_equivalent=true`
- `canonical_history_touched=false`
- `public_network_used=false`
- `live_provider_api_used=false`
- `provider_credentials_used=false`
- `provider_billing_used=false`
- `production_keys_used=false`
- `production_settlement=false`

Important boundary:

This slice proves OpenAI-compatible and Anthropic-compatible request-format interoperability only.

It does NOT claim that live OpenAI or Anthropic commercial APIs/models were contacted.

No live provider API, provider credentials/API keys, or provider billing/spending were used.

Automated verification:

- focused cross-AI tests: 10 passed
- affected regressions: 38 passed

Actual-product verification:

- OpenAI-compatible path: PASS
- Anthropic-compatible path: PASS
- cross-provider semantic equivalence: PASS
- observable evidence: PASS

Consolidated security review:

- OpenAI path reuses existing HTTP runtime: PASS
- Anthropic path reuses existing MCP runtime: PASS
- caller amount override: rejected
- direct core bypass: false
- duplicate payment validator: false
- live provider API used: false
- provider credential access: false
- unresolved Critical/High findings: 0

Published commit:

`b64dad0dbc14c7a5732fcc1b9ff34079152b38b2`

Slice result:

PASS and published to remote `main`.

The Cross-AI Interoperability frozen slice has reached its STOP condition.

## EXISTING INTEROPERABILITY / M2M FOUNDATION
Existing repository surfaces include:

- M2M message/profile work
- service request/quote/payment authorization/settlement reference/service receipt concepts
- UAII / universal AI access
- REST/OpenAPI work
- MCP work
- Python SDK
- TypeScript SDK
- quote/payment/receipt validation surfaces
- canonical JSON rules
- signed-receipt primitives
- transaction-validation delegation to the canonical validator

Known UAII operations include:

- `discover_capabilities`
- `get_protocol_status`
- `get_balance`
- `create_quote`
- `create_unsigned_payment_request`
- `validate_payment`
- `get_payment_receipt`
- `verify_signed_receipt`

## CURRENT PRODUCTION SIGNER / CUSTODY STATE
Production signer/custody remains unresolved.

Recorded production-level restrictions remain:

- `CUSTODY_READINESS=UNRESOLVED`
- `RUNTIME_HARDENING=UNRESOLVED`
- `FAULT_RECOVERY=UNRESOLVED`
- `F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED`
- `SIGNER_RUNTIME_ACTIVE=false`
- `BROADCAST=false`
- production `SETTLEMENT=false`

The completed disposable, two-agent, HTTP/MCP, cross-AI, testnet, and restart-safe payment capabilities do NOT make a production signer eligible.

The disposable restart-safe runtime and the later hardening slice do not change these production gates. `RUNTIME_HARDENING` and `FAULT_RECOVERY` remain UNRESOLVED.

## ASSURANCE MODEL
`ASSURANCE_MODEL=OPEN_SOURCE_PUBLIC_REVIEW`

`NOT_INDEPENDENTLY_AUDITED=true`

No paid or independent audit is claimed for the completed slices.

Known Critical/High findings involving secret exposure, unauthorized signing, Protocol bypass, arbitrary minting, supply/history mutation, validation bypass, or unauthorized production settlement block the affected capability.

## BITCOIN
Bitcoin is external evidence only.

Bitcoin has zero authority over L28 issuance, supply, canonical height, validation, consensus, history, or settlement.

Observation ≠ settlement.

## WORKING CAPABILITY — ISOLATED LOCAL NETWORK
Published capability:

`python -m coin.isolated_local_network_service_demo --input "L28 enables machine payments between autonomous systems."`

Service:

`l28.service.structured_text_analysis/v0.1`

Verified:

- exactly two child agent processes
- IPv4 TCP loopback only on `127.0.0.1`
- request, 28 L28 quote, payment, result, and receipt cross TCP
- canonical validator reused
- `BlocklessLedger` reused
- balances transition 100/0 → 72/28
- work executes only after verified payment
- Agent A verifies result and receipt
- both processes terminate and sockets close
- canonical history untouched
- no public network
- no production keys
- no production settlement

Automated verification:

- focused tests: 10 passed
- affected regressions: 41 passed

Actual-product verification: PASS

Security review: PASS

Unresolved Critical/High findings: 0

Published commit:

`cb20eec3110dfa5a26b06736ef8c4e8bc6748482`

Slice result:

PASS and published to remote `main`.

## WORKING CAPABILITY — LIMITED TESTNET
Verified capability:

`python -m coin.limited_testnet_service_demo --role provider --requester-host 192.168.1.129 --provider-host 192.168.1.138 --port 28428`

`python -m coin.limited_testnet_service_demo --role requester --requester-host 192.168.1.129 --provider-host 192.168.1.138 --port 28428`

Service:

`l28.service.structured_text_analysis/v0.1`

Network identity:

`L28-DISPOSABLE-LIMITED001`

Verified two-host behavior:

- requester `192.168.1.129`
- provider `192.168.1.138:28428`
- distinct explicit RFC1918 endpoints
- signed request, quote for exactly 28 L28, disposable payment, result, and receipt
- canonical validator reused
- `BlocklessLedger` reused
- payment tx id `cf1e700befd46e413218af74120f1edbb3140c11a830b0078ca8d52d5881a537`
- balances transition 100/0 → 72/28
- requester verified the result and the receipt
- duplicate payment rejected with `reason=replay`
- original payment remained applied exactly once
- balances remained 72/28 after replay rejection
- canonical history untouched
- historical state not imported
- no public network
- no production keys
- no mining
- no broadcast
- no production settlement
- sockets closed

Automated verification:

- focused tests: 9 passed
- affected regressions: 52 passed

Actual-product verification: PASS

Security review: PASS

Unresolved Critical/High findings: 0

Identity-module flags `RUNTIME_AUTHORIZED`, `NETWORK_AUTHORIZED`, `TESTNET_START_AUTHORIZED`, `SIGNING_AUTHORIZED`, `MINING_AUTHORIZED`, `BROADCAST_AUTHORIZED`, and `SETTLEMENT_AUTHORIZED` stay false.

Slice result:

PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED

The Limited Testnet frozen slice reached its STOP condition and is published on remote main at commit `586362ef17138e8e82ddfa4ac954e3f54d33ea9d`.

## WORKING CAPABILITY — PUBLIC TESTNET
Verified capability:

`python -m coin.public_testnet_service_demo --role provider --port 28429`

Service:

`l28.service.structured_text_analysis/v0.1`

Network identity:

`L28-DISPOSABLE-PUBLIC001`

Verified public path:

- Surface requester on a separate internet connection
- public endpoint `https://remaining-successful-springs-new.trycloudflare.com`
- ephemeral Cloudflare Quick Tunnel
- Mac provider bound only to `127.0.0.1:28429`

Provider evidence:

- `coordination=provider_evidence`
- `public_testnet=true`
- `canonical_validation=PASS`
- payment tx id `c95bbee5d1e9b5d8dadf66db319099f2930bd7edc624335f3a0f4e2beec579d2`
- balances 100/0 → 72/28
- `payment_applied=true`
- `payment_verified=true`
- `replay_rejected=true`
- `service_executed=true`
- `receipt_created=true`
- `bounded_provider_shutdown=true`
- canonical history untouched
- historical state not imported
- no production keys
- no mining
- no canonical broadcast
- no production settlement

The Surface requester completed the same public HTTPS transaction and showed the same payment tx id. That command completes only after the existing quote, payment, result, and receipt verification flow.

Automated verification after the provider-evidence change:

- focused tests: 7 passed
- affected regressions: 72 passed

Actual-product verification: PASS

Security review: PASS

Unresolved Critical/High findings: 0

Identity-module authorization flags stay false. Protocol v1.0.0 and protected economics are unchanged.

Slice result:

PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED

The Public Testnet frozen slice reached its STOP condition and is published on remote main at commit `3fa23117aafbc1ee78c7bec0e52259008a2783ff`.

## COMPLETED DURABLE RUNTIME SLICE
The Production Entry — Durable Restart-Safe Paid AI Service slice reached its STOP condition and is published on remote main at commit `c0f5467bb2f58a2f59a47cbc2920dcb2e5b3f1a6`.

## COMPLETED HARDENING SLICE
The Production Runtime Hardening / Fault Recovery slice reached its STOP condition and is published on remote main at commit `02974da1c300f18f293980c6fec035f553e87c1f`.

## CURRENT FROZEN SLICE
`FROZEN_SLICE L28.md`

Slice:

**Isolated Non-Production Signer Runtime**

Status:

PASS / ACTUAL-PRODUCT VERIFIED

Baseline:

`6dc5c4bbdf33ee94a952afdc7301ff10192bac1c`

A separate localhost process holds one disposable signing key. The payment process has no signing key. It still uses canonical validation and the durable exactly-once store.

Run 1 payment `eab61398b14764be20044ac4f0c32a8d4f1b1da60626d2f79c73b808061557c5` moved balances 100/0 to 72/28. The result and receipt verified.

The payment process stopped and restarted against the same signer and the same state directory. Replay of that payment was rejected. Balances stayed 72/28.

Run 3 payment `844b6e882adc77846ee2deb2fbb0b093e68c1610625d9edde46a7bc467eea877` paid the same signer identity, moving that provider balance from 28 to 56 and the requester from 72 to 44.

The signer process did not write the key. Production signer gates stayed closed.

Focused tests: 3 passed. Affected regressions: 103 passed.

Security review: PASS. Unresolved Critical/High findings: 0.

`CUSTODY_READINESS=UNRESOLVED`

`RUNTIME_HARDENING=UNRESOLVED`

`FAULT_RECOVERY=UNRESOLVED`

`F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED`

`SIGNER_RUNTIME_ACTIVE=false`

Signing, canonical broadcast, mining, and production settlement stay false.

## PRIOR HARDENING SLICE
Slice:

**Production Runtime Hardening and Fault Recovery**

Status:

PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED

The Production Runtime Hardening / Fault Recovery slice reached its STOP condition and is published on remote main at commit `02974da1c300f18f293980c6fec035f553e87c1f`.

Baseline:

`b3c5dd1f0321e07c12ac874311b47d912ff7e9e4`

The disposable payment runtime now rejects a world-readable state file, a group-accessible state directory, a rolled-back database inside the same directory, a corrupt audit chain, an older payment timestamp, and an over-nested request. A real process still completes the 28 L28 purchase, rejects the replay after restart, and completes a second fresh payment.

Run 1 payment `103c4f35033ba784488b2b9e1b81dcff4415ef621cf7054b1444f1bf0e1024dd` moved balances 100/0 to 72/28.

Run 2 rejected that same payment. Balances stayed 72/28.

Run 3 payment `3c8cf49e8f6e7efa59d95872eda0e738ecffcb241f21c5cb2a962950ec8c4650` completed. The original provider balance stayed 28.

Real process probes rejected `permissions_invalid`, `stale_state`, and `corrupt_state` before any service execution.

Focused tests: 13 passed. Affected regressions: 116 passed.

Security review: PASS. Unresolved Critical/High findings: 0.

This does not resolve the production signer gates. Replacing every file in the state directory together is still outside this slice. No production rate, skew, or topology values were invented.

`CUSTODY_READINESS=UNRESOLVED`

`RUNTIME_HARDENING=UNRESOLVED`

`FAULT_RECOVERY=UNRESOLVED`

`F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED`

`SIGNER_RUNTIME_ACTIVE=false`

Signing, canonical broadcast, mining, and production settlement stay false.

## DURABLE RUNTIME EVIDENCE
Slice:

**Production Entry — Durable Restart-Safe Paid AI Service**

Status:

PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED

The Production Entry — Durable Restart-Safe Paid AI Service slice reached its STOP condition and is published on remote main at commit `c0f5467bb2f58a2f59a47cbc2920dcb2e5b3f1a6`.

Baseline:

`d3f533b5b4e1b60d9f96ba925d08699fc247ae2d`

A real provider process completed one disposable 28 L28 purchase, stopped, and restarted on the same state directory. The original payment was rejected as a replay. A second fresh disposable payment then completed.

Run 1 payment `896222f3a3e07752e91ad9dd1b2f1edec4897b15e8b19505b6eebbad5e939b1e` moved balances 100/0 to 72/28. Canonical validation passed. The result and receipt verified. Durable state version became 1.

Run 2 reopened that state at restart generation 2. The same payment was rejected. Balances stayed 72/28. The service did not run again.

Run 3 payment `5a008e8e2ee662c2f9079a19e7fccb0700438d8a45e2369ecab9a354f15d08ad` moved the same requester from 72 to 44 and a new disposable provider from 0 to 28. The original provider balance stayed 28. The result and receipt verified.

Focused tests: 10 passed. Affected regressions: 58 passed.

Security review: PASS. Unresolved Critical/High findings: 0.

This is local disposable runtime evidence. It is not canonical settlement finality.

`CUSTODY_READINESS=UNRESOLVED`

`RUNTIME_HARDENING=UNRESOLVED`

`FAULT_RECOVERY=UNRESOLVED`

`F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED`

`SIGNER_RUNTIME_ACTIVE=false`

Signing, canonical broadcast, mining, and production settlement stay false.

## NEXT AFTER THIS SLICE
**Production signing, deployment, and settlement**

Status:

NOT AUTHORIZED / NOT STARTED

Do not automatically start production signer/custody, deployment, exchange/listing/liquidity, or REA/Bitcoin/BTCPay work.

## SOURCE-OF-TRUTH RULE
This file records current verified project state.

Update after every completed frozen slice.

Repository/files are authoritative.

Do not treat chat memory as authoritative implementation state.
