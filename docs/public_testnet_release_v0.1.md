# L28 Public-Testnet Release Candidate v0.1

Release candidate: `l28-public-testnet-v0.1.0-rc1`

Designation: **NON-PRODUCTION DISPOSABLE TESTNET**

Source parent: `b2674aff02f67da002442a87f3ff739c73563d11`

This candidate exposes one disposable service transaction:

`DISCOVER → REQUEST → QUOTE 28 L28 → PAY → VERIFY → WORK → RECEIPT`

It does not configure a public endpoint, authorize deployment, grant production
signer eligibility, or use canonical history, production custody, mining,
broadcast, or settlement.

## Local executable example

From the repository root with `requirements-m2m.txt` already installed:

```sh
python -m coin.public_testnet_service_demo \
  --role local-example \
  --input "L28 enables machine payments between autonomous systems."
```

The command starts an ephemeral loopback provider, performs discovery before
creating the disposable payer, completes the one-shot purchase through the real
HTTP/JSON handler, verifies the result and signed receipt, confirms replay
rejection, shuts the provider down, and emits one JSON evidence object. It does
not contact an external network.

Required evidence fields include:

- `service_discovery_verified: true`
- `quoted_amount: 28`
- `canonical_validation: "PASS"`
- `payment_verified: true`
- `replay_rejected: true`
- `service_result_verified: true`
- `receipt_verified: true`
- `public_network_used: false`
- `production_settlement: false`

## HTTP/JSON interface

A separately authorized operator may run the one-shot provider on loopback:

```sh
python -m coin.public_testnet_service_demo --role provider --port 28429
```

The provider deliberately binds only to `127.0.0.1`. Public access requires a
separately authorized HTTPS ingress that forwards these exact routes without
rewriting their bodies:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/v1/l28/public-testnet/services` | Machine-readable catalog |
| `GET` | `/v1/l28/public-testnet/provider_hello` | One-shot provider identity |
| `POST` | `/v1/l28/public-testnet/session` | Request, quote, payment, result, and receipt frames |

Given an operator-supplied HTTPS origin, inspect discovery without starting a
session:

```sh
L28_PUBLIC_ENDPOINT=https://operator-supplied.example
curl --fail --silent --show-error \
  "$L28_PUBLIC_ENDPOINT/v1/l28/public-testnet/services"
```

The catalog must contain exactly one
`l28.service.structured_text_analysis/v0.1` service priced at 28 disposable
L28, `max_input_chars: 4096`, the `L28-DISPOSABLE-PUBLIC001` network binding,
the three paths above, and `production_authority: false`.

Run the requester only against an explicitly authorized public HTTPS origin:

```sh
python -m coin.public_testnet_service_demo \
  --role requester \
  --public-endpoint "$L28_PUBLIC_ENDPOINT" \
  --input "L28 enables machine payments between autonomous systems."
```

The requester rejects HTTP, localhost, LAN, missing, malformed, duplicate-key,
inconsistent, type-substituted, or tampered discovery before provider hello,
request, quote, payment, work, result, or receipt processing. The provider is
one-shot and shuts down after one completed payment flow.

No public HTTPS origin is supplied, live, or authorized by this release
candidate.

## Existing MCP adapter: local stdio only

The existing MCP adapter is a separate local process interface:

```sh
python -m coin.two_agent_service_external_access_demo --runtime mcp
```

It accepts newline-delimited JSON-RPC 2.0 on stdin and writes responses to
stdout. Its only tool is `l28_purchase_structured_text_analysis`; call arguments
are exactly `service_id` and `input`. It executes the existing local disposable
purchase core. It is not a networked MCP server, does not use the public-testnet
discovery endpoint, and does not prove public reachability.

Minimal message sequence:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"l28_purchase_structured_text_analysis","arguments":{"service_id":"l28.service.structured_text_analysis/v0.1","input":"L28 enables machine payments between autonomous systems."}}}
```

## Reproducible package

Verify the SHA-256 inventory from the repository root:

```sh
shasum -a 256 -c release/public-testnet-v0.1.0-rc1/SHA256SUMS
```

`manifest.json` binds the release identity, non-production boundary, transport
claims, service contract, and authorized release artifacts. `SHA256SUMS` also
binds the manifest itself.

## Exposure boundary and rollback

Public exposure is a separate operator gate. Before any exposure, the operator
must supply and approve the public hostname, HTTPS termination, exact route
forwarding, process supervision, rate and resource limits, monitoring, and the
one-shot restart policy. None is created here.

Rollback for a separately authorized exposure is operational and fail-closed:

1. Remove or disable the external ingress routes.
2. Stop the loopback provider process.
3. Verify the public discovery, hello, and session paths are unreachable.
4. Preserve the release evidence and logs; no canonical chain rollback is
   required because this candidate cannot touch canonical history or production
   settlement.

## Residual risks

- The provider and payer identities are disposable and process-local.
- The provider is one-shot, with no durability or availability guarantee.
- Public ingress controls, abuse resistance, observability, and operations are
  outside this candidate and require separate authorization and verification.
- EVD-001 is not integrated and its independent qualified review remains
  outstanding.
- Production custody, F171 signer eligibility, and all production gates remain
  blocked.
