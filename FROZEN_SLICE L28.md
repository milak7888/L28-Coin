# L28 — FROZEN_SLICE.md

Date: 2026-09-30
PROJECT_STATE: ACTIVE
Slice: Isolated Local Network — Two-Process Paid Service Transaction

## OBJECTIVE

Move the already-working L28 paid-service flow across a real bounded local
network boundary between two separate agent processes.

Target:

AGENT A PROCESS (requester / payer)
→ TCP over IPv4 loopback
→ AGENT B PROCESS (provider / payee)
→ request
→ quote for 28 L28
→ signed disposable payment
→ canonical validation + ledger application in Agent B
→ payment verification
→ useful structured-text work
→ signed result + machine-readable receipt
→ returned across the same isolated local network
→ Agent A verifies result + receipt

This slice must create a new runnable capability. It must not merely repeat prior
loopback transport evidence.

## BASELINE

Verified remote `main` at slice start:

`b64dad0dbc14c7a5732fcc1b9ff34079152b38b2`

Already published capabilities to reuse:

- `coin/disposable_offline_transfer_demo.py`
- `coin/two_agent_service_transaction_demo.py`
- `coin/two_agent_service_external_access_demo.py`
- `coin/cross_ai_interoperability_demo.py`

Existing repository networking/security components may be reused for defensive
patterns where applicable:

- `coin/disposable_testnet_p2p_conformance.py`
- `coin/disposable_testnet_two_agent_gate.py`
- `coin/disposable_testnet_option_a_policy.py`
- `coin/foundation168_bounded_runtime_driver.py`

Prior one-shot loopback experiments do NOT constitute persistent authorization
for this slice. This frozen slice is the new bounded authorization.

Prior experiments that only proved HELLO/TIP/CANDIDATE transport, reconnect, or
replay behavior do NOT satisfy this slice because they did not execute the
current paid useful-service transaction across the network.

## ONE SERVICE

Exactly one service remains in scope:

`l28.service.structured_text_analysis/v0.1`

Input:

- caller-supplied text

Output remains the existing deterministic structured result including:

- `character_count`
- `word_count`
- `unique_word_count`
- `sentence_count`
- `top_terms`
- `input_digest`

No additional service is added.

## NETWORK SCOPE

Exactly two child agent processes on one machine:

- Agent A = requester / payer
- Agent B = provider / payee

Transport:

- TCP
- IPv4 only
- `127.0.0.1` only
- no LAN bind
- no `0.0.0.0`
- no hostname/DNS dependency
- no public route
- no external connection
- one bounded transaction session
- provider listener uses loopback only
- ephemeral local port is preferred to avoid fixed-port conflicts
- parent process may coordinate startup/port handoff only
- purchase/request/quote/payment/result/receipt data MUST cross the TCP boundary,
  not a multiprocessing pipe/queue or direct function call between agents

The parent/orchestrator may collect final sanitized evidence from child
processes after the transaction, but it must not carry the business transaction
between Agent A and Agent B.

## AUTHORIZATION

The operator authorization:

`AUTHORIZE NEXT FROZEN SLICE: L28 ISOLATED LOCAL NETWORK`

authorizes only the bounded isolated local networking required by this slice:

- create/start exactly two local child agent processes
- open one IPv4 loopback TCP listener for Agent B
- connect Agent A to that loopback listener
- exchange the bounded service-transaction frames required for one transaction
- close sockets
- terminate both child processes
- perform focused tests and actual-product verification

This authorization does NOT authorize:

- LAN networking
- internet/public networking
- persistent P2P service
- testnet
- public testnet
- production networking
- external provider APIs
- deployment
- production settlement

## AGENT OWNERSHIP

### Agent A — requester / payer

Agent A must own its disposable payer private key in its own process.

Agent A:

1. generates a fresh disposable Ed25519 payer key in memory
2. receives Agent B's public provider identity over the loopback session
3. builds/signs the existing L28 service request
4. sends the request over TCP
5. receives/verifies Agent B's signed quote
6. builds/signs the existing 28 L28 disposable payment
7. builds/signs the existing payment authorization
8. sends payment transaction + authorization over TCP
9. receives service result + receipt over TCP
10. verifies result and receipt using public material
11. reports only public/sanitized evidence
12. destroys process-local ephemeral key material on process exit

Agent A must never receive Agent B's private key.

### Agent B — provider / payee

Agent B must own its disposable provider private key in its own process.

Agent B:

1. generates a fresh disposable Ed25519 provider key in memory
2. opens the bounded loopback listener
3. publishes only its public identity needed for the request
4. receives/verifies Agent A's signed service request
5. builds/signs the existing quote for exactly 28 L28
6. sends the quote over TCP
7. receives the signed payment transaction + payment authorization
8. creates the isolated disposable ledger state:
   - payer = 100
   - provider = 0
9. passes the payment through the existing canonical validation path
10. applies the payment through the existing `BlocklessLedger` path
11. independently verifies accepted payment and exact binding
12. executes useful work only after payment verification
13. builds/signs the existing service result
14. builds/signs the existing machine-readable receipt
15. sends result + receipt over TCP
16. reports only public/sanitized evidence
17. destroys process-local ephemeral key material on process exit

Agent B must never receive Agent A's private key.

## CORE REUSE — NO SECOND PAYMENT SYSTEM

Reuse the existing transaction primitives from the published two-agent
transaction wherever applicable, including existing functions for:

- signed service request
- request verification
- signed quote
- quote verification
- disposable signed transfer construction
- payment authorization
- payment-intent binding
- canonical transaction classification
- `BlocklessLedger` application
- accepted-payment verification
- paid-service execution gate
- service-result construction/verification
- receipt construction/verification

Canonical validator remains:

`coin.tx_validation.validate_transaction`

Do NOT create:

- a second validator
- a second payment engine
- a second ledger authority
- a network-specific definition of settlement
- a network-specific quote amount
- alternate receipt semantics

Transport success is not payment validity.

## PAYMENT

Price remains exactly:

`28 L28`

Agent B's disposable ledger must begin:

- Agent A = 100
- Agent B = 0

After exactly one accepted payment:

- Agent A = 72
- Agent B = 28

The accepted transaction must:

- be signed by Agent A's disposable key
- target Agent B's disposable identity
- bind to the request and quote through the existing payment authorization
- pass the canonical validator
- be applied through `BlocklessLedger`
- have a canonical transaction id
- be present in Agent B's disposable ledger state
- be accepted exactly once

No canonical historical balance, issuance, supply, or height is changed.

## APPLICATION TRANSPORT

Implement one strict bounded application framing format for the networked
service transaction.

The frame must be machine-readable and bounded.

At minimum each frame must bind:

- transport profile/version
- message type
- sequence number
- payload

Allowed message sequence:

1. `provider_hello`
2. `service_request`
3. `service_quote`
4. `payment_package`
5. `service_result_package`

`payment_package` contains only the existing public signed payment transaction
and payment authorization artifacts.

`service_result_package` contains only the existing service result and receipt
artifacts.

Requirements:

- deterministic JSON encoding
- bounded maximum frame size
- exact allowed message types
- exact expected ordering
- duplicate/out-of-order messages fail closed
- malformed JSON fails closed
- oversized frame fails closed
- unknown transport profile/version fails closed
- unexpected extra fields fail closed
- timeouts are bounded
- EOF/disconnect before completion fails closed
- no caller-controlled filesystem path
- no caller-controlled command execution

Do not create a blockchain P2P synchronization protocol in this slice.

## NETWORK / CONSENSUS BOUNDARY

This slice transports one paid service transaction only.

It does NOT perform:

- block propagation
- chain synchronization
- candidate-history import
- fork choice
- automatic reorg
- confirmation policy changes
- canonical-height selection
- peer-selected canonical history
- mining

Existing Option A conflict/reorg safety policy remains untouched and outside the
service-transaction execution path.

Peer/network data has zero authority to alter:

- issuance
- supply
- canonical height
- Protocol validation rules
- canonical history
- protected economics

## ACTUAL-PRODUCT COMMAND

Preferred command:

`python -m coin.isolated_local_network_service_demo --input "L28 enables machine payments between autonomous systems."`

The command must visibly exercise the actual product:

1. parent creates bounded execution context
2. Agent B process starts
3. Agent B binds a loopback TCP listener
4. parent receives only startup/port coordination evidence
5. Agent A process starts
6. Agent A connects through TCP
7. request crosses TCP A→B
8. quote crosses TCP B→A
9. signed payment package crosses TCP A→B
10. Agent B validates/applies/verifies payment
11. Agent B performs useful work
12. result + receipt cross TCP B→A
13. Agent A verifies result + receipt
14. both sockets close
15. both child processes terminate
16. parent emits one machine-readable evidence summary

A same-process direct function call cannot satisfy actual-product verification.

## NEGATIVE CASES

At minimum automated tests must prove:

1. non-loopback bind configuration is impossible/rejected
2. unknown transport profile/version rejected
3. unknown message type rejected
4. out-of-order message rejected
5. duplicate sequence/message rejected
6. malformed JSON rejected
7. oversized frame rejected
8. truncated/disconnected frame rejected
9. wrong provider identity binding rejected
10. wrong amount rejected
11. wrong payer/payee rejected
12. quote/payment mismatch rejected
13. invalid payment signature rejected
14. payment replay rejected
15. service does not execute before verified payment
16. tampered service result rejected
17. tampered receipt rejected
18. failed/rejected network flow does not report successful receipt/work
19. rejected payment does not create extra balance movement
20. both child processes are cleaned up after success
21. both child processes are cleaned up after failure

Existing core negative tests remain authoritative and must continue to pass.

## PROCESS / RESOURCE SAFETY

Execution must be bounded.

Required:

- exactly two child agent processes
- one Agent B listener
- one Agent A connection
- one transaction
- finite socket timeouts
- finite parent deadline
- no retry loop
- cleanup in success and failure paths
- parent verifies both children terminal before PASS
- sockets closed before PASS
- no daemon/persistent background process left running

A reasonable maximum whole-demo duration is 30 seconds unless implementation
evidence requires a smaller deterministic bound.

Do not convert this slice into a persistent node/service.

## ALLOWED SCOPE

- exactly two local child agent processes
- IPv4 loopback TCP only
- one provider listener
- one requester connection
- ephemeral loopback port
- strict bounded JSON framing
- startup-only parent/child coordination
- disposable in-memory Ed25519 keys inside their owning processes
- disposable temporary ledger/data directory
- existing transaction/validation/receipt primitives
- focused transport tests
- affected regressions
- actual-product network verification
- observable evidence
- one consolidated security review
- one commit/local fast-forward merge/pre-push verification
- system-state update

## EXPLICITLY NOT ALLOWED

- `0.0.0.0` binding
- LAN interfaces
- internet/public networking
- outbound external network calls
- peer discovery
- UPnP/NAT traversal
- persistent P2P daemon
- public RPC
- public HTTP/MCP endpoint
- limited testnet
- public testnet
- production network
- live OpenAI/Anthropic/Gemini/Grok/DeepSeek APIs
- provider credentials/API keys
- wallet files
- production private keys/seeds/mnemonics/xprv
- `.env`/secret scanning
- keychain/browser/SSH/Bitcoin Core secret access
- mining
- production broadcast
- production settlement
- canonical history mutation
- protected economics changes
- Protocol v1.0 normative changes
- new fork-choice/reorg/finality policy
- marketplace
- exchange/listing/liquidity work
- deployment
- unrelated refactors/frameworks/governance

## ACTUAL-PRODUCT EVIDENCE

Expected successful summary includes at minimum:

```text
demo_profile=l28-isolated-local-network-service/v0.1
agent_process_count=2
distinct_agent_processes=true
network_transport=tcp_ipv4_loopback
provider_bound_host=127.0.0.1
external_network_used=false

provider_hello_crossed_network=true
service_request_crossed_network=true
service_quote_crossed_network=true
payment_package_crossed_network=true
service_result_package_crossed_network=true

request_verified=true
quote_verified=true
quoted_amount=28
payment_tx_id=<64hex>
canonical_validation=PASS
payment_applied=true
payment_verified=true
agent_a_balance_before=100
agent_b_balance_before=0
agent_a_balance_after=72
agent_b_balance_after=28

service_executed=true
service_result_verified=true
receipt_created=true
receipt_verified=true

both_processes_terminal=true
sockets_closed=true
canonical_history_touched=false
public_network_used=false
production_keys_used=false
production_settlement=false
```

The evidence may contain additional bounded public fields.

## AUTOMATED TESTS

Focused tests must cover:

- frame encode/decode bounds
- strict message sequencing
- malformed/oversized/truncated rejection
- loopback-only bind enforcement
- Agent A request/payment construction
- Agent B quote/payment verification
- canonical validator path invocation
- ledger exactly-once application
- result/receipt return and verification
- failure-before-payment means no work
- replay rejection
- process cleanup
- no private-key serialization/output
- no external-network configuration
- no duplicate validator/payment engine

Affected regressions must include at minimum:

- `tests/test_disposable_offline_transfer_demo.py`
- `tests/test_two_agent_service_transaction_demo.py`
- `tests/test_two_agent_service_external_access.py`
- `tests/test_cross_ai_interoperability_demo.py`

If the implementation reuses or modifies existing disposable-testnet/P2P
components, include their directly affected tests.

Do not run unrelated full-suite tests without a concrete dependency/failure
reason.

## SECURITY REVIEW

Perform one consolidated review after actual-product verification.

Confirm:

- loopback-only TCP binding
- exactly two agent child processes
- no external route/connection
- no persistent listener after completion
- strict bounded frame parser
- no unbounded read/allocation
- no caller-controlled command execution
- no caller-controlled filesystem path
- no environment/keychain/wallet/secret access
- private keys remain process-local and are never serialized/output
- payer key exists only in Agent A process
- provider key exists only in Agent B process
- payment crosses the network only as public signed transaction data
- existing canonical validator is reused
- existing ledger path is reused
- no alternate settlement definition
- no Protocol/economics/history authority is created
- all children/sockets terminate on success and failure

Any unresolved Critical/High finding blocks the slice.

## ACCEPTANCE CRITERIA

1. Exactly two child agent processes execute the product flow.
2. Agent A is requester/payer.
3. Agent B is provider/payee.
4. Agent B binds only to IPv4 `127.0.0.1`.
5. Agent A connects only to Agent B's loopback listener.
6. No transaction business data is carried by parent IPC/direct calls.
7. Provider public identity crosses the TCP boundary.
8. Signed service request crosses TCP A→B.
9. Agent B verifies the request.
10. Signed 28 L28 quote crosses TCP B→A.
11. Agent A verifies the quote.
12. Signed disposable payment crosses TCP A→B.
13. Payment authorization crosses TCP A→B.
14. Agent B uses the existing canonical validator path.
15. Agent B applies payment through the existing `BlocklessLedger` path.
16. Agent B independently verifies exact payment binding.
17. Payment is accepted exactly once.
18. Disposable balances change 100/0 → 72/28.
19. Useful work executes only after successful payment verification.
20. Structured result crosses TCP B→A.
21. Signed machine-readable receipt crosses TCP B→A.
22. Agent A verifies the result.
23. Agent A verifies the receipt using public material.
24. Deterministic service output is independently recomputable.
25. Invalid signature/replay/wrong amount/wrong party/quote mismatch remain rejected.
26. Malformed/oversized/out-of-order/duplicate transport frames fail closed.
27. Failed/rejected flow does not report successful work/receipt.
28. Rejected cases do not create extra accepted balance movement.
29. Payer private key remains only in Agent A process.
30. Provider private key remains only in Agent B process.
31. No private key material is serialized, logged, returned, or persisted.
32. Both child processes terminate after success.
33. Both child processes terminate after failure.
34. All sockets are closed before PASS.
35. Canonical validator remains `coin.tx_validation.validate_transaction`.
36. No duplicate validator/payment engine is introduced.
37. Protected economics remain unchanged.
38. Canonical history remains untouched.
39. No block/chain sync or reorg behavior is introduced.
40. No public/LAN/external network is used.
41. No production keys are used.
42. No production signing/broadcast/settlement is activated.
43. Focused automated tests pass.
44. Affected regressions pass.
45. Actual networked product verification passes.
46. Observable network/payment/work/receipt evidence is captured.
47. One consolidated security review has no unresolved Critical/High finding.
48. One commit is produced when practical.
49. Local fast-forward merge/pre-push verification passes.
50. `SYSTEM_STATE L28.md` is updated after completion.
51. STOP before limited testnet, public networking, production, deployment, or exchange work.

## MANDATORY COMPLETION GATE

IMPLEMENTATION
→ AUTOMATED TESTS
→ ACTUAL-PRODUCT VERIFICATION
→ EVIDENCE
→ ACCEPTANCE CRITERIA
→ STOP

Tests alone cannot PASS this slice.

## EFFICIENCY / ANTI-LOOP

Use one bounded implementation batch:

inspect
→ implement
→ focused tests once
→ affected regressions once
→ actual two-process loopback transaction
→ evidence
→ one consolidated security review
→ acceptance decision
→ one commit
→ local fast-forward merge
→ pre-push verify
→ request explicit push authorization

Do not create another network readiness/gate/evidence-only milestone.

This slice must change what L28 can actually do:
a paid L28 service transaction must cross a real two-process TCP boundary.

If the same top-level blocker survives two corrective attempts with no new
user-visible capability, declare LOOP_DETECTED and stop.

## STOP CONDITION

STOP immediately after:

- one real Agent A → Agent B paid service transaction succeeds over bounded
  loopback TCP
- the actual payment crosses the network as signed public transaction data
- Agent B canonically validates/applies/verifies payment
- useful work executes
- result + signed receipt return across the network
- Agent A verifies result + receipt
- tests pass
- actual-product verification passes
- observable evidence exists
- security review passes
- all acceptance criteria pass
- one commit/local merge/pre-push verification completes
- system state is updated
- push authorization is requested or, if separately authorized, push is verified

Do not automatically start:

- limited testnet
- public testnet
- LAN/public networking
- persistent P2P service
- production signer/custody
- deployment
- exchange/listing/liquidity work

## PRODUCT QUESTION

YES.

This slice directly moves L28 closer to one independent machine purchasing
useful work from another using L28 by placing the real request/quote/payment/
work/result/receipt flow across a genuine isolated network boundary.
