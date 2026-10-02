# L28 — SYSTEM_STATE.md

Last updated: 2026-10-02

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
5. isolated local network — LOCAL COMPLETION CANDIDATE / PUSH PENDING
6. limited testnet
7. public testnet
8. production

## REPOSITORY
Local: `/Users/pjaydondup/Projects/L28-Coin`
Remote: `https://github.com/milak7888/L28-Coin.git`
Public: `milak7888/L28-Coin`

Last completed product implementation commit before the active isolated-network slice:

`b64dad0dbc14c7a5732fcc1b9ff34079152b38b2`

Commit:

`Add cross-AI L28 interoperability demo`

Parent:

`4016cd180643c515865438575ad603d60b54c6e2`

Changed paths in that commit:

- `coin/cross_ai_interoperability_demo.py`
- `tests/test_cross_ai_interoperability_demo.py`

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

The completed disposable, two-agent, HTTP/MCP, and cross-AI capabilities do NOT make a production signer eligible.

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
Local completion candidate. Push pending. Not yet on remote `main`.

Command:

`python -m coin.isolated_local_network_service_demo --input "L28 enables machine payments between autonomous systems."`

Service:

`l28.service.structured_text_analysis/v0.1`

Verified two-process behavior:

- exactly two child processes, Agent A requester/payer and Agent B provider/payee
- Agent B binds IPv4 `127.0.0.1` only
- provider hello, signed request, signed 28 L28 quote, signed payment package, and signed result/receipt cross TCP
- parent IPC carries startup/port coordination and sanitized evidence only
- Agent B verifies the request, validates payment with `coin.tx_validation.validate_transaction`, and applies it with `BlocklessLedger`
- disposable balances change 100/0 → 72/28
- useful structured-text work runs only after payment verification
- Agent A verifies the result and signed receipt
- both child processes terminate and sockets close
- canonical history remains untouched
- no public/LAN network, production keys, or production settlement

Actual-product evidence:

- `demo_profile=l28-isolated-local-network-service/v0.1`
- `agent_process_count=2`
- `distinct_agent_processes=true`
- `network_transport=tcp_ipv4_loopback`
- `provider_bound_host=127.0.0.1`
- `canonical_validation=PASS`
- `payment_applied=true`
- `payment_verified=true`
- `agent_a_balance_before=100`
- `agent_b_balance_before=0`
- `agent_a_balance_after=72`
- `agent_b_balance_after=28`
- `service_executed=true`
- `service_result_verified=true`
- `receipt_created=true`
- `receipt_verified=true`
- `both_processes_terminal=true`
- `sockets_closed=true`
- `canonical_history_touched=false`
- `public_network_used=false`
- `production_keys_used=false`
- `production_settlement=false`

Automated verification:

- focused isolated-network tests: 10 passed
- affected regressions: 41 passed

Consolidated security review:

- loopback-only TCP: PASS
- exactly two child agent processes: PASS
- no unresolved Critical/High finding

Parent of this local slice:

`91297fabd134b196049204f2b4d966f98bd139dc`

Status:

LOCAL COMPLETION CANDIDATE / PUSH PENDING

## CURRENT FROZEN SLICE
`FROZEN_SLICE L28.md`

Slice:

**Isolated Local Network — Two-Process Paid Service Transaction**

Status:

LOCAL COMPLETION CANDIDATE / PUSH PENDING

The bounded two-process loopback purchase has been implemented and verified locally. It is not published. Limited testnet, LAN/public networking, production keys, production settlement, deployment, and exchange work remain unauthorized.

## NEXT AFTER COMPLETED SLICE
If the active isolated-local-network slice completes and stops, the next
recorded product stage is:

**Limited testnet**

Status:

NOT AUTHORIZED / NOT STARTED

Do not automatically start:

- limited testnet
- public testnet
- LAN/public networking
- persistent P2P runtime
- production signer/custody
- deployment
- exchange/listing/liquidity work

A new frozen slice and any required operator authorization are required first.

## SOURCE-OF-TRUTH RULE
This file records current verified project state.

Update after every completed frozen slice.

Repository/files are authoritative.

Do not treat chat memory as authoritative implementation state.
