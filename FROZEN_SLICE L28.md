# L28 — FROZEN_SLICE.md

Date: 2026-10-04
PROJECT_STATE: ACTIVE
Slice: Limited Testnet — Two-Node Private-Network Paid Service

## OBJECTIVE

Move the published L28 paid structured-text service from same-machine loopback to two distinct, explicitly configured private IPv4 endpoints.

Requester node
→ private RFC1918 network
→ Provider node
→ signed service request
→ signed quote for exactly 28 L28
→ signed disposable payment
→ canonical validation
→ BlocklessLedger application
→ payment verification
→ structured-text work
→ signed result
→ signed receipt
→ requester verifies result and receipt

## BASELINE

`93b61bbf9e515ef4e68acb56fe02a5a3fb34a962`

Operator authorization:

`AUTHORIZE NEXT FROZEN SLICE: L28 LIMITED TESTNET`

This authorization covers only this bounded experiment. It does not change `RUNTIME_AUTHORIZED`, `NETWORK_AUTHORIZED`, `TESTNET_START_AUTHORIZED`, `SIGNING_AUTHORIZED`, `MINING_AUTHORIZED`, `BROADCAST_AUTHORIZED`, or `SETTLEMENT_AUTHORIZED`.

## NETWORK

Allowed private IPv4 only:

- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`

Reject loopback, loopback aliases, `0.0.0.0`, public IPs, peer discovery, multicast, broadcast discovery, UPnP, and NAT traversal.

Peer addresses are explicit. The two endpoints must be distinct. Loopback evidence does not satisfy this slice.

If two distinct RFC1918 endpoints are not already available, stop with:

`BLOCKER=DISTINCT_PRIVATE_TESTNET_ENDPOINT_UNAVAILABLE`

Do not install virtualization or download images to manufacture an endpoint.

## TESTNET IDENTITY

Reuse `coin.disposable_testnet_identity.validate_and_bind_disposable_testnet_config`.

- `network_id=L28-DISPOSABLE-LIMITED001`
- `data_dir_tag=l28-disposable-testnet:limited001`
- initial height 0
- issued supply 0
- no historical checkpoint
- no historical balances
- protected economics unchanged
- production keys forbidden

## PAYMENT AND SERVICE

Price remains 28 L28. Disposable balances move 100/0 → 72/28.

Reuse the existing request, quote, payment authorization, signed transfer, `coin.tx_validation.validate_transaction`, `BlocklessLedger`, and result/receipt semantics.

Service remains `l28.service.structured_text_analysis/v0.1`.

Every frame binds profile/version, network id, genesis hash, config hash, message type, sequence, and payload, in this order:

1. `provider_hello`
2. `service_request`
3. `service_quote`
4. `payment_package`
5. `service_result_package`

Fail closed on wrong network, wrong genesis/config hash, wrong peer, malformed or oversized or truncated frames, wrong or duplicate or out-of-order sequence, timeout, wrong amount, wrong payer or payee, invalid signature, replay, and tampered result or receipt.

## STOP

Stop after one bounded experiment. Do not start public testnet, production, deployment, or exchange work.

Do not substitute `127.0.0.1` for a missing private endpoint.

## ACCEPTANCE

Status: STOP CONDITION REACHED

- IMPLEMENTATION PASS
- AUTOMATED TESTS PASS
- ACTUAL-PRODUCT VERIFICATION PASS
- EVIDENCE PASS
- ACCEPTANCE CRITERIA PASS

Verified endpoints:

- requester `192.168.1.129`
- provider `192.168.1.138:28428`

Payment tx id:

`cf1e700befd46e413218af74120f1edbb3140c11a830b0078ca8d52d5881a537`

Balances moved 100/0 → 72/28. The result and receipt verified. A duplicate payment was rejected as replay and did not change those balances. Canonical history was not touched. No public network, production keys, mining, broadcast, or production settlement was used.
